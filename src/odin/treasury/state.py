"""Treasury state calculation."""

from __future__ import annotations

from odin.contracts.treasury import TreasuryState
from odin.treasury.policy import can_mark_safe_to_transfer, default_block_reasons, enforce_read_only
from odin.treasury.portugal_tax import tax_reserve_required


def build_treasury_state(
    *,
    protected_capital_eur: float = 0.0,
    trading_capital_eur: float = 0.0,
    fire_capital_eur: float = 0.0,
    realized_profit_eur: float = 0.0,
    unrealized_profit_eur: float = 0.0,
    opex_reserve_eur: float = 0.0,
    capex_fund_eur: float = 0.0,
    read_only: bool = True,
) -> TreasuryState:
    block_reasons = default_block_reasons()
    tax_reserve_eur = tax_reserve_required(realized_profit_eur)
    withdrawable_surplus_eur = 0.0
    if realized_profit_eur > 0:
        withdrawable_surplus_eur = max(realized_profit_eur - tax_reserve_eur, 0.0)
    safe_to_transfer = can_mark_safe_to_transfer(read_only=read_only, block_reasons=block_reasons)
    state = TreasuryState(
        protected_capital_eur=protected_capital_eur,
        trading_capital_eur=trading_capital_eur,
        fire_capital_eur=fire_capital_eur,
        realized_profit_eur=realized_profit_eur,
        unrealized_profit_eur=unrealized_profit_eur,
        tax_reserve_eur=tax_reserve_eur,
        opex_reserve_eur=opex_reserve_eur,
        capex_fund_eur=capex_fund_eur,
        withdrawable_surplus_eur=withdrawable_surplus_eur,
        blocked_amount_eur=tax_reserve_eur,
        safe_to_transfer=safe_to_transfer,
        transfer_block_reasons=block_reasons,
        read_only=read_only,
    )
    return enforce_read_only(state)


def default_treasury_state() -> TreasuryState:
    return build_treasury_state()

