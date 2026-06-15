import unittest

from odin.contracts.smoke import RuntimeSmokeReport, SmokeModuleResult


class A12SmokeContractTests(unittest.TestCase):
    def test_smoke_contract_serializes(self):
        module = SmokeModuleResult(
            name="validate/core",
            status="PASS",
            safe_to_trade=False,
            real_trading=False,
            execution_allowed=False,
            expected_blocking=True,
            observed_key_state="READY_BLOCKING",
            passed=True,
            reason="module_safe",
        )
        report = RuntimeSmokeReport(
            component="runtime_smoke",
            status="PASS",
            smoke_mode="LOCAL_SAFE_SMOKE",
            modules_count=1,
            all_modules_ok=True,
            safe_state_confirmed=True,
            blocking_state_confirmed=True,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="local_runtime_smoke_passed",
            modules=[module],
            blockers=["real_trading_disabled"],
            notes=["contract test"],
        )

        payload = report.to_dict()

        self.assertEqual(payload["component"], "runtime_smoke")
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["smoke_mode"], "LOCAL_SAFE_SMOKE")
        self.assertIs(payload["all_modules_ok"], True)
        self.assertIs(payload["execution_allowed"], False)
        self.assertEqual(payload["modules"][0]["name"], "validate/core")


if __name__ == "__main__":
    unittest.main()
