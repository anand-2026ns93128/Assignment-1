"""US3 tests for replay mode (T044). Covers FR-035, FR-041, AC-50 and AC-52."""

from __future__ import annotations

from pathlib import Path

import dataset as ds
import evaluate
import pytest
from conftest import StubClient, decision, reply
from replay import ReplayClient

from reminder_agent.client import ModelCallError
from reminder_agent.config import load_config


def _cases():
    data, _ = ds.load_dataset(ds.DEFAULT_DATASET)
    by_id = {c["id"]: c for c in data["cases"]}
    return [by_id[i] for i in ("N-01", "A-01", "G-01", "X-01", "B-03")]


def _live(tmp_path):
    err = ModelCallError("server_error", "overloaded", True)
    script = [
        reply(decision(intent="create", task="call mom", due_at="2026-11-11T09:00:00")),  # N-01
        reply("not json"),                                                              # A-01
        reply(decision(intent="refuse", refusal_reason="I only handle reminders.")),    # G-01
        # X-01 is empty text: no model call
        err, err,                                                                       # B-03
    ]
    return evaluate.run_live(_cases(), StubClient(script), load_config(env={}),
                             tmp_path / "live", dataset_sha256="a" * 64,
                             evidence_dir=tmp_path / "evidence",
                             timer=iter(range(0, 10000, 7)).__next__, sleeper=lambda s: None)


def _strip(report):
    keep = ("case_id", "status", "failed_layer", "violations", "semantic", "fallback",
            "fallback_reason", "decision", "error", "latency_ms", "measured")
    return [{k: c.get(k) for k in keep} for c in report["cases"]]


def test_us3_ac50_replay_reproduces_everything(tmp_path):
    """AC-50, FR-041: replay reproduces statuses, layers, scores, fallback flags and verdict."""
    live = _live(tmp_path)
    replayed = evaluate.run_replay(tmp_path / "live", tmp_path / "replay")
    assert _strip(replayed) == _strip(live)
    assert replayed["verdict"] == live["verdict"]
    assert replayed["totals"] == live["totals"]
    assert replayed["latency"] == live["latency"]
    assert replayed["mode"] == "replay"
    assert replayed["source_run_id"] == live["run_id"]


def test_us3_ac52_replay_and_scoring_make_no_model_calls(tmp_path, monkeypatch):
    """AC-52, FR-035, FR-041: replay never builds or calls a live client."""
    _live(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("a live client was built during replay")

    monkeypatch.setattr("reminder_agent.agent.AnthropicClient", forbidden)
    monkeypatch.setattr(evaluate, "AnthropicClient", forbidden)
    evaluate.run_replay(tmp_path / "live", tmp_path / "replay")


def test_us3_replay_client_reraises_saved_infra_error(tmp_path):
    """FR-041: a saved infra error is re-raised so the agent reproduces the same infra_error."""
    _live(tmp_path)
    client = ReplayClient(tmp_path / "live").for_case("B-03")
    for _ in range(2):
        with pytest.raises(ModelCallError) as info:
            client.complete(None)
        assert info.value.category == "server_error"


def test_us3_replay_missing_raw_file_raises(tmp_path):
    """FR-041: replay refuses to invent a reply when a raw file is missing."""
    _live(tmp_path)
    (tmp_path / "live" / "raw" / "N-01.json").unlink()
    with pytest.raises(FileNotFoundError):
        evaluate.run_replay(tmp_path / "live", tmp_path / "replay")


def test_us3_scoring_layers_hold_no_client():
    """AC-52: the scoring modules never reference a model client."""
    harness = Path(evaluate.__file__).parent
    for name in ("layer1_schema.py", "layer2_invariants.py", "layer3_semantic.py",
                 "aggregate.py"):
        text = (harness / name).read_text(encoding="utf-8")
        assert "anthropic" not in text and "ModelClient" not in text, name
