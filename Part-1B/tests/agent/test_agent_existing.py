"""US4 scenario tests: reschedule and snooze with stubbed replies (T055).

Covers FR-010, FR-011, FR-023, FR-024, FR-025 and AC-53 to AC-57.
"""

from __future__ import annotations

from conftest import DEFAULT_NOW, DEFAULT_TZ, R1, R2, StubClient, decision, reply

from reminder_agent.agent import run_agent
from reminder_agent.models import FALLBACK_DECISION

REMINDERS = [R1, R2]


def _run(text, payload, reminders=REMINDERS):
    return run_agent(text, DEFAULT_NOW, DEFAULT_TZ, reminders,
                     client=StubClient([reply(payload)]))


def test_us4_ac53_reschedule_dentist_to_friday_4pm():
    """AC-53, FR-023: reschedule r1 to 2026-11-13T16:00+05:30."""
    out = _run("move my dentist reminder to Friday at 4pm",
               decision(intent="reschedule", target_id="r1", due_at="2026-11-13T16:00:00"))
    d = out.decision.to_json()
    assert (d["intent"], d["target_id"], d["due_at"]) == \
        ("reschedule", "r1", "2026-11-13T16:00:00+05:30")


def test_us4_ac54_snooze_due_at_is_now_plus_minutes():
    """AC-54, FR-024: snooze r2 for 15 min; due_at is overridden to now + 15 minutes."""
    for model_due in (None, "2026-11-10T11:00:00", "2026-11-10T10:15:00"):
        out = _run("snooze the stand-up reminder for 15 minutes",
                   decision(intent="snooze", target_id="r2", snooze_minutes=15,
                            due_at=model_due))
        d = out.decision.to_json()
        assert (d["intent"], d["target_id"], d["snooze_minutes"]) == ("snooze", "r2", 15)
        assert d["due_at"] == "2026-11-10T10:15:00+05:30"


def test_us4_ac55_missing_target_clarify_passes():
    """AC-55, FR-025: no matching reminder -> a clarify reply passes with target_id null."""
    out = _run("snooze my gym reminder for 10 minutes",
               decision(intent="clarify", clarification_question="Which reminder?"),
               reminders=[])
    assert out.decision.intent == "clarify" and out.decision.target_id is None


def test_us4_unknown_target_becomes_fallback():
    """FR-010: a snooze aimed at a reminder that does not exist becomes the fallback."""
    out = _run("snooze my gym reminder for 10 minutes",
               decision(intent="snooze", target_id="r9", snooze_minutes=10))
    assert out.decision == FALLBACK_DECISION
    assert out.fallback_reason == "invariant:FR-010"


def test_us4_ac56_ambiguous_target_clarify_names_candidates():
    """AC-56, FR-025: two equal matches -> a clarify naming both candidates passes through."""
    reminders = [{"id": "r3", "task": "call Priya", "due_at": "2026-11-11T10:00:00+05:30"},
                 {"id": "r4", "task": "call Priya's manager",
                  "due_at": "2026-11-11T11:00:00+05:30"}]
    question = "Do you mean 'call Priya' (r3) or 'call Priya's manager' (r4)?"
    out = _run("push my call Priya reminder to 6pm",
               decision(intent="clarify", clarification_question=question), reminders)
    assert out.decision.intent == "clarify"
    assert "r3" in out.decision.clarification_question
    assert "r4" in out.decision.clarification_question


def test_us4_ac57_snooze_out_of_range():
    """AC-57, FR-024: 2880 minutes is out of range -> fallback; a clarify reply passes."""
    bad = _run("snooze the stand-up reminder for 2 days",
               decision(intent="snooze", target_id="r2", snooze_minutes=2880))
    assert bad.decision == FALLBACK_DECISION and bad.fallback_reason.startswith("schema:")
    ok = _run("snooze the stand-up reminder for 2 days",
              decision(intent="clarify", clarification_question="Up to 24 hours. How long?"))
    assert ok.decision.intent == "clarify" and ok.decision.snooze_minutes is None


def test_us4_reschedule_without_due_at_becomes_fallback():
    """FR-023: a reschedule must carry a new due_at; without one it is the fallback."""
    out = _run("move my dentist reminder",
               decision(intent="reschedule", target_id="r1", due_at=None))
    assert out.decision == FALLBACK_DECISION
    assert out.fallback_reason == "invariant:FR-023"
