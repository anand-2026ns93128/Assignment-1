"""US2 tests for pre-model guardrails (T033). Covers FR-026, AC-22 and AC-24."""

from __future__ import annotations

import pytest
from conftest import DEFAULT_NOW, DEFAULT_TZ, NoCallClient, StubClient, decision, reply

from reminder_agent.agent import run_agent


@pytest.mark.parametrize("text", ["", "   \n\t ", "x" * 2001])
def test_us2_empty_or_long_text_is_clarify_without_model_call(text):
    """AC-22, AC-24, FR-026: empty, whitespace-only or >2000-char text gets clarify, no call."""
    outcome = run_agent(text, DEFAULT_NOW, DEFAULT_TZ, client=NoCallClient())
    d = outcome.decision
    assert d.intent == "clarify" and d.due_at is None and d.clarification_question
    assert outcome.fallback is False and outcome.attempts == 0 and outcome.raw_reply is None


def test_us2_2000_chars_still_calls_model():
    """FR-026: exactly 2,000 characters is not 'very long' and goes to the model."""
    stub = StubClient([reply(decision(intent="clarify", clarification_question="What?"))])
    run_agent("y" * 2000, DEFAULT_NOW, DEFAULT_TZ, client=stub)
    assert len(stub.calls) == 1
