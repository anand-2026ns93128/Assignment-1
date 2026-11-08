"""US1 tests for invariants and the fallback (T020).

Covers FR-008 to FR-013, FR-030 and AC-29.
"""

from __future__ import annotations

import json

import pytest
from conftest import DEFAULT_NOW, DEFAULT_TZ, R1, StubClient, decision, reply

from reminder_agent.agent import run_agent
from reminder_agent.guardrails import check_invariants
from reminder_agent.inputs import validate_inputs
from reminder_agent.models import FALLBACK_DECISION, ReminderDecision

CTX = validate_inputs("x", DEFAULT_NOW, DEFAULT_TZ, [R1])
FUTURE = "2026-11-11T09:00:00+05:30"


@pytest.mark.parametrize("fields, expected", [
    ({"intent": "create", "task": "call mom", "due_at": FUTURE}, []),
    ({"intent": "create", "task": None, "due_at": FUTURE}, ["FR-008"]),
    ({"intent": "create", "task": "x", "due_at": None}, ["FR-008"]),
    ({"intent": "create", "task": "x", "due_at": "2026-11-10T09:00:00+05:30"}, ["FR-009"]),
    ({"intent": "reschedule", "target_id": None, "due_at": FUTURE}, ["FR-010"]),
    ({"intent": "snooze", "target_id": "r9", "snooze_minutes": 5}, ["FR-010"]),
    ({"intent": "snooze", "target_id": "r1", "snooze_minutes": None}, ["FR-011"]),
    ({"intent": "clarify", "clarification_question": None}, ["FR-012"]),
    ({"intent": "clarify", "clarification_question": "When?", "due_at": FUTURE}, ["FR-012"]),
    ({"intent": "refuse", "refusal_reason": None}, ["FR-013"]),
    ({"intent": "refuse", "refusal_reason": "No.", "task": "x"}, ["FR-013"]),
])
def test_us1_check_invariants(fields, expected):
    """FR-008 to FR-013: each violated invariant is reported by its FR ID."""
    assert check_invariants(ReminderDecision(**fields), CTX) == expected


@pytest.mark.parametrize("text, reason_prefix", [
    ("this is not JSON", "unparseable"),
    (json.dumps({**decision(intent="create", task="x", due_at=FUTURE), "admin": True}), "schema:"),
    (json.dumps(decision(intent="create", task="x", due_at="2026-11-10T08:00:00")),
     "invariant:FR-009"),
])
def test_us1_invalid_model_output_gives_fallback(text, reason_prefix):
    """FR-030, AC-29: invalid output is never returned; the fallback clarify is returned."""
    outcome = run_agent("remind me", DEFAULT_NOW, DEFAULT_TZ, client=StubClient([reply(text)]))
    assert outcome.decision == FALLBACK_DECISION
    assert outcome.fallback is True
    assert outcome.fallback_reason.startswith(reason_prefix)


def test_us1_max_tokens_stop_gives_fallback():
    """FR-030: a truncated reply (stop_reason max_tokens) gives the fallback."""
    truncated = reply('{"intent": "cre', stop_reason="max_tokens")
    outcome = run_agent("remind me", DEFAULT_NOW, DEFAULT_TZ, client=StubClient([truncated]))
    assert outcome.decision == FALLBACK_DECISION
    assert outcome.fallback_reason == "max_tokens"


def test_us1_fallback_itself_passes_schema_and_invariants():
    """FR-030, AC-29: the fallback decision satisfies every invariant."""
    assert check_invariants(FALLBACK_DECISION, CTX) == []
