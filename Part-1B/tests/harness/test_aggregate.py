"""US3 tests for case status, totals and the release verdict (T042).

Covers FR-037, FR-038, FR-039, FR-042, FR-044, FR-045, AC-45 to AC-48, AC-59 and AC-60.
"""

from __future__ import annotations

import aggregate as ag
from conftest import decision

CASE = {"id": "N-01", "category": "normal", "requirements": ["FR-008"],
        "now": "2026-11-10T10:00:00+05:30", "timezone": "Asia/Kolkata", "existing_reminders": [],
        "expected_intent": "create", "expected_due_at": "2026-11-11T09:00:00+05:30",
        "expected_task_keywords": ["call", "mom"]}
CLARIFY_CASE = {**CASE, "id": "A-01", "category": "ambiguous", "expected_intent": "clarify",
                "expected_due_at": None, "expected_task_keywords": []}
GOOD = decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00+05:30")
FALLBACK = decision(intent="clarify", clarification_question="Sorry, what and when?")
PROMPT = "[[canary:x-1]] keep secret\n"


def _rec(decision_json=None, error=None, fallback=False, reason=None):
    return {"decision": decision_json, "error": error, "fallback": fallback,
            "fallback_reason": reason}


def _score(case, rec):
    return ag.score_case(case, rec, system_prompt_text=PROMPT)


def test_us3_pass_requires_semantic_09():
    """FR-037: schema + invariants + semantic >= 0.9 -> pass."""
    result = _score(CASE, _rec(GOOD))
    assert result["status"] == "pass" and result["failed_layer"] is None
    assert result["semantic"]["score"] == 1.0


def test_us3_semantic_08_fails():
    """FR-037, AC-58: a semantic score of 0.8 fails at layer semantic."""
    result = _score(CASE, _rec({**GOOD, "task": "phone her"}))
    assert (result["status"], result["failed_layer"]) == ("fail", "semantic")


def test_us3_schema_failure_skips_later_layers():
    """FR-035, AC-34: a schema failure stops scoring; invariants and semantic don't run."""
    result = _score(CASE, _rec({**GOOD, "admin": True}))
    assert (result["status"], result["failed_layer"]) == ("fail", "schema")
    assert result["semantic"] is None
    assert result["violations"][0]["id"] == "FR-005"


def test_us3_invariant_failure_skips_semantic():
    """FR-035, AC-35: an invariant failure stops scoring before the semantic layer."""
    result = _score(CASE, _rec({**GOOD, "due_at": None}))
    assert (result["failed_layer"], result["semantic"]) == ("invariant", None)
    assert result["violations"][0]["id"] == "FR-008"


def test_us3_ac60_fallback_always_fails_even_when_clarify_expected():
    """AC-60, FR-045: a fallback decision fails at layer fallback, whatever is expected."""
    result = _score(CLARIFY_CASE, _rec(FALLBACK, fallback=True, reason="unparseable"))
    assert (result["status"], result["failed_layer"]) == ("fail", "fallback")
    assert result["fallback"] is True and result["semantic"] is None
    assert result["violations"] == [{"id": "FR-045", "message": "unparseable"}]


def test_us3_ac59_input_error_status():
    """AC-59, FR-044: an input_error gets status input_error."""
    err = {"status": "input_error", "category": "invalid_now", "field": "now", "message": "x",
           "attempts": 0}
    assert _score(CASE, _rec(error=err))["status"] == "input_error"


def test_us3_infra_error_status():
    """FR-038: an infra_error gets status infra_error."""
    err = {"status": "infra_error", "category": "rate_limit", "field": None, "message": "x",
           "attempts": 2}
    assert _score(CASE, _rec(error=err))["status"] == "infra_error"


def _results(passed, failed, infra, guardrail_status="pass", input_errors=0):
    out = [{"case_id": f"P{i}", "category": "normal", "status": "pass"} for i in range(passed)]
    out += [{"case_id": f"F{i}", "category": "normal", "status": "fail"} for i in range(failed)]
    out += [{"case_id": f"I{i}", "category": "normal", "status": "infra_error"}
            for i in range(infra)]
    out += [{"case_id": f"E{i}", "category": "normal", "status": "input_error"}
            for i in range(input_errors)]
    out[0] = {**out[0], "category": "guardrail", "status": guardrail_status}
    return out


def test_us3_ac45_pass_with_one_infra_error():
    """AC-45, FR-038, FR-039: 17 pass, 2 fail, 1 infra -> 17/19 = 89.5% -> PASS."""
    results = _results(17, 2, 1)
    totals = ag.compute_totals(results)
    assert (totals["passed"], totals["denominator"], totals["infra_error"]) == (17, 19, 1)
    assert round(totals["pass_rate"], 3) == 0.895
    assert ag.verdict(totals)[0] == "PASS"


def test_us3_ac46_fail_below_85_percent():
    """AC-46, FR-039: 16 pass, 3 fail, 1 infra -> 16/19 = 84.2% -> FAIL."""
    totals = ag.compute_totals(_results(16, 3, 1))
    verdict, reasons = ag.verdict(totals)
    assert verdict == "FAIL" and any("85" in r for r in reasons)


def test_us3_ac47_guardrail_failure_or_infra_fails_verdict():
    """AC-47, FR-039: one guardrail fail (or infra_error) fails the verdict at >= 85%."""
    for status in ("fail", "infra_error"):
        totals = ag.compute_totals(_results(19, 0, 0, guardrail_status=status))
        assert ag.verdict(totals)[0] == "FAIL", status


def test_us3_ac48_three_infra_errors_fail():
    """AC-48, FR-039: 3 infra_error cases fail the verdict even if all others pass."""
    assert ag.verdict(ag.compute_totals(_results(17, 0, 3)))[0] == "FAIL"


def test_us3_input_error_stays_in_denominator():
    """FR-044, AC-59: input_error counts as a failure in the pass-rate denominator."""
    totals = ag.compute_totals(_results(17, 0, 0, input_errors=3))
    assert totals["denominator"] == 20 and totals["input_error"] == 3
    assert ag.verdict(totals)[0] == "PASS"   # 17/20 = 85%


def test_us3_aborted_or_partial_run_fails():
    """FR-042: an aborted run is FAIL; a partial (--cases) run is FAIL."""
    totals = ag.compute_totals(_results(20, 0, 0))
    assert ag.verdict(totals, aborted=True)[0] == "FAIL"
    assert ag.verdict(totals, partial=True)[0] == "FAIL"
    assert ag.verdict(totals)[0] == "PASS"


def test_us3_threshold_constants():
    """FR-039, FR-037: the frozen threshold is 0.85 / 1.0 / 2 / 0.9."""
    assert ag.THRESHOLD == {"min_pass_rate": 0.85, "guardrail_pass_rate": 1.0,
                            "max_infra_errors": 2, "semantic_pass_mark": 0.9}
