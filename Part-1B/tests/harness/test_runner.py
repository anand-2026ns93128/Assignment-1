"""US3 tests for the live runner, driven only by stub clients (T043). No network.

Covers FR-040, FR-042, AC-49 and AC-51.
"""

from __future__ import annotations

import json
from pathlib import Path

import dataset as ds
import evaluate
import jsonschema
from conftest import StubClient, decision, reply

from reminder_agent.client import ModelCallError
from reminder_agent.config import load_config

ROOT = Path(__file__).resolve().parents[2]
REPORT_SCHEMA = json.loads(
    (ROOT / "specs/001-nl-reminder-agent/contracts/eval_results.schema.json").read_text("utf-8"))
FAKE_KEY = "sk-" + "ant-test-123"


def _cases(*ids):
    data, _ = ds.load_dataset(ds.DEFAULT_DATASET)
    by_id = {c["id"]: c for c in data["cases"]}
    return [by_id[i] for i in ids]


def _replies():
    return [
        reply(decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00")),  # N-01
        reply("garbage, not json"),                                                     # A-01
        reply(decision(intent="refuse", refusal_reason="I only handle reminders.")),    # G-01
    ]


def _run(tmp_path, client, ids=("N-01", "A-01", "G-01"), **kwargs):
    return evaluate.run_live(_cases(*ids), client, load_config(env={}), tmp_path / "run",
                             dataset_sha256="0" * 64, evidence_dir=tmp_path / "evidence",
                             timer=iter(range(1000)).__next__, sleeper=lambda s: None, **kwargs)


def test_us3_report_files_and_schema(tmp_path, monkeypatch):
    """FR-040, AC-49: raw replies, eval-results.json (schema-valid) and summary.md are written."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    report = _run(tmp_path, StubClient(_replies()))
    run = tmp_path / "run"
    for cid in ("N-01", "A-01", "G-01"):
        assert (run / "raw" / f"{cid}.json").is_file()
    on_disk = json.loads((run / "eval-results.json").read_text("utf-8"))
    jsonschema.validate(on_disk, REPORT_SCHEMA)
    assert on_disk == report
    assert (run / "summary.md").is_file() and (run / "cases.json").is_file()


def test_us3_ac49_report_contents(tmp_path):
    """AC-49, FR-040: model config (temperature null), versions, hash, threshold, per-case data."""
    report = _run(tmp_path, StubClient(_replies()))
    assert report["mode"] == "live"
    assert report["model"]["name"] == "claude-haiku-5-5"
    assert report["model"]["max_tokens"] == 300 and report["model"]["temperature"] is None
    assert report["schema_version"] == "1.0.0" and report["prompt_version"] == "v1"
    assert report["dataset_sha256"] == "0" * 64
    assert report["threshold"]["semantic_pass_mark"] == 0.9
    assert report["pricing"]["input_per_mtok"] == 0.10
    by_id = {c["case_id"]: c for c in report["cases"]}
    assert by_id["N-01"]["status"] == "pass"
    assert by_id["N-01"]["semantic"]["score"] == 1.0
    assert by_id["A-01"]["failed_layer"] == "fallback" and by_id["A-01"]["fallback"] is True
    assert by_id["A-01"]["violations"][0]["id"] == "FR-045"
    assert by_id["G-01"]["status"] == "pass"
    assert report["cost"]["input_tokens"] == 3000 and report["cost"]["estimated_usd"] > 0


def test_us3_ac49_no_secret_in_any_written_file(tmp_path, monkeypatch):
    """AC-49, SC-007: with an API key in the environment, no written file contains it."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    _run(tmp_path, StubClient(_replies()))
    for path in (tmp_path / "run").rglob("*"):
        if path.is_file():
            assert "sk-" + "ant-" not in path.read_text("utf-8", errors="ignore"), path


def test_us3_summary_lists_failures_with_fr_ids(tmp_path):
    """FR-040: summary.md lists failing cases as '<case_id> <layer> <FR-id>: <message>'."""
    _run(tmp_path, StubClient(_replies()))
    summary = (tmp_path / "run" / "summary.md").read_text("utf-8")
    assert "A-01 fallback FR-045: unparseable" in summary
    assert "Verdict:" in summary


def test_us3_ac51_cost_abort(tmp_path):
    """AC-51, FR-042: once the cost exceeds $0.50 the run stops before the next case."""
    expensive = reply(decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00"),
                      output_tokens=2_000_000)
    report = _run(tmp_path, StubClient([expensive]))
    statuses = {c["case_id"]: c["status"] for c in report["cases"]}
    assert statuses == {"N-01": "pass", "A-01": "not_run", "G-01": "not_run"}
    assert report["aborted"] is True and report["verdict"] == "FAIL"
    assert "0.50" in report["abort_reason"]


def test_us3_preflight_estimate_printed(tmp_path, capsys):
    """FR-047, R-10: a pre-flight cost estimate is printed before a live run."""
    _run(tmp_path, StubClient(_replies()))
    assert "Pre-flight" in capsys.readouterr().out


def test_us3_partial_run_is_fail(tmp_path):
    """FR-039: a --cases subset run is marked partial and its verdict is FAIL."""
    report = _run(tmp_path, StubClient(_replies()[:1]), ids=("N-01",), partial=True)
    assert report["partial"] is True and report["verdict"] == "FAIL"


def test_us3_infra_error_is_recorded_separately(tmp_path):
    """FR-038: an infra_error case is recorded with its category and excluded from the rate."""
    err = ModelCallError("rate_limit", "rate limited", True)
    report = _run(tmp_path, StubClient([err, err]), ids=("N-01",))
    case = report["cases"][0]
    assert case["status"] == "infra_error" and case["attempts"] == 2
    assert case["error"]["category"] == "rate_limit"
    assert report["totals"]["infra_error"] == 1


def test_us3_check_dataset_command(capsys):
    """FR-034, AC-32: 'evaluate.py check-dataset' exits 0 for the committed dataset."""
    assert evaluate.main(["check-dataset"]) == 0
    assert "26 cases" in capsys.readouterr().out
