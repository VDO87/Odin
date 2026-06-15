"""A1 Hermes permissions."""

from odin.contracts.state import HermesMode


class HermesPermissions:
    mode = HermesMode.READ_ONLY
    can_write_orders = False
    can_modify_risk = False
    can_modify_treasury = False
    can_modify_execution = False

    def assert_read_only(self) -> bool:
        return (
            self.mode is HermesMode.READ_ONLY
            and not self.can_write_orders
            and not self.can_modify_risk
            and not self.can_modify_treasury
            and not self.can_modify_execution
        )

