"""Deterministic guardrails (task T030; spec FR-008 to FR-013).

``check_invariants`` runs on every candidate decision before it is returned. Any violation
replaces the decision with the fallback clarify (FR-030).
"""

from __future__ import annotations

from datetime import datetime

from .models import ReminderDecision, RequestContext


def _before_now(due_at: str, now: datetime) -> bool:
    try:
        return datetime.fromisoformat(due_at) < now
    except ValueError:
        return True


def check_invariants(decision: ReminderDecision, ctx: RequestContext) -> list[str]:
    """Return the FR IDs of every violated structural invariant (empty list = valid)."""
    d = decision
    violations: list[str] = []
    if d.intent == "create" and (d.task is None or d.due_at is None):
        violations.append("FR-008")
    if d.due_at is not None and _before_now(d.due_at, ctx.now):
        violations.append("FR-009")
    if d.intent in ("reschedule", "snooze") and (
            d.target_id is None or d.target_id not in ctx.reminder_ids):
        violations.append("FR-010")
    if d.intent == "snooze" and d.snooze_minutes is None:
        violations.append("FR-011")
    if d.intent == "clarify" and (d.clarification_question is None or d.due_at is not None):
        violations.append("FR-012")
    if d.intent == "refuse" and (
            d.refusal_reason is None or d.task is not None or d.due_at is not None
            or d.target_id is not None):
        violations.append("FR-013")
    if d.intent == "reschedule" and d.due_at is None:
        violations.append("FR-023")  # agent-side rule: a reschedule needs a new time
    return violations


MAX_TEXT_CHARS = 2000  # FR-026: longer input is "very long"

EMPTY_QUESTION = "What would you like me to remind you about, and when?"
TOO_LONG_QUESTION = (
    "That request is too long for me to handle. Please send a shorter reminder request "
    "(under 2,000 characters).")
SAFETY_REFUSAL_REASON = "Request declined by safety policy."


def pre_model_check(text: str) -> ReminderDecision | None:
    """Clarify without calling the model for empty or over-long text (FR-026)."""
    if not text.strip():
        return ReminderDecision(intent="clarify", clarification_question=EMPTY_QUESTION)
    if len(text) > MAX_TEXT_CHARS:
        return ReminderDecision(intent="clarify", clarification_question=TOO_LONG_QUESTION)
    return None


def refusal_decision() -> ReminderDecision:
    """Schema-valid refuse used when the API's safety system declines (FR-028)."""
    return ReminderDecision(intent="refuse", refusal_reason=SAFETY_REFUSAL_REASON)
