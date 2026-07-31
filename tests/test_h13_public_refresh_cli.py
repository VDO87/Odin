import unittest
from unittest.mock import patch

from odin.cli import main


class PublicRefreshCliTests(unittest.TestCase):
    def test_cli_runs_one_bounded_read_only_refresh(self):
        result = {"status": "OK", "safe_to_trade": False, "execution_allowed": False, "real_trading": False}
        with patch("odin.cli.refresh_ecb_public_data", return_value=result), patch("builtins.print") as output:
            code = main(["public-data-refresh", "--cache-root", "/tmp/cache", "--timeout-seconds", "5"])

        self.assertEqual(code, 0)
        self.assertIn('"execution_allowed": false', output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
