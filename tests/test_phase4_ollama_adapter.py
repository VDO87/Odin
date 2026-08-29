import json
import tempfile
import threading
import unittest
from pathlib import Path

from odin.hermes.ollama_adapter import OllamaAdapter, OllamaAdapterConfig


class Phase4OllamaAdapterTests(unittest.TestCase):
    def _config(self, root: Path, **overrides: object) -> OllamaAdapterConfig:
        values: dict[str, object] = {
            "audit_log_path": str(root / "audit.jsonl"),
            "timeout_seconds": 10.0,
            "max_task_seconds": 30.0,
        }
        values.update(overrides)
        return OllamaAdapterConfig(**values)  # type: ignore[arg-type]

    def test_success_has_stable_contract_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def transport(_url, payload, _timeout):
                self.assertEqual(payload["model"], "qwen2.5-coder:1.5b")
                self.assertEqual(payload["options"]["num_predict"], 512)
                return {"response": "codigo", "prompt_eval_count": 12, "eval_count": 7}

            result = OllamaAdapter(self._config(root), transport=transport).run(
                task_id="P4-T1", prompt="Implementar funcao pura"
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["response"], "codigo")
            self.assertEqual(result["metrics"], {"prompt_tokens": 12, "generated_tokens": 7})
            self.assertIsNone(result["error"])

    def test_retries_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempts = 0

            def transport(_url, _payload, _timeout):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise OSError("indisponivel")
                return {"response": "recuperado"}

            result = OllamaAdapter(self._config(Path(tmp)), transport=transport).run(
                task_id="P4-T2", prompt="Tentar novamente"
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["attempt"], 2)

    def test_timeout_is_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            def transport(_url, _payload, _timeout):
                raise TimeoutError

            result = OllamaAdapter(self._config(Path(tmp)), transport=transport).run(
                task_id="P4-T3", prompt="Tarefa lenta"
            )

            self.assertEqual(result["status"], "timeout")
            self.assertEqual(result["error"], "request_timeout")

    def test_pre_cancelled_task_does_not_call_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            cancelled = threading.Event()
            cancelled.set()

            def transport(_url, _payload, _timeout):
                self.fail("transport nao deve ser chamado")

            result = OllamaAdapter(self._config(Path(tmp)), transport=transport).run(
                task_id="P4-T4", prompt="Cancelar", cancel_event=cancelled
            )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"], "cancelled")

    def test_invalid_response_fails_after_bounded_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = OllamaAdapter(
                self._config(Path(tmp)), transport=lambda *_args: {"response": ""}
            ).run(task_id="P4-T5", prompt="Validar")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["attempt"], 2)

    def test_audit_excludes_prompt_and_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            OllamaAdapter(
                self._config(root), transport=lambda *_args: {"response": "SEGREDO_RESPOSTA"}
            ).run(task_id="P4-T6", prompt="SEGREDO_PROMPT")

            record = json.loads((root / "audit.jsonl").read_text(encoding="utf-8"))
            serialized = json.dumps(record)
            self.assertNotIn("SEGREDO_PROMPT", serialized)
            self.assertNotIn("SEGREDO_RESPOSTA", serialized)

    def test_rejects_non_local_endpoint(self):
        with self.assertRaisesRegex(ValueError, "host local"):
            OllamaAdapterConfig(base_url="http://192.0.2.1:11434")

    def test_rejects_unbounded_output_configuration(self):
        with self.assertRaisesRegex(ValueError, "max_output_tokens"):
            OllamaAdapterConfig(max_output_tokens=4096)

    def test_json_mode_requests_native_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen: dict[str, object] = {}

            def transport(_url, payload, _timeout):
                seen.update(payload)
                return {"response": '{"files":{"solution.py":"x = 1"}}'}

            adapter = OllamaAdapter(
                self._config(Path(tmp), json_mode=True),
                transport=transport,
            )
            result = adapter.run(task_id="P4-JSON", prompt="JSON")

            self.assertEqual(result["status"], "success")
            self.assertEqual(seen["format"], "json")


if __name__ == "__main__":
    unittest.main()
