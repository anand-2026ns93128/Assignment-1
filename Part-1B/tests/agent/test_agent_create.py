"""US1 scenario tests for create decisions with stubbed model replies (T023).

The stub plays the model's local wall-time answer; these tests verify the agent's
deterministic handling. Covers FR-008, FR-014 to FR-018, FR-022, AC-01 to AC-05, AC-08, AC-13.
"""

from __future__ import annotations

import pytest
from conftest import DEFAULT_NOW, DEFAULT_TZ, StubClient, decision, reply

from reminder_agent.agent import run_agent


def _create(task, due_at):
    return reply(decision(intent="create", task=task, due_at=due_at))


def test_us1_ac01_call_mom_tomorrow_9am():
    """AC-01: create, due 2026-11-11T09:00+05:30, task with 'call' and 'mom'."""
    outcome = run_agent("remind me to call mom tomorrow at 9am", DEFAULT_NOW, DEFAULT_TZ,
                        client=StubClient([_create("call mom", "2026-11-11T09:00:00")]))
    d = outcome.decision.to_json()
    assert d["intent"] == "create"
    assert d["due_at"] == "2026-11-11T09:00:00+05:30"
    assert "call" in d["task"] and "mom" in d["task"]
    assert outcome.fallback is False and outcome.attempts == 1


@pytest.mark.parametrize("text, model_due, expected", [
    ("remind me in 2 hours to take my medicine", "2026-11-10T12:00:00",
     "2026-11-10T12:00:00+05:30"),                                                  # AC-02
    ("remind me next Monday at 10am to renew my passport", "2026-11-16T10:00:00",
     "2026-11-16T10:00:00+05:30"),                                                  # AC-03
    ("remind me tonight to lock the gate", "2026-11-10T20:00:00+05:30",
     "2026-11-10T20:00:00+05:30"),                                                  # AC-04
    ("at 9am remind me to water the plants", "2026-11-11T09:00:00",
     "2026-11-11T09:00:00+05:30"),                                                  # AC-05
])
def test_us1_ac02_to_ac05_pass_through(text, model_due, expected):
    """AC-02 to AC-05, FR-014 to FR-017: local times are normalized with the right offset."""
    outcome = run_agent(text, DEFAULT_NOW, DEFAULT_TZ,
                        client=StubClient([_create("task", model_due)]))
    assert outcome.decision.due_at == expected


def test_us1_ac08_dst_offset_corrected():
    """AC-08, FR-018: a -04:00 offset from the model becomes -05:00 after DST ends."""
    outcome = run_agent("remind me tomorrow at 9am to call the bank", "2026-10-31T12:00:00-04:00",
                        "America/New_York",
                        client=StubClient([_create("call the bank", "2026-11-01T09:00:00-04:00")]))
    assert outcome.decision.due_at == "2026-11-01T09:00:00-05:00"


def test_us1_ac13_long_task_is_shortened_not_fallback():
    """AC-13, FR-022: a 260-character task is shortened to 1-200 chars, not a fallback."""
    long_task = "call mom about " + "the plans for the family holiday " * 8
    long_task = long_task[:260]
    assert len(long_task) == 260
    outcome = run_agent("remind me ...", DEFAULT_NOW, DEFAULT_TZ,
                        client=StubClient([_create(long_task, "2026-11-11T09:00:00")]))
    assert outcome.fallback is False
    task = outcome.decision.task
    assert 1 <= len(task) <= 200
    assert "call" in task and "mom" in task


def test_us1_request_sent_to_model_contains_text():
    """FR-014: exactly one model request is made and it carries the user text."""
    stub = StubClient([_create("call mom", "2026-11-11T09:00:00")])
    run_agent("remind me to call mom tomorrow at 9am", DEFAULT_NOW, DEFAULT_TZ, client=stub)
    assert len(stub.calls) == 1
    assert "remind me to call mom tomorrow at 9am" in stub.calls[0].user
