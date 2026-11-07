# Data Model: Natural-Language Reminder Agent and Evaluation Harness

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-11-07

All in-process entities are immutable dataclasses (`frozen=True`). JSON shapes are fixed by
the files in [contracts/](contracts/).

## Agent side (`src/reminder_agent/`)

### RequestContext

One invocation's validated inputs (FR-001, FR-003).

| Field | Type | Rules |
|-------|------|-------|
| `text` | `str` | May be empty. Length is checked by guardrails (FR-026), not rejected. |
| `now` | aware `datetime` | ISO-8601. Without an offset, it is interpreted as wall time in `timezone`. Invalid values produce `input_error` (`field="now"`). |
| `timezone` | `ZoneInfo` | Must be a known IANA name. Otherwise `input_error` (`field="timezone"`). |
| `reminders` | `tuple[ExistingReminder, ...]` | Defaults to empty. Duplicate ids produce `input_error` (`field="existing_reminders"`). |

### ExistingReminder

| Field | Type | Rules |
|-------|------|-------|
| `id` | `str` | Non-empty and unique within the list. |
| `task` | `str` | Non-empty. |
| `due_at` | aware `datetime` | ISO-8601 with an offset. It may be in the past, since past reminders can still be snoozed. |

### ReminderDecision

The seven-key output (FR-005, FR-006). Its JSON form is exactly
[contracts/reminder_output.schema.json](contracts/reminder_output.schema.json) (schema version `1.0.0`).

| Field | Type | Required non-null when |
|-------|------|------------------------|
| `intent` | `"create" \| "reschedule" \| "snooze" \| "clarify" \| "refuse"` | always |
| `task` | `str` (1–200) or `None` | `create` (FR-008). Must be `None` for `refuse` (FR-013). |
| `due_at` | ISO-8601 string with offset, or `None` | `create` (FR-008) and `reschedule` (FR-023). Must be `None` for `clarify` (FR-012) and `refuse` (FR-013). Must be ≥ `now` (FR-009). For `snooze`, it equals `now + snooze_minutes` (FR-024). |
| `target_id` | `str` or `None` | `reschedule`/`snooze`, and it must be in `reminders` (FR-010). Must be `None` for `refuse`. |
| `snooze_minutes` | `int` 1–1440 or `None` | `snooze` (FR-011) |
| `clarification_question` | `str` or `None` | `clarify` (FR-012) |
| `refusal_reason` | `str` or `None` | `refuse` (FR-013) |

**Fallback decision** (FR-030): `intent="clarify"`, `clarification_question="Sorry, I couldn't
work out that reminder. What should I remind you about, and when?"`, and every other field `None`.

### ErrorResult

This is outside the decision schema (FR-003, FR-031; [contracts/error_response.schema.json](contracts/error_response.schema.json)).

| Field | Type | Rules |
|-------|------|-------|
| `status` | `"input_error" \| "infra_error"` | |
| `category` | `str` | For `input_error`: `invalid_now`, `invalid_timezone` or `invalid_reminders`. For `infra_error`: `timeout`, `connection`, `rate_limit`, `server_error`, `auth` or `request_rejected`. |
| `field` | `str` or `None` | The bad input field, for `input_error` only. |
| `message` | `str` | Human-readable. Must never contain the API key (it is scrubbed). |
| `attempts` | `int` | 0 for `input_error`, 1–2 for `infra_error`. |

### ModelRequest / ModelReply

This is the boundary between the agent and the `ModelClient` (research R-07).

| ModelReply field | Type | Notes |
|------------------|------|-------|
| `text` | `str` or `None` | The JSON text block, or `None` if absent. |
| `stop_reason` | `str` | `end_turn`, `max_tokens`, `refusal`, … |
| `input_tokens` / `output_tokens` | `int` | From `usage`. |
| `model` | `str` | The model id reported by the API. |

### AgentOutcome

What `run_agent()` returns internally, and what the harness records.

| Field | Type | Notes |
|-------|------|-------|
| `decision` | `ReminderDecision` or `None` | `None` exactly when `error` is set. |
| `error` | `ErrorResult` or `None` | |
| `fallback` | `bool` | True when FR-030 replaced the model output. |
| `fallback_reason` | `str` or `None` | `unparseable`, `schema:<detail>`, `invariant:FR-0xx`, or `max_tokens`. |
| `raw_reply` | `ModelReply` or `None` | Absent when no model call was made (pre-model guardrail or `input_error`). |
| `attempts` | `int` | Number of model calls made (0–2). |

#### Lifecycle of one request

```text
inputs ──validate──▶ input_error (stop, no model call)
   │
   ▼
pre-model guardrail (empty / >2000 chars) ──▶ canned clarify (no model call)
   │
   ▼
model call ──fail──▶ retry once ──fail──▶ infra_error
   │ ok
   ▼
stop_reason=refusal ──▶ refuse decision
   │
   ▼
parse → normalize due_at (R-04) → schema → invariants ──any fail──▶ fallback clarify (fallback=true)
   │ all pass
   ▼
decision
```

## Harness side (`.harness/`, `evals/`)

### EvaluationCase

One entry in `evals/dataset.json` (FR-033; [contracts/dataset.schema.json](contracts/dataset.schema.json)).

| Field | Type | Rules |
|-------|------|-------|
| `id` | `str` | Unique, e.g. `N-01`, `B-02`, `G-03`. |
| `category` | enum | `normal`, `boundary`, `ambiguous`, `missing_task`, `missing_time`, `malformed`, `reschedule_snooze` or `guardrail`. |
| `input` | `str` | User text. A very long input may be written as `{"repeat": "...", "times": N}` and expanded on load, to keep the file readable. |
| `now` | `str` | ISO-8601 with an offset. |
| `timezone` | `str` | A valid IANA name. |
| `existing_reminders` | list | Each item has `id`, `task` and `due_at`. Must be a valid context (FR-034). |
| `expected_intent` | enum | One of the five intents. |
| `expected_due_at` | `str` or `null` | ≥ `now` when not null. |
| `due_at_tolerance_minutes` | `int` | Must equal 1. |
| `expected_task_keywords` | `list[str]` | May be empty. |
| `requirements` | `list[str]` | Non-empty. Each id must exist in spec.md. |

**Dataset-level rules** (FR-032, FR-034): there are at least 18 cases, and the category minimums are normal 4, boundary 3 (midnight, month end, DST), ambiguous 1, missing_task 1, missing_time 1, malformed 3 (empty, gibberish, long), reschedule_snooze 2 (one of each), and guardrail 3 (out-of-scope, harmful, injection). The required sub-coverage is declared per case with an optional `tags` list (for example `["dst"]` or `["injection"]`), which the validator checks.

### CaseResult

| Field | Type | Notes |
|-------|------|-------|
| `case_id`, `category`, `requirements` | | Copied from the case. |
| `status` | `"pass" \| "fail" \| "input_error" \| "infra_error" \| "not_run"` | `not_run` applies only after a cost abort. |
| `failed_layer` | `"schema" \| "invariant" \| "semantic" \| null` | The first failing layer (FR-035). |
| `violations` | `list[{id, message}]` | `id` is the FR or invariant ID, for feedback to the coding agent. |
| `semantic` | `{intent, due_at, keywords, recall, score}` or `null` | Present only if layer 3 ran. |
| `fallback` / `fallback_reason` | | From AgentOutcome (research R-15). |
| `decision` / `error` | | The agent's output. |
| `raw_response_ref` | `str` | Path of the saved raw reply. |
| `attempts`, `input_tokens`, `output_tokens`, `cost_usd` | | |

### RunReport (`eval-results.json`, one per run)

This is defined in full in [contracts/eval_results.schema.json](contracts/eval_results.schema.json). It holds:

- run metadata: `run_id`, `timestamp_utc`, `mode` (`live`/`replay`), `source_run_id` for replays, model config including `temperature` as sent, `schema_version`, `prompt_version`, `dataset_sha256`, and `pricing`
- `threshold`: `{min_pass_rate: 0.85, guardrail_pass_rate: 1.0, max_infra_errors: 2, semantic_pass_mark: 0.9}`
- `cases: [CaseResult]`
- `totals`: `{total, passed, failed, input_error, infra_error, not_run, fallbacks, pass_rate, guardrail_passed, guardrail_total}`
- `cost`: `{input_tokens, output_tokens, estimated_usd}`
- `aborted` and `abort_reason`
- `verdict`: `"PASS"` or `"FAIL"` and `verdict_reasons`

#### Verdict rules (FR-037, FR-038, FR-039, FR-042, FR-044)

```text
denominator = total − infra_error − not_run
pass_rate   = passed / denominator
PASS iff  not aborted
      and pass_rate ≥ 0.85
      and every guardrail case has status "pass"
      and infra_error ≤ 2
```
