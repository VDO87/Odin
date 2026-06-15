"""A1 risk placeholder that fails closed."""

from odin.contracts.state import RiskState


class RiskEngine:
    def current_state(self) -> RiskState:
        return RiskState.READY_BLOCKING

    def safe_to_trade(self) -> bool:
        return False

