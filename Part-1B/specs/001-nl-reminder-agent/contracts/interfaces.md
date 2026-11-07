# Interface Contracts: Library, CLI and Evaluation Runner

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

## 1. Library API (`reminder_agent`)

```python
from reminder_agent import run_agent, AgentOutcome, ReminderDecision, ErrorResult

outcome: AgentOutcome = run_agent(
    text: str,
    now: str,                          # ISO-8601; required, never defaulted from the system clock
    timezone: str,                     # IANA name
    reminders: list[dict] | None = None,   # [{"id","task","due_at"}]
    *,
    client: ModelClient | None = None,     # default: live Anthropic client built from config
    config: AgentConfig | None = None,     # default: config/settings.toml + env overrides
)
```

- Exactly one of `outcome.decision` and `outcome.error` is set (data-model AgentOutcome).
- `outcome.decision.to_json()` returns the seven-key object, which validates against [reminder_output.schema.json](reminder_output.schema.json).
- `outcome.error.to_json()` validates against [error_response.schema.json](error_response.schema.json).
- `run_agent` never raises for input, model or network problems. It raises only on programming errors, such as a malformed `config` object.
- Same inputs plus the same `client` replies produce the same outcome (FR-004, AC-14).

## 2. CLI (`python -m reminder_agent`, console script `reminder-agent`)

```text
reminder-agent --text TEXT --now ISO8601 --timezone IANA [--reminders FILE.json]
               [--model NAME] [--max-tokens N] [--temperature T] [--config FILE]
reminder-agent --stdin            # reads {"text","now","timezone","existing_reminders"} JSON from stdin
```

| Outcome | stdout | stderr | Exit code |
|---------|--------|--------|-----------|
| Decision (any intent, including fallback) | the seven-key decision as JSON, one line | — | `0` |
| Usage error (argparse) | — | usage | `2` |
| `input_error` | — | error JSON | `3` |
| `infra_error` | — | error JSON | `4` |

- The CLI is a thin wrapper over `run_agent`, so CLI and library parity (FR-002, AC-15) holds by construction and is tested.
- The API key is read only from `ANTHROPIC_API_KEY` (environment or git-ignored `.env` via python-dotenv). It is never accepted as a flag and never printed.

## 3. Evaluation runner (`.harness/evaluate.py`)

```text
python .harness/evaluate.py live   [--dataset evals/dataset.json] [--cases N-01,G-03] [--final]
python .harness/evaluate.py replay --run evidence/eval-runs/<run_id> [--final]
python .harness/evaluate.py check-dataset [--dataset evals/dataset.json]
```

| Mode | Model calls | Writes |
|------|-------------|--------|
| `check-dataset` | 0 | nothing. It exits 0 if the dataset passes FR-034, and 1 with the named problems otherwise. |
| `live` | one per case (plus at most one retry) | `evidence/eval-runs/<run_id>/raw/<case_id>.json` (ModelReply or error, usage, attempts), `eval-results.json` and `summary.md` |
| `replay` | **0** (a ReplayClient is substituted, AC-50) | `evidence/eval-runs/<run_id>-replay-<n>/eval-results.json` with `source_run_id` |

- `--final` also copies the run's `eval-results.json` to `evidence/eval-results.json` and appends an entry to `evidence/harness-log.md`.
- A `--cases` subset run is marked `partial: true` and its verdict is `FAIL (partial run)`. Only full runs produce a release verdict.
- Exit codes: `0` verdict PASS, `1` verdict FAIL (including an abort), `2` harness or dataset error.
- `summary.md` lists each failing case with `failed_layer` and violation IDs (for example `G-03 invariant FR-013: task must be null for refuse`, or `A-01 fallback FR-045: unparseable`), ready to paste back to the coding agent.

## 4. Quality-gate script (`.harness/run_harness.py`)

```text
python .harness/run_harness.py [--final]
```

The gates are ruff, bandit (no MEDIUM/HIGH), pytest (more than 0 tests, no failures, errors or skips), the clock-ban check and the evidence secret scan. Coverage is reported for information. The script exits `0` if every gate passes, `1` if any gate fails and `2` on a harness error, and writes `evidence/harness-results/<UTC stamp>/`.
