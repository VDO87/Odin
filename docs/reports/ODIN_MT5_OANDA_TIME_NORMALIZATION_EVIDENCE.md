# ODIN MT5/OANDA time normalization evidence

**Scope:** read-only evidence for `OANDA TMS Brokers S.A.` / `OANDATMS-MT5`.
No Stage 0, CANARY, `order_check`, `order_send`, positions or orders were called.

## Live evidence — 2026-08-23

Five samples were collected over approximately two minutes with the official
MetaTrader 5 Python package. Windows and WSL UTC differed by less than 2.1
seconds in every sample. The latest M1 and M15 candle boundaries were exactly
`+7200` seconds from the corresponding UTC boundary. Tick offsets were between
approximately `+7190` and `+7196` seconds; after applying the same `+7200`
source offset, their actual ages were approximately 4 to 10 seconds.

The original failing sample is retained as a separate reproducible datum:
`tick.time=1787529500`, raw interpretation `2026-08-23T23:58:20Z`, and ODIN
time `2026-08-23T21:58:42.356064Z`. The source profile normalizes it to
`2026-08-23T21:58:20Z`, producing age `22.356064` seconds (`FRESH`) without
altering the raw value.

The Sunday session's first available M1 candle had raw wall-clock time
`2026-08-23 23:05`. The official OANDA TMS instrument specification publishes
Sunday opening at `23:05` and states that its instrument hours use CET in the
winter period and CEST from the last Sunday of March through the last Saturday
of October. On this CEST date, `23:05` server time corresponds to `21:05Z`,
which independently confirms the observed `+7200` seconds.

The Windows MT5 UI was inspected passively, but the capture returned a stale
window from another application. No UI input was attempted and the terminal's
visual clock is therefore recorded as unavailable rather than inferred.

## Source profile and contract

The only enabled profile is:

```text
broker=OANDA TMS Brokers S.A.
server=OANDATMS-MT5
profile=oanda_tms_mt5_cet_cest_v1
timezone=Europe/Warsaw (CET/CEST)
standard_offset=+3600
daylight_offset=+7200
dst_rule=EU last Sunday March 01:00Z to last Sunday October 01:00Z
maximum_live_observation_lag=300 seconds
```

Normalization preserves the raw broker epoch and raw server wall clock. It
derives a unique UTC candidate from the profile and records method, observed
offset and confidence. Unknown identity, unexpected offset, ambiguous DST time
or a timestamp still in the future after normalization blocks fail-closed.
The five-minute live-observation bound is not a freshness threshold: events
older than 60 seconds still become `STALE`. It prevents a different source
encoding (for example an unconfigured `+3h`) from being mistaken for this
profile. A raw-UTC timestamp arriving under this exact source profile is also
blocked rather than silently changing timestamp semantics.

The terminal cache did not contain a usable winter sample for this instrument.
The `+3600` winter rule is therefore documentary evidence from the official
OANDA TMS specification, while the current `+7200` CEST rule has both live and
documentary evidence.

## References

- MetaQuotes Python documentation:
  <https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py>
- OANDA TMS MT5 guide identifying the broker and `OANDATMS-MT5` server:
  <https://help.oanda.com/eu/en/faqs/mt5-user-guide-eu.htm>
- OANDA TMS instrument specification with CET/CEST rule:
  <https://www.oanda.com/eu-en/sites/default/files/document_files/sif-tms-connect-eng-12.02.2024.pdf>

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
broker_submission_called=false
```
