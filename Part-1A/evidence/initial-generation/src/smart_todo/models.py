"""Task entity, enumerations and value rules (data-model.md).

Tasks T012 (constants, Task), T014 (shared validators) and T023 (US1 validators).
The same validators are used for user input and for data-file validation, so both
apply identical rules.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from smart_todo import errors

PRIORITIES = ("low", "medium", "high")
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
STATUSES = ("todo", "in_progress", "done")
DEFAULT_PRIORITY = "medium"

_TASK_ID = re.compile(r"[0-9]+", flags=re.ASCII)


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    priority: str
    status: str
    tags: tuple[str, ...]


def parse_task_id(raw: str) -> int:
    """ASCII decimal digits with value >= 1 (FR-011; research R4)."""
    if _TASK_ID.fullmatch(raw) is None or int(raw) < 1:
        raise errors.invalid_task_id(raw)
    return int(raw)


def validate_status(raw: str) -> str:
    """One of ``todo``, ``in_progress``, ``done``; case-sensitive (FR-010)."""
    if raw not in STATUSES:
        raise errors.invalid_status(raw)
    return raw


_TAG = re.compile(r"[A-Za-z0-9_-]{1,20}", flags=re.ASCII)
MAX_TITLE_LENGTH = 100


def validate_title(raw: str) -> str:
    """Reject any control character in the raw value, trim, then 1-100 code points (FR-002)."""
    if any(unicodedata.category(ch) == "Cc" for ch in raw):
        raise errors.invalid_title()
    title = raw.strip()
    if not 1 <= len(title) <= MAX_TITLE_LENGTH:
        raise errors.invalid_title()
    return title


def validate_priority(raw: str) -> str:
    """One of ``low``, ``medium``, ``high``; case-sensitive (FR-003)."""
    if raw not in PRIORITIES:
        raise errors.invalid_priority(raw)
    return raw


def normalize_tags(raws: list[str] | None) -> tuple[str, ...]:
    """Validate (ASCII letters, digits, '-', '_'; 1-20 chars), lowercase, dedupe (FR-004)."""
    tags: list[str] = []
    for raw in raws or ():
        if _TAG.fullmatch(raw) is None:
            raise errors.invalid_tag(raw)
        tag = raw.lower()
        if tag not in tags:
            tags.append(tag)
    return tuple(tags)


# Task T040: the only allowed status changes (FR-010). Same-status moves are rejected.
ALLOWED_TRANSITIONS = frozenset(
    {("todo", "in_progress"), ("in_progress", "done"), ("todo", "done")}
)


def check_transition(task_id: int, old: str, new: str) -> None:
    if (old, new) not in ALLOWED_TRANSITIONS:
        raise errors.invalid_transition(task_id, old, new)
