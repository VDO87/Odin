import unittest

from odin.adapters.brokers.isolated_observer import observer_status, validate_observer_request


class IsolatedObserverGuardTests(unittest.TestCase):
    def test_runtime_is_fail_closed_even_when_enabled_argument_is_true(self):
        result = observer_status(enabled=True, runtime_available=True)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["enabled"])
        self.assertFalse(result["generic_navigation_allowed"])
        self.assertIs(result["execution_allowed"], False)

    def test_known_capability_is_only_validated_while_runtime_is_off(self):
        result = validate_observer_request({"capability": "open_positions", "request_id": "safe-1"})

        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["validated_read_only_request"])
        self.assertEqual(result["reason"], "observer_runtime_not_enabled")
        self.assertIs(result["safe_to_trade"], False)

    def test_orders_navigation_and_free_form_fields_are_rejected(self):
        order = validate_observer_request({"capability": "place_order"})
        navigation = validate_observer_request({"capability": "open_positions", "url": "https://example"})
        script = validate_observer_request({"capability": "open_positions", "script": "unsafe"})

        self.assertEqual(order["reason"], "observer_capability_not_allowed")
        self.assertEqual(navigation["reason"], "observer_request_contains_unapproved_fields")
        self.assertEqual(script["reason"], "observer_request_contains_unapproved_fields")
        self.assertFalse(order["validated_read_only_request"])


if __name__ == "__main__":
    unittest.main()
