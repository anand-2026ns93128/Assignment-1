"""Project spend cap and pre-flight estimate (task T050; spec FR-047, SC-005; Constitution X)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import dataset as ds

from reminder_agent.config import AgentConfig, Pricing
from reminder_agent.inputs import validate_inputs
from reminder_agent.models import RequestContext
from reminder_agent.prompt import build_messages, load_system_prompt

ATTEMPTS_PER_CASE = 2      # one call plus one retry: the worst case
CHARS_PER_TOKEN = 3        # deliberately pessimistic


class HarnessError(RuntimeError):
    """The harness cannot proceed safely (for example, an unreadable cost record)."""


@dataclass(frozen=True)
class CapCheck:
    allowed: bool
    recorded_usd: float
    estimate_usd: float
    cap_usd: float

    def message(self) -> str:
        return (f"Recorded live spend ${self.recorded_usd:.2f} + pre-flight estimate "
                f"${self.estimate_usd:.4f} vs project cap ${self.cap_usd:.2f}")


class ProjectCapExceeded(HarnessError):
    def __init__(self, check: CapCheck) -> None:
        super().__init__(f"Live run refused: {check.message()}")
        self.check = check


def estimate_case_cost(pricing: Pricing, input_tokens: int, output_tokens: int) -> float:
    return pricing.cost(input_tokens, output_tokens)


def recorded_live_spend(evidence_dir: Path) -> float:
    """Sum ``cost.estimated_usd`` over every live report under ``evidence_dir/eval-runs``."""
    total = 0.0
    runs = Path(evidence_dir) / "eval-runs"
    if not runs.is_dir():
        return total
    for report in sorted(runs.glob("*/eval-results.json")):
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            if data.get("mode") == "live":
                total += float(data["cost"]["estimated_usd"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HarnessError(f"cannot read cost from {report}: {exc}") from None
    return total


def _prompt_chars(case: dict) -> int:
    ctx = validate_inputs(ds.expand_input(case), case["now"], case["timezone"],
                          case.get("existing_reminders"))
    if isinstance(ctx, RequestContext):
        request = build_messages(ctx)
        return len(request.system) + len(request.user)
    return len(load_system_prompt()) + len(ds.expand_input(case))


def preflight_estimate(cases: list[dict], config: AgentConfig) -> float:
    """Worst case: every case makes 2 attempts at the maximum output length."""
    pricing = config.pricing_for()
    total = 0.0
    for case in cases:
        input_tokens = math.ceil(_prompt_chars(case) / CHARS_PER_TOKEN)
        total += ATTEMPTS_PER_CASE * estimate_case_cost(pricing, input_tokens, config.max_tokens)
    return total


def check_project_cap(evidence_dir: Path, cases: list[dict], config: AgentConfig) -> CapCheck:
    recorded = recorded_live_spend(evidence_dir)
    estimate = preflight_estimate(cases, config)
    return CapCheck(allowed=recorded + estimate <= config.project_cap_usd,
                    recorded_usd=recorded, estimate_usd=estimate,
                    cap_usd=config.project_cap_usd)
