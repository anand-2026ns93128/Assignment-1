# AI Augmented SDLC – Assignment 1: Spec-Driven Development & Harness Engineering

This repository has two parts. Each part was built with GitHub Spec Kit (constitution → specify → clarify → plan → tasks → analyze → implement) and is checked by its own harness.

| Part | System | Behaviour | Harness |
|------|--------|-----------|---------|
| **Part-1A** | Smart Todo CLI | Deterministic | Quality gates: ruff, bandit, pytest, coverage ≥ 90% |
| **Part-1B** | Natural-Language Reminder Agent (`claude-haiku-5-5`) | Non-deterministic (LLM) | Quality gates plus a 3-layer evaluation (schema, invariants, semantic score) over a frozen 26-case dataset, with live and replay modes |

- **Part-1A**: a single-user command-line todo manager. Its commands are `add`, `list` (with filtering), `update`, `status` and `delete`. Tasks are saved to a local JSON file (`todo.json` by default, or set with `--file`).
- **Part-1B**: a Python library and CLI. It turns one natural-language sentence into one schema-validated reminder decision (`create`, `reschedule`, `snooze`, `clarify` or `refuse`). The current time and timezone are always explicit inputs. See [Part-1B/README.md](Part-1B/README.md).

## Repository layout

```
Assignment-1/
├── Part-1A/                              Smart Todo CLI (deterministic)
│   ├── .specify/                         Spec Kit config, templates, scripts
│   │   └── memory/constitution.md        Constitution
│   ├── .claude/skills/speckit-*/         Spec Kit commands for Claude Code
│   ├── specs/001-smart-todo-cli/         spec.md, plan.md, tasks.md, research.md, data-model.md,
│   │                                     quickstart.md, analysis-report.md, contracts/, checklists/
│   ├── src/smart_todo/                   Implementation
│   ├── tests/                            unit/ and acceptance/ tests
│   ├── .harness/                         run_harness.py, README.md, tests/ (harness self-tests)
│   ├── evidence/
│   │   ├── initial-generation/           First generated code
│   │   ├── final-generation/             Final code
│   │   ├── harness-results/<UTC stamp>/  Output of every harness run
│   │   └── harness-log.md                Harness log
│   ├── todo, todo.cmd                    Launchers
│   └── pyproject.toml
├── Part-1B/                              Natural-Language Reminder Agent (non-deterministic)
│   ├── .specify/, .claude/skills/        Spec Kit (constitution in .specify/memory/constitution.md)
│   ├── specs/001-nl-reminder-agent/      spec.md, plan.md, tasks.md, research.md, data-model.md,
│   │                                     quickstart.md, analysis-report.md, contracts/, checklists/
│   ├── src/reminder_agent/               Implementation
│   ├── prompts/system_prompt.v1.txt      System prompt
│   ├── schemas/                          Output JSON schema
│   ├── config/settings.toml              Model, token, cost settings
│   ├── tests/                            agent/ and harness/ tests
│   ├── .harness/                         run_harness.py (gates), evaluate.py (live/replay),
│   │                                     layer1_schema.py, layer2_invariants.py, layer3_semantic.py, ...
│   ├── evals/dataset.json                Frozen evaluation dataset (26 cases)
│   ├── evidence/
│   │   ├── initial-generation/           Snapshot taken before any live run
│   │   ├── final-generation/             Final code
│   │   ├── harness-results/<UTC stamp>/  Gate harness runs
│   │   ├── eval-runs/<run-id>/           Live and replay evaluation runs
│   │   ├── eval-results.json             Final evaluation result
│   │   └── harness-log.md                Harness log
│   ├── .env.example                      Template for the API key file
│   └── pyproject.toml
└── README.md
```

## Prerequisites

- Windows with **Python 3.11**, invoked as `py -3.11`. The `--final` harness runs fail on any other version.
- **GitHub Spec Kit** (`specify` CLI; the projects were initialised with 1.3.2.dev0, Claude integration, PowerShell scripts). It is only needed to re-run the Spec Kit workflow, not to build or test the code:
  ```powershell
  uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
  ```
- **Anthropic API key**, used by Part-1B live evaluation only. Copy `Part-1B\.env.example` to `Part-1B\.env` and set `ANTHROPIC_API_KEY=...`. The `.env` file is git-ignored and must never be committed. Tests, the gate harness, dataset check and replay need no key.

## Part-1A: Smart Todo CLI

All commands run from `Part-1A\`.

```powershell
cd Part-1A
py -3.11 -m pip install pytest pytest-cov ruff bandit

# Use the CLI (todo.cmd puts src\ on PYTHONPATH; no install needed)
.\todo.cmd --help

# Run the harness (ruff, bandit, pytest, coverage)
py -3.11 .harness\run_harness.py
py -3.11 .harness\run_harness.py --final     # final report; requires Python 3.11
```

Each run writes `evidence\harness-results\<UTC stamp>\` (`summary.json`, tool outputs, `junit.xml`, `coverage.json`). Exit codes: 0 = all PASS, 1 = a gate failed, 2 = harness error.

## Part-1B: Natural-Language Reminder Agent

All commands run from `Part-1B\`. The package **must** be installed into Python 3.11 in editable mode (`py -3.11 -m pip install -e .`); the `[dev]` extra adds pytest, ruff and bandit for the harness.

```powershell
cd Part-1B
py -3.11 -m pip install -e ".[dev]"
copy .env.example .env                       # then edit .env: ANTHROPIC_API_KEY=...

# Gate harness (ruff, bandit, pytest, clock-ban, secret-scan); offline
py -3.11 .harness\run_harness.py
py -3.11 .harness\run_harness.py --final     # final report; requires Python 3.11

# Validate the frozen dataset; offline
py -3.11 .harness\evaluate.py check-dataset

# Live evaluation (calls the model, costs money; needs .env)
py -3.11 .harness\evaluate.py live
py -3.11 .harness\evaluate.py live --final   # also writes evidence\eval-results.json and a log entry

# Replay a saved run (zero API calls). --run takes the run FOLDER path, not just the id
py -3.11 .harness\evaluate.py replay --run evidence\eval-runs\<run-id>
py -3.11 .harness\evaluate.py replay --run evidence\eval-runs\20261108T115616Z-live
```

Live runs write `evidence\eval-runs\<stamp>-live\` and replays write `evidence\eval-runs\<run-id>-replay\`. Each contains `raw\` (live only), `cases.json`, `eval-results.json` and `summary.md`. Evaluation exit codes: 0 = verdict PASS, 1 = verdict FAIL, 2 = harness/dataset error or cost cap refusal.

Release verdict (frozen in `spec.md` before any run): ≥ 85% of non-`infra_error` cases pass, 100% of guardrail cases pass, ≤ 2 `infra_error`. Cost controls: per-run abort at USD 0.50, project cap USD 5.00. See [Part-1B/.harness/README.md](Part-1B/.harness/README.md).

## Final results

| Part | Final run | Result | Location |
|------|-----------|--------|----------|
| Part-1A | Harness run `20261107T171956Z` (`--final`, Python 3.11.9) | PASS: ruff, bandit (0 MEDIUM/HIGH), pytest 198 tests, coverage 98.78% | `Part-1A\evidence\harness-results\20261107T171956Z\summary.json` |
| Part-1B | Replay `20261108T115616Z-live-replay` of live run `20261108T115616Z-live` | PASS: 26/26 (100%), guardrails 4/4, infra_error 0, fallbacks 0 | `Part-1B\evidence\eval-runs\20261108T115616Z-live-replay\summary.md`, `Part-1B\evidence\eval-results.json` |
| Part-1B | Gate harness run `20261108T114434Z` | PASS: ruff, bandit, pytest, clock-ban, secret-scan, python | `Part-1B\evidence\harness-results\20261108T114434Z\` |

Harness logs:

- [Part-1A/evidence/harness-log.md](Part-1A/evidence/harness-log.md)
- [Part-1B/evidence/harness-log.md](Part-1B/evidence/harness-log.md)
