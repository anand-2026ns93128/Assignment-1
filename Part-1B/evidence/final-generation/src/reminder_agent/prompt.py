"""Prompt building (task T029; spec FR-014 to FR-017, FR-029; research R-04).

The system prompt is a versioned text file. The user message carries the calendar facts
computed from the injected clock, then the user's text inside ``<user_request>`` delimiters.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .models import ModelRequest, RequestContext
from .parsing import derive_api_schema, load_contract_schema
from .timeutil import calendar_context

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = "v1"
PROMPT_PATH = PROJECT_ROOT / "prompts" / f"system_prompt.{PROMPT_VERSION}.txt"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def escape_untrusted(text: str) -> str:
    """Neutralize angle brackets so untrusted text cannot open or close a block (FR-029)."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def reminders_block(ctx: RequestContext) -> str:
    """One line per existing reminder (id, task, local due_at), or "(none)" (FR-025)."""
    if not ctx.reminders:
        return "(none)"
    return "\n".join(
        f"- id: {escape_untrusted(r.id)} | task: {escape_untrusted(r.task)} | due_at: "
        f"{r.due_at.astimezone(ctx.timezone).isoformat(timespec='seconds')}"
        for r in ctx.reminders)


def build_messages(ctx: RequestContext, prompt_text: str | None = None) -> ModelRequest:
    """Build the model request for one context."""
    user = "\n".join([
        "<calendar>",
        calendar_context(ctx.now, ctx.timezone),
        "</calendar>",
        "<existing_reminders>",
        reminders_block(ctx),
        "</existing_reminders>",
        "<user_request>",
        escape_untrusted(ctx.text),
        "</user_request>",
    ])
    return ModelRequest(
        system=load_system_prompt() if prompt_text is None else prompt_text,
        user=user,
        schema=derive_api_schema(load_contract_schema()),
    )
