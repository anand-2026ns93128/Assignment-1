"""US3 tests for the project spend cap (T046). Covers FR-047, SC-005, Constitution X, AC-63."""

from __future__ import annotations

import json
import math

import budget
import dataset as ds
import evaluate
import pytest
from conftest import NoCallClient

from reminder_agent.config import load_config
from reminder_agent.prompt import load_system_prompt


def _write_report(evidence, run_id, usd, mode="live"):
    run = evidence / "eval-runs" / run_id
    run.mkdir(parents=True)
    (run / "eval-results.json").write_text(
        json.dumps({"mode": mode, "cost": {"estimated_usd": usd}}), encoding="utf-8")


def _cases():
    data, _ = ds.load_dataset(ds.DEFAULT_DATASET)
    return data["cases"]


def test_us3_recorded_live_spend_ignores_replays(tmp_path):
    """FR-047: recorded spend sums live reports only."""
    _write_report(tmp_path, "a", 1.25)
    _write_report(tmp_path, "b", 0.75)
    _write_report(tmp_path, "c", 9.99, mode="replay")
    assert budget.recorded_live_spend(tmp_path) == pytest.approx(2.00)
    assert budget.recorded_live_spend(tmp_path / "missing") == 0.0


def test_us3_unreadable_report_is_harness_error(tmp_path):
    """FR-047: an unreadable report stops the check rather than guessing."""
    run = tmp_path / "eval-runs" / "bad"
    run.mkdir(parents=True)
    (run / "eval-results.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(budget.HarnessError):
        budget.recorded_live_spend(tmp_path)


def test_us3_preflight_estimate_is_deterministic_worst_case():
    """FR-047: 2 attempts x (ceil(chars/3) input + max_tokens output) per case."""
    cfg = load_config(env={})
    cases = _cases()[:1]
    estimate = budget.preflight_estimate(cases, cfg)
    assert estimate == budget.preflight_estimate(cases, cfg)
    prompt_chars = len(load_system_prompt())
    assert estimate > 2 * cfg.pricing_for().cost(math.ceil(prompt_chars / 3), 300)


def test_us3_ac63_cap_refuses_live_run(tmp_path, capsys):
    """AC-63, FR-047: recorded 4.99 + estimate > 0.01 -> exit 2, no model call, totals shown."""
    _write_report(tmp_path, "old", 4.99)
    code = evaluate.main(["live", "--evidence-dir", str(tmp_path)], client=NoCallClient())
    out = capsys.readouterr().out
    assert code == 2
    assert "4.99" in out and "5.00" in out and "pre-flight" in out.lower()
    assert not any(p.name != "old" for p in (tmp_path / "eval-runs").iterdir())


def test_us3_cap_allows_run_with_low_spend(tmp_path):
    """FR-047: recorded spend of 0.10 leaves room, so the cap check allows the run."""
    _write_report(tmp_path, "old", 0.10)
    check = budget.check_project_cap(tmp_path, _cases(), load_config(env={}))
    assert check.allowed is True and check.recorded_usd == pytest.approx(0.10)


def test_us3_replay_is_never_blocked(tmp_path):
    """AC-63, FR-047: a replay proceeds even when recorded spend is at the cap."""
    from conftest import StubClient, decision, reply
    cases = [c for c in _cases() if c["id"] == "N-01"]
    script = [reply(decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00"))]
    evaluate.run_live(cases, StubClient(script), load_config(env={}), tmp_path / "live",
                      dataset_sha256="d" * 64, evidence_dir=tmp_path / "ev",
                      timer=iter(range(100)).__next__, sleeper=lambda s: None)
    _write_report(tmp_path / "ev", "huge", 4.99)
    report = evaluate.run_replay(tmp_path / "live", tmp_path / "replay")
    assert report["mode"] == "replay"


def test_us3_cap_read_from_config():
    """FR-047: the cap comes from config/settings.toml [budget].project_cap_usd."""
    assert load_config(env={}).project_cap_usd == 5.00
