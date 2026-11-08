"""US1 tests for the Anthropic request shape (T022), using a fake SDK object (no network).

Covers research R-02 and R-03, the plan Constraints (temperature at the model default) and FR-040.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from reminder_agent.client import AnthropicClient
from reminder_agent.config import load_config
from reminder_agent.models import ModelRequest

SCHEMA = {"type": "object", "additionalProperties": False}


class FakeSDK:
    def __init__(self, **client_kwargs):
        self.client_kwargs = client_kwargs
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""),
                     SimpleNamespace(type="text", text='{"intent": "clarify"}')],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1200, output_tokens=90),
            model="claude-haiku-5-5",
        )


def _client(config):
    holder = {}

    def factory(**kwargs):
        holder["sdk"] = FakeSDK(**kwargs)
        return holder["sdk"]

    client = AnthropicClient(config, sdk_factory=factory)
    return client, holder["sdk"]


def test_us1_request_shape_and_no_temperature():
    """R-02, R-03, FR-040: model, max_tokens, thinking, output_config; no temperature sent."""
    client, sdk = _client(load_config(env={}))
    reply = client.complete(ModelRequest(system="SYS", user="USER", schema=SCHEMA))
    call = sdk.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["max_tokens"] == 300
    assert call["thinking"] == {"type": "disabled"}
    assert call["output_config"] == {"effort": "low",
                                     "format": {"type": "json_schema", "schema": SCHEMA}}
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
    assert "temperature" not in call and "extra_body" not in call
    assert reply.text == '{"intent": "clarify"}'    # first *text* block, read by type
    assert (reply.input_tokens, reply.output_tokens) == (1200, 90)


def test_us1_sdk_client_built_without_retries():
    """R-06: the SDK client has max_retries=0 and the configured timeout."""
    _, sdk = _client(load_config(env={}))
    assert sdk.client_kwargs == {"max_retries": 0, "timeout": 30}


def test_us1_configured_temperature_is_passed_through():
    """FR-040: a configured temperature is sent (via extra_body; the SDK has no parameter)."""
    client, sdk = _client(replace(load_config(env={}), temperature=0.7))
    client.complete(ModelRequest(system="S", user="U", schema=SCHEMA))
    assert sdk.calls[0]["extra_body"] == {"temperature": 0.7}
