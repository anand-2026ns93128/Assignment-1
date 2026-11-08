"""Shared test helpers: scripted model clients and frozen contexts (task T016).

No test makes a live API call (Constitution VIII, X).
"""

from __future__ import annotations

import json

import pytest

from reminder_agent.models import DECISION_KEYS, ModelReply, ModelRequest

DEFAULT_NOW = "2026-11-10T10:00:00+05:30"
DEFAULT_TZ = "Asia/Kolkata"
R1 = {"id": "r1", "task": "dentist appointment", "due_at": "2026-11-11T10:00:00+05:30"}
R2 = {"id": "r2", "task": "stand-up meeting", "due_at": "2026-11-10T10:00:00+05:30"}


class StubClient:
    """Returns scripted replies (or raises scripted exceptions) in order; records calls."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelReply:
        self.calls.append(request)
        if not self.script:
            raise AssertionError("StubClient called more times than scripted")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class NoCallClient:
    """Fails the test if any model call is attempted."""

    def __init__(self):
        self.calls = []

    def complete(self, request: ModelRequest) -> ModelReply:
        raise AssertionError("a model call was made where none is allowed")


def decision(**fields) -> dict:
    """A seven-key decision dict with unspecified fields set to null."""
    out = dict.fromkeys(DECISION_KEYS)
    out.update(fields)
    return out


def reply(payload, stop_reason: str = "end_turn", input_tokens: int = 1000,
          output_tokens: int = 80) -> ModelReply:
    """A ModelReply whose text is ``payload`` (a dict is JSON-encoded, a str is used as-is)."""
    text = payload if isinstance(payload, str) or payload is None else json.dumps(payload)
    return ModelReply(text=text, stop_reason=stop_reason, input_tokens=input_tokens,
                      output_tokens=output_tokens, model="claude-haiku-5-5")


@pytest.fixture
def default_ctx():
    return {"now": DEFAULT_NOW, "timezone": DEFAULT_TZ}


@pytest.fixture
def reminders_r1_r2():
    return [dict(R1), dict(R2)]
