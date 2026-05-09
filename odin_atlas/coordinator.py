from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_atlas.agent_router import AgentRouter
from odin_atlas.consensus_engine import ConsensusEngine
from odin_atlas.decision_packet import DecisionPacket
from odin_logs.logger import JsonlLogger


class AtlasCoordinator:
    def __init__(self, *, min_consensus_score: float = 0.65, log_root: str | Path = "logs") -> None:
        root = Path(log_root)
        self.router = AgentRouter()
        self.consensus = ConsensusEngine(min_consensus_score=min_consensus_score)
        self.agent_log = JsonlLogger(root / "atlas" / "agent_outputs.log")
        self.consensus_log = JsonlLogger(root / "atlas" / "consensus.log")
        self.critic_log = JsonlLogger(root / "atlas" / "critic.log")
        self.packet_log = JsonlLogger(root / "atlas" / "decision_packets.log")

    def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        outputs = self.router.run_all(context)
        self.agent_log.write("atlas_agent_outputs", outputs)

        scores = {
            "market": float(outputs["market"].get("score", 0.0)),
            "technical": float(outputs["technical"].get("score", 0.0)),
            "news": float(outputs["news"].get("score", 0.0)),
            "macro": float(outputs["macro"].get("score", 0.0)),
        }
        consensus = self.consensus.evaluate(scores)
        self.consensus_log.write("atlas_consensus", consensus)

        critic_result = str(outputs["critic"].get("result", "NO_REVIEW"))
        self.critic_log.write("atlas_critic", {"result": critic_result})
        memory_note = str(outputs["memory"].get("result", "NO_MEMORY_NOTE"))

        packet = DecisionPacket.empty(symbol=str(context.get("symbol", "UNKNOWN")))
        packet.market_agent_score = scores["market"]
        packet.technical_agent_score = scores["technical"]
        packet.news_agent_score = scores["news"]
        packet.macro_agent_score = scores["macro"]
        packet.risk_agent_result = str(outputs["risk"].get("result", "UNKNOWN"))
        packet.critic_agent_result = critic_result
        packet.consensus_score = float(consensus["consensus_score"])
        packet.execution_permission = "SHADOW_ONLY"

        if not consensus["accepted"]:
            packet.critic_agent_result = "BLOCKED_LOW_CONSENSUS"

        packet_payload = packet.to_dict()
        self.packet_log.write("atlas_decision_packet", packet_payload)
        return {
            "accepted": bool(consensus["accepted"]),
            "reason": consensus["reason"],
            "decision_packet": packet_payload,
            "atlas_executes_orders": False,
            "critic_explanation": critic_result,
            "memory_note": memory_note,
        }
