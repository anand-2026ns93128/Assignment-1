"""Model-client boundary (task T016; research R-06, R-07).

``ModelClient`` is the only way the agent talks to a model. Tests use stub clients and the
harness uses a replay client, so the same post-processing runs live, in tests and in replay.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any, Protocol

from .config import AgentConfig
from .models import ModelReply, ModelRequest


class ModelCallError(Exception):
    """A model-service failure mapped to an ``infra_error`` category (FR-031)."""

    def __init__(self, category: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.retryable = retryable


class ModelClient(Protocol):
    def complete(self, request: ModelRequest) -> ModelReply:
        """Send one request and return the reply, or raise ``ModelCallError``."""
        ...


_KEY_PATTERN = re.compile("sk-" + "ant-" + r"[A-Za-z0-9_\-]+")


def scrub(message: str) -> str:
    """Remove anything that looks like an Anthropic API key, and the configured key itself."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        message = message.replace(key, "[redacted]")
    return _KEY_PATTERN.sub("[redacted]", message)


def map_sdk_error(exc: Exception) -> ModelCallError:
    """Map an SDK exception to an infra_error category, most specific first (research R-06)."""
    import anthropic

    status = getattr(exc, "status_code", None)
    detail = f"{type(exc).__name__}" + (f" (HTTP {status})" if status else "")
    if isinstance(exc, anthropic.APITimeoutError):
        return ModelCallError("timeout", scrub(f"model request timed out: {detail}"), True)
    if isinstance(exc, anthropic.APIConnectionError):
        return ModelCallError("connection", scrub(f"could not reach the model API: {detail}"),
                              True)
    if isinstance(exc, anthropic.RateLimitError):
        return ModelCallError("rate_limit", scrub(f"rate limited: {detail}"), True)
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return ModelCallError("auth", scrub(f"authentication failed: {detail}"), False)
    if isinstance(exc, anthropic.InternalServerError):
        return ModelCallError("server_error", scrub(f"model API server error: {detail}"), True)
    if isinstance(exc, anthropic.APIStatusError) and status == 408:
        return ModelCallError("timeout", scrub(f"request timeout: {detail}"), True)
    if isinstance(exc, anthropic.APIStatusError):
        return ModelCallError("request_rejected", scrub(f"request rejected: {detail}"), False)
    if isinstance(exc, anthropic.CredentialsError):
        return ModelCallError("auth", scrub(f"no usable API credentials: {detail}"), False)
    return ModelCallError("request_rejected", scrub(f"model call failed: {detail}"), False)


def _default_sdk_factory(**kwargs: Any) -> Any:
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()  # ANTHROPIC_API_KEY from the environment or a git-ignored .env only
    return anthropic.Anthropic(**kwargs)


class AnthropicClient:
    """Live client for the Claude Messages API (research R-02, R-03).

    The SDK's own retries are disabled (``max_retries=0``); the agent owns the single retry.
    """

    def __init__(self, config: AgentConfig,
                 sdk_factory: Callable[..., Any] = _default_sdk_factory) -> None:
        self.config = config
        self._sdk = sdk_factory(max_retries=0, timeout=config.timeout_seconds)

    def build_kwargs(self, request: ModelRequest) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "thinking": {"type": self.config.thinking},
            "output_config": {
                "effort": self.config.effort,
                "format": {"type": "json_schema", "schema": request.schema},
            },
        }
        if self.config.temperature is not None:
            # The SDK has no temperature parameter; the API decides whether to accept it.
            kwargs["extra_body"] = {"temperature": self.config.temperature}
        return kwargs

    def complete(self, request: ModelRequest) -> ModelReply:
        import anthropic

        try:
            message = self._sdk.messages.create(**self.build_kwargs(request))
        except anthropic.AnthropicError as exc:
            raise map_sdk_error(exc) from None
        text = next((block.text for block in message.content
                     if getattr(block, "type", None) == "text"), None)
        usage = getattr(message, "usage", None)
        return ModelReply(
            text=text,
            stop_reason=str(message.stop_reason),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            model=str(getattr(message, "model", self.config.model)),
        )
