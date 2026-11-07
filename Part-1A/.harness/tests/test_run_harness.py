"""Self-tests for the pure helpers of .harness/run_harness.py (task T004).

These tests never start the real gates.
"""

import importlib.util
import json
from pathlib import Path

HARNESS_PATH = Path(__file__).parents[1] / "run_harness.py"
_spec = importlib.util.spec_from_file_location("run_harness", HARNESS_PATH)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def _junit(tmp_path, tests, failures=0, errors=0, skipped=0):
    path = tmp_path / "junit.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites>'
        f'<testsuite name="pytest" errors="{errors}" failures="{failures}" '
        f'skipped="{skipped}" tests="{tests}" time="0.1"></testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def test_bandit_gate_passes_with_only_low_findings():
    report = {"errors": [], "results": [{"issue_severity": "LOW"}]}
    result = harness.bandit_status(report)
    assert result["status"] == "PASS"
    assert result["low_count"] == 1
    assert result["medium_high_count"] == 0


def test_bandit_gate_fails_on_medium_or_high():
    for severity in ("MEDIUM", "HIGH"):
        report = {"errors": [], "results": [{"issue_severity": severity}]}
        assert harness.bandit_status(report)["status"] == "FAIL"


def test_bandit_gate_fails_on_bandit_errors():
    report = {"errors": [{"filename": "x.py", "reason": "syntax error"}], "results": []}
    assert harness.bandit_status(report)["status"] == "FAIL"


def test_bandit_gate_fails_without_report():
    assert harness.bandit_status(None)["status"] == "FAIL"


def test_pytest_gate_from_junit(tmp_path):
    assert harness.pytest_status(_junit(tmp_path, tests=3))["status"] == "PASS"
    assert harness.pytest_status(_junit(tmp_path, tests=3, failures=1))["status"] == "FAIL"
    assert harness.pytest_status(_junit(tmp_path, tests=3, errors=1))["status"] == "FAIL"
    assert harness.pytest_status(_junit(tmp_path, tests=3, skipped=1))["status"] == "FAIL"
    assert harness.pytest_status(_junit(tmp_path, tests=0))["status"] == "FAIL"
    assert harness.pytest_status(tmp_path / "missing.xml")["status"] == "FAIL"


def test_coverage_gate_threshold(tmp_path):
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps({"totals": {"percent_covered": 90.0}}), encoding="utf-8")
    assert harness.coverage_status(path, 90.0)["status"] == "PASS"
    path.write_text(json.dumps({"totals": {"percent_covered": 89.99}}), encoding="utf-8")
    assert harness.coverage_status(path, 90.0)["status"] == "FAIL"
    assert harness.coverage_status(tmp_path / "missing.json", 90.0)["status"] == "FAIL"


def test_coverage_threshold_constant_is_90():
    assert harness.COVERAGE_THRESHOLD == 90.0


def test_overall_and_exit_code():
    all_pass = {"ruff": {"status": "PASS"}, "bandit": {"status": "PASS"}}
    one_fail = {"ruff": {"status": "PASS"}, "bandit": {"status": "FAIL"}}
    assert harness.overall(all_pass) == "PASS"
    assert harness.exit_code_for("PASS") == 0
    assert harness.overall(one_fail) == "FAIL"
    assert harness.exit_code_for("FAIL") == 1


def test_unique_run_dir(tmp_path):
    first = harness.unique_run_dir(tmp_path, "20261107T120000Z")
    assert first == tmp_path / "20261107T120000Z"
    first.mkdir()
    assert harness.unique_run_dir(tmp_path, "20261107T120000Z") == tmp_path / "20261107T120000Z-1"


def test_python_check():
    assert harness.python_status((3, 11, 9), final=True)["status"] == "PASS"
    assert harness.python_status((3, 13, 2), final=True)["status"] == "FAIL"
    warn = harness.python_status((3, 13, 2), final=False)
    assert warn["status"] == "WARN"
    assert harness.overall({"ruff": {"status": "PASS"}, "python": warn}) == "PASS"
