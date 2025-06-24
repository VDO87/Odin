"""Testes para o módulo ai.openai."""

import pytest

from ai.openai.client import OpenAIClient


def test_openai_client_not_implemented() -> None:
    client = OpenAIClient()
    with pytest.raises(NotImplementedError):
        client.enviar_mensagem("ola")
