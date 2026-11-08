"""Input validation (task T026; spec FR-001, FR-003).

Invalid ``now``, timezone or reminder list gives an ``input_error`` result: no decision and no
model request.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import ErrorResult, ExistingReminder, RequestContext


def _input_error(category: str, field: str, message: str) -> ErrorResult:
    return ErrorResult(status="input_error", category=category, field=field, message=message,
                       attempts=0)


def _parse_aware(value: object, tz: ZoneInfo | None = None) -> datetime | None:
    """Parse ISO-8601; a naive value is wall time in ``tz`` (or rejected when tz is None)."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        if tz is None:
            return None
        parsed = parsed.replace(tzinfo=tz, fold=0)
    return parsed


def validate_inputs(text: object, now: object, timezone: object,
                    reminders: object = None) -> RequestContext | ErrorResult:
    """Return a validated ``RequestContext`` or an ``input_error`` ``ErrorResult``."""
    try:
        if not isinstance(timezone, str) or not timezone:
            raise ValueError
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return _input_error("invalid_timezone", "timezone",
                            f"Unknown IANA timezone: {timezone!r}")

    parsed_now = _parse_aware(now, tz)
    if parsed_now is None:
        return _input_error("invalid_now", "now", f"now is not an ISO-8601 datetime: {now!r}")
    parsed_now = parsed_now.astimezone(tz)

    if reminders is None:
        reminders = []
    if not isinstance(reminders, list):
        return _input_error("invalid_reminders", "existing_reminders",
                            "existing_reminders must be a list")
    items: list[ExistingReminder] = []
    for index, item in enumerate(reminders):
        if not isinstance(item, dict):
            return _input_error("invalid_reminders", "existing_reminders",
                                f"reminder {index} is not an object")
        rid, task = item.get("id"), item.get("task")
        if not isinstance(rid, str) or not rid or not isinstance(task, str) or not task:
            return _input_error("invalid_reminders", "existing_reminders",
                                f"reminder {index} needs a non-empty id and task")
        due = _parse_aware(item.get("due_at"))
        if due is None:
            return _input_error("invalid_reminders", "existing_reminders",
                                f"reminder {rid!r} has an invalid due_at")
        items.append(ExistingReminder(id=rid, task=task, due_at=due.astimezone(tz)))
    duplicates = [rid for rid, count in Counter(r.id for r in items).items() if count > 1]
    if duplicates:
        return _input_error("invalid_reminders", "existing_reminders",
                            f"duplicate reminder id(s): {', '.join(sorted(duplicates))}")

    return RequestContext(text="" if text is None else str(text), now=parsed_now, timezone=tz,
                          reminders=tuple(items))
