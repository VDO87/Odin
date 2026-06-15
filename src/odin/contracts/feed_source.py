"""A18 mock feed source selector contract."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeedSourceSelection:
    component: str
    status: str
    selector_mode: str
    selected_source: str
    fallback_source: str
    mt5_feed_quality_status: str
    mt5_feed_available: bool
    market_data_available: bool
    safe_to_use_for_decision: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "selector_mode": self.selector_mode,
            "selected_source": self.selected_source,
            "fallback_source": self.fallback_source,
            "mt5_feed_quality_status": self.mt5_feed_quality_status,
            "mt5_feed_available": self.mt5_feed_available,
            "market_data_available": self.market_data_available,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "blockers": self.blockers,
            "notes": self.notes,
        }
