# Quickstart & Validation Guide: Smart Todo CLI

**Plan**: [plan.md](./plan.md) | **Interface**: [contracts/cli.md](./contracts/cli.md) |
**Data file**: [contracts/data-file.md](./contracts/data-file.md)

## Prerequisites

- Python 3.11 (Constitution: Technology Constraints). Check with `python --version`.
- Dev tools, used only for the quality gates:

  ```bash
  python -m venv .venv
  # Windows: .venv\Scripts\activate    POSIX: source .venv/bin/activate
  python -m pip install pytest pytest-cov ruff bandit
  ```

## Run the program

No setup is needed. The launchers at the repository root (`Part-1A/`) put `src/` on the path
themselves (research R8):

```bash
./todo add "Buy milk"             # POSIX shells (or: sh todo add "Buy milk")
.\todo.cmd add "Buy milk"         # Windows PowerShell; in cmd.exe just: todo add "Buy milk"
```

To use plain `todo` from any directory, add `Part-1A/` to your `PATH`. The examples below write
plain `todo`.

## Smoke scenarios (expected output in comments)

Run these in an empty scratch directory, or pass `--file` with a scratch path:

```bash
todo add "Buy milk"                                   # Added task 1: Buy milk
todo add "Pay rent" --priority high --tag home --tag Bills
                                                      # Added task 2: Pay rent
todo list                                             # 2 [todo] (high) Pay rent #home #bills
                                                      # 1 [todo] (medium) Buy milk
todo status 1 in_progress                             # Task 1: todo -> in_progress
todo status 1 todo ; echo $?                          # stderr: Error: cannot change status of task 1 from in_progress to todo.   → 1
todo list --tag HOME                                  # 2 [todo] (high) Pay rent #home #bills
todo delete 2                                         # Deleted task 2.
todo add "Next"                                       # Added task 3: Next   (ID 2 never reused)
echo '{not json' > todo.json ; todo list ; echo $?    # stderr: Error: data file 'todo.json' is corrupt or unreadable; it was not modified.   → 3
todo frobnicate ; echo $?                             # stderr starts with: usage: todo   → 2
```

All of these are covered exactly by AC-01–AC-59 in [spec.md](./spec.md). The automated suite
below is the authoritative check.

## Quality gates (Constitution II): all must pass

All gates run through the harness (research R11):

```bash
python .harness/run_harness.py            # during development (non-3.11 Python only warns)
python .harness/run_harness.py --final    # final report: also requires Python 3.11
```

It runs, from the repository root:

| Gate | Command | PASS when |
|------|---------|-----------|
| ruff | `python -m ruff check .` | exit 0 (0 errors) |
| bandit | `python -m bandit -r src tests .harness -f json` | no MEDIUM/HIGH findings, no bandit errors |
| pytest | `python -m pytest --cov=smart_todo …` (collects `tests/` and `.harness/tests/`) | > 0 tests; 0 failures, errors or skips |
| coverage | from `coverage.json` | ≥ 90.0% of `smart_todo` |

Expected: the exit code is 0 and the last line names a new
`evidence/harness-results/<timestamp>/` directory. That directory holds `summary.json`
(`"overall": "PASS"`) and each tool's stdout/stderr. A non-zero exit code means at least one
gate failed; see `summary.json`.

## Traceability check (Constitution III)

Every AC has a matching test name:

```bash
python - <<'EOF'
import pathlib, re
spec = pathlib.Path("specs/001-smart-todo-cli/spec.md").read_text(encoding="utf-8")
acs = sorted({m.replace("-", "") for m in re.findall(r"\*\*(AC-\d\d)\*\*", spec)})
tests = "".join(p.read_text(encoding="utf-8") for p in pathlib.Path("tests").rglob("test_*.py"))
missing = [a for a in acs if not re.search(rf"def test_{a}_", tests)]
print(f"{len(acs)} ACs, missing tests: {missing or 'none'}")
EOF
```

Expected: `59 ACs, missing tests: none`.
