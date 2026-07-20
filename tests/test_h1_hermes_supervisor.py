import sqlite3
import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke
from odin.hermes.goals import SUPPORTED_GOAL_STATES
from odin.hermes.supervisor import run_hermes_supervisor


class H1HermesSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project_root = Path.cwd()

    def tearDown(self):
        self.tmp.cleanup()

    def test_supervisor_reports_degraded_without_ollama(self):
        report = run_hermes_supervisor(
            project_root=str(self.project_root),
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
            command_overrides={
                "ollama_version": (False, ""),
                "ollama_list": (False, ""),
                "codex_version": (False, ""),
                "nvidia_smi": (False, ""),
            },
        )
        self.assertEqual(report["status"], "DEGRADED")
        self.assertEqual(report["operational_state"], "MODEL_UNAVAILABLE")
        self.assertIs(report["safe_to_trade"], False)
        self.assertIs(report["real_trading"], False)
        self.assertEqual(report["agents_count"], 11)
        self.assertEqual(report["skills_count"], 22)

    def test_supervisor_persists_agents_skills_goals_and_memory(self):
        sqlite_path = self.root / "runtime" / "odin.sqlite"
        report = run_hermes_supervisor(
            project_root=str(self.project_root),
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(sqlite_path),
            command_overrides={
                "ollama_version": (True, "ollama version 0.3.0"),
                "ollama_list": (True, "NAME ID SIZE\nqwen2.5-coder:1.5b abc 986 MB"),
                "codex_version": (False, ""),
                "nvidia_smi": (False, ""),
            },
        )
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["operational_state"], "LOCAL_ONLY")

        with sqlite3.connect(sqlite_path) as conn:
            agent_count = conn.execute("SELECT COUNT(*) FROM hermes_agents").fetchone()[0]
            skill_count = conn.execute("SELECT COUNT(*) FROM hermes_skills").fetchone()[0]
            goal_count = conn.execute("SELECT COUNT(*) FROM hermes_goals").fetchone()[0]
            memory_count = conn.execute("SELECT COUNT(*) FROM hermes_memory").fetchone()[0]
            checkpoint_count = conn.execute("SELECT COUNT(*) FROM hermes_checkpoints").fetchone()[0]
            runtime_count = conn.execute("SELECT COUNT(*) FROM hermes_runtime_cycles").fetchone()[0]
        self.assertEqual(agent_count, 11)
        self.assertEqual(skill_count, 22)
        self.assertEqual(goal_count, 1)
        self.assertGreaterEqual(memory_count, 2)
        self.assertEqual(checkpoint_count, 1)
        self.assertEqual(runtime_count, 1)

    def test_goal_engine_supports_required_states(self):
        self.assertEqual(
            SUPPORTED_GOAL_STATES,
            (
                "PENDING",
                "RUNNING",
                "WAITING",
                "BLOCKED",
                "RETRYING",
                "DEGRADED",
                "COMPLETED",
                "FAILED",
                "SAFE_STOP",
            ),
        )

    def test_smoke_includes_hermes_supervisor(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}
        self.assertIn("hermes-supervisor", names)
        self.assertEqual(report["modules_count"], 21)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
