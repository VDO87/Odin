"""Read-only MT5/OANDA TMS M1 import with explicit, fail-closed gap quality.

This module deliberately has no MetaTrader5 dependency.  The Windows launcher
performs the allowed read-only API calls and passes plain rate/tick evidence
here, keeping validation and persistence reproducible on every platform.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from odin.contracts.historical_candles import CANONICAL_CANDLE_COLUMNS, CANONICAL_CANDLE_SCHEMA_VERSION
from odin.data.canonical_candle_history import canonical_dataset_hash, import_canonical_candle_history

PROVIDER = "OANDA TMS Brokers S.A."
PLATFORM = "MetaTrader 5"
SERVER = "OANDATMS-MT5"
LICENSE_ID = "NOT_EXPLICITLY_STATED"
USAGE_BASIS = "local_internal_ODIN_validation_replay_only_no_redistribution"
TERMS_REFERENCES = [
    "https://help.oanda.com/eu/en/faqs/mt5-user-guide-eu.htm",
    "https://www.oanda.com/eu-en/legal/",
]

class Mt5OandaHistoryError(ValueError):
    pass

def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise Mt5OandaHistoryError("mt5_oanda_timestamp_not_utc")
    return value.astimezone(UTC).replace(microsecond=0)

def _stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat().replace("+00:00", "Z")

def normalize_m1_rates(rates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Losslessly retain the MT5 fields needed for raw provenance and quality."""
    result: list[dict[str, Any]] = []
    previous = -1
    for rate in rates:
        try:
            ms = int(rate["time"]) * 1000 if int(rate["time"]) < 10**12 else int(rate["time"])
            candle = {"timestamp_ms": ms, "open": float(rate["open"]), "high": float(rate["high"]), "low": float(rate["low"]), "close": float(rate["close"]), "tick_volume": int(rate.get("tick_volume", 0)), "spread": int(rate.get("spread", 0)), "real_volume": int(rate.get("real_volume", 0))}
        except (KeyError, TypeError, ValueError) as error:
            raise Mt5OandaHistoryError("mt5_oanda_raw_rate_invalid") from error
        if ms % 60000 or ms <= previous or not all(math.isfinite(candle[x]) for x in ("open", "high", "low", "close")) or candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]) or min(candle["tick_volume"], candle["spread"], candle["real_volume"]) < 0:
            raise Mt5OandaHistoryError("mt5_oanda_raw_rate_invalid")
        previous = ms; result.append(candle)
    if not result: raise Mt5OandaHistoryError("mt5_oanda_raw_empty")
    return result

def classify_gaps(candles: list[dict[str, Any]], *, start_utc: datetime, end_utc: datetime, tick_counts: dict[tuple[int, int], int]) -> list[dict[str, Any]]:
    """Classify absence, never repair it. Tick evidence is mandatory off-weekend."""
    start, end = _utc(start_utc), _utc(end_utc)
    if start >= end or candles[0]["timestamp_ms"] != int(start.timestamp() * 1000):
        raise Mt5OandaHistoryError("mt5_oanda_period_start_incomplete")
    edges = [(candles[i]["timestamp_ms"] + 60000, candles[i + 1]["timestamp_ms"]) for i in range(len(candles) - 1)]
    # The requested end is an exclusive query boundary.  The observed end is
    # recorded separately; only internal discontinuities are quality gaps.
    gaps=[]
    for left, right in edges:
        if right <= left: continue
        prior = datetime.fromtimestamp((left - 60000) / 1000, UTC)
        classification = "EXPECTED_GAP" if prior.weekday() == 4 and datetime.fromtimestamp(right / 1000, UTC).weekday() == 6 else None
        if classification is None:
            if (left, right) not in tick_counts: raise Mt5OandaHistoryError("mt5_oanda_gap_tick_evidence_missing")
            classification = "NO_TICK_GAP" if tick_counts[(left, right)] == 0 else "SUSPICIOUS_GAP"
        gaps.append({"start_utc": _stamp(left), "end_utc": _stamp(right), "duration_seconds": (right-left)//1000, "classification": classification, "tick_count": tick_counts.get((left, right))})
    return gaps

def aggregate_complete_m15(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for candle in candles: groups.setdefault(candle["timestamp_ms"] - candle["timestamp_ms"] % 900000, []).append(candle)
    result=[]
    for window, group in sorted(groups.items()):
        expected=[window + i*60000 for i in range(15)]
        if [c["timestamp_ms"] for c in group] != expected: continue
        result.append({"timestamp_ms":window,"open":group[0]["open"],"high":max(c["high"] for c in group),"low":min(c["low"] for c in group),"close":group[-1]["close"],"volume":sum(c["tick_volume"] for c in group)})
    if not result: raise Mt5OandaHistoryError("mt5_oanda_m15_empty")
    return result

def _m15_exceptions(m15: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> list[dict[str, str]]:
    exceptions=[]
    for before, after in zip(m15, m15[1:]):
        if after["timestamp_ms"] - before["timestamp_ms"] == 900000: continue
        start, end = before["timestamp_ms"] + 900000, after["timestamp_ms"]
        overlaps=[gap for gap in gaps if int(datetime.fromisoformat(gap["end_utc"].replace("Z","+00:00")).timestamp()*1000)>start and int(datetime.fromisoformat(gap["start_utc"].replace("Z","+00:00")).timestamp()*1000)<end]
        if not overlaps or any(g["classification"] not in {"EXPECTED_GAP","NO_TICK_GAP"} for g in overlaps): raise Mt5OandaHistoryError("mt5_oanda_m15_gap_unexplained")
        classes={g["classification"] for g in overlaps}
        exceptions.append({"from_utc":_stamp(before["timestamp_ms"]),"to_utc":_stamp(after["timestamp_ms"]),"classification":"EXPECTED_GAP" if classes=={"EXPECTED_GAP"} else "NO_TICK_GAP"})
    return exceptions

def import_mt5_oanda_tms_m1(*, rates: Iterable[dict[str, Any]], start_utc: datetime, end_utc: datetime, acquired_at: datetime, artifact_root: str | Path, tick_counts: dict[tuple[int,int], int], terminal_version: str | None = None, runtime_version: str | None = None) -> dict[str, object]:
    """Validate first, then persist immutable M1 RAW and its validated M15 derivative."""
    start, end, acquired = _utc(start_utc), _utc(end_utc), _utc(acquired_at)
    m1=normalize_m1_rates(rates); gaps=classify_gaps(m1,start_utc=start,end_utc=end,tick_counts=tick_counts)
    if any(g["classification"] in {"SUSPICIOUS_GAP","INVALID_GAP"} for g in gaps): raise Mt5OandaHistoryError("mt5_oanda_quality_blocked")
    m15=aggregate_complete_m15(m1); m15_exceptions=_m15_exceptions(m15,gaps)
    raw_lines=[json.dumps({**c,"timestamp_utc":_stamp(c["timestamp_ms"])},sort_keys=True,separators=(",",":")) for c in m1]
    raw_blob=("\n".join(raw_lines)+"\n").encode(); raw_hash=hashlib.sha256(raw_blob).hexdigest()
    expected_minutes=int((end-start).total_seconds()//60); expected_gap_minutes=sum(g["duration_seconds"]//60 for g in gaps if g["classification"]=="EXPECTED_GAP"); active_expected=expected_minutes-expected_gap_minutes; coverage=round(len(m1)/active_expected*100,6)
    provenance={"provider":PROVIDER,"platform":PLATFORM,"server":SERVER,"symbol":"EURUSD","raw_timeframe":"M1","price_component":"BID","timezone":"UTC","requested_period":{"start_utc":_stamp(int(start.timestamp()*1000)),"end_utc":_stamp(int(end.timestamp()*1000))},"observed_period":{"start_utc":_stamp(m1[0]["timestamp_ms"]),"end_utc":_stamp(m1[-1]["timestamp_ms"])},"acquired_at_utc":_stamp(int(acquired.timestamp()*1000)),"terminal_version":terminal_version,"runtime_version":runtime_version,"api":"MetaTrader5.copy_rates_range","license_id":LICENSE_ID,"usage_basis":USAGE_BASIS,"terms_reference":TERMS_REFERENCES,"redistribution_rights":"not_inferred"}
    quality={"policy_version":"mt5_oanda_gap_quality_v1","total_gaps":len(gaps),"expected_gap_count":sum(g["classification"]=="EXPECTED_GAP" for g in gaps),"no_tick_gap_count":sum(g["classification"]=="NO_TICK_GAP" for g in gaps),"suspicious_gap_count":sum(g["classification"]=="SUSPICIOUS_GAP" for g in gaps),"invalid_gap_count":sum(g["classification"]=="INVALID_GAP" for g in gaps),"gaps":gaps,"active_coverage_percent":coverage,"raw_m1_bars":len(m1)}
    rows=[{"symbol":"EURUSD","timeframe":"M15","timestamp_utc":_stamp(c["timestamp_ms"]),"open":f"{c['open']:.5f}","high":f"{c['high']:.5f}","low":f"{c['low']:.5f}","close":f"{c['close']:.5f}","volume":f"{c['volume']:.6f}","source":f"{PROVIDER} via {PLATFORM}","source_version":terminal_version or "not_available","schema_version":CANONICAL_CANDLE_SCHEMA_VERSION,"provenance":json.dumps(provenance,sort_keys=True,separators=(",",":")),"license":LICENSE_ID} for c in m15]
    digest=canonical_dataset_hash(rows)
    for row in rows: row["hash"]=digest
    with tempfile.TemporaryDirectory(prefix="odin-mt5-oanda-") as temp:
        temp_path=Path(temp)/"EURUSD_M15.csv"
        with temp_path.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=CANONICAL_CANDLE_COLUMNS); writer.writeheader(); writer.writerows(rows)
        extras={"manifest_schema_version":"odin.market_data_manifest/v2","raw_m1_sha256":raw_hash,"raw_m1_bars":len(m1),"raw_m1_format":"normalized_MetaTrader5_copy_rates_range_JSONL_v1","raw_m1_relative_path":f"EURUSD/M1/raw/{raw_hash}/EURUSD_M1_RAW.jsonl","provenance_v2":provenance,"quality":quality,"aggregation":"M1_to_M15_UTC_complete_windows_v1","derived_from_raw_sha256":raw_hash,"m15_continuity_exceptions":m15_exceptions}
        result=import_canonical_candle_history(temp_path,symbol="EURUSD",timeframe="M15",artifact_root=artifact_root,ingested_at=acquired,manifest_extras=extras,continuity_exceptions=m15_exceptions)
        if result["status"] != "VALIDATED": return result
        raw_path=Path(artifact_root)/"artifacts"/"market-data"/"EURUSD"/"M1"/"raw"/raw_hash/"EURUSD_M1_RAW.jsonl"
        try:
            raw_path.parent.mkdir(parents=True,exist_ok=True)
            if not raw_path.exists(): raw_path.write_bytes(raw_blob)
        except OSError as error: raise Mt5OandaHistoryError("mt5_oanda_raw_persistence_failed") from error
    return {**result,"raw_m1_sha256":raw_hash,"raw_m1_bars":len(m1),"quality":quality,"provider":PROVIDER,"platform":PLATFORM,"server":SERVER,"safe_to_trade":False,"real_trading":False,"execution_allowed":False}
