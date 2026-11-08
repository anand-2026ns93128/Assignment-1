"""Agent orchestration: ``run_agent`` (task T031; data-model lifecycle).

inputs -> prompt -> one model call -> parse -> shorten task -> normalize due_at -> schema ->
invariants. Any failure after the model call yields the fallback clarify (FR-030). The agent
never reads the system clock (FR-004) and never raises for input or model problems.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from .client import AnthropicClient, ModelCallError, ModelClient, scrub
from .config import AgentConfig, load_config
from .guardrails import check_invariants, pre_model_check, refusal_decision
from .inputs import validate_inputs
from .models import (
    FALLBACK_DECISION,
    AgentOutcome,
    ErrorResult,
    ModelReply,
    ModelRequest,
    ReminderDecision,
    RequestContext,
)
from .parsing import ReplyError, parse_json, shorten_task, validate_decision
from .prompt import build_messages
from .timeutil import normalize_due_at, snooze_due_at

MAX_ATTEMPTS = 2           # one call plus at most one retry (FR-031)
RETRY_DELAY_SECONDS = 1.0


def _fallback(reason: str, reply: ModelReply | None, attempts: int) -> AgentOutcome:
    return AgentOutcome(decision=FALLBACK_DECISION, fallback=True, fallback_reason=reason,
                        raw_reply=reply, attempts=attempts)


def _postprocess(data: dict, ctx: RequestContext) -> dict:
    """Deterministic repairs before validation: task length (FR-022), due_at offset (FR-018)."""
    task = data.get("task")
    if isinstance(task, str) and len(task) > 200:
        data["task"] = shorten_task(task)
    minutes = data.get("snooze_minutes")
    if (data.get("intent") == "snooze" and isinstance(minutes, int)
            and not isinstance(minutes, bool) and 1 <= minutes <= 1440):
        # FR-024: a snooze is due exactly snooze_minutes after now, whatever the model said.
        data["due_at"] = snooze_due_at(ctx.now, minutes)
        return data
    due = data.get("due_at")
    if isinstance(due, str):
        try:
            data["due_at"] = normalize_due_at(due, ctx.timezone)
        except ValueError:
            pass  # left as-is; schema validation rejects it
    return data


def decide(reply: ModelReply, ctx: RequestContext, attempts: int) -> AgentOutcome:
    """Turn one model reply into a validated decision or the fallback."""
    if reply.stop_reason == "refusal":
        return AgentOutcome(decision=refusal_decision(), raw_reply=reply, attempts=attempts)
    if reply.stop_reason == "max_tokens":
        return _fallback("max_tokens", reply, attempts)
    try:
        data = parse_json(reply.text)
    except ReplyError:
        return _fallback("unparseable", reply, attempts)
    data = _postprocess(data, ctx)
    problems = validate_decision(data)
    if problems:
        return _fallback(problems[0], reply, attempts)
    decision = ReminderDecision.from_json(data)
    violations = check_invariants(decision, ctx)
    if violations:
        return _fallback(f"invariant:{violations[0]}", reply, attempts)
    return AgentOutcome(decision=decision, raw_reply=reply, attempts=attempts)


def call_with_retry(client: ModelClient, request: ModelRequest,
                    sleeper: Callable[[float], None]) -> tuple[ModelReply | None,
                                                              ErrorResult | None, int]:
    """One retry for retryable failures, then infra_error (FR-031, research R-06)."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return client.complete(request), None, attempts
        except ModelCallError as exc:
            if exc.retryable and attempts < MAX_ATTEMPTS:
                sleeper(RETRY_DELAY_SECONDS)
                continue
            error = ErrorResult(status="infra_error", category=exc.category, field=None,
                                message=scrub(exc.message), attempts=attempts)
            return None, error, attempts


def run_agent(text: object, now: object, timezone: object, reminders: object = None, *,
              client: ModelClient | None = None,
              config: AgentConfig | None = None,
              sleeper: Callable[[float], None] = time.sleep) -> AgentOutcome:
    """Decide what to do with one natural-language reminder request."""
    ctx = validate_inputs(text, now, timezone, reminders)
    if isinstance(ctx, ErrorResult):
        return AgentOutcome(error=ctx)
    canned = pre_model_check(ctx.text)
    if canned is not None:
        return AgentOutcome(decision=canned, attempts=0)
    if client is None:
        client = AnthropicClient(config or load_config())
    reply, error, attempts = call_with_retry(client, build_messages(ctx), sleeper)
    if error is not None:
        return AgentOutcome(error=error, attempts=attempts)
    return decide(reply, ctx, attempts=attempts)
