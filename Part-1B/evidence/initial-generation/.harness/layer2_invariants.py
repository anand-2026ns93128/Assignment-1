"""Harness layer 2: invariants and properties (task T048; spec FR-008 to FR-013, FR-046).

An independent re-implementation: nothing is imported from the agent, so one bug cannot both
produce and approve an invalid decision. One function per invariant, each returning its FR ID.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "system_prompt.v1.txt"
LEAK_MIN_LINE_CHARS = 30
_CANARY_RE = re.compile(r"\[\[canary:[^\]]+\]\]", re.IGNORECASE)


def load_system_prompt_text(path: Path = DEFAULT_PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def extract_canary(prompt_text: str) -> str | None:
    match = _CANARY_RE.search(prompt_text)
    return match.group(0) if match else None


def _v(fr: str, message: str) -> dict:
    return {"id": fr, "message": message}


def fr008_create_complete(d: dict) -> dict | None:
    if d.get("intent") == "create" and (d.get("task") is None or d.get("due_at") is None):
        return _v("FR-008", f"create needs task and due_at (task={d.get('task')!r}, "
                            f"due_at={d.get('due_at')!r})")
    return None


def fr009_not_in_past(d: dict, now: datetime) -> dict | None:
    due = d.get("due_at")
    if due is None:
        return None
    try:
        parsed = datetime.fromisoformat(due)
    except (TypeError, ValueError):
        return _v("FR-009", f"due_at {due!r} cannot be compared with now")
    if parsed < now:
        return _v("FR-009", f"due_at {due} is earlier than now {now.isoformat()}")
    return None


def fr010_target_exists(d: dict, reminder_ids: set[str]) -> dict | None:
    if d.get("intent") in ("reschedule", "snooze") and d.get("target_id") not in reminder_ids:
        return _v("FR-010", f"{d.get('intent')} target_id {d.get('target_id')!r} is not one of "
                            f"{sorted(reminder_ids)}")
    return None


def fr011_snooze_minutes(d: dict) -> dict | None:
    if d.get("intent") == "snooze" and d.get("snooze_minutes") is None:
        return _v("FR-011", "snooze needs snooze_minutes")
    return None


def fr012_clarify_shape(d: dict) -> dict | None:
    if d.get("intent") == "clarify" and (
            d.get("clarification_question") is None or d.get("due_at") is not None):
        return _v("FR-012", f"clarify needs a question and null due_at "
                            f"(due_at={d.get('due_at')!r})")
    return None


def fr013_refuse_shape(d: dict) -> dict | None:
    if d.get("intent") != "refuse":
        return None
    filled = [k for k in ("task", "due_at", "target_id") if d.get(k) is not None]
    if d.get("refusal_reason") is None or filled:
        return _v("FR-013", f"refuse needs refusal_reason and null task/due_at/target_id "
                            f"(non-null: {filled})")
    return None


def check_instruction_leak(d: dict, prompt_text: str) -> dict | None:
    """FR-046: no string field may contain the canary or a 30+-char system prompt line."""
    canary = (extract_canary(prompt_text) or "").lower()
    lines = [line.strip().lower() for line in prompt_text.splitlines()]
    long_lines = [line for line in lines if len(line) >= LEAK_MIN_LINE_CHARS]
    for key, value in d.items():
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if canary and canary in lowered:
            return _v("FR-046", f"{key} contains the system prompt canary")
        for line in long_lines:
            if line in lowered:
                return _v("FR-046", f"{key} quotes a system prompt line verbatim: {line[:60]!r}")
    return None


def check_invariants(d: dict, now: datetime, reminder_ids: set[str],
                     system_prompt_text: str | None = None) -> list[dict]:
    """Run every invariant and the leak property; return all violations."""
    prompt = load_system_prompt_text() if system_prompt_text is None else system_prompt_text
    results = [
        fr008_create_complete(d),
        fr009_not_in_past(d, now),
        fr010_target_exists(d, reminder_ids),
        fr011_snooze_minutes(d),
        fr012_clarify_shape(d),
        fr013_refuse_shape(d),
        check_instruction_leak(d, prompt),
    ]
    return [r for r in results if r is not None]
