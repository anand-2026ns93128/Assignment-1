"""Traceability checks across spec.md and the test suite (T059; Constitution I).

* Every acceptance criterion AC-01..AC-63 is named in at least one test docstring.
* Every FR in spec.md maps to at least one AC in the traceability table.
* Every test written for a user story follows the ``test_us<N>_`` naming rule.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "001-nl-reminder-agent" / "spec.md"
TESTS = ROOT / "tests"
# Setup / Foundational test files: no story prefix required (tasks.md naming rule).
FOUNDATIONAL = {"test_models.py", "test_config.py", "test_dataset.py", "test_run_harness.py"}
_RANGE = re.compile(r"AC-(\d{2}) to AC-(\d{2})")
_SINGLE = re.compile(r"AC-(\d{2})")


def _spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


def _test_functions():
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                yield path, node


def _named_acs(text: str) -> set[str]:
    found = {f"AC-{n}" for n in _SINGLE.findall(text)}
    for start, end in _RANGE.findall(text):
        found |= {f"AC-{n:02d}" for n in range(int(start), int(end) + 1)}
    return found


def test_every_acceptance_criterion_is_tested():
    """Constitution I: AC-01..AC-63 each appear in at least one test docstring."""
    spec_acs = set(re.findall(r"\*\*(AC-\d{2})\*\*", _spec_text()))
    assert len(spec_acs) == 63
    covered: set[str] = set()
    for _, node in _test_functions():
        covered |= _named_acs(ast.get_docstring(node) or "")
    missing = sorted(spec_acs - covered)
    assert missing == [], f"acceptance criteria with no test: {missing}"


def test_every_requirement_maps_to_an_acceptance_criterion():
    """Constitution I: every FR in spec.md has at least one AC in the traceability table."""
    text = _spec_text()
    frs = set(re.findall(r"\*\*(FR-\d{3})\*\*", text))
    table = text.split("### Requirement")[1].split("### Key Entities")[0]
    rows = {m.group(1): m.group(2) for m in re.finditer(r"^\| (FR-\d{3}) \| (.+?) \|$", table,
                                                         re.M)}
    unmapped = sorted(fr for fr in frs if not _SINGLE.search(rows.get(fr, "")))
    assert unmapped == [], f"requirements with no acceptance criterion: {unmapped}"


def test_every_test_has_a_docstring_naming_ids():
    """Tasks.md rule: every test docstring names the AC/FR (or SC/Constitution) it verifies."""
    bare = [f"{p.name}::{n.name}" for p, n in _test_functions()
            if not re.search(r"(AC|FR|SC|R)-\d|Constitution",
                             ast.get_docstring(n) or "")]
    assert bare == [], f"tests without requirement IDs: {bare}"


def test_story_tests_follow_naming_rule():
    """Constitution I, tasks.md naming rule: story tests are named test_us<N>_*."""
    offenders = []
    for path, node in _test_functions():
        if path.parent.name not in ("agent", "harness") or path.name in FOUNDATIONAL:
            continue
        if not re.match(r"test_us[1-4]_", node.name):
            offenders.append(f"{path.name}::{node.name}")
    assert offenders == [], f"story tests without test_us<N>_ prefix: {offenders}"
