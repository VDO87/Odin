from __future__ import annotations

from typing import Any

from odin_atlas.agents.critic_agent import CriticAgent
from odin_atlas.agents.execution_agent import ExecutionAgent
from odin_atlas.agents.fire_agent import FireAgent
from odin_atlas.agents.macro_agent import MacroAgent
from odin_atlas.agents.market_agent import MarketAgent
from odin_atlas.agents.memory_agent import MemoryAgent
from odin_atlas.agents.news_agent import NewsAgent
from odin_atlas.agents.risk_agent import RiskAgent
from odin_atlas.agents.technical_agent import TechnicalAgent


class AgentRouter:
    def __init__(self) -> None:
        self.agents: dict[str, Any] = {
            "market": MarketAgent(),
            "technical": TechnicalAgent(),
            "news": NewsAgent(),
            "macro": MacroAgent(),
            "risk": RiskAgent(),
            "fire": FireAgent(),
            "execution": ExecutionAgent(),
            "critic": CriticAgent(),
            "memory": MemoryAgent(),
        }

    def run_all(self, context: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {name: agent.analyze(context) for name, agent in self.agents.items()}
