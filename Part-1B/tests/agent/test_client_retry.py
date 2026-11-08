"""US2 tests for retry and infra_error mapping with a fake SDK (T035), no network.

Covers FR-031, AC-30, research R-06 and Constitution VII and IX.
"""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx  # the anthropic 2.x SDK uses httpx2
import pytest
from conftest import DEFAULT_NOW, DEFAULT_TZ

from reminder_agent import cli
from reminder_agent.agent import run_agent
from reminder_agent.client import AnthropicClient
from reminder_agent.config import load_config

FAKE_KEY = "sk-" + "ant-test-123"
REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _status_error(cls, status):
    response = httpx.Response(status, request=REQ)
    return cls(f"HTTP {status} key={FAKE_KEY}", response=response, body=None)


def _timeout():
    return anthropic.APITimeoutError(request=REQ)


def _connection():
    return anthropic.APIConnectionError(message=f"conn refused {FAKE_KEY}", request=REQ)


def _ok_message():
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps({
            "intent": "clarify", "task": None, "due_at": None, "target_id": None,
            "snooze_minutes": None, "clarification_question": "When?", "refusal_reason": None}))],
        stop_reason="end_turn", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-haiku-5-5")


class ScriptedSDK:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _client(script):
    sdk = ScriptedSDK(script)
    return AnthropicClient(load_config(env={}), sdk_factory=lambda **kw: sdk), sdk


def _run(script, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    client, sdk = _client(script)
    sleeps = []
    outcome = run_agent("remind me to call mom tomorrow at 9am", DEFAULT_NOW, DEFAULT_TZ,
                        client=client, sleeper=sleeps.append)
    return outcome, sdk, sleeps


def test_us2_timeout_then_success_retries_once(monkeypatch):
    """AC-30, R-06: a timeout is retried once; success on the second attempt."""
    outcome, sdk, sleeps = _run([_timeout(), _ok_message()], monkeypatch)
    assert outcome.decision is not None and outcome.attempts == 2
    assert sdk.calls == 2 and sleeps == [1.0]


@pytest.mark.parametrize("make, category", [
    (lambda: _status_error(anthropic.RateLimitError, 429), "rate_limit"),
    (lambda: _status_error(anthropic.InternalServerError, 500), "server_error"),
    (lambda: _status_error(anthropic.OverloadedError, 529), "server_error"),
    (_connection, "connection"),
    (_timeout, "timeout"),
])
def test_us2_retryable_errors_twice_give_infra_error(make, category, monkeypatch):
    """AC-30, FR-031: two retryable failures give infra_error with attempts=2."""
    outcome, sdk, _ = _run([make(), make()], monkeypatch)
    assert outcome.decision is None
    assert outcome.error.status == "infra_error"
    assert outcome.error.category == category
    assert outcome.error.attempts == 2 and sdk.calls == 2


@pytest.mark.parametrize("make, category", [
    (lambda: _status_error(anthropic.AuthenticationError, 401), "auth"),
    (lambda: _status_error(anthropic.PermissionDeniedError, 403), "auth"),
    (lambda: _status_error(anthropic.BadRequestError, 400), "request_rejected"),
    (lambda: _status_error(anthropic.NotFoundError, 404), "request_rejected"),
])
def test_us2_non_retryable_errors_fail_immediately(make, category, monkeypatch):
    """AC-30, R-06: auth and bad-request errors are not retried (attempts=1)."""
    outcome, sdk, sleeps = _run([make()], monkeypatch)
    assert outcome.error.category == category
    assert outcome.error.attempts == 1 and sdk.calls == 1 and sleeps == []


def test_us2_error_message_never_contains_api_key(monkeypatch):
    """FR-031, Constitution IX: error messages are scrubbed of the API key."""
    outcome, _, _ = _run([_status_error(anthropic.AuthenticationError, 401)], monkeypatch)
    assert "ant-test-123" not in json.dumps(outcome.error.to_json())
    outcome, _, _ = _run([_connection(), _connection()], monkeypatch)
    assert "ant-test-123" not in json.dumps(outcome.error.to_json())


def test_us2_cli_infra_error_exit_4(monkeypatch):
    """AC-30, FR-031: the CLI prints the error JSON to stderr and exits 4."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    client, _ = _client([_status_error(anthropic.AuthenticationError, 401)])
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--text", "remind me to call mom at 9pm", "--now", DEFAULT_NOW,
                     "--timezone", DEFAULT_TZ], client=client, stdout=out, stderr=err)
    assert code == 4 and out.getvalue() == ""
    data = json.loads(err.getvalue())
    assert data["status"] == "infra_error" and data["category"] == "auth"
    assert "ant-test-123" not in err.getvalue()
