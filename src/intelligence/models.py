from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.utils import ensure_utc, utc_now


@dataclass(frozen=True, slots=True)
class AdvisorySource:
    source_id: str
    kind: str
    summary: str
    ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "kind": self.kind,
            "summary": self.summary,
            "ref": self.ref,
        }


@dataclass(frozen=True, slots=True)
class AdvisoryRequest:
    question: str
    requested_by: str
    query_scope: str
    created_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.question.strip():
            raise ValueError("question is required")
        if not self.requested_by.strip():
            raise ValueError("requested_by is required")
        if not self.query_scope.strip():
            raise ValueError("query_scope is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "requested_by": self.requested_by,
            "query_scope": self.query_scope,
            "created_at_utc": self.created_at_utc.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class AdvisoryResponse:
    accepted: bool
    provider: str
    advisory_only: bool
    answer: str | None = None
    reason_code: str | None = None
    sources: tuple[AdvisorySource, ...] = tuple()
    used_context: tuple[str, ...] = tuple()
    completed_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "completed_at_utc", ensure_utc(self.completed_at_utc))
        if self.accepted and not (self.answer or "").strip():
            raise ValueError("accepted advisory response requires answer")
        if not self.accepted and not (self.reason_code or "").strip():
            raise ValueError("rejected advisory response requires reason_code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "rejected": not self.accepted,
            "provider": self.provider,
            "advisory_only": self.advisory_only,
            "answer": self.answer,
            "reason_code": self.reason_code,
            "sources": [source.to_dict() for source in self.sources],
            "used_context": list(self.used_context),
            "completed_at_utc": self.completed_at_utc.isoformat(),
        }

