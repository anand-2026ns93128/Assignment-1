"""Evaluation runner: check-dataset | live | replay (task T053; contracts/interfaces.md §3).

Spec FR-034, FR-040 to FR-042, FR-047; SC-005, SC-006.

* ``live`` calls the agent (and so the model) once per case, saves every raw reply, times each
  call, tracks token cost, stops before the next case once cost exceeds the per-run limit, and
  refuses to start if the project spend cap would be exceeded.
* ``replay`` re-scores saved raw replies through the same agent post-processing with zero model
  calls, reproducing statuses, scores and the verdict.

Exit codes: 0 verdict PASS, 1 verdict FAIL (including an abort), 2 harness or dataset error.
Live runs are started manually by the project owner; no automated task runs one.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import aggregate
import budget
import dataset as ds
import layer2_invariants
from replay import ReplayClient, load_raw

from reminder_agent.agent import run_agent
from reminder_agent.client import AnthropicClient, ModelCallError, ModelClient
from reminder_agent.config import AgentConfig, load_config
from reminder_agent.models import ModelReply, ModelRequest
from reminder_agent.parsing import SCHEMA_VERSION
from reminder_agent.prompt import PROMPT_VERSION

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "evidence"


def _evidence_timestamp() -> str:
    """Wall-clock time for evidence folder names and report metadata only (Constitution III)."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")  # clock-ban: allowed (evidence metadata)


def _unique_dir(base: Path, name: str) -> Path:
    candidate, n = base / name, 0
    while candidate.exists():
        n += 1
        candidate = base / f"{name}-{n}"
    return candidate


class RecordingClient:
    """Wraps a client and records every attempt (reply or infra error) for the raw file."""

    def __init__(self, inner: ModelClient) -> None:
        self.inner = inner
        self.attempts: list[dict] = []

    def complete(self, request: ModelRequest) -> ModelReply:
        try:
            reply = self.inner.complete(request)
        except ModelCallError as exc:
            self.attempts.append({"error": {"category": exc.category, "message": exc.message,
                                            "retryable": exc.retryable}})
            raise
        self.attempts.append({"reply": reply.to_json()})
        return reply

    def tokens(self) -> tuple[int, int]:
        replies = [a["reply"] for a in self.attempts if "reply" in a]
        return (sum(r["input_tokens"] for r in replies), sum(r["output_tokens"] for r in replies))


def _record(outcome) -> dict:
    return {
        "decision": outcome.decision.to_json() if outcome.decision else None,
        "error": outcome.error.to_json() if outcome.error else None,
        "fallback": outcome.fallback,
        "fallback_reason": outcome.fallback_reason,
    }


def _agent_args(case: dict) -> tuple:
    return (ds.expand_input(case), case["now"], case["timezone"], case.get("existing_reminders"))


def _not_run(case: dict) -> dict:
    return {"case_id": case["id"], "category": case["category"],
            "requirements": list(case.get("requirements", [])), "status": "not_run",
            "failed_layer": None, "violations": [], "semantic": None, "fallback": False,
            "fallback_reason": None, "decision": None, "error": None, "raw_response_ref": None,
            "attempts": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
            "latency_ms": None, "measured": False}


def _finish_case(case: dict, outcome, attempts_log: list[dict], tokens: tuple[int, int],
                 latency_ms: int | None, config: AgentConfig, prompt_text: str) -> dict:
    result = aggregate.score_case(case, _record(outcome), system_prompt_text=prompt_text)
    cost = config.pricing_for().cost(*tokens)
    result.update(
        raw_response_ref=f"raw/{case['id']}.json", attempts=outcome.attempts,
        input_tokens=tokens[0], output_tokens=tokens[1], cost_usd=round(cost, 8),
        latency_ms=latency_ms,
        measured=bool(outcome.attempts > 0 and outcome.error is None),
    )
    return result


def _build_report(*, run_id: str, mode: str, results: list[dict], config_evidence: dict,
                  pricing: dict, dataset_sha256: str, aborted: bool, abort_reason: str | None,
                  partial: bool, source_run_id: str | None, spend_before: float | None,
                  preflight: float | None) -> dict:
    totals = aggregate.compute_totals(results)
    verdict, reasons = aggregate.verdict(totals, aborted=aborted, partial=partial)
    return {
        "run_id": run_id, "timestamp_utc": _evidence_timestamp(), "mode": mode,
        "source_run_id": source_run_id, "model": config_evidence,
        "schema_version": SCHEMA_VERSION, "prompt_version": PROMPT_VERSION,
        "dataset_sha256": dataset_sha256, "pricing": pricing,
        "threshold": dict(aggregate.THRESHOLD), "cases": results, "totals": totals,
        "cost": {
            "input_tokens": sum(r["input_tokens"] for r in results),
            "output_tokens": sum(r["output_tokens"] for r in results),
            "estimated_usd": round(sum(r["cost_usd"] for r in results), 8),
            "project_spend_before_usd": spend_before, "preflight_estimate_usd": preflight,
        },
        "latency": aggregate.latency_summary(results),
        "aborted": aborted, "abort_reason": abort_reason, "partial": partial,
        "verdict": verdict, "verdict_reasons": reasons,
    }


def _summary_md(report: dict) -> str:
    t = report["totals"]
    rate = "n/a" if t["pass_rate"] is None else f"{t['pass_rate']:.1%}"
    lines = [
        f"# Evaluation run {report['run_id']} ({report['mode']})", "",
        f"- Model: {report['model']['name']}, max_tokens {report['model']['max_tokens']}, "
        f"temperature {report['model']['temperature']} (null = not sent, model default)",
        f"- Dataset sha256: {report['dataset_sha256']}",
        f"- Schema {report['schema_version']}, prompt {report['prompt_version']}",
        f"- Pass rate: {t['passed']}/{t['denominator']} ({rate}); guardrails "
        f"{t['guardrail_passed']}/{t['guardrail_total']}; infra_error {t['infra_error']}; "
        f"input_error {t['input_error']}; fallbacks {t['fallbacks']}; not_run {t['not_run']}",
        f"- Estimated cost: ${report['cost']['estimated_usd']:.6f}", "",
        f"Verdict: **{report['verdict']}**",
    ]
    lines += [f"- {reason}" for reason in report["verdict_reasons"]]
    lines += ["", "## Failing cases (paste into the coding agent)", ""]
    failures = 0
    for case in report["cases"]:
        status = case["status"]
        if status == "pass":
            continue
        failures += 1
        if status in ("infra_error", "input_error"):
            err = case["error"] or {}
            lines.append(f"- {case['case_id']} {status} {err.get('category')}: "
                         f"{err.get('message')}")
        elif status == "not_run":
            lines.append(f"- {case['case_id']} not_run: skipped after the cost abort")
        else:
            for v in case["violations"]:
                lines.append(f"- {case['case_id']} {case['failed_layer']} {v['id']}: "
                             f"{v['message']}")
    if not failures:
        lines.append("- none")
    lat = report["latency"]
    lines.append("")
    if lat["measured_cases"]:
        lines.append(f"SC-006: p95 {lat['p95_ms']} ms, {lat['within_10s_rate'] * 100:.0f}% "
                     f"within 10 s, {'met' if lat['sc006_met'] else 'not met'} "
                     f"(informational, not part of the verdict)")
    else:
        lines.append("SC-006: no measured cases")
    return "\n".join(lines) + "\n"


def _write_run(out_dir: Path, report: dict, cases: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (out_dir / "eval-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(_summary_md(report), encoding="utf-8")


def _write_raw(out_dir: Path, case_id: str, attempts: list[dict], latency_ms: int | None,
               measured: bool) -> None:
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {"case_id": case_id, "attempts": attempts, "latency_ms": latency_ms,
               "measured": measured}
    (raw_dir / f"{case_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_live(cases: list[dict], client: ModelClient, config: AgentConfig, out_dir: Path, *,
             dataset_sha256: str, evidence_dir: Path = EVIDENCE_DIR,
             timer: Callable[[], float] = time.perf_counter,
             sleeper: Callable[[float], None] = time.sleep, partial: bool = False,
             run_id: str | None = None) -> dict:
    """Run every case through the agent, save evidence and return the report (FR-040)."""
    check = budget.check_project_cap(evidence_dir, cases, config)
    print(f"Pre-flight estimate: ${check.estimate_usd:.4f} "
          f"(recorded live spend ${check.recorded_usd:.2f}, cap ${check.cap_usd:.2f})")
    if not check.allowed:
        raise budget.ProjectCapExceeded(check)
    out_dir = Path(out_dir)
    prompt_text = layer2_invariants.load_system_prompt_text()
    results: list[dict] = []
    total_cost, aborted, abort_reason = 0.0, False, None
    for case in cases:
        if not aborted and total_cost > config.run_abort_usd:
            aborted = True
            abort_reason = (f"estimated cost ${total_cost:.4f} exceeded the "
                            f"${config.run_abort_usd:.2f} per-run limit")
        if aborted:
            results.append(_not_run(case))
            continue
        recorder = RecordingClient(client)
        start = timer()
        outcome = run_agent(*_agent_args(case), client=recorder, config=config, sleeper=sleeper)
        latency_ms = int(round((timer() - start) * 1000))
        result = _finish_case(case, outcome, recorder.attempts, recorder.tokens(), latency_ms,
                              config, prompt_text)
        _write_raw(out_dir, case["id"], recorder.attempts, latency_ms, result["measured"])
        total_cost += result["cost_usd"]
        results.append(result)
    report = _build_report(
        run_id=run_id or out_dir.name, mode="live", results=results,
        config_evidence=config.to_evidence(), pricing=config.pricing_for().to_json(),
        dataset_sha256=dataset_sha256, aborted=aborted, abort_reason=abort_reason,
        partial=partial, source_run_id=None, spend_before=round(check.recorded_usd, 8),
        preflight=round(check.estimate_usd, 8))
    _write_run(out_dir, report, cases)
    return report


def run_replay(run_dir: Path, out_dir: Path) -> dict:
    """Re-score a saved live run with zero model calls (FR-041). Never blocked by the cap."""
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    source = json.loads((run_dir / "eval-results.json").read_text(encoding="utf-8"))
    cases = json.loads((run_dir / "cases.json").read_text(encoding="utf-8"))
    source_status = {c["case_id"]: c["status"] for c in source["cases"]}
    replay = ReplayClient(run_dir)
    prompt_text = layer2_invariants.load_system_prompt_text()
    config = load_config(env={})
    results = []
    for case in cases:
        if source_status.get(case["id"]) == "not_run":
            results.append(_not_run(case))
            continue
        raw = load_raw(run_dir, case["id"])
        client = replay.for_case(case["id"])
        outcome = run_agent(*_agent_args(case), client=client, sleeper=lambda _s: None)
        tokens = (sum(a["reply"]["input_tokens"] for a in raw["attempts"] if "reply" in a),
                  sum(a["reply"]["output_tokens"] for a in raw["attempts"] if "reply" in a))
        result = _finish_case(case, outcome, raw["attempts"], tokens, raw.get("latency_ms"),
                              config, prompt_text)
        result["measured"] = raw.get("measured", result["measured"])
        results.append(result)
    report = _build_report(
        run_id=out_dir.name, mode="replay", results=results, config_evidence=source["model"],
        pricing=source["pricing"], dataset_sha256=source["dataset_sha256"],
        aborted=source["aborted"], abort_reason=source.get("abort_reason"),
        partial=source.get("partial", False), source_run_id=source["run_id"],
        spend_before=None, preflight=None)
    _write_run(out_dir, report, cases)
    return report


def _append_log(evidence_dir: Path, report: dict, run_dir: Path) -> None:
    log = evidence_dir / "harness-log.md"
    t, c = report["totals"], report["cost"]
    rate = "n/a" if t["pass_rate"] is None else f"{t['pass_rate']:.1%}"
    line = (f"- Eval {report['mode']} run `{report['run_id']}`: **{report['verdict']}**, "
            f"pass rate {t['passed']}/{t['denominator']} ({rate}), guardrails "
            f"{t['guardrail_passed']}/{t['guardrail_total']}, infra_error {t['infra_error']}, "
            f"fallbacks {t['fallbacks']}, cost ${c['estimated_usd']:.6f}, evidence "
            f"`{run_dir.as_posix()}`\n")
    existing = log.read_text(encoding="utf-8") if log.exists() else ""
    if "## Evaluation runs (final)" not in existing:
        line = "\n## Evaluation runs (final)\n\n" + line
    with log.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _finalize(report: dict, run_dir: Path, evidence_dir: Path) -> None:
    shutil.copyfile(run_dir / "eval-results.json", evidence_dir / "eval-results.json")
    _append_log(evidence_dir, report, run_dir)


def main(argv: list[str] | None = None, *, client: ModelClient | None = None,
         evidence_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reminder agent evaluation harness")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-dataset", help="validate evals/dataset.json (FR-034)")
    check.add_argument("--dataset", type=Path, default=ds.DEFAULT_DATASET)
    live = sub.add_parser("live", help="run the agent on every case (costs money)")
    live.add_argument("--dataset", type=Path, default=ds.DEFAULT_DATASET)
    live.add_argument("--cases", help="comma-separated case ids (partial run, verdict FAIL)")
    live.add_argument("--final", action="store_true")
    live.add_argument("--evidence-dir", type=Path)
    rep = sub.add_parser("replay", help="re-score a saved run with zero model calls")
    rep.add_argument("--run", type=Path, required=True)
    rep.add_argument("--final", action="store_true")
    rep.add_argument("--evidence-dir", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    evidence_dir = Path(evidence_dir or getattr(args, "evidence_dir", None) or EVIDENCE_DIR)

    try:
        if args.command == "check-dataset":
            data, sha = ds.load_dataset(args.dataset)
            problems = ds.validate_dataset(data)
            if problems:
                print("Dataset problems:\n" + "\n".join(f"- {p}" for p in problems))
                return 1
            print(f"Dataset OK: {len(data['cases'])} cases, sha256 {sha}")
            return 0

        if args.command == "replay":
            source = Path(args.run)
            out_dir = _unique_dir(source.parent, f"{source.name}-replay")
            report = run_replay(source, out_dir)
            print(_summary_md(report))
            if args.final:
                _finalize(report, out_dir, evidence_dir)
            return 0 if report["verdict"] == "PASS" else 1

        data, sha = ds.load_dataset(args.dataset)
        problems = ds.validate_dataset(data)
        if problems:
            print("Dataset problems:\n" + "\n".join(f"- {p}" for p in problems))
            return 2
        cases = data["cases"]
        partial = bool(args.cases)
        if partial:
            wanted = {c.strip() for c in args.cases.split(",")}
            cases = [c for c in cases if c["id"] in wanted]
        config = load_config()
        cap = budget.check_project_cap(evidence_dir, cases, config)
        if not cap.allowed:
            print(f"Live run refused (FR-047): {cap.message()}")
            return 2
        live_client = client or AnthropicClient(config)
        out_dir = _unique_dir(evidence_dir / "eval-runs", f"{_evidence_timestamp()}-live")
        report = run_live(cases, live_client, config, out_dir, dataset_sha256=sha,
                          evidence_dir=evidence_dir, partial=partial)
        print(_summary_md(report))
        if args.final:
            _finalize(report, out_dir, evidence_dir)
        return 0 if report["verdict"] == "PASS" else 1
    except budget.ProjectCapExceeded as exc:
        print(str(exc))
        return 2
    except (budget.HarnessError, FileNotFoundError, ValueError) as exc:
        print(f"Harness error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
