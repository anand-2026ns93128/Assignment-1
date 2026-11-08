"""US1 tests for the CLI and library/CLI parity (T024). Covers FR-002 and AC-15."""

from __future__ import annotations

import io
import json

from conftest import DEFAULT_NOW, DEFAULT_TZ, StubClient, decision, reply

from reminder_agent import cli
from reminder_agent.agent import run_agent
from reminder_agent.models import DECISION_KEYS

CREATE = decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00")
ARGS = ["--text", "remind me to call mom tomorrow at 9am", "--now", DEFAULT_NOW,
        "--timezone", DEFAULT_TZ]


def _run(argv, client, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, client=client, stdin=io.StringIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_us1_cli_prints_one_line_decision():
    """FR-002: the CLI prints the seven-key decision as one JSON line and exits 0."""
    code, out, err = _run(ARGS, StubClient([reply(CREATE)]))
    assert code == 0 and err == ""
    assert out.count("\n") == 1
    data = json.loads(out)
    assert tuple(data) == DECISION_KEYS
    assert data["due_at"] == "2026-11-11T09:00:00+05:30"


def test_us1_cli_input_error_exit_3():
    """FR-003, AC-16: an input error goes to stderr as error JSON with exit code 3."""
    argv = ["--text", "hi", "--now", DEFAULT_NOW, "--timezone", "Mars/Olympus"]
    code, out, err = _run(argv, StubClient([]))
    assert code == 3 and out == ""
    assert json.loads(err)["category"] == "invalid_timezone"


def test_us1_cli_stdin_mode():
    """FR-002: --stdin reads text, now, timezone and existing_reminders as JSON."""
    payload = json.dumps({"text": "remind me to call mom tomorrow at 9am", "now": DEFAULT_NOW,
                          "timezone": DEFAULT_TZ, "existing_reminders": []})
    code, out, _ = _run(["--stdin"], StubClient([reply(CREATE)]), stdin=payload)
    assert code == 0 and json.loads(out)["intent"] == "create"


def test_us1_cli_missing_args_is_usage_error():
    """FR-002: missing required arguments is an argparse usage error (exit 2)."""
    code, _, _ = _run(["--text", "x"], StubClient([]))
    assert code == 2


def test_us1_ac15_library_and_cli_parity():
    """AC-15, FR-002: the library decision equals the CLI output for the same inputs."""
    lib = run_agent(ARGS[1], DEFAULT_NOW, DEFAULT_TZ, client=StubClient([reply(CREATE)]))
    _, out, _ = _run(ARGS, StubClient([reply(CREATE)]))
    assert json.loads(out) == lib.decision.to_json()
