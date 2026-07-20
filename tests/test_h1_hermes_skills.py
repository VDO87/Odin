import unittest
from pathlib import Path


REQUIRED_SKILLS = (
    "verificar_estado_odin",
    "iniciar_odin",
    "parar_odin",
    "reiniciar_servico_odin",
    "verificar_ollama",
    "verificar_modelo_local",
    "analisar_logs_recentes",
    "identificar_erro_recorrente",
    "executar_testes",
    "gerar_relatorio_testes",
    "criar_checkpoint",
    "recuperar_checkpoint",
    "monitorizar_recursos",
    "compactar_contexto",
    "resumir_sessao",
    "recuperar_memoria",
    "criar_tarefa_codex",
    "validar_resultado_codex",
    "verificar_git_status",
    "criar_branch_trabalho",
    "gerar_relatorio_telegram",
    "executar_safe_stop",
)


class H1HermesSkillsTests(unittest.TestCase):
    def test_skill_files_exist(self):
        for name in REQUIRED_SKILLS:
            path = Path(".agents") / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists(), str(path))

    def test_skill_files_contain_required_sections(self):
        required_sections = (
            "Finalidade",
            "Parametros",
            "Permissoes",
            "Pre-condicoes",
            "Passos",
            "Validacoes",
            "Resultado Esperado",
            "Erros Possiveis",
            "Recuperacao",
            "Testes",
            "Versao",
        )
        for name in REQUIRED_SKILLS:
            path = Path(".agents") / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            for section in required_sections:
                self.assertIn(f"## {section}", text, f"{name}: {section}")


if __name__ == "__main__":
    unittest.main()
