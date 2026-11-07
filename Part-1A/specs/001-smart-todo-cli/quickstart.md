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

From the repository root (`Part-1A/`):

```bash
# POSIX shells
export PYTHONPATH=src
todo() { python -m smart_todo "$@"; }

# PowerShell
$env:PYTHONPATH = "src"
function todo { python -m smart_todo @args }
```

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

All of these are covered exactly by AC-01–AC-58 in [spec.md](./spec.md). The automated suite
below is the authoritative check.

## Quality gates (Constitution II): all must pass

```bash
ruff check .                                          # expect: All checks passed! (0 errors)
bandit -r src tests                                   # expect: no Medium / High issues
pytest --cov=smart_todo --cov-report=term-missing --cov-fail-under=90
                                                      # expect: 100% passed, coverage ≥ 90%
```

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

Expected: `58 ACs, missing tests: none`.
