"""Reply parsing and schema validation (task T028; spec FR-005, FR-006, FR-007, FR-022).

The contract schema in ``schemas/reminder_output.schema.json`` is the single source of truth.
The API schema sent to the model is derived from it (research R-03); the full contract is
always enforced locally.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "schemas" / "reminder_output.schema.json"
TASK_LIMIT = 200
_UNSUPPORTED = ("minLength", "maxLength", "minimum", "maximum", "pattern", "format")


@lru_cache(maxsize=1)
def _contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def load_contract_schema() -> dict:
    """A fresh copy of the decision contract schema."""
    return json.loads(_contract_text())


SCHEMA_VERSION = load_contract_schema()["$id"].rsplit(":", 1)[-1]


def derive_api_schema(schema: dict) -> dict:
    """Copy of ``schema`` without keywords structured outputs may not support (R-03)."""
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items()
                    if k not in _UNSUPPORTED and not k.startswith("$")}
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node
    return strip(copy.deepcopy(schema))


def shorten_task(text: str, limit: int = TASK_LIMIT) -> str:
    """Shorten an over-long task deterministically, keeping the leading words (FR-022)."""
    if len(text) <= limit:
        return text
    head = text[:limit + 1]
    cut = head.rfind(" ")
    candidate = head[:cut] if cut > 0 else text[:limit]
    candidate = candidate.rstrip(" \t\n.,;:!?-")
    return candidate if candidate else text[:limit]


class ReplyError(ValueError):
    """The model reply could not be turned into a JSON object."""


def parse_json(text: str | None) -> dict:
    """Decode the reply text into a JSON object or raise ``ReplyError``."""
    if not text:
        raise ReplyError("empty reply")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReplyError(f"invalid JSON: {exc.msg}") from None
    if not isinstance(data, dict):
        raise ReplyError("reply is not a JSON object")
    return data


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load_contract_schema())


def validate_decision(data: dict) -> list[str]:
    """Full contract validation; returns ``["schema:<path>: <message>", ...]``."""
    problems = []
    for error in sorted(_validator().iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in error.absolute_path) or "(root)"
        problems.append(f"schema:{path}: {error.message}")
    due = data.get("due_at")
    if isinstance(due, str) and not problems:
        try:
            datetime.fromisoformat(due)
        except ValueError:
            problems.append(f"schema:due_at: not a valid datetime: {due!r}")
    return problems


def parse_reply(text: str | None) -> tuple[dict | None, list[str]]:
    """Parse and validate a reply as-is (no shortening or normalization)."""
    try:
        data = parse_json(text)
    except ReplyError as exc:
        return None, [f"unparseable: {exc}"]
    return data, validate_decision(data)
