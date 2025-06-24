"""Integração simulada com APIs externas."""

from .openai_client import OpenAIClient
from .xtb_client import XTBClient

__all__ = ["OpenAIClient", "XTBClient"]
