"""Tests for dataset loading and validation, .harness/dataset.py (T009).

Covers FR-032, FR-033, FR-034, AC-32 and AC-33.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import dataset as ds

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "001-nl-reminder-agent" / "spec.md"
REAL_DATASET = ROOT / "evals" / "dataset.json"

NOW = "2026-11-10T10:00:00+05:30"
TZ = "Asia/Kolkata"


def _case(cid, category, tags=(), **over):
    case = {
        "id": cid, "category": category, "tags": list(tags), "input": "remind me", "now": NOW,
        "timezone": TZ, "existing_reminders": [], "expected_intent": "clarify",
        "expected_due_at": None, "due_at_tolerance_minutes": 1, "expected_task_keywords": [],
        "requirements": ["FR-012"],
    }
    case.update(over)
    return case


def _valid_data():
    cases = [_case(f"N-0{i}", "normal") for i in range(1, 5)]
    cases += [_case("B-01", "boundary", ["midnight"]), _case("B-02", "boundary", ["month_end"]),
              _case("B-03", "boundary", ["dst"])]
    cases += [_case("A-01", "ambiguous"), _case("M-01", "missing_task"),
              _case("T-01", "missing_time")]
    cases += [_case("X-01", "malformed", ["empty"], input=""),
              _case("X-02", "malformed", ["gibberish"]),
              _case("X-03", "malformed", ["long"], input={"repeat": "ab ", "times": 3})]
    cases += [_case("R-01", "reschedule_snooze", ["reschedule"]),
              _case("R-02", "reschedule_snooze", ["snooze"])]
    cases += [_case("G-01", "guardrail", ["out_of_scope"]), _case("G-02", "guardrail", ["harmful"]),
              _case("G-03", "guardrail", ["injection"])]
    return {"dataset_version": "test", "cases": cases}


def test_valid_dataset_has_no_problems():
    """FR-034, AC-32: a dataset meeting every rule validates cleanly."""
    assert ds.validate_dataset(_valid_data(), SPEC) == []


def test_minimum_case_count_and_category_minimums():
    """FR-032, AC-32: at least 18 cases and every category minimum are required."""
    data = _valid_data()
    data["cases"] = [c for c in data["cases"] if c["id"] != "G-03"]
    problems = ds.validate_dataset(data, SPEC)
    assert any("guardrail" in p for p in problems)
    assert any("18" in p for p in problems)


def test_required_tag_coverage():
    """FR-032, AC-32: boundary/malformed/reschedule_snooze/guardrail sub-coverage is checked."""
    data = _valid_data()
    for case in data["cases"]:
        if case["id"] == "B-03":
            case["tags"] = []
    problems = ds.validate_dataset(data, SPEC)
    assert any("boundary" in p and "dst" in p for p in problems)


def test_case_problems_name_the_case():
    """FR-034, AC-33: each per-case problem is prefixed with the case id."""
    data = copy.deepcopy(_valid_data())
    bad = data["cases"][0]
    bad["requirements"] = ["FR-999"]
    data["cases"][1]["timezone"] = "Mars/Olympus"
    data["cases"][2]["now"] = "not-a-date"
    data["cases"][3]["expected_due_at"] = "2026-11-10T09:00:00+05:30"   # before now
    data["cases"][4]["due_at_tolerance_minutes"] = 5
    data["cases"][5]["existing_reminders"] = [
        {"id": "r1", "task": "a", "due_at": NOW}, {"id": "r1", "task": "b", "due_at": NOW}]
    problems = ds.validate_dataset(data, SPEC)
    text = "\n".join(problems)
    assert "N-01" in text and "FR-999" in text
    assert "N-02" in text and "timezone" in text
    assert "N-03" in text and "now" in text
    assert "N-04" in text and "expected_due_at" in text
    assert "B-01" in text
    assert "B-02" in text and "r1" in text


def test_missing_field_is_reported():
    """FR-033, AC-33: a case missing a required field is rejected."""
    data = _valid_data()
    del data["cases"][0]["expected_intent"]
    problems = ds.validate_dataset(data, SPEC)
    assert any("N-01" in p and "expected_intent" in p for p in problems)


def test_duplicate_case_ids_rejected():
    """FR-033: case ids are unique."""
    data = _valid_data()
    data["cases"][1]["id"] = "N-01"
    assert any("duplicate" in p for p in ds.validate_dataset(data, SPEC))


def test_repeat_input_expands():
    """FR-033: {"repeat": s, "times": n} inputs expand to s * n."""
    assert ds.expand_input({"input": {"repeat": "ab ", "times": 3}}) == "ab ab ab "
    assert ds.expand_input({"input": "plain"}) == "plain"


def test_load_dataset_hash(tmp_path):
    """FR-040: dataset_sha256 is the SHA-256 of the file bytes."""
    path = tmp_path / "d.json"
    raw = json.dumps(_valid_data()).encode("utf-8")
    path.write_bytes(raw)
    data, digest = ds.load_dataset(path)
    assert digest == hashlib.sha256(raw).hexdigest()
    assert len(data["cases"]) == 18


def test_real_dataset_is_valid():
    """FR-032, FR-033, FR-034, AC-32: the committed evals/dataset.json has zero problems."""
    data, _ = ds.load_dataset(REAL_DATASET)
    assert ds.validate_dataset(data, SPEC) == []
    assert len(data["cases"]) == 26
