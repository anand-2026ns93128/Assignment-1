"""US1 tests for deterministic time handling (T018).

Covers FR-014, FR-018, FR-024, AC-06 to AC-10 and AC-12. No model is involved.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from reminder_agent import timeutil

KOLKATA = ZoneInfo("Asia/Kolkata")
NEW_YORK = ZoneInfo("America/New_York")
OFFSET_RE = re.compile(r"[+-]\d{2}:\d{2}$")


def _now(text, tz):
    return datetime.fromisoformat(text).astimezone(tz)


def test_us1_calendar_context_lists_dates_and_offset():
    """FR-014: the calendar gives local now, weekday, today, tomorrow, next 7 days, offset."""
    text = timeutil.calendar_context(_now("2026-11-10T10:00:00+05:30", KOLKATA), KOLKATA)
    assert "2026-11-10T10:00:00+05:30" in text
    assert "Tuesday" in text
    assert "Today: 2026-11-10 (Tuesday)" in text
    assert "Tomorrow: 2026-11-11 (Wednesday)" in text
    assert "2026-11-16 (Monday)" in text and "2026-11-17 (Tuesday)" in text
    assert "UTC offset +05:30" in text
    assert "Asia/Kolkata" in text


def test_us1_calendar_context_notes_dst_change():
    """FR-018: an upcoming DST transition is called out with old and new offsets."""
    text = timeutil.calendar_context(_now("2026-10-31T12:00:00-04:00", NEW_YORK), NEW_YORK)
    assert "2026-11-01" in text
    assert "-04:00" in text and "-05:00" in text
    assert "clocks change" in text.lower()


def test_us1_normalize_reattaches_correct_offset_after_dst_end():
    """AC-08, FR-018: a wrong offset from the model is replaced by the zone's real offset."""
    assert timeutil.normalize_due_at("2026-11-01T09:00:00-04:00", NEW_YORK) == \
        "2026-11-01T09:00:00-05:00"
    assert timeutil.normalize_due_at("2026-11-01T09:00:00", NEW_YORK) == \
        "2026-11-01T09:00:00-05:00"


def test_us1_normalize_gap_moves_forward():
    """AC-09, FR-018: a local time inside the spring-forward gap moves forward by the gap."""
    assert timeutil.normalize_due_at("2026-03-08T02:30:00", NEW_YORK) == \
        "2026-03-08T03:30:00-04:00"


def test_us1_normalize_fold_takes_first_occurrence():
    """AC-10, FR-018: a repeated local time resolves to its first occurrence."""
    assert timeutil.normalize_due_at("2026-11-01T01:30:00", NEW_YORK) == \
        "2026-11-01T01:30:00-04:00"


def test_us1_midnight_and_month_end_pass_through():
    """AC-06, AC-07, FR-014: date rollovers resolved by the model keep the right offset."""
    assert timeutil.normalize_due_at("2026-11-11T00:10:00", KOLKATA) == \
        "2026-11-11T00:10:00+05:30"
    assert timeutil.normalize_due_at("2026-02-01T08:00:00+05:30", KOLKATA) == \
        "2026-02-01T08:00:00+05:30"


def test_us1_add_minutes_is_elapsed_time_across_midnight():
    """AC-06, FR-014: 'in N minutes' is exact elapsed time, rolling over midnight."""
    now = _now("2026-11-10T23:50:00+05:30", KOLKATA)
    assert timeutil.snooze_due_at(now, 20) == "2026-11-11T00:10:00+05:30"


def test_us1_output_always_has_explicit_offset():
    """AC-12: every normalized due_at carries an explicit UTC offset."""
    for value, tz in [("2026-11-11T09:00:00", KOLKATA), ("2026-03-08T02:30:00", NEW_YORK),
                      ("2026-07-01T12:00:00Z", NEW_YORK)]:
        assert OFFSET_RE.search(timeutil.normalize_due_at(value, tz))


def test_us1_snooze_due_at():
    """FR-024: snooze due_at is now plus snooze_minutes."""
    assert timeutil.snooze_due_at(_now("2026-11-10T10:00:00+05:30", KOLKATA), 15) == \
        "2026-11-10T10:15:00+05:30"


def test_us1_is_not_before():
    """FR-009: comparison is by absolute instant."""
    now = _now("2026-11-10T10:00:00+05:30", KOLKATA)
    assert timeutil.is_not_before("2026-11-10T04:30:00+00:00", now)
    assert not timeutil.is_not_before("2026-11-10T09:59:00+05:30", now)
