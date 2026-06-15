"""Treasury safety policy for A4."""

from __future__ import annotations

from odin.contracts.treasury import DEFAULT_TRANSFER_BLOCK_REASONS, TreasuryState


def default_block_reasons() -> list[str]:
    return list(DEFAULT_TRANSFER_BLOCK_REASONS)


def can_mark_safe_to_transfer(*, read_only: bool, block_reasons: list[str]) -> bool:
    if read_only:
        return False
    return not block_reasons


def enforce_read_only(state: TreasuryState) -> TreasuryState:
    if state.read_only and state.safe_to_transfer:
        return TreasuryState(
            protected_capital_eur=state.protected_capital_eur,
            trading_capital_eur=state.trading_capital_eur,
            fire_capital_eur=state.fire_capital_eur,
            realized_profit_eur=state.realized_profit_eur,
            unrealized_profit_eur=state.unrealized_profit_eur,
            tax_reserve_eur=state.tax_reserve_eur,
            opex_reserve_eur=state.opex_reserve_eur,
            capex_fund_eur=state.capex_fund_eur,
            withdrawable_surplus_eur=state.withdrawable_surplus_eur,
            blocked_amount_eur=state.blocked_amount_eur,
            safe_to_transfer=False,
            transfer_block_reasons=state.transfer_block_reasons,
            jurisdiction=state.jurisdiction,
            fiscal_residency=state.fiscal_residency,
            currency=state.currency,
            read_only=True,
        )
    return state

