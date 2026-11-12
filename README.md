# AI Augmented SDLC – Assignment 1: Spec-Driven Development & Harness Engineering

This repository has two parts. Both were built with GitHub Spec Kit (constitution → specify → clarify → plan → tasks → analyze → implement), and each is checked by its own harness.

| Part | System | Behaviour | Harness |
|------|--------|-----------|---------|
| **Part-1A** | Smart Todo CLI | Deterministic | Quality gates: ruff, bandit, pytest, coverage ≥ 90% |
| **Part-1B** | Natural-Language Reminder Agent (`claude-haiku-5-5`) | Non-deterministic (LLM) | Quality gates, plus a 3-layer evaluation (schema, invariants, semantic score) over a frozen 26-case dataset, in live and replay modes |

- **Part-1A** is a single-user command-line todo manager with the commands `add`, `list` (with filters), `update`, `status` and `delete`. Tasks are stored in a local JSON file (`todo.json` by default, or the path given with `--file`).
- **Part-1B** is a Python library and CLI. It turns one natural-language sentence into one schema-validated reminder decision: `create`, `reschedule`, `snooze`, `clarify` or `refuse`. The current time and timezone are always passed in explicitly. See [Part-1B/README.md](Part-1B/README.md).

## Repository layout

Both parts use the same structure:

```
Part-1A/ | Part-1B/
├── .specify/            Spec Kit config, templates, scripts; constitution in memory/constitution.md
├── .claude/skills/      Spec Kit commands for Claude Code
├── specs/001-*/         spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md,
│                        analysis-report.md, contracts/, checklists/
├── src/                 Implementation (smart_todo / reminder_agent)
├── tests/               Test suite
├── .harness/            Harness scripts and README.md
├── evidence/
│   ├── initial-generation/, final-generation/   Code snapshots
│   ├── harness-results/<UTC stamp>/             Output of each gate harness run
│   ├── eval-runs/<run-id>/                      Part-1B only: live and replay evaluation runs
│   ├── eval-results.json                        Part-1B only: final evaluation result
│   └── harness-log.md                           Harness log
└── pyproject.toml
```

Part-1A also has the `todo` / `todo.cmd` launchers. Part-1B also has `evals/dataset.json` (the frozen evaluation dataset), `prompts/`, `schemas/`, `config/settings.toml` and `.env.example`.

## Prerequisites

- Windows, with **Python 3.11** run as `py -3.11`. The `--final` harness runs fail on any other Python version.
- **Anthropic API key**, needed only for Part-1B live evaluation. Create `Part-1B\.env` from `Part-1B\.env.example` and set `ANTHROPIC_API_KEY=...`. `.env` is git-ignored and must never be committed. The tests, gate harness, dataset check and replay do not need a key.

## Part-1A: Smart Todo CLI

Run from `Part-1A\`:

```powershell
cd Part-1A
py -3.11 -m pip install pytest pytest-cov ruff bandit

.\todo.cmd --help                            # run the CLI (no install needed)

py -3.11 .harness/run_harness.py --final     # ruff, bandit, pytest, coverage; requires Python 3.11
```

Each run writes `evidence\harness-results\<UTC stamp>\`, which contains `summary.json` and each tool's output. Exit codes: 0 = all gates PASS, 1 = a gate failed, 2 = harness error.

## Part-1B: Natural-Language Reminder Agent

Run from `Part-1B\`:

```powershell
cd Part-1B
py -3.11 -m pip install -e .                 # the package (editable install is required)
py -3.11 -m pip install -e ".[dev]"          # adds pytest, pytest-cov, ruff, bandit for the harness
copy .env.example .env                       # then set ANTHROPIC_API_KEY=... in .env

# Gate harness: ruff, bandit, pytest, clock-ban, secret-scan (offline)
py -3.11 .harness/run_harness.py --final

# Check the frozen dataset (offline)
py -3.11 .harness/evaluate.py check-dataset

# Live evaluation: one model call per case, about USD 0.006 per run; needs .env
py -3.11 .harness/evaluate.py live

# Replay a saved run with zero API calls. --run takes the run FOLDER path, not only the id
py -3.11 .harness/evaluate.py replay --run evidence\eval-runs\<run-id>
```

A live run writes `evidence\eval-runs\<stamp>-live\` and a replay writes `evidence\eval-runs\<run-id>-replay\`. Each run folder contains `eval-results.json` and `summary.md`. Exit codes: 0 = verdict PASS, 1 = verdict FAIL, 2 = harness or dataset error, or a refusal by the cost cap.

The release verdict needs ≥ 85% of non-`infra_error` cases to pass, 100% of guardrail cases to pass, and ≤ 2 `infra_error` cases. A run aborts at USD 0.50 and the whole project is capped at USD 5.00. See [Part-1B/.harness/README.md](Part-1B/.harness/README.md).

## Final results

| Part | Final run | Result | Location |
|------|-----------|--------|----------|
| Part-1A | Harness run `20261107T171956Z` (`--final`, Python 3.11.9) | PASS: ruff, bandit (0 MEDIUM/HIGH), pytest 198 tests, coverage 98.78% | `Part-1A\evidence\harness-results\20261107T171956Z\summary.json` |
| Part-1B | Replay `20261108T115616Z-live-replay` of live run `20261108T115616Z-live` | PASS: 26/26 (100%), guardrails 4/4, infra_error 0, fallbacks 0 | `Part-1B\evidence\eval-runs\20261108T115616Z-live-replay\summary.md`, `Part-1B\evidence\eval-results.json` |

Harness logs:

- [Part-1A/evidence/harness-log.md](Part-1A/evidence/harness-log.md)
- [Part-1B/evidence/harness-log.md](Part-1B/evidence/harness-log.md)
