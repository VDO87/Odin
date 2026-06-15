import tempfile
import unittest
from pathlib import Path

from odin.hermes.service import generate_hermes_summary


class A3HermesRecommendationTests(unittest.TestCase):
    def _recommendations(self) -> list[dict[str, object]]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = generate_hermes_summary(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            return summary["recommendations"]

    def test_hermes_recommendations_are_read_only(self):
        recommendations = self._recommendations()

        self.assertGreaterEqual(len(recommendations), 1)
        for recommendation in recommendations:
            self.assertIs(recommendation["read_only"], True)
            self.assertIs(recommendation["requires_human_review"], True)

    def test_hermes_recommendations_cannot_execute(self):
        recommendations = self._recommendations()

        for recommendation in recommendations:
            self.assertIs(recommendation["can_execute"], False)


if __name__ == "__main__":
    unittest.main()

