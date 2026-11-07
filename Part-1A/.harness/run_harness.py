"""Quality-gate harness for Smart Todo CLI (tasks T004-T007; research R11).

Runs the Constitution II gates from the repository root and records evidence:

* ruff      - ``ruff check .`` must exit 0
* bandit    - no MEDIUM/HIGH findings and no bandit errors in ``src tests .harness``
* pytest    - more than 0 tests; no failures, errors or skips
* coverage  - at least 90.0% line coverage of the ``smart_todo`` package

Every run writes each tool's stdout/stderr, ``bandit.json``, ``junit.xml``,
``coverage.json`` and ``summary.json`` to
``evidence/harness-results/<UTC timestamp>/``.

Exit codes: 0 = every gate PASS, 1 = at least one gate FAIL, 2 = harness error.
``--final`` additionally requires Python 3.11 (research R10).

Standard library only. The junit report is read with a regular expression rather
than ``xml.etree`` so the harness itself stays free of bandit findings.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evidence" / "harness-results"
COVERAGE_THRESHOLD = 90.0
REQUIRED_PYTHON = (3, 11)

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"

_SUITE_TAG = re.compile(r"<testsuite\b([^>]*)>")
_ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
_JUNIT_COUNTS = ("tests", "failures", "errors", "skipped")


# --------------------------------------------------------------------------- helpers


def unique_run_dir(base: Path, stamp: str) -> Path:
    """Return ``base/stamp``, or ``base/stamp-N`` if that directory already exists."""
    candidate = base / stamp
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = base / f"{stamp}-{suffix}"
    return candidate


def bandit_status(report: object) -> dict:
    """Gate result for a parsed bandit JSON report (``None`` if it could not be read)."""
    if not isinstance(report, dict):
        return {
            "status": FAIL,
            "medium_high_count": None,
            "low_count": None,
            "note": "bandit report missing or not valid JSON",
        }
    results = report.get("results") or []
    errors = report.get("errors") or []
    medium_high = sum(1 for r in results if r.get("issue_severity") in ("MEDIUM", "HIGH"))
    low = sum(1 for r in results if r.get("issue_severity") == "LOW")
    result = {
        "status": PASS if medium_high == 0 and not errors else FAIL,
        "medium_high_count": medium_high,
        "low_count": low,
    }
    if errors:
        result["note"] = f"{len(errors)} bandit error(s)"
    return result


def pytest_status(junit_path: Path) -> dict:
    """Gate result from a pytest junit XML report."""
    try:
        text = Path(junit_path).read_text(encoding="utf-8")
    except OSError:
        return {"status": FAIL, **dict.fromkeys(_JUNIT_COUNTS, 0), "note": "junit report missing"}
    totals = dict.fromkeys(_JUNIT_COUNTS, 0)
    suites = _SUITE_TAG.findall(text)
    for attributes in suites:
        values = dict(_ATTRIBUTE.findall(attributes))
        for key in _JUNIT_COUNTS:
            totals[key] += int(values.get(key, "0"))
    passed = (
        bool(suites)
        and totals["tests"] > 0
        and totals["failures"] == 0
        and totals["errors"] == 0
        and totals["skipped"] == 0
    )
    return {"status": PASS if passed else FAIL, **totals}


def coverage_status(coverage_json_path: Path, threshold: float) -> dict:
    """Gate result from a coverage.py JSON report."""
    try:
        data = json.loads(Path(coverage_json_path).read_text(encoding="utf-8"))
        percent = float(data["totals"]["percent_covered"])
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "status": FAIL,
            "percent": None,
            "threshold": threshold,
            "note": "coverage report missing or unreadable",
        }
    return {
        "status": PASS if percent >= threshold else FAIL,
        "percent": round(percent, 2),
        "threshold": threshold,
    }


def python_status(version_info: tuple, final: bool) -> dict:
    """Interpreter check: FAIL on a non-3.11 Python only in ``--final`` mode, else WARN."""
    version = ".".join(str(part) for part in tuple(version_info)[:3])
    required = ".".join(str(part) for part in REQUIRED_PYTHON)
    if tuple(version_info)[:2] == REQUIRED_PYTHON:
        status = PASS
    else:
        status = FAIL if final else WARN
    return {"status": status, "version": version, "required": required}


def overall(gates: dict) -> str:
    """PASS unless any entry has status FAIL (WARN does not fail the run)."""
    return FAIL if any(gate.get("status") == FAIL for gate in gates.values()) else PASS


def exit_code_for(result: str) -> int:
    return 0 if result == PASS else 1


# --------------------------------------------------------------------------- gate runners


def _run_tool(name: str, args: list[str], run_dir: Path) -> tuple[dict, str]:
    """Run ``python -m <args>`` from ROOT, save stdout/stderr, return (record, stdout)."""
    command = [sys.executable, "-m", *args]
    record: dict = {"command": command}
    try:
        completed = subprocess.run(  # argument list, never a shell
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        (run_dir / f"{name}.stdout.txt").write_text("", encoding="utf-8")
        (run_dir / f"{name}.stderr.txt").write_text(f"{exc}\n", encoding="utf-8")
        record.update(exit_code=None, note="tool not installed")
        return record, ""
    (run_dir / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    record["exit_code"] = completed.returncode
    if f"No module named {args[0]}" in completed.stderr:
        record["note"] = "tool not installed"
    return record, completed.stdout


def _ruff_gate(run_dir: Path) -> dict:
    record, _ = _run_tool("ruff", ["ruff", "check", "."], run_dir)
    record["status"] = PASS if record.get("exit_code") == 0 else FAIL
    return record


def _bandit_gate(run_dir: Path) -> dict:
    record, stdout = _run_tool(
        "bandit", ["bandit", "-r", "src", "tests", ".harness", "-f", "json"], run_dir
    )
    (run_dir / "bandit.json").write_text(stdout, encoding="utf-8")
    try:
        report = json.loads(stdout)
    except ValueError:
        report = None
    result = bandit_status(report)
    if "note" in record:
        result["note"] = record["note"]
    return {**record, **result}


def _pytest_gate(run_dir: Path) -> dict:
    junit = run_dir / "junit.xml"
    record, _ = _run_tool(
        "pytest",
        [
            "pytest",
            "--cov=smart_todo",
            "--cov-report=term-missing",
            f"--cov-report=json:{run_dir / 'coverage.json'}",
            f"--junitxml={junit}",
        ],
        run_dir,
    )
    result = pytest_status(junit)
    if "note" in record:
        result["note"] = record["note"]
    return {**record, **result}


def _print_table(summary: dict, run_dir: Path) -> None:
    gates = summary["gates"]
    details = {
        "ruff": f"exit code {gates['ruff'].get('exit_code')}",
        "bandit": (
            f"medium/high={gates['bandit'].get('medium_high_count')} "
            f"low={gates['bandit'].get('low_count')}"
        ),
        "pytest": (
            f"tests={gates['pytest'].get('tests')} failures={gates['pytest'].get('failures')} "
            f"errors={gates['pytest'].get('errors')} skipped={gates['pytest'].get('skipped')}"
        ),
        "coverage": (
            f"{gates['coverage'].get('percent')}% (threshold {gates['coverage']['threshold']}%)"
        ),
    }
    for name in ("ruff", "bandit", "pytest", "coverage"):
        print(f"{name:<9} {gates[name]['status']:<5} {details[name]}")
    python = summary["python"]
    print(f"python    {python['status']:<5} {python['version']} (required {python['required']})")
    print(f"OVERALL   {summary['overall']}")
    print(f"Evidence: {run_dir}")


def _write_summary(run_dir: Path, summary: dict) -> None:
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (run_dir / "summary.json").write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Smart Todo CLI quality gates.")
    parser.add_argument(
        "--final", action="store_true", help="also require Python 3.11 (final gate report)"
    )
    args = parser.parse_args(argv)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = unique_run_dir(RESULTS_DIR, stamp)
    run_dir.mkdir(parents=True)
    summary: dict = {
        "timestamp": stamp,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "final": args.final,
        "gates": {},
        "warnings": [],
    }
    try:
        gates = summary["gates"]
        gates["ruff"] = _ruff_gate(run_dir)
        gates["bandit"] = _bandit_gate(run_dir)
        gates["pytest"] = _pytest_gate(run_dir)
        gates["coverage"] = coverage_status(run_dir / "coverage.json", COVERAGE_THRESHOLD)
        summary["python"] = python_status(sys.version_info, args.final)
        if summary["python"]["status"] == WARN:
            summary["warnings"].append("python_version is not 3.11")
        summary["overall"] = overall({**gates, "python": summary["python"]})
    except Exception as exc:  # harness bug: record what is known, exit 2
        summary["overall"] = FAIL
        summary["harness_error"] = repr(exc)
        _write_summary(run_dir, summary)
        print(f"Harness error: {exc!r}", file=sys.stderr)
        print(f"Evidence: {run_dir}")
        return 2
    _write_summary(run_dir, summary)
    _print_table(summary, run_dir)
    return exit_code_for(summary["overall"])


if __name__ == "__main__":
    sys.exit(main())
