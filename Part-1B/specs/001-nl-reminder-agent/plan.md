# Implementation Plan: Natural-Language Reminder Agent and Evaluation Harness

**Branch**: `001-nl-reminder-agent` (spec directory; work is currently on git `main`) | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-nl-reminder-agent/spec.md` (v1.2, with the 2026-11-07 clarifications: 0.9 pass mark, `input_error` scoring, fallback always fails, temperature at the model default)

## Summary

This feature is a Python 3.11 library and CLI that turns a user's sentence, an injected clock
and timezone, and optional existing reminders into one schema-validated seven-key reminder
decision (`create`, `reschedule`, `snooze`, `clarify` or `refuse`). It also includes a layered,
deterministic evaluation harness that scores a frozen dataset of at least 18 cases and gives a
PASS/FAIL release verdict.

The approach (see [research.md](research.md)):

- **Model call**: one Claude Haiku 5.5 request per input, with structured outputs (`output_config.format` JSON Schema), thinking disabled, effort `low` and `max_tokens` 300.
- **Time handling**: the model interprets the language. Deterministic code supplies a calendar context and normalizes `due_at` offsets for DST with `zoneinfo`.
- **Guardrails**: cheap pre-model checks, delimited untrusted text, and post-model schema and invariant checks with a fixed fallback-clarify response.
- **Retries**: one retry, then `infra_error`.
- **Harness**: separate schema, invariant and semantic layers that record the failing layer and the violated FR ID per case, plus a live mode, a zero-cost replay mode, a USD 0.50 per-run abort and a Part-1A-style quality-gate script.

## Technical Context

**Language/Version**: Python 3.11 (3.11.9, `py -3.11`)

**Primary Dependencies**:

- Runtime: `anthropic` (official SDK), `jsonschema`, `python-dotenv`, `tzdata`
- Dev: `pytest`, `pytest-cov`, `ruff`, `bandit`
- Config uses stdlib `tomllib`

**Storage**: Files only.

- Read: JSON Schema contracts, `config/settings.toml`, `prompts/system_prompt.v1.txt`, `evals/dataset.json`
- Written: evidence JSON and Markdown under `evidence/`
- No database. The agent does not persist reminders.

**Testing**: pytest with a scripted `StubClient` and a `ReplayClient`. There are no live API calls in tests. ruff and bandit run through `.harness/run_harness.py`.

**Target Platform**: Windows 11 (developer machine) and any OS with Python 3.11. `tzdata` supplies the IANA database on Windows.

**Project Type**: A single project: a library plus a CLI, with a separate evaluation harness.

**Performance Goals**: One model call per request. At least 95% of non-infra requests return within 10 s (SC-006). The client timeout is 30 s, so the worst case is 2 attempts.

**Constraints**:

- Model settings: `max_tokens` ≤ 300 (enforced in config validation) and Haiku-class default model.
- Budget: ≤ USD 0.50 per run (abort) and < USD 5.00 project total.
- No system clock or timezone reads in agent or scoring code.
- No secrets in evidence.
- `temperature` is **left at the model default (not sent)**, because Claude Haiku 5.5 rejects `temperature = 0` and any other non-default sampling value (research R-02; spec Assumptions and Change Log v1.2). Every run report records it as `null` = "not sent (model default)". Reproducibility comes from replay of saved raw responses.

**Scale/Scope**: One user request per call, a dataset of 18 to 25 cases, about 1.3K tokens per call, and about $0.005 per evaluation run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | How the plan complies | Pre | Post |
|---|-----------|----------------------|-----|------|
| I | Spec First | Spec v1.1 and this plan exist. No code before `tasks.md` is approved. Every module traces to FRs (see Project Structure). | ✅ | ✅ |
| II | Structured, schema-validated output | API structured outputs, then full local `jsonschema` validation against `schemas/reminder_output.schema.json` (versioned `1.0.0`). Invalid output produces the fallback clarify (FR-030), never passed through. `error_response.schema.json` covers non-decisions. | ✅ | ✅ |
| III | Injected clock and timezone | `now` and `timezone` are required parameters. The only wall-clock read is the evidence run timestamp in `evaluate.py`. A gate check bans `datetime.now(`, `time.time(`, `date.today(` and `tzlocal` in `src/` and the layer modules (R-08). | ✅ | ✅ |
| IV | Safety, scope, clarification | Pre-model guardrails, delimited user text, refuse and clarify rules in the versioned prompt, and post-model invariants. Guardrail dataset category with at least 3 cases (out-of-scope, harmful, injection). Missing-task and missing-time categories. | ✅ | ✅ |
| V | Evaluation integrity | Dataset (≥18) and threshold (85% / 100% / ≤2, pass mark 0.9) are declared in the spec before any run. `dataset_sha256` and the threshold are recorded per run. The threshold values are constants in the report schema (`const`). Changes go through the spec's Evaluation Change Log. | ✅ | ✅ |
| VI | Layered harness, no LLM judge | Fallback check (FR-045) → `layer1_schema` → `layer2_invariants` → `layer3_semantic`, with short-circuiting. Scoring is pure functions with no model client in scope. | ✅ | ✅ |
| VII | infra_error separation | Typed error chain, one retry, then `infra_error` (category and attempts). Excluded from the denominator, capped at 2 and reported separately. `input_error` is distinct and counted as a failure (FR-044). | ✅ | ✅ |
| VIII | Quality gates | `.harness/run_harness.py` runs ruff (0 errors), bandit (0 MEDIUM/HIGH) and pytest (offline), plus the clock-ban and secret-scan checks. No project-wide suppressions. Inline `# noqa`/`# nosec` require a justification comment. | ✅ | ✅ |
| IX | Secrets hygiene | Key read only from env or `.env` (git-ignored at the repo root, verified). Never a CLI flag. Error messages are scrubbed. The gate scans `evidence/` for `sk-ant-`. Raw responses store only model output and usage, never request headers. | ✅ | ✅ |
| X | Cost control | Default `claude-haiku-5-5`, `max_tokens` 300. Pricing in `config/settings.toml`. Per-case token and cost accounting, with an abort before the next case once the total exceeds $0.50. Raw responses are saved and replay makes zero calls. Tests use stubs. | ✅ | ✅ |
| Tech | Model and temperature configurable and recorded | Model, `max_tokens`, `temperature`, effort and thinking come from config, env or a flag and are recorded per run. **Note**: `temperature` is left at the model default (`null`, not sent) instead of `0`, because the chosen model rejects `0`. This is recorded in spec Change Log v1.2 and Assumptions. It stays configurable, which is all the constitution requires. See Complexity Tracking. | ✅ | ✅ |

**Gate result**: PASS. No unjustified violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-nl-reminder-agent/
├── spec.md              # v1.2 (clarified 2026-11-07)
├── plan.md              # this file
├── research.md          # Phase 0: decisions R-01..R-15
├── data-model.md        # Phase 1: entities, lifecycle, verdict rules
├── quickstart.md        # Phase 1: run and validation guide
├── contracts/
│   ├── reminder_output.schema.json   # decision contract v1.0.0 (copied to schemas/)
│   ├── error_response.schema.json    # input_error / infra_error
│   ├── dataset.schema.json           # evals/dataset.json shape
│   ├── eval_results.schema.json      # run report shape
│   └── interfaces.md                 # library API, CLI, runner, gate script
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (`Part-1B/`)

```text
pyproject.toml                    # deps, ruff (py311, line 100), pytest (pythonpath src + .harness)
.env.example                      # ANTHROPIC_API_KEY= (placeholder only)
config/
└── settings.toml                 # model, max_tokens ≤300, temperature (unset), effort, thinking,
                                  # timeout, pricing per model, budget            (R-09; FR-040, FR-042)
prompts/
└── system_prompt.v1.txt          # versioned system prompt; version recorded in evidence (FR-014..FR-029)
schemas/
└── reminder_output.schema.json   # decision contract v1.0.0                      (FR-005..FR-007)
src/reminder_agent/
├── __init__.py                   # public API: run_agent, AgentOutcome, ReminderDecision, ErrorResult
├── __main__.py                   # python -m reminder_agent → cli.main
├── cli.py                        # argparse, stdout/stderr, exit codes 0/2/3/4     (FR-002, FR-031)
├── agent.py                      # run_agent orchestration (lifecycle in data-model)
├── config.py                     # settings.toml + env + flags; validates max_tokens ≤300 (R-09)
├── models.py                     # RequestContext, ExistingReminder, ReminderDecision, ErrorResult, AgentOutcome
├── inputs.py                     # input validation → input_error                  (FR-001, FR-003)
├── timeutil.py                   # calendar context, offset normalization, DST gap/fold, snooze due_at
│                                 #                                                 (FR-014..FR-018, FR-024)
├── prompt.py                     # builds system and user messages, delimits untrusted text (FR-029)
├── client.py                     # ModelClient protocol, AnthropicClient, retry-once, error mapping
│                                 #                                                 (R-06/R-07; FR-031)
├── parsing.py                    # JSON parse, full schema validation, API-schema derivation (R-03; FR-030)
└── guardrails.py                 # pre-model checks, invariant checks, fallback decision, refusal mapping
                                  #                                                 (FR-008..FR-013, FR-026..FR-030)
evals/
└── dataset.json                  # ≥18 frozen cases                                (FR-032, FR-033)
.harness/
├── README.md
├── evaluate.py                   # runner: check-dataset | live | replay; cost guard; evidence (FR-040..FR-042)
├── dataset.py                    # load, expand repeat-inputs, validate FR-034, sha256
├── layer1_schema.py              # schema and ISO-8601 checks → FR-005/FR-006 violations
├── layer2_invariants.py          # independent FR-008..FR-013 checks, one function each
├── layer3_semantic.py            # FR-036 scoring, whole-word keyword recall (R-12)
├── aggregate.py                  # fallback check, case status, totals, verdict    (FR-037..FR-039, FR-044, FR-045)
├── replay.py                     # ReplayClient over evidence/eval-runs/<id>/raw   (FR-041)
└── run_harness.py                # quality gates: ruff, bandit, pytest, clock-ban, secret-scan (R-13)
tests/
├── conftest.py                   # StubClient fixtures, frozen contexts
├── agent/                        # test_inputs, test_timeutil, test_prompt, test_parsing,
│                                 # test_guardrails, test_client_retry, test_agent_scenarios (AC-01..AC-31, AC-53..AC-57),
│                                 # test_cli (exit codes, parity AC-15), test_determinism (AC-14)
└── harness/                      # test_dataset (AC-32/33), test_layer1..3 (AC-34..AC-44, AC-58),
                                  # test_aggregate (AC-45..AC-48, AC-59, AC-60), test_runner_cost_abort (AC-51),
                                  # test_replay (AC-50/52), test_report_no_secrets (AC-49), test_run_harness
evidence/
├── initial-generation/           # snapshot of first generated code
├── final-generation/             # snapshot of final code
├── eval-runs/<run_id>/           # raw/*.json, eval-results.json, summary.md
├── harness-results/<stamp>/      # gate outputs
├── eval-results.json             # final run (copied by --final)
└── harness-log.md                # human-readable log of gate and eval runs
```

**Structure Decision**: This is the single-project layout from the plan input. Agent code lives in `src/reminder_agent/`. The harness lives in `.harness/` and is kept separate so it re-implements invariants independently instead of importing the agent's guards. It does import `reminder_agent.run_agent` to drive cases. `.harness` is not an importable package name, so it is put on `pythonpath` in `pyproject.toml` (as in Part 1A), and tests live under `tests/harness/`.

## Key Design Notes

1. **Request settings**: Claude Haiku 5.5 is called with `thinking={"type":"disabled"}`, `output_config={"effort":"low","format":{"type":"json_schema","schema":<derived>}}` and `max_tokens=300`. `temperature` is omitted unless configured (R-02, R-03). The SDK-feature check comes first in tasks (R-14), with a strict-tool fallback.
2. **Time normalization** (R-04): the model returns local wall time. Code re-attaches the correct offset, applies the FR-018 gap and fold rules, and computes the snooze `due_at`. This is unit-tested against AC-06 to AC-10 without the model.
3. **Fallback is the only path for bad output** (FR-030). Every fallback records a reason. A safety refusal from the API (`stop_reason="refusal"`) becomes a `refuse` decision.
4. **Retry** (R-06): SDK `max_retries=0`, one manual retry with an injectable sleeper, and a typed catch chain mapped to `infra_error` categories.
5. **Harness attribution** (R-11): every violation carries an FR ID, and `summary.md` is formatted for pasting into a coding-agent prompt.
6. **Fallback always fails** (R-15, FR-045, AC-60): `aggregate.py` checks the agent's `fallback` flag **before** the three layers. A flagged case gets status `fail` and `failed_layer: "fallback"`, whatever the expected intent, and layers 1 to 3 are not run for it. The fallback decision and `fallback_reason` are still saved for diagnosis, and `summary.md` lists fallback cases as `<case_id> fallback <reason>`. Replay reproduces the flag because it runs the same post-processing on the saved raw reply.

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|-----------|-----------|--------------------------------------|
| `temperature` left at the model default (`null`, not sent) instead of the requested `0` (spec Change Log v1.2) | Claude Haiku 5.5 returns HTTP 400 for non-default sampling parameters, and on API version `2026-10-21` for any value | Sending `0` would make every live call fail. Switching to an older Haiku (4.5) that accepts `temperature=0` would cost about 10× more per token and isn't needed: determinism for evaluation comes from saved raw responses and replay. |
| Harness re-implements invariants instead of importing the agent's | An evaluation must not share the code it checks | Importing would let one bug both produce and approve invalid output. |
