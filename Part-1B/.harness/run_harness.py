"""Quality-gate harness for the reminder agent (task T008; research R-08, R-13).

Runs the Constitution VIII gates from the Part-1B root and records evidence:

* ruff         - ``ruff check .`` must exit 0
* bandit       - no MEDIUM/HIGH findings and no bandit errors in ``src tests .harness``
* pytest       - more than 0 tests; no failures, errors or skips (coverage reported, NOT gated)
* clock-ban    - no system-clock / local-timezone reads in agent or scoring code (Constitution III)
* secret-scan  - no Anthropic API key anywhere under ``evidence/`` (Constitution IX)

Each run writes tool output, ``bandit.json``, ``junit.xml``, ``coverage.json`` and
``summary.json`` to ``evidence/harness-results/<UTC stamp>/`` and appends one line to
``evidence/harness-log.md``.

Exit codes: 0 = every gate PASS, 1 = at least one gate FAIL, 2 = harness error.
``--final`` additionally requires Python 3.11.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import platform
import re

# Justification for nosec B404: subprocess only runs fixed tool argument lists, never a shell.
import subprocess  # nosec B404
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evidence" / "harness-results"
HARNESS_LOG = ROOT / "evidence" / "harness-log.md"
REQUIRED_PYTHON = (3, 11)

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"

_SUITE_TAG = re.compile(r"<testsuite\b([^>]*)>")
_ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
_JUNIT_COUNTS = ("tests", "failures", "errors", "skipped")

# Clock-ban (research R-08). Order matters: the first matching pattern on a line is reported.
CLOCK_PATTERNS = (
    "datetime.now(",
    "datetime.utcnow(",
    "date.today(",
    "time.time(",
    "tzlocal",
)
CLOCK_ALLOW_MARKER = "# clock-ban: allowed (evidence metadata)"
CLOCK_SCOPES = (
    "src/reminder_agent/**/*.py",
    ".harness/layer*.py",
    ".harness/aggregate.py",
    ".harness/budget.py",
    ".harness/evaluate.py",
)

# Secret scan: the key prefix is assembled so this file never contains it literally.
_KEY_RE = re.compile("sk-" + "ant-" + r"[A-Za-z0-9_\-]{6,}")


# --------------------------------------------------------------------------- pure helpers


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
        return {"status": FAIL, "medium_high_count": None, "low_count": None,
                "note": "bandit report missing or not valid JSON"}
    results = report.get("results") or []
    errors = report.get("errors") or []
    medium_high = sum(1 for r in results if r.get("issue_severity") in ("MEDIUM", "HIGH"))
    low = sum(1 for r in results if r.get("issue_severity") == "LOW")
    result = {"status": PASS if medium_high == 0 and not errors else FAIL,
              "medium_high_count": medium_high, "low_count": low}
    if errors:
        result["note"] = f"{len(errors)} bandit error(s)"
    return result


def pytest_status(junit_path: Path) -> dict:
    """Gate result from a pytest junit XML report (read with a regex, no XML parser)."""
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
    passed = (bool(suites) and totals["tests"] > 0 and totals["failures"] == 0
              and totals["errors"] == 0 and totals["skipped"] == 0)
    return {"status": PASS if passed else FAIL, **totals}


def coverage_info(coverage_json_path: Path) -> dict:
    """Coverage is reported for information only (not a 1B constitutional gate)."""
    try:
        data = json.loads(Path(coverage_json_path).read_text(encoding="utf-8"))
        return {"status": "INFO", "percent": round(float(data["totals"]["percent_covered"]), 2)}
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "INFO", "percent": None, "note": "coverage report missing"}


def clock_ban_violations(root: Path) -> list[str]:
    """Return ``"<relpath>:<line>: <pattern>"`` for each banned clock read in scope."""
    violations: list[str] = []
    seen: set[Path] = set()
    for scope in CLOCK_SCOPES:
        for path in sorted(Path(root).glob(scope)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            rel = path.relative_to(root).as_posix()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for number, line in enumerate(lines, start=1):
                if CLOCK_ALLOW_MARKER in line:
                    continue
                for pattern in CLOCK_PATTERNS:
                    if pattern in line:
                        violations.append(f"{rel}:{number}: {pattern}")
                        break
    return violations


def secret_scan(root: Path) -> list[str]:
    """Return the relative paths of files under ``evidence/`` that contain an API key."""
    hits: list[str] = []
    evidence = Path(root) / "evidence"
    if not evidence.is_dir():
        return hits
    for path in sorted(evidence.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if _KEY_RE.search(text):
                hits.append(path.relative_to(root).as_posix())
    return hits


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
    """PASS unless any entry has status FAIL (WARN and INFO do not fail the run)."""
    return FAIL if any(gate.get("status") == FAIL for gate in gates.values()) else PASS


def exit_code_for(result: str) -> int:
    return 0 if result == PASS else 1


# --------------------------------------------------------------------------- gate runners


def _run_tool(name: str, args: list[str], run_dir: Path) -> tuple[dict, str]:
    """Run ``python -m <args>`` from ROOT, save stdout/stderr, return (record, stdout)."""
    command = [sys.executable, "-m", *args]
    record: dict = {"command": command}
    try:
        # Justification for nosec B603: fixed argument list built above, shell=False.
        completed = subprocess.run(  # nosec B603
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
    except OSError as exc:
        (run_dir / f"{name}.stderr.txt").write_text(f"{exc}\n", encoding="utf-8")
        record.update(exit_code=None, note="tool not installed")
        return record, ""
    (run_dir / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    record["exit_code"] = completed.returncode
    return record, completed.stdout


def _ruff_gate(run_dir: Path) -> dict:
    record, _ = _run_tool("ruff", ["ruff", "check", "."], run_dir)
    record["status"] = PASS if record.get("exit_code") == 0 else FAIL
    return record


def _bandit_gate(run_dir: Path) -> dict:
    record, stdout = _run_tool(
        "bandit", ["bandit", "-r", "src", "tests", ".harness", "-f", "json"], run_dir)
    (run_dir / "bandit.json").write_text(stdout, encoding="utf-8")
    try:
        report = json.loads(stdout)
    except ValueError:
        report = None
    return {**record, **bandit_status(report)}


def _pytest_gate(run_dir: Path) -> dict:
    junit = run_dir / "junit.xml"
    record, _ = _run_tool("pytest", [
        "pytest", "--cov=reminder_agent", "--cov-report=term-missing",
        f"--cov-report=json:{run_dir / 'coverage.json'}", f"--junitxml={junit}",
    ], run_dir)
    return {**record, **pytest_status(junit)}


def _write_summary(run_dir: Path, summary: dict) -> None:
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (run_dir / "summary.json").write_text(text, encoding="utf-8")


def _append_log(summary: dict, run_dir: Path) -> None:
    gates = summary.get("gates", {})
    parts = ", ".join(f"{name} {gate.get('status')}" for name, gate in gates.items())
    line = (f"- Gate run {summary['timestamp']}{' (--final)' if summary['final'] else ''}: "
            f"**{summary['overall']}** ({parts}); python {summary['python_version']}; "
            f"evidence `{run_dir.relative_to(ROOT).as_posix()}`\n")
    HARNESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    existing = HARNESS_LOG.read_text(encoding="utf-8") if HARNESS_LOG.exists() else ""
    if "## Quality gate runs" not in existing:
        line = "\n## Quality gate runs\n\n" + line
    with HARNESS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the reminder agent quality gates.")
    parser.add_argument("--final", action="store_true",
                        help="also require Python 3.11 (final gate report)")
    args = parser.parse_args(argv)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = unique_run_dir(RESULTS_DIR, stamp)
    run_dir.mkdir(parents=True)
    summary: dict = {"timestamp": stamp, "python_version": platform.python_version(),
                     "platform": platform.platform(), "final": args.final, "gates": {}}
    try:
        gates = summary["gates"]
        gates["ruff"] = _ruff_gate(run_dir)
        gates["bandit"] = _bandit_gate(run_dir)
        gates["pytest"] = _pytest_gate(run_dir)
        clock = clock_ban_violations(ROOT)
        gates["clock_ban"] = {"status": PASS if not clock else FAIL, "violations": clock}
        secrets = secret_scan(ROOT)
        gates["secret_scan"] = {"status": PASS if not secrets else FAIL, "files": secrets}
        gates["python"] = python_status(sys.version_info, args.final)
        summary["coverage"] = coverage_info(run_dir / "coverage.json")
        summary["overall"] = overall(gates)
    except Exception as exc:  # harness bug: record what is known, exit 2
        summary["overall"] = FAIL
        summary["harness_error"] = repr(exc)
        _write_summary(run_dir, summary)
        print(f"Harness error: {exc!r}", file=sys.stderr)
        return 2
    _write_summary(run_dir, summary)
    _append_log(summary, run_dir)
    for name, gate in summary["gates"].items():
        print(f"{name:<12} {gate['status']}")
    print(f"coverage     {summary['coverage'].get('percent')}% (informational)")
    print(f"OVERALL      {summary['overall']}")
    print(f"Evidence: {run_dir}")
    return exit_code_for(summary["overall"])


if __name__ == "__main__":
    sys.exit(main())
