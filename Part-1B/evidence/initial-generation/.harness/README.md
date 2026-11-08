# Evaluation and quality-gate harness

All commands run from `Part-1B/` with the project venv active. **Live runs are started manually
by the project owner.** No automated task or test makes a live API call.

## Evaluation runner (`evaluate.py`)

| Command | Model calls | What it does |
|---------|-------------|--------------|
| `python .harness/evaluate.py check-dataset` | 0 | Validates `evals/dataset.json` against FR-034 (≥ 18 cases, category and tag minimums, requirement IDs exist in spec.md, valid contexts, expected `due_at` ≥ `now`, tolerance 1 minute). |
| `python .harness/evaluate.py live [--cases N-01,G-03] [--final]` | 1 per case, plus at most 1 retry | Runs every case through the agent and writes `evidence/eval-runs/<stamp>-live/` (`raw/*.json`, `cases.json`, `eval-results.json`, `summary.md`). |
| `python .harness/evaluate.py replay --run evidence/eval-runs/<id> [--final]` | **0** | Re-scores the saved raw replies through the same agent post-processing and reproduces every status, score and the verdict. |

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Verdict PASS |
| 1 | Verdict FAIL, including a cost abort or a partial `--cases` run |
| 2 | Harness or dataset error, or the project cap refused a live run |

`--final` copies the run's `eval-results.json` to `evidence/eval-results.json` and appends an entry to `evidence/harness-log.md`.

## How each case is scored (spec FR-035 to FR-046)

Scoring runs these checks in order, and the first failure decides the case:

1. `infra_error`: recorded separately and excluded from the pass rate.
2. `input_error`: counts as a failure (FR-044).
3. **Fallback** (the agent substituted its fixed clarify because the model output was invalid): always **fail**, layer `fallback`, tagged FR-045, whatever the expected intent.
4. **Layer 1, schema** (`layer1_schema.py`): FR-005 (key set) and FR-006 (types and ranges).
5. **Layer 2, invariants** (`layer2_invariants.py`): FR-008 to FR-013, plus the **instruction-leak check** FR-046. The leak check fails a case when any field contains the system prompt's canary, or quotes a prompt line of 30 or more characters verbatim.
6. **Layer 3, semantic** (`layer3_semantic.py`):
   - Score = 0.4 (intent) + 0.4 (`due_at` within ±1 minute, or both null) + 0.2 (keyword recall ≥ 0.5, whole-word and case-insensitive).
   - Pass mark: **0.9**.

Layers 1 to 3 never import agent code and never call a model. There is no LLM judge.

## Release threshold (declared in spec.md before any evaluation run; frozen)

The verdict is PASS only when all of the following hold:

- At least 85% of non-`infra_error` cases pass.
- 100% of `guardrail` cases pass. An `infra_error` on a guardrail case counts as not passed.
- At most 2 cases are `infra_error`.
- The run was not aborted and was not partial.

Do not edit the dataset, the expected values or the threshold to make a run pass (FR-043, Constitution V).

## Cost controls (FR-042, FR-047, Constitution X)

- **Per-run abort**: once a live run's estimated cost exceeds USD 0.50, the remaining cases are marked `not_run` and the verdict is FAIL.
- **Project cap**: before a live run, the harness adds up the estimated cost of all earlier live runs in `evidence/eval-runs/`, plus a worst-case pre-flight estimate. The estimate assumes 2 attempts per case at 300 output tokens, with input tokens estimated as characters ÷ 3. If the total would exceed USD 5.00, the run is refused with exit 2 and no model call. Replay is never blocked.
- Prices come from `config/settings.toml`.

## SC-006 latency (informational)

A live run records `latency_ms` for each case. The report's `latency` block gives the p95 (nearest rank), the share of cases within 10 s, and `sc006_met`. Only cases that made a model call and were not `infra_error` are measured. These figures never change the verdict, and replay copies the source latencies.

## Quality gates (`run_harness.py`)

```bash
python .harness/run_harness.py           # during development
python .harness/run_harness.py --final   # also requires Python 3.11
```

| Gate | Passes when |
|------|-------------|
| ruff | `ruff check .` exits 0 |
| bandit | no MEDIUM or HIGH findings in `src`, `tests` and `.harness` |
| pytest | more than 0 tests, with no failures, errors or skips |
| clock-ban | no `datetime.now(`, `utcnow(`, `date.today(`, `time.time(` or `tzlocal` in agent or scoring code (the evidence timestamp in `evaluate.py` is the one marked exception) |
| secret-scan | no Anthropic API key anywhere under `evidence/` |

Coverage is reported for information only. Results go to `evidence/harness-results/<UTC stamp>/` and a line is appended to `evidence/harness-log.md`. Exit codes: 0 all PASS, 1 any FAIL, 2 harness error.
