"""Evaluation dataset loading and validation (task T013; spec FR-032, FR-033, FR-034).

The harness validates ``evals/dataset.json`` independently of the agent's own input checks,
so a bug in the agent cannot make an invalid case look valid.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "evals" / "dataset.json"
DEFAULT_SPEC = ROOT / "specs" / "001-nl-reminder-agent" / "spec.md"
DATASET_SCHEMA = ROOT / "specs" / "001-nl-reminder-agent" / "contracts" / "dataset.schema.json"

MIN_CASES = 18
CATEGORY_MINIMUMS = {
    "normal": 4, "boundary": 3, "ambiguous": 1, "missing_task": 1, "missing_time": 1,
    "malformed": 3, "reschedule_snooze": 2, "guardrail": 3,
}
REQUIRED_TAGS = {
    "boundary": {"midnight", "month_end", "dst"},
    "malformed": {"empty", "gibberish", "long"},
    "reschedule_snooze": {"reschedule", "snooze"},
    "guardrail": {"out_of_scope", "harmful", "injection"},
}


def load_dataset(path: Path = DEFAULT_DATASET) -> tuple[dict, str]:
    """Return ``(data, sha256_of_file_bytes)``."""
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def expand_input(case: dict) -> str:
    """Expand a ``{"repeat": s, "times": n}`` input to ``s * n``; plain strings pass through."""
    value = case["input"]
    if isinstance(value, dict):
        return value["repeat"] * value["times"]
    return value


def spec_requirement_ids(spec_path: Path = DEFAULT_SPEC) -> set[str]:
    """All ``**FR-xxx**`` identifiers defined in the spec."""
    text = Path(spec_path).read_text(encoding="utf-8")
    return set(re.findall(r"\*\*(FR-\d{3})\*\*", text))


def _aware(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _schema_problems(data: dict) -> list[str]:
    schema = json.loads(DATASET_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    problems = []
    cases = data.get("cases") if isinstance(data, dict) else None
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = list(error.absolute_path)
        prefix = "dataset"
        if len(path) >= 2 and path[0] == "cases" and isinstance(cases, list):
            index = path[1]
            case = cases[index] if index < len(cases) else {}
            prefix = str(case.get("id", f"case[{index}]")) if isinstance(case, dict) else prefix
        if error.validator == "minItems" and path == ["cases"]:
            problems.append(f"dataset: at least {MIN_CASES} cases are required")
            continue
        location = "/".join(str(p) for p in path[2:]) or "case"
        problems.append(f"{prefix}: {location}: {error.message}")
    return problems


def _case_problems(case: dict, known_ids: set[str]) -> list[str]:
    cid = case.get("id", "?")
    out: list[str] = []
    for req in case.get("requirements", []):
        if isinstance(req, str) and req not in known_ids:
            out.append(f"{cid}: requirements: {req} is not defined in spec.md")
    try:
        ZoneInfo(str(case.get("timezone")))
    except (ZoneInfoNotFoundError, ValueError):
        out.append(f"{cid}: timezone: unknown IANA timezone {case.get('timezone')!r}")
    now = _aware(case.get("now"))
    if now is None:
        out.append(f"{cid}: now: not an ISO-8601 datetime with an offset: {case.get('now')!r}")
    expected = case.get("expected_due_at")
    if expected is not None:
        due = _aware(expected)
        if due is None:
            out.append(f"{cid}: expected_due_at: not an ISO-8601 datetime with an offset")
        elif now is not None and due < now:
            out.append(f"{cid}: expected_due_at {expected} is earlier than now {case.get('now')}")
    if case.get("due_at_tolerance_minutes", 1) != 1:
        out.append(f"{cid}: due_at_tolerance_minutes must equal 1")
    reminders = case.get("existing_reminders") or []
    ids = [r.get("id") for r in reminders if isinstance(r, dict)]
    for rid, count in Counter(ids).items():
        if count > 1:
            out.append(f"{cid}: existing_reminders: duplicate reminder id {rid!r}")
    for reminder in reminders:
        if isinstance(reminder, dict) and _aware(reminder.get("due_at")) is None:
            out.append(f"{cid}: existing_reminders: {reminder.get('id')!r} has an invalid due_at")
    return out


def validate_dataset(data: dict, spec_path: Path = DEFAULT_SPEC) -> list[str]:
    """Return every FR-034 problem; an empty list means the dataset is valid."""
    problems = _schema_problems(data)
    cases = [c for c in (data.get("cases") or []) if isinstance(c, dict)]
    if len(cases) < MIN_CASES and not any("at least" in p for p in problems):
        problems.append(f"dataset: at least {MIN_CASES} cases are required, found {len(cases)}")
    for cid, count in Counter(c.get("id") for c in cases).items():
        if count > 1:
            problems.append(f"dataset: duplicate case id {cid!r}")
    by_category = Counter(c.get("category") for c in cases)
    for category, minimum in CATEGORY_MINIMUMS.items():
        if by_category[category] < minimum:
            problems.append(f"dataset: category {category} needs at least {minimum} cases, "
                            f"found {by_category[category]}")
    for category, tags in REQUIRED_TAGS.items():
        present = {t for c in cases if c.get("category") == category for t in c.get("tags", [])}
        missing = sorted(tags - present)
        if missing:
            problems.append(f"dataset: category {category} is missing tag coverage: "
                            f"{', '.join(missing)}")
    known = spec_requirement_ids(spec_path)
    for case in cases:
        problems.extend(_case_problems(case, known))
    return problems
