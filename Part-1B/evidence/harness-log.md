# Harness Log: Natural-Language Reminder Agent (Part 1B)

This is the human-readable log of approvals, quality-gate runs and evaluation runs. Entries are appended in order and never rewritten.

## Approval

- **Date**: 2026-11-07
- **Approver**: Anand Srivastava (project owner)
- **Commit approved**: `f93de80` ("1B: resolve analyze findings (C1, G1-G4, I1, D1, SC-006)")
- **Approved versions**:
  - `specs/001-nl-reminder-agent/spec.md` v1.3 (status set to Approved)
  - `specs/001-nl-reminder-agent/plan.md`
  - `specs/001-nl-reminder-agent/tasks.md` (T001 to T066)
  - `.specify/memory/constitution.md` v1.0.0
- **Decision recorded with the approval**: analysis finding U4 is resolved by keeping example output strings of 30 or more characters **out** of the system prompt, so the FR-046 leak check stays strict. No spec change was needed.
- **Constitution I committed the all changes and 

## Setup: SDK feature check (T006, offline, no API call)

- **Date**: 2026-11-07. Python 3.11.9 venv `.venv`, `anthropic` 2.6.0, `jsonschema` 4.26.0.
- **Result** (`inspect.signature(Anthropic(api_key="dummy").messages.create)`):
  - `output_config` and `thinking` are accepted. Structured outputs via `output_config.format` will be used, so the strict-tool fallback from research R-02 is **not** needed.
  - The `temperature` argument is **not** accepted by this SDK version, which matches API version `2026-10-21` rejecting sampling parameters. When the config leaves temperature unset (the default), nothing is sent. If a temperature is ever configured, the client passes it through `extra_body` so the API, not the SDK, accepts or rejects it.
- **Error classes**: `APITimeoutError`, `APIConnectionError`, `RateLimitError`, `InternalServerError`, `AuthenticationError`, `PermissionDeniedError`, `BadRequestError`, `NotFoundError` and `APIStatusError` all exist. `APITimeoutError` is a subclass of `APIConnectionError`, so the catch chain checks the timeout first (research R-06).
- **Pricing**: $0.10 / $0.50 per MTok for `claude-haiku-5-5`, from the claude-api reference cached on 2026-10-06. It was not re-checked against the live pricing page, because no network fetch was made. Re-check before the first live run.

## Quality gate runs

- Gate run 20261107T210751Z: **PASS** (ruff PASS, bandit PASS, pytest PASS, clock_ban PASS, secret_scan PASS, python PASS); python 3.11.9; evidence `evidence/harness-results/20261107T210751Z`

## Reproducibility record (T061)

### Initial generation

- **Date**: 2026-11-08, taken **before any live evaluation run** (T062).
- **Contents**: copies of `src/`, `.harness/`, `prompts/`, `schemas/`, `config/` and `evals/` in `evidence/initial-generation/`. There are 26 files; caches and `.env` are excluded.
- **Commit**: taken from the working tree on top of `f93de80`. The implementation was not yet committed when the snapshot was made; the snapshot itself is the record of the initial generation.
- **State at snapshot**: all user stories (US1 to US4) implemented, 233 offline tests passing, prompt version `v1`, schema version `1.0.0`.

### Live evaluation runs (manual)

The owner fills this in after each manual `python .harness/evaluate.py live` run. Every run's full evidence is in `evidence/eval-runs/<run_id>/`.

| run_id | date | model | verdict | pass rate | infra_error | fallbacks | cost (USD) |
|--------|------|-------|---------|-----------|-------------|-----------|------------|
| | | | | | | | |

### Final generation

Manual step: after the final live run, copy `src/`, `.harness/`, `prompts/`, `schemas/`, `config/` and `evals/` to `evidence/final-generation/`. Then record the date, the commit and the run_id here.

### Spend tracker

Project cap: USD 5.00. The cap is enforced automatically before every live run (FR-047, which sums `cost.estimated_usd` of every live report); this table is the human-readable copy.

| run_id | estimated cost (USD) | running total (USD) |
|--------|----------------------|---------------------|
| (no live runs yet) | 0.00 | 0.00 |
- Gate run 20261108T094402Z (--final): **PASS** (ruff PASS, bandit PASS, pytest PASS, clock_ban PASS, secret_scan PASS, python PASS); python 3.11.9; evidence `evidence/harness-results/20261108T094402Z`

## Polish: offline validation (T063 to T066, 2026-11-08)

- **T063, lint and security**:
  - `ruff check .` reports 0 errors.
  - bandit reports 0 MEDIUM/HIGH and 338 LOW findings: 332 B101 (`assert` in tests) and 6 B105 false positives on the threshold key name `min_pass_rate`.
  - There are 4 inline `# nosec` (B404/B603 for fixed-argument `subprocess` calls), each with a justification comment on the line above. There is no project-wide suppression.
- **T064, frozen dataset**: `python .harness/evaluate.py check-dataset` exits 0 and reports 26 cases with all category and tag minimums met.
  - **Frozen dataset sha256: `e7512a65595ced4ba6ef3be4b09b112fefaff8ae4c385f967ab6bed38613c4ef`**. Every evaluation report must show this hash unless a change is recorded in the spec's Evaluation Change Log (FR-043).
- **T065, quickstart §2 (offline only; §3 and §4 are live and were skipped)**:
  - pytest: 233 passed, with 0 failures, errors or skips.
  - Gate script: PASS.
  - check-dataset: exit 0.
  - `reminder-agent --text "hi" ... --timezone Mars/Olympus` printed `{"status": "input_error", "category": "invalid_timezone", ...}` with exit 3 (AC-16).
  - `reminder-agent --text "" ...` printed a clarify decision with exit 0. The empty-text check returns before any model client is built, so no model call is made; the unit test with `NoCallClient` covers this (AC-22).
- **T066, final gates** (`run_harness.py --final`, Python 3.11.9): **PASS**. ruff, bandit, pytest (233 tests), clock-ban, secret-scan and python all pass, and coverage is 92.48% (informational). Evidence: `evidence/harness-results/20261108T094402Z/`.
- **No live evaluation has been run.** The first live run is a manual step for the owner. Before it, re-check the `claude-haiku-5-5` prices in `config/settings.toml` against the live pricing page.
- Gate run 20261108T114434Z: **PASS** (ruff PASS, bandit PASS, pytest PASS, clock_ban PASS, secret_scan PASS, python PASS); python 3.11.9; evidence `evidence/harness-results/20261108T114434Z`

## Evaluation runs (final)

- Eval replay run `20261108T115616Z-live-replay`: **PASS**, pass rate 26/26 (100.0%), guardrails 4/4, infra_error 0, fallbacks 0, cost $0.006443, evidence `evidence/eval-runs/20261108T115616Z-live-replay`
