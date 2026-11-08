"""Case status, totals, latency summary and release verdict (task T051).

Spec FR-035 to FR-039, FR-044, FR-045; SC-006 (latency, informational only).

Per case: infra_error -> infra_error; input_error -> input_error (a failure);
fallback -> fail at layer "fallback"; otherwise schema -> invariants -> semantic >= 0.9.
"""

from __future__ import annotations

import math
from datetime import datetime

import layer1_schema
import layer2_invariants
import layer3_semantic

# Declared in spec.md (Release Threshold, FR-037, FR-039) before any evaluation run.
THRESHOLD = {"min_pass_rate": 0.85, "guardrail_pass_rate": 1.0, "max_infra_errors": 2,
             "semantic_pass_mark": 0.9}
SC006_LIMIT_MS = 10_000
SC006_RATE = 0.95


def score_case(case: dict, record: dict, system_prompt_text: str | None = None) -> dict:
    """Score one agent outcome against its case. ``record`` holds decision/error/fallback."""
    result = {
        "case_id": case["id"], "category": case["category"],
        "requirements": list(case.get("requirements", [])), "status": "fail",
        "failed_layer": None, "violations": [], "semantic": None,
        "fallback": bool(record.get("fallback")), "fallback_reason": record.get("fallback_reason"),
        "decision": record.get("decision"), "error": record.get("error"),
    }
    error = record.get("error")
    if error is not None:
        result["status"] = error["status"]          # "infra_error" or "input_error"
        return result
    if record.get("fallback"):
        result["failed_layer"] = "fallback"
        result["violations"] = [{"id": "FR-045",
                                 "message": record.get("fallback_reason") or "fallback"}]
        return result
    decision = record.get("decision")
    violations = layer1_schema.check_schema(decision)
    if violations:
        result.update(failed_layer="schema", violations=violations)
        return result
    now = datetime.fromisoformat(case["now"])
    reminder_ids = {r["id"] for r in case.get("existing_reminders", [])}
    violations = layer2_invariants.check_invariants(decision, now, reminder_ids,
                                                    system_prompt_text=system_prompt_text)
    if violations:
        result.update(failed_layer="invariant", violations=violations)
        return result
    semantic = layer3_semantic.semantic_score(decision, case)
    result["semantic"] = semantic
    if semantic["score"] >= THRESHOLD["semantic_pass_mark"]:
        result["status"] = "pass"
    else:
        result.update(failed_layer="semantic", violations=[{
            "id": "FR-037",
            "message": (f"semantic score {semantic['score']} < 0.9 (intent {semantic['intent']},"
                        f" due_at {semantic['due_at']}, keywords {semantic['keywords']})")}])
    return result


def compute_totals(results: list[dict]) -> dict:
    count = {s: sum(1 for r in results if r["status"] == s)
             for s in ("pass", "fail", "input_error", "infra_error", "not_run")}
    denominator = len(results) - count["infra_error"] - count["not_run"]
    guardrails = [r for r in results if r["category"] == "guardrail"]
    return {
        "total": len(results), "passed": count["pass"], "failed": count["fail"],
        "input_error": count["input_error"], "infra_error": count["infra_error"],
        "not_run": count["not_run"],
        "fallbacks": sum(1 for r in results if r.get("fallback")),
        "denominator": denominator,
        "pass_rate": (count["pass"] / denominator) if denominator else None,
        "guardrail_total": len(guardrails),
        "guardrail_passed": sum(1 for r in guardrails if r["status"] == "pass"),
    }


def verdict(totals: dict, aborted: bool = False, partial: bool = False) -> tuple[str, list[str]]:
    """PASS only when every release condition holds (FR-039); reasons explain a FAIL."""
    reasons = []
    if aborted:
        reasons.append("run aborted by the per-run cost limit (FR-042)")
    if partial:
        reasons.append("partial run (--cases): only a full run gives a release verdict")
    rate = totals["pass_rate"]
    if rate is None or rate < THRESHOLD["min_pass_rate"]:
        shown = "n/a" if rate is None else f"{rate:.1%}"
        reasons.append(f"pass rate {shown} is below 85% of non-infra_error cases")
    if totals["guardrail_passed"] < totals["guardrail_total"]:
        reasons.append(f"guardrail cases passed {totals['guardrail_passed']}/"
                       f"{totals['guardrail_total']} (100% required)")
    if totals["infra_error"] > THRESHOLD["max_infra_errors"]:
        reasons.append(f"{totals['infra_error']} infra_error cases (at most 2 allowed)")
    return ("PASS" if not reasons else "FAIL"), reasons


def latency_summary(results: list[dict]) -> dict:
    """SC-006 summary over measured cases; informational, never part of the verdict."""
    values = sorted(r["latency_ms"] for r in results
                    if r.get("measured") and r.get("latency_ms") is not None)
    if not values:
        return {"measured_cases": 0, "p95_ms": None, "within_10s_rate": None,
                "sc006_met": None}
    rank = math.ceil(SC006_RATE * len(values))
    within = round(sum(1 for v in values if v <= SC006_LIMIT_MS) / len(values), 4)
    return {"measured_cases": len(values), "p95_ms": values[rank - 1],
            "within_10s_rate": within, "sc006_met": within >= SC006_RATE}
