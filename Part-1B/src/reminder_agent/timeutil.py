"""Deterministic time handling (task T027; spec FR-014, FR-018, FR-024; research R-04).

Everything here is computed from the injected ``now`` and timezone with ``zoneinfo``. Nothing
reads the system clock or the machine's timezone (Constitution III).
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

CALENDAR_DAYS = 7


def _offset(dt: datetime) -> str:
    """Format a UTC offset as ``+HH:MM``."""
    return dt.isoformat(timespec="seconds")[-6:] if dt.utcoffset() else "+00:00"


def _iso(dt: datetime) -> str:
    """ISO-8601 with seconds and an explicit numeric offset (never ``Z``)."""
    return dt.replace(microsecond=0).isoformat(timespec="seconds")


def _noon(day, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time(12, 0), tzinfo=tz)


def calendar_context(now: datetime, tz: ZoneInfo) -> str:
    """Calendar facts for the prompt, computed from the injected clock (research R-04)."""
    local = now.astimezone(tz)
    today = local.date()
    lines = [
        f"Current local time: {_iso(local)} ({local.strftime('%A')}), timezone {tz.key}, "
        f"UTC offset {_offset(local)}",
        f"Current UTC time: {_iso(local.astimezone(UTC))}",
        f"Today: {today.isoformat()} ({today.strftime('%A')})",
        f"Tomorrow: {(today + timedelta(days=1)).isoformat()} "
        f"({(today + timedelta(days=1)).strftime('%A')})",
        "Next 7 days:",
    ]
    for n in range(1, CALENDAR_DAYS + 1):
        day = today + timedelta(days=n)
        lines.append(f"- {day.isoformat()} ({day.strftime('%A')})")
    previous = local
    for n in range(0, CALENDAR_DAYS + 2):
        day = today + timedelta(days=n)
        current = _noon(day, tz)
        if current.utcoffset() != previous.utcoffset():
            lines.append(
                f"Note: clocks change on {day.isoformat()}: UTC offset goes from "
                f"{_offset(previous)} to {_offset(current)}.")
            break
        previous = current
    return "\n".join(lines)


def normalize_due_at(value: str, tz: ZoneInfo) -> str:
    """Treat ``value`` as local wall time in ``tz`` and attach the correct offset (FR-018).

    Any offset supplied by the model is discarded. A time inside a spring-forward gap moves
    forward by the gap length; a repeated (fall-back) time resolves to its first occurrence.
    Raises ``ValueError`` if ``value`` is not ISO-8601.
    """
    wall = datetime.fromisoformat(value).replace(tzinfo=None)
    first = wall.replace(tzinfo=tz, fold=0)
    # Round-tripping through UTC moves a non-existent (gap) time forward by the gap length.
    return _iso(first.astimezone(UTC).astimezone(tz))


def snooze_due_at(now: datetime, minutes: int) -> str:
    """``now`` plus an exact elapsed duration, in now's timezone (FR-014, FR-024)."""
    tz = now.tzinfo
    return _iso((now.astimezone(UTC) + timedelta(minutes=minutes)).astimezone(tz))


def is_not_before(due_at: str, now: datetime) -> bool:
    """True when ``due_at`` (ISO-8601 with offset) is at or after ``now`` (FR-009)."""
    return datetime.fromisoformat(due_at) >= now
