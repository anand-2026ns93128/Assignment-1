# Quality-gate harness

`run_harness.py` runs the four Constitution II gates for Smart Todo CLI and saves the evidence
of every run.

| Gate | Command (run from the repository root) | PASS when |
|------|-----------------------------------------|-----------|
| ruff | `python -m ruff check .` | exit code 0 |
| bandit | `python -m bandit -r src tests .harness -f json` | no MEDIUM/HIGH findings and no bandit errors (LOW findings are counted, not failed) |
| pytest | `python -m pytest --cov=smart_todo …` (collects `tests/` and `.harness/tests/`) | more than 0 tests; 0 failures, errors and skips |
| coverage | read from `coverage.json` | ≥ 90.0% line coverage of `smart_todo` |

## Install

```bash
python -m pip install pytest pytest-cov ruff bandit
```

## Run

```bash
python .harness/run_harness.py           # during development: a non-3.11 Python only warns
python .harness/run_harness.py --final   # final report: a non-3.11 Python fails the run
```

## Output

Each run creates `evidence/harness-results/<UTC timestamp>/` (with `-1`, `-2`, … appended if
that name already exists) containing:

- `ruff.stdout.txt`, `ruff.stderr.txt`
- `bandit.stdout.txt`, `bandit.stderr.txt`, `bandit.json`
- `pytest.stdout.txt`, `pytest.stderr.txt`, `junit.xml`, `coverage.json`
- `summary.json`: PASS/FAIL per gate, the Python check, and `"overall"`

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | every gate PASS |
| 1 | at least one gate FAIL |
| 2 | the harness itself failed (see `summary.json` → `harness_error`) |

## Self-tests

The self-tests in `.harness/tests/` are listed in pytest's `testpaths`, so the pytest gate runs
them. To run only them:

```bash
python -m pytest .harness/tests
```
