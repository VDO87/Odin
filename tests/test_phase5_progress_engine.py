import tempfile
import unittest

from odin.hermes.progress_engine import (
    ProgressAction,
    ProgressEngine,
    ProgressSnapshot,
    TaskState,
    TaskStateStore,
    TaskStatus,
    build_codex_escalation_package,
)


class Phase5ProgressEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ProgressEngine()

    def test_first_snapshot_records_baseline(self):
        decision = self.engine.evaluate(
            previous=None,
            current=ProgressSnapshot(tests_passed=3, tests_failed=2),
            local_attempt=1,
            no_progress_attempts=0,
        )
        self.assertEqual(decision.action, ProgressAction.CONTINUE)
        self.assertTrue(decision.improved)

    def test_fewer_failed_tests_is_progress(self):
        decision = self.engine.evaluate(
            previous=ProgressSnapshot(tests_passed=3, tests_failed=2),
            current=ProgressSnapshot(tests_passed=4, tests_failed=1),
            local_attempt=2,
            no_progress_attempts=0,
        )
        self.assertEqual(decision.action, ProgressAction.CONTINUE)
        self.assertIn("fewer_failed_tests", decision.reasons)

    def test_first_stall_allows_one_bounded_retry(self):
        snapshot = ProgressSnapshot(tests_passed=3, tests_failed=2)
        decision = self.engine.evaluate(
            previous=snapshot,
            current=snapshot,
            local_attempt=1,
            no_progress_attempts=0,
        )
        self.assertEqual(decision.action, ProgressAction.RETRY_LOCAL)

    def test_second_stall_escalates_to_codex(self):
        snapshot = ProgressSnapshot(tests_passed=3, tests_failed=2)
        decision = self.engine.evaluate(
            previous=snapshot,
            current=snapshot,
            local_attempt=2,
            no_progress_attempts=1,
        )
        self.assertEqual(decision.action, ProgressAction.ESCALATE_CODEX)
        self.assertIn("max_no_progress_attempts", decision.reasons)

    def test_repeated_error_escalates_immediately(self):
        decision = self.engine.evaluate(
            previous=ProgressSnapshot(error_signature="TypeError:x"),
            current=ProgressSnapshot(error_signature="TypeError:x"),
            local_attempt=2,
            no_progress_attempts=0,
        )
        self.assertEqual(decision.action, ProgressAction.ESCALATE_CODEX)
        self.assertIn("repeated_error_signature", decision.reasons)

    def test_out_of_scope_and_regression_escalate(self):
        decision = self.engine.evaluate(
            previous=None,
            current=ProgressSnapshot(
                out_of_scope_files=("src/odin/risk/live.py",),
                regressions=("test_safe_state",),
            ),
            local_attempt=1,
            no_progress_attempts=0,
        )
        self.assertEqual(decision.action, ProgressAction.ESCALATE_CODEX)

    def test_critical_change_escalates_immediately(self):
        decision = self.engine.evaluate(
            previous=None,
            current=ProgressSnapshot(),
            local_attempt=1,
            no_progress_attempts=0,
            critical_change=True,
        )
        self.assertEqual(decision.action, ProgressAction.ESCALATE_CODEX)

    def test_state_round_trip_is_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskStateStore(tmp)
            state = TaskState(
                task_id="P5-T1",
                objective="Validar progresso",
                acceptance_criteria=["testes passam"],
                allowed_paths=["src/odin/hermes/"],
                status=TaskStatus.TESTING,
                attempts=1,
            )
            path = store.save(state)
            loaded = store.load("P5-T1")

            self.assertTrue(path.exists())
            self.assertEqual(loaded, state)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_invalid_task_id_cannot_escape_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskStateStore(tmp)
            state = TaskState(
                task_id="../escape",
                objective="Nao escapar",
                acceptance_criteria=[],
                allowed_paths=[],
            )
            with self.assertRaisesRegex(ValueError, "caracteres"):
                store.save(state)

    def test_escalation_package_is_compact_and_truncates_diff(self):
        state = TaskState(
            task_id="P5-T2",
            objective="Corrigir modulo",
            acceptance_criteria=["pytest passa"],
            allowed_paths=["src/odin/hermes/"],
            attempts=2,
            error_signature="AssertionError:test_x",
            changed_files=["src/odin/hermes/x.py"],
        )
        package = build_codex_escalation_package(
            state=state,
            failed_tests=["test_x"],
            relevant_diff="x" * 100,
            progress_metrics=ProgressSnapshot(tests_failed=1),
            technical_question="Qual e a causa?",
            max_diff_chars=20,
        )

        self.assertEqual(len(package["relevant_diff"]), 20)
        self.assertIs(package["diff_truncated"], True)
        self.assertNotIn("repository", package)


if __name__ == "__main__":
    unittest.main()
