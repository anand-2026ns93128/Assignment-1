<!--
Sync Impact Report
- Version change: (unfilled template) → 1.0.0
- Modified principles: all template placeholders replaced (initial ratification)
- Added principles:
  I. Spec First (NON-NEGOTIABLE)
  II. Structured, Schema-Validated Output
  III. Deterministic Testability (Injected Clock and Timezone)
  IV. Safety, Scope, and Clarification
  V. Evaluation Integrity (NON-NEGOTIABLE)
  VI. Layered Evaluation Harness (No LLM Judge)
  VII. Failure Separation (infra_error)
  VIII. Quality Gates
  IX. Secrets Hygiene
  X. Cost Control
- Added sections: Technology & Model Constraints; Development Workflow & Evidence
- Removed sections: none
- Templates: dependent templates read this file at runtime; not modified by this command
- Deferred TODOs: none
-->

# Natural-Language Reminder Agent Constitution

## Core Principles

### I. Spec First (NON-NEGOTIABLE)

No application code, prompt, or evaluation code is written until the feature's `spec.md`,
`plan.md`, and `tasks.md` exist and have been approved. Every implemented behavior MUST trace to
a requirement in the spec and a task in `tasks.md`. Changes in behavior MUST be made in the spec
first, then propagated to plan, tasks, and code.

**Rationale**: Traceability makes the agent auditable and keeps evaluation expectations anchored
to a reviewed specification rather than to whatever the code happens to do.

### II. Structured, Schema-Validated Output

- Every model response MUST be parsed into a JSON object and validated against a declared,
  versioned schema before any downstream use.
- Output that fails parsing or validation MUST NOT be presented to the user as a reminder; it is
  surfaced as an explicit error or clarification result instead.
- The schema MUST cover every response kind the agent can return (e.g. reminder, clarification
  request, refusal) so that no response bypasses validation.

**Rationale**: A reminder with a hallucinated or malformed time is worse than no reminder;
schema validation is the first line of defense.

### III. Deterministic Testability (Injected Clock and Timezone)

The current date/time and the user's timezone are explicit inputs to the agent. Code MUST NOT
read the system clock or local timezone implicitly (no bare `datetime.now()`, `time.time()`, or
`tzlocal`) in agent or scoring logic. Relative expressions ("tomorrow", "in 2 hours", "next
Monday") MUST be resolved against the injected reference time.

**Rationale**: Evaluations are only reproducible if the same input yields the same expected
result on any machine, on any day.

### IV. Safety, Scope, and Clarification

- The agent MUST refuse requests outside reminder management, returning a structured refusal.
- Instructions embedded in user-supplied text (prompt injection) MUST be treated as data, never
  as commands; they MUST NOT alter the agent's role, schema, or guardrails.
- When the task or the time is missing or ambiguous, the agent MUST return a structured
  clarification request instead of guessing.
- Guardrails MUST be covered by evaluation cases (out-of-scope, injection, missing task, missing
  time).

**Rationale**: A reminder agent that guesses or obeys injected text silently produces wrong or
unsafe actions.

### V. Evaluation Integrity (NON-NEGOTIABLE)

- An evaluation dataset of at least 15 cases and a numeric pass threshold MUST be declared and
  committed before the final evaluation run.
- Cases MUST NOT be deleted, expected results MUST NOT be changed without a recorded spec change,
  the threshold MUST NOT be lowered, and guardrails MUST NOT be disabled or weakened to make an
  evaluation pass.
- Any change to the dataset or threshold MUST be recorded with its rationale in the spec and
  evidence.

**Rationale**: An evaluation that can be edited until it passes measures nothing.

### VI. Layered Evaluation Harness (No LLM Judge)

The harness evaluates every response in this order:

1. **Schema validation** — the response parses and conforms to the declared schema.
2. **Deterministic invariant/property checks** — e.g. resolved times are timezone-aware, not in
   the past relative to the injected clock, refusals carry no reminder payload.
3. **Semantic/quality scoring** — deterministic comparison against ground truth (task text,
   resolved datetime, response kind).

A later layer runs only if the earlier layer passed. An LLM judge MUST NOT be used at any layer.

**Rationale**: Deterministic layered checks are cheap, reproducible, and make failures easy to
localize.

### VII. Failure Separation (infra_error)

API and model-transport errors (timeouts, rate limits, connection errors, 5xx responses) MUST be
recorded with status `infra_error`, distinct from application failures (schema, invariant, or
semantic failures). `infra_error` cases MUST be reported separately and MUST NOT be silently
counted as passes; how they affect the pass rate MUST be declared alongside the threshold.

**Rationale**: Mixing infrastructure noise with application defects hides real regressions and
inflates or deflates quality metrics.

### VIII. Quality Gates

Before any task is marked complete and before final evaluation:

- `ruff check` reports 0 errors.
- `bandit` reports 0 medium- or high-severity findings.
- All deterministic unit tests pass, without network or API access.

Gates MUST NOT be bypassed by suppressing rules project-wide; any inline suppression MUST carry
a justification comment.

**Rationale**: Gates are only meaningful if they are enforced uniformly and cannot be quietly
switched off.

### IX. Secrets Hygiene

The Anthropic API key MUST be read only from the environment or a git-ignored `.env` file. It
MUST NEVER appear in source code, tests, logs, saved model responses, evaluation reports, or any
evidence artifact. `.env` MUST remain listed in `.gitignore`.

**Rationale**: Evidence and logs are committed and shared; a leaked key is an immediate security
and cost incident.

### X. Cost Control

- Total API spend for the whole project MUST stay under **USD 5.00**.
- The default model MUST be a small Haiku-class model with `max_tokens <= 300`.
- The evaluation runner MUST track input/output token usage and estimated cost per run, and MUST
  abort a run once its estimated cost exceeds **USD 0.50**.
- Every evaluation run MUST save raw model responses, and the runner MUST support a replay mode
  that re-scores saved responses without making API calls.
- Development and unit tests MUST use stubbed or replayed responses, not live API calls.

**Rationale**: A hard budget, per-run abort, and replay make iteration on scoring logic free and
keep total spend predictable.

## Technology & Model Constraints

- Language/runtime: Python 3.11.
- Model access: the official Anthropic Python SDK (`anthropic`).
- Model name and temperature MUST be configurable (config file, environment, or CLI flag); the
  defaults actually used MUST be recorded in the evidence for each evaluation run.
- `max_tokens` MUST NOT exceed 300 in any configuration.
- Pricing constants used for cost estimation MUST be declared in one place and recorded in
  evidence alongside token totals.

## Development Workflow & Evidence

- Workflow: `/speckit-specify` → `/speckit-clarify` (as needed) → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`. No implementation before tasks
  are approved (Principle I).
- Each evaluation run MUST produce an evidence record containing: timestamp, model name,
  temperature, max_tokens, dataset version, threshold, per-case status (pass / fail layer /
  infra_error), raw responses, token usage, and estimated cost — and no secrets.
- Final evaluation results MUST be reproducible from saved raw responses via replay mode.
- Quality gate outputs (ruff, bandit, unit tests) MUST be captured in evidence for the final
  submission.

## Governance

This constitution supersedes other project practices. Every spec, plan, task list, and review
MUST check compliance with these principles; `/speckit-analyze` findings that conflict with the
constitution are treated as critical.

- **Amendments**: proposed as an edit to this file with a written rationale, reviewed by the
  project owner, and recorded with a version bump and updated Last Amended date.
- **Versioning**: semantic versioning — MAJOR for removing or redefining a principle, MINOR for
  adding a principle or materially expanding guidance, PATCH for clarifications and wording.
- **Compliance review**: before final evaluation, the owner verifies Principles V, IX, and X
  explicitly (dataset/threshold unchanged or change recorded, no secrets in evidence, spend under
  budget).

**Version**: 1.0.0 | **Ratified**: 2026-11-07 | **Last Amended**: 2026-11-07
