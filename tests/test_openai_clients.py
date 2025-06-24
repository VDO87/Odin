"""Testes dos clientes de API fictícios."""

from ai.openai import OpenAIClient, XTBClient


def test_openai_consulta_stub():
    """Verifica se o stub do OpenAIClient responde corretamente ao prompt."""
    client = OpenAIClient(api_key="fake-key")
    resposta = client.consultar_modelo("Qual a previsão de hoje?")
    assert isinstance(resposta, str)
    assert resposta.startswith("Resposta simulada do modelo:")


def test_xtb_login_stub():
    """Garante que o login simulado retorna dicionário com status."""
    client = XTBClient()
    resultado = client.login("user", "senha")
    assert isinstance(resultado, dict)
    assert resultado.get("status") in {"simulado", "login simulado"}


def test_xtb_executar_ordem_stub():
    """Verifica o retorno da execução de ordem simulada."""
    client = XTBClient()
    resultado = client.executar_ordem("compra", "EURUSD", 1.0)
    assert isinstance(resultado, dict)
    assert set(resultado.keys()) == {"tipo", "ativo", "volume", "status"}
    assert resultado["tipo"] == "compra"
    assert resultado["ativo"] == "EURUSD"
    assert resultado["volume"] == 1.0
    assert resultado["status"] == "simulado"
