"""Tests for the quality-gate script .harness/run_harness.py (T007; research R-08, R-13)."""

from __future__ import annotations

import run_harness as rh


def test_bandit_low_findings_pass():
    """Constitution VIII: LOW findings are counted but do not fail the bandit gate."""
    report = {"results": [{"issue_severity": "LOW"}], "errors": []}
    result = rh.bandit_status(report)
    assert result["status"] == rh.PASS
    assert result["low_count"] == 1


def test_bandit_medium_high_or_errors_fail():
    """Constitution VIII: any MEDIUM/HIGH finding or bandit error fails the gate."""
    assert rh.bandit_status({"results": [{"issue_severity": "MEDIUM"}]})["status"] == rh.FAIL
    assert rh.bandit_status({"results": [{"issue_severity": "HIGH"}]})["status"] == rh.FAIL
    assert rh.bandit_status({"results": [], "errors": [{"x": 1}]})["status"] == rh.FAIL
    assert rh.bandit_status(None)["status"] == rh.FAIL


def _junit(tmp_path, **counts):
    attrs = " ".join(f'{k}="{v}"' for k, v in counts.items())
    path = tmp_path / "junit.xml"
    path.write_text(f"<testsuites><testsuite {attrs}></testsuite></testsuites>", encoding="utf-8")
    return path


def test_pytest_gate_counts(tmp_path):
    """Constitution VIII: more than 0 tests and no failures, errors or skips."""
    ok = _junit(tmp_path, tests=3, failures=0, errors=0, skipped=0)
    assert rh.pytest_status(ok)["status"] == rh.PASS
    for bad in ({"tests": 0}, {"tests": 3, "failures": 1}, {"tests": 3, "errors": 1},
                {"tests": 3, "skipped": 1}):
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, **bad}
        assert rh.pytest_status(_junit(tmp_path, **counts))["status"] == rh.FAIL
    assert rh.pytest_status(tmp_path / "missing.xml")["status"] == rh.FAIL


def _make_tree(tmp_path, files: dict[str, str]):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_clock_ban_flags_agent_and_layer_code(tmp_path):
    """FR-004, Constitution III: system clock reads are banned in agent and scoring code."""
    root = _make_tree(tmp_path, {
        "src/reminder_agent/a.py": "from datetime import datetime\nx = datetime.now()\n",
        "src/reminder_agent/b.py": "import time\ny = time.time()\n",
        "src/reminder_agent/c.py": "import datetime\nz = datetime.date.today()\n",
        "src/reminder_agent/d.py": "import tzlocal\n",
        ".harness/layer2_invariants.py": "import datetime\nq = datetime.datetime.utcnow()\n",
        ".harness/aggregate.py": "ok = 1\n",
    })
    violations = rh.clock_ban_violations(root)
    flagged = {v.split(":")[0] for v in violations}
    assert flagged == {
        "src/reminder_agent/a.py", "src/reminder_agent/b.py", "src/reminder_agent/c.py",
        "src/reminder_agent/d.py", ".harness/layer2_invariants.py",
    }


def test_clock_ban_allows_marked_evidence_timestamp(tmp_path):
    """Constitution III: the evidence timestamp in evaluate.py is the one allowed clock read."""
    root = _make_tree(tmp_path, {
        ".harness/evaluate.py": (
            "def _evidence_timestamp():\n"
            "    return datetime.now(UTC)  # clock-ban: allowed (evidence metadata)\n"
        ),
        "src/reminder_agent/ok.py": "start = time.perf_counter()\n",
    })
    assert rh.clock_ban_violations(root) == []
    _make_tree(tmp_path, {".harness/evaluate.py": "x = datetime.now()\n"})
    assert rh.clock_ban_violations(root) == [".harness/evaluate.py:1: datetime.now("]


def test_secret_scan_finds_api_key_in_evidence(tmp_path):
    """AC-49, SC-007, Constitution IX: no API key may appear under evidence/."""
    fake = "sk-" + "ant-test-123456"
    root = _make_tree(tmp_path, {
        "evidence/eval-runs/r1/raw/N-01.json": '{"text": "fine"}',
        "evidence/harness-log.md": "nothing secret here, sk-ant mention without a key\n",
    })
    assert rh.secret_scan(root) == []
    _make_tree(tmp_path, {"evidence/eval-runs/r1/eval-results.json": f'{{"k": "{fake}"}}'})
    assert rh.secret_scan(root) == ["evidence/eval-runs/r1/eval-results.json"]


def test_unique_run_dir_suffixes(tmp_path):
    """R-13: evidence run directories never overwrite each other."""
    first = rh.unique_run_dir(tmp_path, "20261107T000000Z")
    first.mkdir()
    second = rh.unique_run_dir(tmp_path, "20261107T000000Z")
    assert second.name == "20261107T000000Z-1"


def test_overall_and_exit_codes():
    """R-13: overall PASS only when no gate FAILs; exit 0 for PASS, 1 for FAIL."""
    assert rh.overall({"a": {"status": rh.PASS}, "b": {"status": rh.WARN}}) == rh.PASS
    assert rh.overall({"a": {"status": rh.PASS}, "b": {"status": rh.FAIL}}) == rh.FAIL
    assert rh.exit_code_for(rh.PASS) == 0
    assert rh.exit_code_for(rh.FAIL) == 1


def test_python_status_final_requires_311():
    """R-13: --final fails on a non-3.11 interpreter; otherwise only warns."""
    assert rh.python_status((3, 11, 9), final=True)["status"] == rh.PASS
    assert rh.python_status((3, 13, 0), final=True)["status"] == rh.FAIL
    assert rh.python_status((3, 13, 0), final=False)["status"] == rh.WARN
