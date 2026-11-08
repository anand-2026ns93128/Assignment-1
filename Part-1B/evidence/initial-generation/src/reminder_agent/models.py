"""Core data types for the reminder agent (task T014; data-model.md).

All types are immutable dataclasses. JSON shapes follow the contracts in
``specs/001-nl-reminder-agent/contracts/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

INTENTS = ("create", "reschedule", "snooze", "clarify", "refuse")

# FR-005: exactly these seven keys, in this order, always present.
DECISION_KEYS = (
    "intent",
    "task",
    "due_at",
    "target_id",
    "snooze_minutes",
    "clarification_question",
    "refusal_reason",
)

INPUT_ERROR_CATEGORIES = ("invalid_now", "invalid_timezone", "invalid_reminders")
INFRA_ERROR_CATEGORIES = (
    "timeout",
    "connection",
    "rate_limit",
    "server_error",
    "auth",
    "request_rejected",
)


@dataclass(frozen=True)
class ExistingReminder:
    """A reminder the caller already has: ``id`` unique within the list, aware ``due_at``."""

    id: str
    task: str
    due_at: datetime


@dataclass(frozen=True)
class RequestContext:
    """One invocation's validated inputs (FR-001)."""

    text: str
    now: datetime
    timezone: ZoneInfo
    reminders: tuple[ExistingReminder, ...] = ()

    @property
    def reminder_ids(self) -> frozenset[str]:
        return frozenset(r.id for r in self.reminders)


@dataclass(frozen=True)
class ReminderDecision:
    """The seven-key decision (FR-005, FR-006).

    Field constraints (enforced by schema validation, not here):
    ``task`` str (1–200) or None; ``due_at`` ISO-8601 string with offset, or None;
    ``snooze_minutes`` int 1–1440 or None; ``intent`` in INTENTS.
    """

    intent: str
    task: str | None = None
    due_at: str | None = None
    target_id: str | None = None
    snooze_minutes: int | None = None
    clarification_question: str | None = None
    refusal_reason: str | None = None

    def to_json(self) -> dict:
        return {key: getattr(self, key) for key in DECISION_KEYS}

    @classmethod
    def from_json(cls, data: dict) -> ReminderDecision:
        return cls(**{key: data.get(key) for key in DECISION_KEYS})


FALLBACK_QUESTION = (
    "Sorry, I couldn't work out that reminder. What should I remind you about, and when?"
)
# FR-030: the only thing returned when model output is invalid.
FALLBACK_DECISION = ReminderDecision(intent="clarify", clarification_question=FALLBACK_QUESTION)


@dataclass(frozen=True)
class ErrorResult:
    """A non-decision outcome, outside the decision schema (FR-003, FR-031)."""

    status: str
    category: str
    field: str | None
    message: str
    attempts: int

    def __post_init__(self) -> None:
        if self.status == "input_error":
            if self.category not in INPUT_ERROR_CATEGORIES or self.attempts != 0:
                raise ValueError(f"invalid input_error: {self.category}/{self.attempts}")
        elif self.status == "infra_error":
            if self.category not in INFRA_ERROR_CATEGORIES or not 1 <= self.attempts <= 2:
                raise ValueError(f"invalid infra_error: {self.category}/{self.attempts}")
        else:
            raise ValueError(f"unknown error status {self.status!r}")
        if not self.message:
            raise ValueError("error message must not be empty")

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "category": self.category,
            "field": self.field,
            "message": self.message,
            "attempts": self.attempts,
        }


@dataclass(frozen=True)
class ModelRequest:
    """What the agent sends across the ModelClient boundary."""

    system: str
    user: str
    schema: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ModelReply:
    """What comes back from the model (research R-07)."""

    text: str | None
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    def to_json(self) -> dict:
        return {
            "text": self.text,
            "stop_reason": self.stop_reason,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.model,
        }

    @classmethod
    def from_json(cls, data: dict) -> ModelReply:
        return cls(
            text=data.get("text"),
            stop_reason=data.get("stop_reason", ""),
            input_tokens=int(data.get("input_tokens", 0)),
            output_tokens=int(data.get("output_tokens", 0)),
            model=data.get("model", ""),
        )


@dataclass(frozen=True)
class AgentOutcome:
    """Result of ``run_agent``: exactly one of ``decision`` or ``error`` is set."""

    decision: ReminderDecision | None = None
    error: ErrorResult | None = None
    fallback: bool = False
    fallback_reason: str | None = None
    raw_reply: ModelReply | None = None
    attempts: int = 0

    def __post_init__(self) -> None:
        if (self.decision is None) == (self.error is None):
            raise ValueError("AgentOutcome needs exactly one of decision or error")
