"""US1 tests for reply parsing and schema handling (T019).

Covers FR-005, FR-006, FR-007, FR-022, AC-11 and AC-13.
"""

from __future__ import annotations

import json

import pytest
from conftest import decision

from reminder_agent import parsing


def _valid():
    return decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00+05:30")


def test_us1_accepts_seven_keys_with_nulls():
    """FR-005, AC-11: a decision with all seven keys (nulls allowed) parses cleanly."""
    data, problems = parsing.parse_reply(json.dumps(_valid()))
    assert problems == [] and data["intent"] == "create"


@pytest.mark.parametrize("mutate, reason", [
    (lambda d: "not json at all", "unparseable"),
    (lambda d: json.dumps({**d, "admin": True}), "schema"),
    (lambda d: json.dumps({k: v for k, v in d.items() if k != "target_id"}), "schema"),
    (lambda d: json.dumps({**d, "task": "x" * 201}), "schema"),
    (lambda d: json.dumps({**d, "intent": "snooze", "snooze_minutes": 0}), "schema"),
    (lambda d: json.dumps({**d, "intent": "snooze", "snooze_minutes": 1441}), "schema"),
    (lambda d: json.dumps({**d, "due_at": "2026-11-11T09:00:00"}), "schema"),
    (lambda d: json.dumps({**d, "due_at": "2026-13-45T09:00:00+05:30"}), "schema"),
    (lambda d: json.dumps([1, 2]), "unparseable"),
])
def test_us1_rejects_invalid_replies(mutate, reason):
    """FR-005, FR-006, AC-11, AC-13: invalid JSON or schema violations are reported."""
    data, problems = parsing.parse_reply(mutate(_valid()))
    assert problems and problems[0].startswith(reason)


def test_us1_derive_api_schema_strips_unsupported_keywords():
    """R-03: the API schema drops length/range/pattern/format keywords, keeps structure."""
    contract = parsing.load_contract_schema()
    api = parsing.derive_api_schema(contract)
    text = json.dumps(api)
    for keyword in ("minLength", "maxLength", "minimum", "maximum", "pattern", "format"):
        assert f'"{keyword}"' not in text
    assert api["additionalProperties"] is False
    assert api["required"] == contract["required"]
    assert api["properties"]["intent"]["enum"] == ["create", "reschedule", "snooze", "clarify",
                                                   "refuse"]
    assert "minLength" in json.dumps(contract)   # the contract itself is not modified


def test_us1_schema_version_exposed():
    """FR-007: the contract schema version is 1.0.0."""
    assert parsing.SCHEMA_VERSION == "1.0.0"


def test_us1_shorten_task_keeps_short_text():
    """FR-022: tasks of at most 200 characters are unchanged."""
    assert parsing.shorten_task("call mom") == "call mom"
    assert parsing.shorten_task("x" * 200) == "x" * 200


def test_us1_shorten_task_cuts_at_word_boundary():
    """FR-022, AC-13: long tasks are cut at the last whitespace, keeping the leading words."""
    text = "call mom about " + "the holiday plans, " * 20
    out = parsing.shorten_task(text)
    assert 1 <= len(out) <= 200
    assert out.startswith("call mom about")
    assert not out.endswith((" ", ","))
    assert text.startswith(out)


def test_us1_shorten_task_hard_cut_without_whitespace():
    """FR-022: with no whitespace, the task is hard-cut at 200 characters."""
    assert parsing.shorten_task("y" * 300) == "y" * 200
