"""US1 tests for prompt building (T021).

Covers FR-014, FR-015, FR-016, FR-017 and research R-04.
"""

from __future__ import annotations

from conftest import DEFAULT_NOW, DEFAULT_TZ

from reminder_agent import prompt
from reminder_agent.inputs import validate_inputs


def test_us1_user_text_and_calendar_in_message():
    """FR-014, R-04: the user message carries the calendar and the delimited user text."""
    ctx = validate_inputs("remind me to call mom tomorrow at 9am", DEFAULT_NOW, DEFAULT_TZ, None)
    request = prompt.build_messages(ctx)
    assert "Today: 2026-11-10 (Tuesday)" in request.user
    assert "<user_request>\nremind me to call mom tomorrow at 9am\n</user_request>" in request.user
    assert request.system == prompt.load_system_prompt()
    assert request.schema["additionalProperties"] is False


def test_us1_prompt_version_and_file():
    """FR-014: the system prompt is loaded from prompts/system_prompt.v1.txt, version v1."""
    assert prompt.PROMPT_VERSION == "v1"
    assert prompt.PROMPT_PATH.name == "system_prompt.v1.txt"


def test_us1_system_prompt_time_rules():
    """FR-015, FR-016, FR-017, R-04: the documented time conventions are in the prompt."""
    text = prompt.load_system_prompt()
    assert "morning 09:00, noon 12:00, afternoon 15:00, evening 18:00, tonight 20:00" in text
    lowered = text.lower()
    assert "soonest date after today" in lowered and "7 days later" in lowered
    assert "local wall time" in lowered
    assert "never invent a time" in lowered
    assert "[[canary:rem-agent-v1-7f3c9a]]" in text
