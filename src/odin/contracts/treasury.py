"""Treasury contracts for Portugal skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_TRANSFER_BLOCK_REASONS = [
    "treasury_skeleton_read_only",
    "no_real_broker_data",
    "tax_reserve_not_validated",
    "protected_capital_policy_not_funded",
]


@dataclass(frozen=True)
class PortugalTaxPolicy:
    capital_gains_reserve_rate: float = 0.30
    capital_income_reserve_rate: float = 0.30
    short_holding_high_income_reserve_rate: float = 0.53
    only_realized_profit_counts: bool = True
    release_excess_only_after_irs_closed: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "capital_gains_reserve_rate": self.capital_gains_reserve_rate,
            "capital_income_reserve_rate": self.capital_income_reserve_rate,
            "short_holding_high_income_reserve_rate": self.short_holding_high_income_reserve_rate,
            "only_realized_profit_counts": self.only_realized_profit_counts,
            "release_excess_only_after_irs_closed": self.release_excess_only_after_irs_closed,
        }


@dataclass(frozen=True)
class TreasuryState:
    protected_capital_eur: float = 0.0
    trading_capital_eur: float = 0.0
    fire_capital_eur: float = 0.0
    realized_profit_eur: float = 0.0
    unrealized_profit_eur: float = 0.0
    tax_reserve_eur: float = 0.0
    opex_reserve_eur: float = 0.0
    capex_fund_eur: float = 0.0
    withdrawable_surplus_eur: float = 0.0
    blocked_amount_eur: float = 0.0
    safe_to_transfer: bool = False
    transfer_block_reasons: list[str] = field(default_factory=lambda: list(DEFAULT_TRANSFER_BLOCK_REASONS))
    jurisdiction: str = "PT"
    fiscal_residency: str = "PT"
    currency: str = "EUR"
    read_only: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "OK",
            "component": "treasury",
            "jurisdiction": self.jurisdiction,
            "fiscal_residency": self.fiscal_residency,
            "currency": self.currency,
            "read_only": self.read_only,
            "safe_to_transfer": self.safe_to_transfer,
            "protected_capital_eur": self.protected_capital_eur,
            "trading_capital_eur": self.trading_capital_eur,
            "fire_capital_eur": self.fire_capital_eur,
            "realized_profit_eur": self.realized_profit_eur,
            "unrealized_profit_eur": self.unrealized_profit_eur,
            "tax_reserve_eur": self.tax_reserve_eur,
            "opex_reserve_eur": self.opex_reserve_eur,
            "capex_fund_eur": self.capex_fund_eur,
            "withdrawable_surplus_eur": self.withdrawable_surplus_eur,
            "blocked_amount_eur": self.blocked_amount_eur,
            "transfer_block_reasons": self.transfer_block_reasons,
        }

