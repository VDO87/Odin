"""Cliente de integração futura com a API da XTB (stub)."""


class XTBClient:
    """Facilita a comunicação com a XTB de forma simplificada."""

    def login(self, user: str, password: str):
        """Realiza login simulando sucesso."""
        # Aqui ocorreria a chamada real de autenticação
        self.user = user
        return {"status": "login simulado"}

    def executar_ordem(self, tipo: str, ativo: str, volume: float):
        """Envia uma ordem de compra ou venda (simulada)."""
        # Implementação real de ordem via API ficaria aqui
        return {"status": "simulado", "tipo": tipo, "ativo": ativo, "volume": volume}
