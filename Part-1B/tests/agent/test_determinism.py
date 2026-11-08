"""US1 determinism test (T024). Covers FR-004 and AC-14.

The agent is run in two subprocesses with different TZ environment values. On Windows, TZ
only partly changes the local timezone; the clock-ban gate (T008) is the primary guarantee
that agent code never reads the system clock or timezone.
"""

from __future__ import annotations

import os

# Justification for nosec B404: subprocess only re-runs this interpreter with a fixed script.
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r"""
import json
from reminder_agent.agent import run_agent
from reminder_agent.models import ModelReply

class Stub:
    def complete(self, request):
        return ModelReply(text=json.dumps({"intent": "create", "task": "call mom",
            "due_at": "2026-11-11T09:00:00", "target_id": None, "snooze_minutes": None,
            "clarification_question": None, "refusal_reason": None}), stop_reason="end_turn")

out = run_agent("remind me to call mom tomorrow at 9am", "2026-11-10T10:00:00+05:30",
                "Asia/Kolkata", client=Stub())
print(json.dumps(out.decision.to_json()))
"""


def _run_with_tz(tz: str) -> str:
    env = {**os.environ, "TZ": tz, "PYTHONPATH": str(ROOT / "src")}
    # Justification for nosec B603: fixed argument list (this interpreter + inline script).
    done = subprocess.run([sys.executable, "-c", SCRIPT], env=env, capture_output=True,  # nosec B603
                          text=True, check=True, cwd=ROOT)
    return done.stdout.strip()


def test_us1_ac14_same_output_under_different_system_timezones():
    """AC-14, FR-004: identical inputs and replies give identical decisions on any machine."""
    first, second = _run_with_tz("UTC"), _run_with_tz("Asia/Tokyo")
    assert first == second
    assert '"due_at": "2026-11-11T09:00:00+05:30"' in first
