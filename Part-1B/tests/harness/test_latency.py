"""US3 tests for latency reporting, SC-006 coverage (T045).

An injected fake timer returns scripted values, so no real time is measured.
Covers SC-006, FR-040 and AC-61.
"""

from __future__ import annotations

import aggregate as ag
import dataset as ds
import evaluate
from conftest import StubClient, decision, reply

from reminder_agent.client import ModelCallError
from reminder_agent.config import load_config


class FakeTimer:
    """Returns pairs (start, end) so each timed call lasts the scripted number of seconds."""

    def __init__(self, durations):
        self.values = []
        t = 0.0
        for d in durations:
            self.values += [t, t + d]
            t += d + 1
        self.values.reverse()

    def __call__(self):
        return self.values.pop()


def _measured(ms_values):
    return [{"case_id": f"C{i}", "status": "pass", "latency_ms": ms, "measured": True}
            for i, ms in enumerate(ms_values)]


def test_us3_latency_summary_sc006_met_at_95_percent():
    """AC-61, SC-006: 19 of 20 within 10 s -> within_10s_rate 0.95 and sc006_met true."""
    summary = ag.latency_summary(_measured([1000] * 19 + [12000]))
    assert summary["measured_cases"] == 20
    assert summary["within_10s_rate"] == 0.95 and summary["sc006_met"] is True


def test_us3_latency_summary_sc006_not_met_at_90_percent():
    """AC-61, SC-006: 18 of 20 within 10 s -> 0.90 and sc006_met false."""
    summary = ag.latency_summary(_measured([1000] * 18 + [12000, 15000]))
    assert summary["within_10s_rate"] == 0.9 and summary["sc006_met"] is False


def test_us3_p95_nearest_rank():
    """AC-61: p95 uses the nearest-rank method."""
    values = list(range(100, 2100, 100))           # 20 values: 100..2000
    assert ag.latency_summary(_measured(values))["p95_ms"] == 1900


def test_us3_unmeasured_cases_excluded():
    """AC-61: unmeasured cases (infra_error, no model call) do not count."""
    results = _measured([1000, 2000]) + [
        {"case_id": "I", "status": "infra_error", "latency_ms": 99999, "measured": False}]
    summary = ag.latency_summary(results)
    assert summary["measured_cases"] == 2 and summary["sc006_met"] is True


def test_us3_empty_latency_summary():
    """AC-61: with no measured cases the summary fields are null."""
    assert ag.latency_summary([]) == {"measured_cases": 0, "p95_ms": None,
                                      "within_10s_rate": None, "sc006_met": None}


def _cases(*ids):
    data, _ = ds.load_dataset(ds.DEFAULT_DATASET)
    by_id = {c["id"]: c for c in data["cases"]}
    return [by_id[i] for i in ids]


def test_us3_live_run_records_latency_and_measured_flag(tmp_path):
    """AC-61, FR-040: latency_ms per case; pre-model and infra_error cases are unmeasured."""
    err = ModelCallError("rate_limit", "limited", True)
    script = [reply(decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00")),
              err, err]
    report = evaluate.run_live(_cases("N-01", "X-01", "B-03"), StubClient(script),
                               load_config(env={}), tmp_path / "run", dataset_sha256="b" * 64,
                               evidence_dir=tmp_path / "ev", timer=FakeTimer([1.5, 0.0, 3.0]),
                               sleeper=lambda s: None)
    by_id = {c["case_id"]: c for c in report["cases"]}
    assert by_id["N-01"]["latency_ms"] == 1500 and by_id["N-01"]["measured"] is True
    assert by_id["X-01"]["measured"] is False          # empty text: no model call
    assert by_id["B-03"]["measured"] is False          # infra_error
    assert report["latency"]["measured_cases"] == 1
    summary = (tmp_path / "run" / "summary.md").read_text("utf-8")
    assert "SC-006: p95 1500 ms, 100% within 10 s, met" in summary


def test_us3_latency_does_not_change_verdict(tmp_path):
    """AC-61: the verdict is identical whatever the latencies are."""
    def run(durations, name):
        script = [reply(decision(intent="create", task="call mom",
                                 due_at="2026-11-11T09:00:00"))]
        return evaluate.run_live(_cases("N-01"), StubClient(script), load_config(env={}),
                                 tmp_path / name, dataset_sha256="c" * 64,
                                 evidence_dir=tmp_path / "ev", timer=FakeTimer(durations),
                                 sleeper=lambda s: None)
    fast, slow = run([0.1], "fast"), run([60.0], "slow")
    assert fast["verdict"] == slow["verdict"]
    assert fast["latency"]["sc006_met"] is True and slow["latency"]["sc006_met"] is False
