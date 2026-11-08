# Natural-Language Reminder Agent (Part 1B)

This is a Python 3.11 library and CLI. It turns one user sentence into one schema-validated reminder decision, given:

- the user's text
- the current time (`now`, ISO-8601)
- an IANA timezone
- optionally, the reminders the user already has

It also includes a deterministic evaluation harness that scores the agent against a frozen dataset and gives a PASS/FAIL release verdict.

The spec-driven artifacts are in `specs/001-nl-reminder-agent/`: `spec.md` (v1.3), `plan.md`, `tasks.md`, `research.md`, `data-model.md` and `contracts/`.

## Output

Every decision has exactly seven keys:

```json
{"intent": "create", "task": "call mom", "due_at": "2026-11-11T09:00:00+05:30",
 "target_id": null, "snooze_minutes": null, "clarification_question": null, "refusal_reason": null}
```

`intent` is one of these:

| Intent | Used when |
|--------|-----------|
| `create` | The request names both a task and a time. |
| `reschedule` | An existing reminder moves to a new time. |
| `snooze` | An existing reminder is postponed by 1–1440 minutes. |
| `clarify` | The task or time is missing or ambiguous, or the input is malformed. |
| `refuse` | The request is out of scope, harmful, unsupported, or only an injection attempt. |

Invalid model output is never returned. The agent substitutes a fixed `clarify` instead. Errors are separate JSON objects, never decisions:

- `input_error`: bad `now`, timezone or reminder list.
- `infra_error`: the model API failed after one retry.

## Setup

```bash
py -3.11 -m venv .venv
source .venv/Scripts/activate            # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cp .env.example .env                     # put ANTHROPIC_API_KEY=... here (needed only for live calls)
```

The API key is read only from the environment or the git-ignored `.env`. It is never a CLI flag, and it is never written to logs or evidence.

## Library

```python
from reminder_agent import run_agent

outcome = run_agent("remind me to call mom tomorrow at 9am",
                    now="2026-11-10T10:00:00+05:30", timezone="Asia/Kolkata",
                    reminders=[])
if outcome.error:
    print(outcome.error.to_json())        # input_error / infra_error
else:
    print(outcome.decision.to_json())     # the seven-key decision
```

The agent never reads the system clock or timezone. All times come from `now` and `timezone`.

## CLI

```bash
reminder-agent --text "remind me to call mom tomorrow at 9am" \
  --now 2026-11-10T10:00:00+05:30 --timezone Asia/Kolkata [--reminders reminders.json]
echo '{"text": "...", "now": "...", "timezone": "...", "existing_reminders": []}' | reminder-agent --stdin
```

| Exit code | Meaning | Output |
|-----------|---------|--------|
| 0 | Decision | JSON on stdout |
| 2 | Usage error | message on stderr |
| 3 | `input_error` | error JSON on stderr |
| 4 | `infra_error` | error JSON on stderr |

## Model settings (`config/settings.toml`)

| Setting | Value |
|---------|-------|
| Model | `claude-haiku-5-5` |
| `max_tokens` | 300 (never more) |
| Thinking | disabled |
| Effort | `low` |
| Structured output | JSON schema derived from `schemas/reminder_output.schema.json` |
| Temperature | left at the model default, not sent |

**Why temperature isn't set**: `claude-haiku-5-5` rejects `temperature = 0`. Live responses can therefore vary between runs, and evaluation results are made reproducible by saving raw responses and re-scoring them in replay mode. The `REMINDER_MODEL`, `REMINDER_MAX_TOKENS` and `REMINDER_TEMPERATURE` environment variables and the matching CLI flags override the file.

## Tests and quality gates (offline, no API key needed)

```bash
python -m pytest                         # all tests use stub or replay clients, no network
python .harness/run_harness.py           # ruff, bandit, pytest, clock-ban, secret scan
python .harness/evaluate.py check-dataset
```

## Evaluation

Live runs are **manual**, because they cost money.

```bash
python .harness/evaluate.py live                         # pre-flight cost check, then one call per case
python .harness/evaluate.py replay --run evidence/eval-runs/<run_id>   # zero API calls
```

Each run writes `evidence/eval-runs/<run_id>/`. Its `summary.md` lists every failing case as `<case_id> <layer> <FR-id>: <message>`.

**Release verdict**: PASS requires all of the following:

- At least 85% of non-`infra_error` cases pass.
- 100% of guardrail cases pass.
- At most 2 cases are `infra_error`.

A case passes when it passes the schema and invariant checks (including the instruction-leak check) and has a semantic score of at least 0.9. A fallback always fails.

**Cost controls**: a run aborts once its estimated cost exceeds USD 0.50, and a run is refused if total live spend would exceed USD 5.00.

See `.harness/README.md` for details.
