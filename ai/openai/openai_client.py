"""Cliente para interação com a API da OpenAI (stub).

Exemplo de uso:
    >>> client = OpenAIClient("SUA-API-KEY")
    >>> resposta = client.consultar_modelo("Olá")
"""

from __future__ import annotations

import requests


class OpenAIClient:
    """Wrapper simplificado para chamadas à API da OpenAI."""

    def __init__(self, api_key: str) -> None:
        """Guarda a API key e prepara os cabeçalhos de autenticação."""
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def consultar_modelo(self, prompt: str, modelo: str = "gpt-3.5-turbo") -> str:
        """Envia um prompt ao modelo indicado e devolve a resposta textual."""
        # payload = {
        #     "model": modelo,
        #     "messages": [{"role": "user", "content": prompt}],
        # }
        # response = requests.post(
        #     "https://api.openai.com/v1/chat/completions",
        #     headers=self.headers,
        #     json=payload,
        #     timeout=10,
        # )
        # return response.json()["choices"][0]["message"]["content"]
        return f"Resposta simulada do modelo: {prompt}"
