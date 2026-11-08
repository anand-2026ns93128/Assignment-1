"""US3 tests for harness layer 1, schema validation (T039).

Covers FR-005, FR-006, FR-035 and AC-34. The layer loads the schema itself and does not
import the agent's parsing module.
"""

from __future__ import annotations

from pathlib import Path

import layer1_schema as l1
import pytest
from conftest import decision

VALID = decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00+05:30")


def test_us3_valid_decision_has_no_violations():
    """FR-005, FR-006: a contract-valid decision passes layer 1."""
    assert l1.check_schema(VALID) == []


@pytest.mark.parametrize("data, fr", [
    ({**VALID, "admin": True}, "FR-005"),
    ({k: v for k, v in VALID.items() if k != "refusal_reason"}, "FR-005"),
    ({**VALID, "intent": "delete"}, "FR-006"),
    ({**VALID, "task": "x" * 201}, "FR-006"),
    ({**VALID, "task": ""}, "FR-006"),
    ({**VALID, "snooze_minutes": 0}, "FR-006"),
    ({**VALID, "snooze_minutes": 1441}, "FR-006"),
    ({**VALID, "snooze_minutes": "15"}, "FR-006"),
    ({**VALID, "due_at": "2026-11-11T09:00:00"}, "FR-006"),
    ({**VALID, "due_at": "2026-02-30T09:00:00+05:30"}, "FR-006"),
    ("not an object", "FR-005"),
])
def test_us3_schema_violations_are_tagged(data, fr):
    """AC-34, FR-005, FR-006: each schema violation carries the FR it breaks."""
    violations = l1.check_schema(data)
    assert violations and violations[0]["id"] == fr
    assert violations[0]["message"]


def test_us3_layer1_is_independent_of_agent_code():
    """FR-035: layer 1 does not import the agent's parsing module."""
    source = Path(l1.__file__).read_text(encoding="utf-8")
    assert "reminder_agent" not in source
