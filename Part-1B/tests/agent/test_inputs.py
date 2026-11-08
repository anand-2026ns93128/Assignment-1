"""US1 tests for input validation (T017). Covers FR-001, FR-003 and AC-16."""

from __future__ import annotations

from conftest import DEFAULT_NOW, DEFAULT_TZ, R1, R2, NoCallClient

from reminder_agent.agent import run_agent
from reminder_agent.inputs import validate_inputs
from reminder_agent.models import ErrorResult, RequestContext


def test_us1_accepts_default_context():
    """FR-001: text, ISO-8601 now, IANA timezone and reminders are accepted."""
    ctx = validate_inputs("remind me", DEFAULT_NOW, DEFAULT_TZ, [R1, R2])
    assert isinstance(ctx, RequestContext)
    assert ctx.now.isoformat() == DEFAULT_NOW
    assert ctx.reminder_ids == {"r1", "r2"}


def test_us1_missing_reminder_list_is_empty():
    """FR-001: a missing reminder list is treated as empty."""
    ctx = validate_inputs("x", DEFAULT_NOW, DEFAULT_TZ, None)
    assert ctx.reminders == ()


def test_us1_unknown_timezone_is_input_error():
    """FR-003, AC-16: an unknown IANA timezone gives input_error naming the field."""
    err = validate_inputs("hi", DEFAULT_NOW, "Mars/Olympus", None)
    assert err == ErrorResult(status="input_error", category="invalid_timezone",
                              field="timezone", message=err.message, attempts=0)


def test_us1_invalid_now_is_input_error():
    """FR-003, AC-16: a now that is not ISO-8601 gives invalid_now."""
    err = validate_inputs("hi", "not-a-date", DEFAULT_TZ, None)
    assert isinstance(err, ErrorResult)
    assert (err.category, err.field) == ("invalid_now", "now")


def test_us1_bad_reminders_are_input_error():
    """FR-003, AC-16: duplicate ids, missing task or a bad due_at give invalid_reminders."""
    bad_lists = [
        [R1, dict(R1)],
        [{"id": "r9", "due_at": DEFAULT_NOW}],
        [{"id": "r9", "task": "x", "due_at": "tomorrow"}],
        "not a list",
    ]
    for reminders in bad_lists:
        err = validate_inputs("hi", DEFAULT_NOW, DEFAULT_TZ, reminders)
        assert isinstance(err, ErrorResult), reminders
        assert (err.category, err.field) == ("invalid_reminders", "existing_reminders")


def test_us1_naive_now_is_wall_time_in_timezone():
    """FR-001 (assumption): a now without an offset is wall time in the given timezone."""
    ctx = validate_inputs("x", "2026-11-10T10:00:00", "America/New_York", None)
    assert ctx.now.isoformat() == "2026-11-10T10:00:00-05:00"


def test_us1_input_error_makes_no_model_call():
    """FR-003, AC-16: run_agent returns the input_error without any model request."""
    outcome = run_agent("hi", DEFAULT_NOW, "Mars/Olympus", client=NoCallClient())
    assert outcome.decision is None
    assert outcome.error.category == "invalid_timezone"
    assert outcome.attempts == 0
