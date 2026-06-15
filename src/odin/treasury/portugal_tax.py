"""Portugal tax reserve policy skeleton."""

from __future__ import annotations

from odin.contracts.treasury import PortugalTaxPolicy


def portugal_tax_policy() -> PortugalTaxPolicy:
    return PortugalTaxPolicy()


def tax_reserve_required(realized_profit_eur: float) -> float:
    if realized_profit_eur <= 0:
        return 0.0
    return round(realized_profit_eur * portugal_tax_policy().capital_gains_reserve_rate, 2)

