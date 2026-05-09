from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DecisionPacket:
    decision_id: str
    symbol: str
    asset_class: str
    timeframe: str
    direction: str
    entry_type: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_percent: float | None
    market_agent_score: float
    technical_agent_score: float
    news_agent_score: float
    macro_agent_score: float
    risk_agent_result: str
    critic_agent_result: str
    consensus_score: float
    openai_support_required: bool
    execution_permission: str
    created_at: str

    @classmethod
    def empty(cls, symbol: str = "UNKNOWN") -> "DecisionPacket":
        return cls(
            decision_id=f"decision_{uuid4().hex}",
            symbol=symbol,
            asset_class="UNKNOWN",
            timeframe="UNKNOWN",
            direction="HOLD",
            entry_type="MARKET",
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_percent=None,
            market_agent_score=0.0,
            technical_agent_score=0.0,
            news_agent_score=0.0,
            macro_agent_score=0.0,
            risk_agent_result="NOT_EVALUATED",
            critic_agent_result="NOT_EVALUATED",
            consensus_score=0.0,
            openai_support_required=False,
            execution_permission="SHADOW_ONLY",
            created_at=now_iso(),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
