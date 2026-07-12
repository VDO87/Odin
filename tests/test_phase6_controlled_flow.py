import json
import tempfile
import time
import unittest
from pathlib import Path

from odin.hermes.controlled_flow import (
    ControlledFlow,
    ControlledTask,
    ValidationResult,
    apply_sandbox_proposal,
    parse_proposal_response,
)
from odin.hermes.progress_engine import ProgressSnapshot, TaskStateStore, TaskStatus


class Phase6ControlledFlowTests(unittest.TestCase):
    def _task(self) -> ControlledTask:
        return ControlledTask(
            task_id="P6-T1",
            objective="Criar funcao deterministica",
            acceptance_criteria=("testes passam", "ruff passa", "mypy passa"),
            allowed_paths=("src/", "tests/"),
        )

    def test_success_stops_for_final_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def validator(_root, files):
                return ValidationResult(ProgressSnapshot(tests_passed=2, changed_files=files))

            flow = ControlledFlow(
                state_store=TaskStateStore(root / "state"),
                sandbox_root=root / "sandboxes",
                validator=validator,
            )
            result = flow.run(self._task(), lambda _attempt, _feedback: {"src/x.py": "x = 1\n"})

            self.assertEqual(result.status, TaskStatus.AWAITING_APPROVAL)
            self.assertEqual(result.next_action, "codex_final_review")
            self.assertEqual(result.attempts, 1)

    def test_failure_retries_then_escalates_without_calling_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = ProgressSnapshot(tests_failed=1, error_signature="same-error")

            def validator(_root, _files):
                return ValidationResult(snapshot, ("tests/test_x.py::test_x",), "AssertionError")

            store = TaskStateStore(root / "state")
            flow = ControlledFlow(
                state_store=store,
                sandbox_root=root / "sandboxes",
                validator=validator,
            )
            result = flow.run(self._task(), lambda _attempt, _feedback: {"src/x.py": "x = 0\n"})

            self.assertEqual(result.status, TaskStatus.CODEX_REVIEW)
            self.assertTrue(result.escalation_created)
            self.assertEqual(result.attempts, 2)
            package = json.loads((store.escalations_dir / "P6-T1.json").read_text())
            self.assertIs(package["automatic_call"], False)

    def test_feedback_is_returned_to_second_local_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validations = iter(
                (
                    ValidationResult(ProgressSnapshot(tests_failed=2), feedback="dois erros"),
                    ValidationResult(ProgressSnapshot(tests_passed=2), feedback=""),
                )
            )
            feedback_seen: list[str | None] = []

            def provider(_attempt, feedback):
                feedback_seen.append(feedback)
                return {"src/x.py": "x = 1\n"}

            flow = ControlledFlow(
                state_store=TaskStateStore(root / "state"),
                sandbox_root=root / "sandboxes",
                validator=lambda _root, _files: next(validations),
            )
            result = flow.run(self._task(), provider)

            self.assertEqual(result.status, TaskStatus.AWAITING_APPROVAL)
            self.assertEqual(feedback_seen, [None, "dois erros"])

    def test_proposal_cannot_escape_or_touch_disallowed_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaisesRegex(ValueError, "inseguro"):
                apply_sandbox_proposal(
                    workspace=root,
                    proposal={"../escape.py": ""},
                    allowed_paths=("src/",),
                )
            with self.assertRaisesRegex(ValueError, "fora do ambito"):
                apply_sandbox_proposal(
                    workspace=root,
                    proposal={"config/risk.yaml": ""},
                    allowed_paths=("src/",),
                )

    def test_parser_accepts_only_files_contract(self):
        parsed = parse_proposal_response('{"files":{"src/x.py":"x = 1\\n"}}')
        self.assertEqual(parsed, {"src/x.py": "x = 1\n"})
        with self.assertRaisesRegex(ValueError, "apenas"):
            parse_proposal_response('{"files":{"src/x.py":""},"command":"rm"}')

    def test_invalid_provider_output_is_bounded_and_escalated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = 0

            def provider(_attempt, _feedback):
                nonlocal calls
                calls += 1
                raise ValueError("JSON invalido")

            store = TaskStateStore(root / "state")
            flow = ControlledFlow(
                state_store=store,
                sandbox_root=root / "sandboxes",
            )
            result = flow.run(self._task(), provider)

            self.assertEqual(result.status, TaskStatus.CODEX_REVIEW)
            self.assertEqual(calls, 2)
            self.assertTrue(result.escalation_created)

    def test_provider_timeout_is_bounded_and_escalated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def provider(_attempt, _feedback):
                time.sleep(0.2)
                return {"src/x.py": "x = 1\n"}

            flow = ControlledFlow(
                state_store=TaskStateStore(root / "state"),
                sandbox_root=root / "sandboxes",
                provider_timeout_seconds=0.01,
                max_flow_seconds=1.0,
            )
            result = flow.run(self._task(), provider)

            self.assertEqual(result.status, TaskStatus.CODEX_REVIEW)
            self.assertTrue(result.escalation_created)


if __name__ == "__main__":
    unittest.main()
