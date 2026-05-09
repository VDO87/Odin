from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from odin_market.market_models import AccountInfo, Candle, OrderInfo, PositionInfo, SymbolInfo, Tick
from odin_market.timeframes import Timeframe, normalize_timeframe


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result(
    status: str,
    message: str,
    data: dict[str, Any] | None = None,
    *,
    safe_to_trade: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "data": data or {},
        "safe_to_trade": safe_to_trade,
        "timestamp": _ts(),
    }


class MT5ShadowAdapter:
    def __init__(self, *, order_send_enabled: bool = False) -> None:
        self.order_send_enabled = bool(order_send_enabled)
        self.enabled = os.getenv("MT5_ENABLED", "true").lower() == "true"
        self.shadow_mode = os.getenv("MT5_SHADOW_MODE", "true").lower() == "true"
        self.login = os.getenv("MT5_LOGIN", "").strip()
        self.password = os.getenv("MT5_PASSWORD", "").strip()
        self.server = os.getenv("MT5_SERVER", "").strip()
        self.path = os.getenv("MT5_PATH", "").strip()
        self._mt5: Any | None = None
        self._initialized = False
        self._import_error: str | None = None

        try:
            import MetaTrader5 as mt5  # type: ignore

            self._mt5 = mt5
        except Exception as error:  # pragma: no cover - env dependent
            self._import_error = f"{error.__class__.__name__}: {error}"
            self._mt5 = None

    def is_available(self) -> bool:
        return self._mt5 is not None

    def initialize(self) -> dict[str, Any]:
        if not self.enabled:
            return _result("WARNING", "MT5 desactivado por configuração.", {"enabled": False})

        if not self.is_available():
            return _result(
                "WARNING",
                "Biblioteca MetaTrader5 indisponível neste ambiente.",
                {"import_error": self._import_error, "availability": "UNAVAILABLE"},
            )

        kwargs: dict[str, Any] = {}
        if self.path:
            kwargs["path"] = self.path

        ok = bool(self._mt5.initialize(**kwargs))  # type: ignore[union-attr]
        self._initialized = ok
        if not ok:
            return _result(
                "WARNING",
                "Não foi possível inicializar terminal MT5.",
                {"last_error": self._mt5.last_error()},  # type: ignore[union-attr]
            )

        return _result("OK", "MT5 inicializado em modo sombra.", {"shadow_mode": self.shadow_mode})

    def shutdown(self) -> dict[str, Any]:
        if not self.is_available() or not self._initialized:
            return _result("WARNING", "MT5 não inicializado.", {"initialized": self._initialized})

        self._mt5.shutdown()  # type: ignore[union-attr]
        self._initialized = False
        return _result("OK", "MT5 encerrado.")

    def _ensure_initialized(self) -> dict[str, Any] | None:
        if not self.is_available():
            return _result(
                "WARNING",
                "Biblioteca MetaTrader5 indisponível neste ambiente.",
                {"import_error": self._import_error, "availability": "UNAVAILABLE"},
            )
        if self._initialized:
            return None
        init = self.initialize()
        if init["status"] != "OK":
            return init
        return None

    def get_terminal_info(self) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        info = self._mt5.terminal_info()  # type: ignore[union-attr]
        if info is None:
            return _result("WARNING", "Terminal info indisponível.", {"last_error": self._mt5.last_error()})  # type: ignore[union-attr]
        data = info._asdict()
        return _result("OK", "Terminal info lida.", data, safe_to_trade=True)

    def get_account_info(self) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        info = self._mt5.account_info()  # type: ignore[union-attr]
        if info is None:
            return _result("WARNING", "Conta MT5 indisponível.", {"last_error": self._mt5.last_error()})  # type: ignore[union-attr]
        payload = AccountInfo(
            login=getattr(info, "login", None),
            server=getattr(info, "server", None),
            balance=getattr(info, "balance", None),
            equity=getattr(info, "equity", None),
            margin_free=getattr(info, "margin_free", None),
            leverage=getattr(info, "leverage", None),
        ).to_dict()
        return _result("OK", "Conta MT5 lida.", payload, safe_to_trade=True)

    def get_symbols(self) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        symbols = self._mt5.symbols_get()  # type: ignore[union-attr]
        if symbols is None:
            return _result("WARNING", "Lista de símbolos indisponível.", {"last_error": self._mt5.last_error()})  # type: ignore[union-attr]
        data = [str(getattr(symbol, "name", "")) for symbol in symbols]
        return _result("OK", "Símbolos lidos.", {"symbols": data}, safe_to_trade=True)

    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        info = self._mt5.symbol_info(symbol)  # type: ignore[union-attr]
        if info is None:
            return _result("WARNING", f"Símbolo {symbol} indisponível.", {"symbol": symbol})
        payload = SymbolInfo(
            symbol=symbol,
            description=str(getattr(info, "description", "")),
            digits=int(getattr(info, "digits", 0)),
            spread=int(getattr(info, "spread", 0)),
            point=float(getattr(info, "point", 0.0)),
            trade_mode=int(getattr(info, "trade_mode", 0)),
        ).to_dict()
        return _result("OK", f"Symbol info de {symbol} lida.", payload, safe_to_trade=True)

    def get_tick(self, symbol: str) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        tick = self._mt5.symbol_info_tick(symbol)  # type: ignore[union-attr]
        if tick is None:
            return _result("WARNING", f"Tick indisponível para {symbol}.", {"symbol": symbol})
        payload = Tick(
            symbol=symbol,
            time=datetime.fromtimestamp(int(getattr(tick, "time", 0)), tz=timezone.utc).isoformat(),
            bid=float(getattr(tick, "bid", 0.0)),
            ask=float(getattr(tick, "ask", 0.0)),
            last=float(getattr(tick, "last", 0.0)),
            volume=float(getattr(tick, "volume", 0.0)),
        ).to_dict()
        return _result("OK", f"Tick de {symbol} lido.", payload, safe_to_trade=True)

    def _map_timeframe(self, timeframe: str) -> int:
        tf = normalize_timeframe(timeframe)
        lookup = {
            Timeframe.M1: getattr(self._mt5, "TIMEFRAME_M1"),  # type: ignore[union-attr]
            Timeframe.M5: getattr(self._mt5, "TIMEFRAME_M5"),  # type: ignore[union-attr]
            Timeframe.M15: getattr(self._mt5, "TIMEFRAME_M15"),  # type: ignore[union-attr]
            Timeframe.M30: getattr(self._mt5, "TIMEFRAME_M30"),  # type: ignore[union-attr]
            Timeframe.H1: getattr(self._mt5, "TIMEFRAME_H1"),  # type: ignore[union-attr]
            Timeframe.H4: getattr(self._mt5, "TIMEFRAME_H4"),  # type: ignore[union-attr]
            Timeframe.D1: getattr(self._mt5, "TIMEFRAME_D1"),  # type: ignore[union-attr]
        }
        return int(lookup[tf])

    def get_candles(self, symbol: str, timeframe: str, count: int) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        try:
            tf = self._map_timeframe(timeframe)
        except Exception as error:
            return _result("WARNING", "Timeframe inválido.", {"timeframe": timeframe, "error": str(error)})

        rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, int(max(1, count)))  # type: ignore[union-attr]
        if rates is None:
            return _result("WARNING", f"Candles indisponíveis para {symbol}.", {"symbol": symbol, "timeframe": timeframe})

        candles: list[dict[str, Any]] = []
        for row in rates:
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                time=datetime.fromtimestamp(int(row["time"]), tz=timezone.utc).isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                tick_volume=int(row["tick_volume"]),
                spread=int(row["spread"]),
                real_volume=int(row["real_volume"]),
            )
            candles.append(candle.to_dict())

        return _result("OK", f"Candles de {symbol} lidos.", {"symbol": symbol, "timeframe": timeframe, "candles": candles}, safe_to_trade=True)

    def get_positions(self) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        positions = self._mt5.positions_get()  # type: ignore[union-attr]
        if positions is None:
            return _result("WARNING", "Leitura de posições indisponível.", {"last_error": self._mt5.last_error()})  # type: ignore[union-attr]

        parsed = [
            PositionInfo(
                ticket=int(getattr(p, "ticket", 0)),
                symbol=str(getattr(p, "symbol", "")),
                type=int(getattr(p, "type", 0)),
                volume=float(getattr(p, "volume", 0.0)),
                price_open=float(getattr(p, "price_open", 0.0)),
                sl=float(getattr(p, "sl", 0.0)),
                tp=float(getattr(p, "tp", 0.0)),
                profit=float(getattr(p, "profit", 0.0)),
                magic=getattr(p, "magic", None),
                comment=str(getattr(p, "comment", "")),
                time=datetime.fromtimestamp(int(getattr(p, "time", 0)), tz=timezone.utc).isoformat(),
            ).to_dict()
            for p in positions
        ]

        return _result("OK", "Posições lidas.", {"positions": parsed}, safe_to_trade=True)

    def get_orders(self) -> dict[str, Any]:
        pre = self._ensure_initialized()
        if pre:
            return pre
        orders = self._mt5.orders_get()  # type: ignore[union-attr]
        if orders is None:
            return _result("WARNING", "Leitura de ordens indisponível.", {"last_error": self._mt5.last_error()})  # type: ignore[union-attr]

        parsed = [
            OrderInfo(
                ticket=int(getattr(o, "ticket", 0)),
                symbol=str(getattr(o, "symbol", "")),
                type=int(getattr(o, "type", 0)),
                volume_current=float(getattr(o, "volume_current", 0.0)),
                price_open=float(getattr(o, "price_open", 0.0)),
                sl=float(getattr(o, "sl", 0.0)),
                tp=float(getattr(o, "tp", 0.0)),
                magic=getattr(o, "magic", None),
                comment=str(getattr(o, "comment", "")),
                time_setup=datetime.fromtimestamp(int(getattr(o, "time_setup", 0)), tz=timezone.utc).isoformat(),
            ).to_dict()
            for o in orders
        ]
        return _result("OK", "Ordens lidas.", {"orders": parsed}, safe_to_trade=True)

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return _result(
            "BLOCKED",
            "MT5 order_send bloqueado em RC1.2 Shadow Mode.",
            {"order": order},
            safe_to_trade=False,
        )

    def healthcheck(self) -> dict[str, Any]:
        if not self.enabled:
            return _result("WARNING", "MT5 desactivado por configuração.", {"enabled": False})
        if not self.is_available():
            return _result(
                "WARNING",
                "Biblioteca MetaTrader5 indisponível neste ambiente.",
                {
                    "availability": "UNAVAILABLE",
                    "import_error": self._import_error,
                    "order_send_blocked": True,
                },
                safe_to_trade=False,
            )

        init = self.initialize()
        if init["status"] != "OK":
            init["data"]["order_send_blocked"] = True
            init["safe_to_trade"] = False
            return init

        term = self.get_terminal_info()
        account = self.get_account_info()
        symbols = self.get_symbols()

        safe = all(item.get("status") == "OK" for item in [term, account, symbols]) and not self.order_send_enabled
        return _result(
            "OK" if safe else "WARNING",
            "Healthcheck MT5 executado em modo sombra.",
            {
                "terminal": term,
                "account": account,
                "symbols": symbols,
                "shadow_mode": self.shadow_mode,
                "order_send_blocked": not self.order_send_enabled,
            },
            safe_to_trade=safe,
        )
