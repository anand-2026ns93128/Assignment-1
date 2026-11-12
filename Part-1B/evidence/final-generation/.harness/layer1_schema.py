"""Harness layer 1: schema validation (task T047; spec FR-005, FR-006, FR-035).

Independent of the agent: loads the contract schema itself. Every violation is tagged with the
requirement it breaks: FR-005 for the key set (extra/missing keys, not an object), FR-006 for
field types and ranges.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "reminder_output.schema.json"
_KEYSET_VALIDATORS = {"additionalProperties", "required"}


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def check_schema(decision: object) -> list[dict]:
    """Return ``[{"id": "FR-005"|"FR-006", "message": ...}]``; empty means valid."""
    if not isinstance(decision, dict):
        return [{"id": "FR-005", "message": "decision is not a JSON object"}]
    violations = []
    errors = sorted(_validator().iter_errors(decision),
                    key=lambda e: (e.validator not in _KEYSET_VALIDATORS, list(e.absolute_path)))
    for error in errors:
        path = "/".join(str(p) for p in error.absolute_path) or "(root)"
        fr = "FR-005" if error.validator in _KEYSET_VALIDATORS and not error.absolute_path \
            else "FR-006"
        violations.append({"id": fr, "message": f"{path}: {error.message}"})
    due = decision.get("due_at")
    if isinstance(due, str) and not violations:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            violations.append({"id": "FR-006", "message": f"due_at is not a valid datetime: {due}"})
    return violations
