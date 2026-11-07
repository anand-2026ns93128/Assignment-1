# Phase 0 Research: Natural-Language Reminder Agent and Evaluation Harness

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-11-07

Each entry gives the decision, the rationale and the alternatives considered. Facts about the
Claude API come from the bundled `claude-api` skill reference (model table cached 2026-10-06).
Re-check them against the live docs when the SDK is installed (see R-14).

---

## R-01 Language, runtime and dependencies

- **Decision**: Use Python 3.11 (3.11.9 is installed on this machine via `py -3.11`).
  - Runtime dependencies: `anthropic` (official SDK), `jsonschema`, `python-dotenv`, `tzdata`.
  - Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `bandit`.
  - Config is read with the standard-library `tomllib`. No other runtime dependencies.
- **Rationale**: The constitution's Technology section requires Python 3.11 and the official SDK. Windows has no system IANA database, so `zoneinfo` needs `tzdata`. `tomllib` ships with 3.11, so the config needs no extra package.
- **Alternatives**: `pydantic` for models and validation was rejected. The contract is a JSON Schema file that the harness must validate independently, so `jsonschema` plus stdlib dataclasses keeps one source of truth with fewer dependencies. `pendulum` and `dateutil` for time handling were rejected because `zoneinfo` covers DST gaps and folds.

## R-02 Model call shape for Claude Haiku 5.5 (important deviation from the plan input)

- **Decision**: Each request is sent as follows:
  - `model="claude-haiku-5-5"`
  - `max_tokens=300`
  - `thinking={"type": "disabled"}`
  - `output_config={"effort": "low", "format": {"type": "json_schema", "schema": <API schema>}}`
  - **no `temperature` parameter**

  The `temperature` config key defaults to `null`, which means not sent, so the model default applies. Evidence records it as `temperature: null (not sent; model default)`. The owner confirmed this, and it is recorded in spec Assumptions and Change Log v1.2.
- **Rationale**:
  - **Temperature**: Claude Haiku 5.5 rejects non-default sampling parameters with HTTP 400. On API version `2023-06-01`, only `temperature=1` is accepted. On `2026-10-21`, any `temperature` is rejected. The requested `temperature 0` cannot be sent. The constitution only requires temperature to be configurable and recorded, and that still holds: a non-null value is passed through, and the API decides whether to accept it. Reproducibility comes from replay mode (Constitution X), not from sampling settings.
  - **Thinking**: Haiku 5.5 thinks by default, and thinking tokens count toward `max_tokens`. With the constitutional cap of 300, thinking could use up the budget before any JSON is produced. Disabled thinking is accepted at effort `low`/`medium`/`high`.
  - **Structured outputs**: `output_config.format` with `json_schema` guarantees a text block containing schema-shaped JSON, which matches the plan input's "tool use / structured output". A tool is not needed because nothing executes. Structured outputs are the documented replacement for forced tool calls.
- **Alternatives**:
  - A forced strict tool (`tool_choice: {"type":"tool"}`, `strict: true`) works on Haiku 5.5. It adds a tool-call wrapper with no benefit. It is kept as a fallback if `output_config.format` turns out to be unavailable in the installed SDK (see R-14).
  - Prompt-only JSON was rejected because it gives no guarantee of shape.

## R-03 API schema compared with the contract schema

- **Decision**: `schemas/reminder_output.schema.json` (contract, [contracts/reminder_output.schema.json](contracts/reminder_output.schema.json)) is the single source of truth.
  - At runtime, the agent derives the **API schema** from it by removing the keywords `minLength`, `maxLength`, `minimum`, `maximum`, `pattern` and `format`, and keeping `type`, `enum`, `required`, `properties` and `additionalProperties: false`.
  - After the call, the full contract is enforced locally with `jsonschema`. The harness enforces it again independently as layer 1.
- **Rationale**: Structured-output features support only a subset of JSON Schema. Sending only the safe subset avoids a 400 on an unsupported keyword, and local validation still catches lengths, ranges and the offset format.
- **Alternatives**: Sending the full schema risks rejection. Keeping two hand-written schemas risks drift.

## R-04 Who resolves dates: model + deterministic normalization

- **Decision**: The model interprets the language and returns `due_at` as **local wall time** in the user's timezone. Deterministic code then does two things:
  1. **Prompt calendar context**: the user message includes:
     - `now` (local and UTC)
     - the weekday
     - the dates of today, tomorrow and the next 7 days with weekday names
     - the current UTC offset
     - a note when a DST transition falls within the next 8 days

     This information is computed with `zoneinfo` from the injected clock.
  2. **Post-normalization** (`timeutil.normalize_due_at`):
     - Take the model's local date and time, discard its offset, and re-attach the correct offset for the user's timezone at that instant.
     - Apply the gap rule (shift forward by the gap length) and the fold rule (`fold=0`, the first occurrence) from FR-018.
     - For `snooze`, override `due_at` with `now + snooze_minutes` (FR-024).
- **Rationale**: Small models are reliable at language and weekday mapping when given a calendar, and unreliable at offset arithmetic across DST changes. Code is exact. This puts each job where it is reliable and makes AC-08, AC-09 and AC-10 deterministic.
- **Alternatives**:
  - **Model returns the final instant unchanged**: rejected because of offset errors around DST.
  - **Model returns a structured time expression (e.g. `{"weekday":"monday","hour":10}`) that code resolves completely**: rejected because it changes the external output contract, needs a second schema, and moves a large grammar into code.

## R-05 Deterministic guardrails before and after the model

- **Decision**:
  - **Pre-model (no API call)**: empty or whitespace-only text, and text over 2,000 characters, return a canned `clarify` (FR-026). Input validation errors return `input_error` (FR-003).
  - **Prompt-level**:
    - The user text goes inside `<user_request>…</user_request>` delimiters, with a system-prompt rule that its content is data and never instructions (FR-029).
    - Existing reminders go in a separate delimited block.
    - Out-of-scope, harmful and unsupported operations produce `refuse` (FR-027, FR-028).
  - **Post-model**: parse → full schema validation → invariant check (FR-008 to FR-013, including `target_id` existence and `due_at >= now` after normalization). Any failure produces the fixed fallback clarify plus a `fallback` record (FR-030).
  - **Safety refusals**: `stop_reason == "refusal"` maps to a schema-valid `refuse` decision with reason "Request declined by safety policy." Haiku 5.5 has no server-side fallback.
  - **Truncation**: `stop_reason == "max_tokens"` is invalid output and produces the fallback.
- **Rationale**: Cheap, deterministic checks handle the cases that need no language understanding. Regex blocking of "ignore previous instructions" was rejected because it would break AC-28, where a valid reminder carries an injection.
- **Alternatives**: A second "moderation" model call was rejected on cost and constitution grounds (Principle VI does not apply to the agent, but cost does).

## R-06 Retry policy and error classification

- **Decision**: The SDK client is built with `max_retries=0`, and the agent implements **exactly one retry** itself, with a 1-second delay injected through a sleeper so tests don't wait.
  - **Retried once, then `infra_error`**: `APITimeoutError` and `APIConnectionError` (category `connection`/`timeout`), `RateLimitError` (`rate_limit`), and `InternalServerError` including 529 (`server_error`).
  - **Not retried, immediately `infra_error`**: `AuthenticationError`/`PermissionDeniedError` (`auth`), `BadRequestError`/`NotFoundError`/other `APIStatusError` (`request_rejected`).
  - The number of attempts is recorded per case.
- **Rationale**: The plan input says "retry at most once". Owning the retry makes it unit-testable with a stub that fails once and then succeeds, and visible in evidence. The SDK's built-in retry would double-retry and hide attempts. The catch chain goes from most specific to least specific, as the SDK guidance recommends.
- **Alternatives**: SDK `max_retries=1` is equivalent at runtime but can't be tested without network access.

## R-07 Model client abstraction (testability)

- **Decision**: A `ModelClient` protocol with one method, `complete(request) -> ModelReply`, has three implementations:
  - `AnthropicClient` (live)
  - `StubClient` (tests: scripted replies or exceptions)
  - `ReplayClient` (reads saved raw responses keyed by case id)

  `ModelReply` carries raw text, `stop_reason`, usage (input/output tokens) and the model id actually reported.
- **Rationale**: This keeps unit tests offline (Constitution VIII and X) and makes replay go through **the same** post-processing as live runs, so replayed verdicts match (FR-041, AC-50).

## R-08 Injected clock everywhere

- **Decision**:
  - The agent and scoring receive `now` as an argument.
  - The only wall-clock read in the codebase is `.harness/evaluate.py`'s run timestamp for evidence folder names, isolated in one function marked as evidence metadata only.
  - A ruff/grep check in the gate script forbids `datetime.now(`, `time.time(`, `date.today(` and `tzlocal` in `src/reminder_agent/` and the layer modules.
- **Rationale**: Constitution III, AC-14.

## R-09 Configuration and pricing

- **Decision**: `config/settings.toml` holds:
  - `[model]`: `name="claude-haiku-5-5"`, `max_tokens=300` (validated ≤300), `temperature` (absent means null), `effort="low"`, `thinking="disabled"`, `timeout_seconds=30`.
  - `[pricing."claude-haiku-5-5"]`: `input_per_mtok=0.10`, `output_per_mtok=0.50`, `long_context_threshold_tokens=100000`, `long_input_per_mtok=0.50`, `long_output_per_mtok=2.50`.
  - `[budget]`: `run_abort_usd=0.50`, `project_cap_usd=5.00`.

  Environment variables (`REMINDER_MODEL`, `REMINDER_MAX_TOKENS`, `REMINDER_TEMPERATURE`) and CLI flags override in the order CLI > env > file. The resolved values are written into every run's evidence.
- **Rationale**: Constitution Technology section ("pricing constants in one place", "configurable model/temperature", `max_tokens ≤ 300`).
- **Estimate**: about 1,200 input and 120 output tokens per case gives about $0.00018 per case, or about $0.004 per 20-case run. That is far below the $0.50 abort, so the abort is a safety net, not a constraint.

## R-10 Cost guard mechanics

- **Decision**:
  - After each live case, `estimated_cost += in_tokens*rate_in + out_tokens*rate_out`, using the long-context rates if the prompt exceeded 100K tokens.
  - **Before starting the next case**, if `estimated_cost > run_abort_usd`, stop. The run is marked `aborted`, unrun cases are listed, and the verdict is FAIL (FR-042, AC-51).
  - Retries count toward cost when the failed attempt reported usage.
- **Alternatives**: A pre-flight worst-case estimate (`cases × (prompt + 300) tokens`) is also printed before a live run, for information only.

## R-11 Harness layering and failure attribution

- **Decision**: These are separate modules under `.harness/`:
  - `layer1_schema.py`: JSON Schema validation plus ISO-8601 parse of `due_at`. It returns a list of violations, each tagged `FR-005`/`FR-006`.
  - `layer2_invariants.py`: an independent re-implementation of FR-008 to FR-013, one function per invariant, each returning its FR ID.
  - `layer3_semantic.py`: the FR-036 formula with whole-word keyword matching (R-12).
  - `aggregate.py`: the fallback check (FR-045, run first) and the FR-037/038/039/044 verdict.

  Each `CaseResult` records `failed_layer` (`fallback`/`schema`/`invariant`/`semantic`/null), `violations: [{"id":"FR-009","message":"due_at 2026-11-10T09:00+05:30 < now 2026-11-10T10:00+05:30"}]`, the semantic components and the `requirements` covered. These records are written for feedback to the coding agent.
- **Rationale**: The plan input explicitly asks for this. Constitution VI requires layered checks with no LLM judge. The harness re-implements invariants instead of importing the agent's, so a bug in the agent's guard can't hide itself.

## R-12 Keyword recall matching rule

- **Decision**: Lower-case both strings, then match each expected keyword as a whole word or phrase (`\b<keyword>\b`, keyword regex-escaped) against the output task. Recall is matched / expected. An empty expected list gives 1.0, and a null task gives 0 (FR-036).
- **Rationale**: Substring matching would count "call" inside "recall". No stemming keeps the rule deterministic and simple, and dataset authors list the exact surface form.
- **Alternatives**: Substring matching (false positives) and stemming or lemmatization (adds a dependency and is less predictable) were rejected.

## R-13 Quality-gate script

- **Decision**: `.harness/run_harness.py` is modelled on Part 1A and uses the standard library only. It runs:
  - `ruff check .`
  - `bandit -r src tests .harness -f json` (fails on MEDIUM/HIGH or bandit errors)
  - `pytest` (more than 0 tests, 0 failures, errors and skips)
  - the clock-ban grep (R-08)
  - a secret scan of `evidence/` for the `sk-ant-` prefix (Constitution IX, AC-49)

  Coverage is collected with `pytest-cov` and reported as information only, not gated, because the 1B constitution's gates are ruff, bandit and pytest. Output goes to `evidence/harness-results/<UTC stamp>/` and an appended entry in `evidence/harness-log.md`. `--final` additionally requires Python 3.11.
- **Rationale**: Constitution VIII and the plan input ("like Part 1A").

## R-14 Items to verify when the SDK is installed (first implementation task)

- `output_config={"format": {...}, "effort": "low"}` and `thinking={"type":"disabled"}` are accepted by the installed `anthropic` version with `claude-haiku-5-5`. If `format` is missing, use the strict-tool fallback from R-02.
- The live pricing page still shows $0.10 / $0.50 per MTok for Claude Haiku 5.5, and `config/settings.toml` is updated if it differs.
- The installed SDK's error class names match R-06.

## R-15 Scoring of fallback decisions (resolved by the owner, 2026-11-07)

- **Decision**: A fallback clarify decision **always counts as a failed case**, whatever the expected intent. It is recorded as `status: "fail"`, `failed_layer: "fallback"`, `fallback: true` and the `fallback_reason` (spec FR-045, AC-60, Change Log v1.2).
  - The check runs in `aggregate.py` before layers 1 to 3, which are skipped for that case.
  - The case stays in the pass-rate denominator. On a guardrail case, it fails the 100% guardrail condition.
- **Rationale**: A fallback means the model output was invalid. Letting it pass `clarify`-expected cases (ambiguous, missing-field and malformed) would reward broken output and inflate the pass rate (Constitution V).
- **Alternatives**:
  - Scoring the fallback like any other decision was rejected because it inflates the pass rate.
  - Scoring normally with a separate fallback-count limit was rejected as more complex, and it still lets individual broken cases pass.
