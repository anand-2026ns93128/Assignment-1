"""Tests for the core types, src/reminder_agent/models.py (T010).

Covers FR-003, FR-005, FR-030 and FR-031.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from reminder_agent.models import (
    DECISION_KEYS,
    FALLBACK_DECISION,
    AgentOutcome,
    ErrorResult,
    ReminderDecision,
)

ROOT = Path(__file__).resolve().parents[2]
ERROR_SCHEMA = json.loads(
    (ROOT / "specs/001-nl-reminder-agent/contracts/error_response.schema.json").read_text("utf-8"))


def test_decision_json_has_exactly_seven_keys():
    """FR-005: to_json always emits exactly the seven keys, in contract order."""
    out = ReminderDecision(intent="create", task="call mom",
                           due_at="2026-11-11T09:00:00+05:30").to_json()
    assert tuple(out) == DECISION_KEYS
    assert out["target_id"] is None and out["snooze_minutes"] is None


def test_fallback_decision_constant():
    """FR-030: the fallback is a clarify with the fixed question and every other field null."""
    out = FALLBACK_DECISION.to_json()
    assert out["intent"] == "clarify"
    assert out["clarification_question"] == (
        "Sorry, I couldn't work out that reminder. What should I remind you about, and when?")
    assert all(out[k] is None for k in DECISION_KEYS if k not in ("intent",
                                                                  "clarification_question"))


def test_decision_from_json_roundtrip():
    """FR-005: a validated JSON object converts to a decision and back unchanged."""
    data = dict.fromkeys(DECISION_KEYS)
    data.update(intent="refuse", refusal_reason="Out of scope.")
    assert ReminderDecision.from_json(data).to_json() == data


def test_error_result_validates_against_contract():
    """FR-003, FR-031: error results match error_response.schema.json."""
    err = ErrorResult(status="input_error", category="invalid_timezone", field="timezone",
                      message="Unknown timezone 'Mars/Olympus'", attempts=0)
    jsonschema.validate(err.to_json(), ERROR_SCHEMA)
    infra = ErrorResult(status="infra_error", category="rate_limit", field=None,
                        message="rate limited", attempts=2)
    jsonschema.validate(infra.to_json(), ERROR_SCHEMA)


@pytest.mark.parametrize("kwargs", [
    {"status": "boom", "category": "auth", "attempts": 1},
    {"status": "input_error", "category": "invalid_now", "attempts": 1},
    {"status": "infra_error", "category": "auth", "attempts": 0},
    {"status": "infra_error", "category": "auth", "attempts": 3},
    {"status": "infra_error", "category": "invalid_now", "attempts": 1},
])
def test_error_result_rejects_bad_values(kwargs):
    """FR-003, FR-031: status/category/attempts combinations outside the contract are rejected."""
    with pytest.raises(ValueError):
        ErrorResult(field=None, message="x", **kwargs)


def test_agent_outcome_exactly_one_of_decision_or_error():
    """FR-003, FR-031: an outcome carries a decision or an error, never both or neither."""
    AgentOutcome(decision=FALLBACK_DECISION)
    AgentOutcome(error=ErrorResult("infra_error", "auth", None, "denied", 1))
    with pytest.raises(ValueError):
        AgentOutcome()
    with pytest.raises(ValueError):
        AgentOutcome(decision=FALLBACK_DECISION,
                     error=ErrorResult("infra_error", "auth", None, "denied", 1))
