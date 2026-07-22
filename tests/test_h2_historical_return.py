import contextlib
import io
import json
import unittest

from odin.cli import main
from odin.research.historical_return import historical_return_report


class HistoricalReturnReportTests(unittest.TestCase):
    def test_report_is_deterministic_and_observational(self):
        first = historical_return_report([100.0, 90.0, 110.0], transaction_cost_bps=10.0)
        second = historical_return_report([100.0, 90.0, 110.0], transaction_cost_bps=10.0)

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "OK")
        self.assertEqual(first["net_return_after_costs"], 0.098)
        self.assertEqual(first["max_drawdown"], -0.1)
        self.assertIs(first["not_investment_advice"], True)
        self.assertIs(first["decision_generated"], False)
        self.assertIs(first["proposal_generated"], False)
        self.assertIs(first["execution_allowed"], False)
        self.assertIs(first["safe_to_trade"], False)
        self.assertIs(first["real_trading"], False)

    def test_invalid_prices_fail_closed(self):
        result = historical_return_report([100.0, 0.0])

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "at_least_two_positive_close_prices_required")
        self.assertIs(result["execution_allowed"], False)

    def test_cli_returns_observational_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["historical-return-report", "--closes-json", "[100, 110]"])

        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
