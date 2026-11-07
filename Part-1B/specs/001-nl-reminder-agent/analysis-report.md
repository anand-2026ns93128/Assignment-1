# Specification Analysis Report

**Feature**: `specs/001-nl-reminder-agent` | **Date**: 2026-11-07 | **Command**: `/speckit-analyze` (read-only)

**Artifacts analysed**: `spec.md` (v1.2), `plan.md`, `tasks.md` (T001 to T062), `research.md`, `data-model.md`, `contracts/`, `.specify/memory/constitution.md` (v1.0.0)

There are no critical issues. One HIGH issue should be fixed before implementation: a contradiction about over-long task text (C1). All 45 functional requirements have at least one task. Four success criteria aren't fully built: SC-006 (no task), and SC-002, SC-003 and SC-005 (partly). No files were modified by the analysis.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Inconsistency | HIGH | spec.md:52 (AC-13), spec.md:223 (FR-022); tasks.md:226 (T022) | The spec says a task phrase over 200 characters is shortened to 200. T022 instead expects a 201-character task from the model to become the fallback, so `task` is null and AC-13 fails. In evaluation, every such case would also fail under FR-045. | Add a deterministic shortening step in `agent.py` before validation (cut at the last word boundary at or below 200 characters). Change T022 to expect a 1–200-character task containing the key words, and add the step to T030. |
| G1 | Coverage gap | MEDIUM | spec.md:387 (SC-006) | No task measures response time. The run report has no per-case latency, so the "95% within 10 s" target can't be checked. | Add `latency_ms` per case and a p95 figure to `eval_results.schema.json`, T042 and T049. |
| G2 | Coverage gap | MEDIUM | spec.md:85 (AC-27), spec.md:384 (SC-003) | "No field reveals the agent's instructions" is only tested against a stubbed reply (T033). The harness can't detect a leak in a real response: G-03 passes on intent `refuse` even if `refusal_reason` quotes the system prompt. | Add a deterministic property check to `layer2_invariants.py`: no string field contains a sentinel line from `system_prompt.v1.txt`. Tag it FR-029 and add it to T039/T045. |
| G3 | Coverage gap / constitution | MEDIUM | spec.md:386 (SC-005); tasks.md:48, 432; constitution X | The USD 5.00 project cap is in config, but only a manual spend tracker (T057) covers it. Nothing adds up spend across runs. This doesn't strictly violate the constitution, which requires per-run tracking and the $0.50 abort, but "total spend MUST stay under $5.00" isn't enforced. | Have `evaluate.py live` total `estimated_usd` over `evidence/eval-runs/*/eval-results.json` and refuse to start if the total plus the pre-flight estimate would exceed `project_cap_usd`. Add this to T042/T049. |
| G4 | Coverage gap | MEDIUM | spec.md:217 (FR-016, "tonight after 20:00 → clarify"); FR-021 (conflicting times) | These two edge cases are only described in the prompt. No unit test or dataset case covers them. | Add stub-based tests to T033. Optionally add dataset cases, but before the first run (FR-043). |
| I1 | Inconsistency | MEDIUM | tasks.md:180, 272, 395 | The per-story "Independent Test" commands use `pytest -k "us1"` etc., but only T016 requires the `test_us1_*` naming. Other test files (e.g. `test_timeutil.py`, `test_agent_safety.py`) wouldn't be selected. | Require the `test_us<N>_` prefix in every story test task, or replace `-k` with explicit file lists. |
| D1 | Constitution (process) | MEDIUM | constitution I; tasks.md Phase 1 | Principle I requires spec, plan and tasks to be approved before any code, but no step records that approval. | Add a T000 (or a note before T001): "Owner approval of spec v1.2, plan and tasks recorded in `evidence/harness-log.md` with date and commit." |
| U1 | Underspecification | LOW | research R-06; spec FR-031 | 400 and 404 responses (`request_rejected`) are counted as `infra_error`, which leaves them out of the pass rate. A case-specific 400 could hide an application defect (up to the 2-error limit). | Accept, but list `request_rejected` cases by name in `summary.md`, or count them as failures. |
| U2 | Underspecification | LOW | spec.md:155 (AC-56) | AC-56 bundles two outcomes ("if only one matches…"), so it isn't strictly yes/no. | Split it into AC-56a (clarify naming both) and AC-56b (unique match is targeted). |
| U3 | Underspecification | LOW | FR-026 ("gibberish"), FR-025 ("match equally") | Both judgements are left to the model with no deterministic definition. | Acceptable, because dataset X-02 and AC-56 anchor them. Optionally add one example each to the prompt. |
| I2 | Inconsistency | LOW | plan.md tests tree vs tasks.md | The plan names `test_guardrails.py` and `test_client_retry.py`. The tasks use different files: `test_invariants_fallback.py`, `test_client_request.py`, `test_agent_create.py`, `test_agent_safety.py` and `test_runner.py`. | Update the plan's tree to the names in tasks.md. |
| I3 | Inconsistency | LOW | spec.md:7; plan header | Spec status is still "Draft" at v1.2, and the plan says `001-nl-reminder-agent` while work is on `main`. | Set the status to "Approved" once D1 is done, and create the branch or note `main`. |
| A1 | Ambiguity | LOW | T023 (AC-14) | Changing the `TZ` environment variable on Windows only partly changes the local timezone, so the determinism test can pass without proving anything. The clock-ban gate (T007) is the real protection. | Keep both, and note in T023 that the clock-ban gate is the main check. |
| A2 | Ambiguity | LOW | FR-042 vs constitution X | The cost check runs between cases, so the in-flight case can push spend slightly over $0.50. This is consistent with "once exceeds", but SC-005 says "stays at or below". | Accept: the overshoot is under $0.001 per case. Optionally reword SC-005 to "abort once exceeded". |
| L1 | Duplication | LOW | spec FR-039 and the "Release Threshold" section | The threshold is stated twice. This is intentional, but the two copies could drift. | Keep FR-039 as the authoritative copy and have the section refer to it. |

## Coverage

| Requirement | Tasks | Notes |
|-------------|-------|-------|
| FR-001, FR-003 | T009, T013, T016, T025 | |
| FR-002 | T001, T023, T031 | |
| FR-004 | T007, T015, T023, T030, T062 | See A1 |
| FR-005 to FR-007 | T004, T009, T018, T027, T038, T044 | |
| FR-008 to FR-013 | T019, T029, T039, T045 | |
| FR-014 to FR-018 | T017, T020, T026, T028 | FR-016 "passed today" rule untested (G4) |
| FR-019 to FR-021 | T033, T036 | FR-021 conflicting times untested (G4) |
| FR-022 | T022, T028 | **Conflict (C1)** |
| FR-023 to FR-025 | T017, T026, T051 to T054 | |
| FR-026 to FR-029 | T032, T033, T035, T036, T052 | No harness check for leaked instructions (G2) |
| FR-030 | T019, T030 | |
| FR-031 | T005, T034, T037 | See U1 |
| FR-032 to FR-034 | T008, T011, T012, T060 | |
| FR-035 to FR-039, FR-044, FR-045 | T038 to T041, T043 to T047, T050 | |
| FR-040 to FR-042 | T042, T043, T048, T049 | |
| FR-043 | T011, T058, T060 | |
| SC-002 | T019, T030 | Fully covered except two gaps: the task-shortening conflict (C1) and no harness check for leaked instructions (G2) |
| SC-003 | T033, T041 | Partly covered (G2) |
| SC-004 | T043 | |
| SC-005 | T042, T049 | Per-run abort only; project cap not enforced (G3) |
| SC-006 | none | **Gap (G1)** |
| SC-007 | T006, T007, T042, T062 | |

SC-001 (a PASS verdict) depends on the manual live run, so it is out of scope for the task list.

## Constitution Alignment

There are no MUST violations. D1 (approval not recorded, Principle I) and G3 (spend cap not enforced, Principle X) are process gaps, rated MEDIUM. The temperature deviation is recorded and still complies, because temperature stays configurable and recorded (spec Change Log v1.2, plan Complexity Tracking).

## Unmapped Tasks

None. All 62 tasks name FR or AC IDs.

## Metrics

- 45 functional requirements, plus 6 success criteria that need buildable work (SC-002 to SC-007)
- 62 tasks
- Coverage: 100% of requirements; success criteria 3 of 6 fully, 2 partly, 1 none (SC-006)
- Findings: 15 (1 HIGH, 6 MEDIUM, 8 LOW, 0 critical), including 2 ambiguity and 1 duplication findings

## Next Actions

- **Fix C1 before `/speckit-implement`**, because otherwise tests T022 and T030 build the wrong behaviour. It is a tasks-and-plan edit only; the spec is already correct.
- G1 to G4 add small amounts of work to T039, T042, T045 and T049, plus tests in T033. Fold them in now, before the harness is built and before the first live run.
- D1 is a one-line addition to the task list. The LOW items are optional tidy-ups.
- Offered remediation: concrete edits for the top 7 issues (C1, G1 to G4, I1, D1). None has been applied yet; each needs the owner's approval.

## Remediation Applied (2026-11-07, before any evaluation run)

Applied with the owner's approval. Spec v1.3 change-log entry added.

| Finding | Resolution |
|---------|------------|
| C1 | Deterministic `shorten_task` (at most 200 characters, cut at a word boundary) runs before schema validation. T019 and T023 now expect a shortened task, not a fallback, and T028/T031 implement it. The spec was already correct (FR-022). |
| G1 / SC-006 | New FR-040 report content and AC-61: per-case `latency_ms` and an informational `latency` summary (p95, share within 10 s, `sc006_met`), outside the verdict. New test task T045, implementation in T051 and T053, and a schema update. |
| G2 | New FR-046 and AC-62: an instruction-leak property in the invariant layer (canary token or a 30+-character prompt line), using a canary added to the prompt (T029). Covered by T040 and T048. |
| G3 | New FR-047 and AC-63: a project-cap check before every live run (recorded live spend plus a worst-case pre-flight estimate must stay at or below USD 5.00). New test task T046, new module `.harness/budget.py` (T050), and wiring in T053. |
| G4 | Stub tests for "tonight" after 20:00 and for conflicting times were added to T034, with the prompt rules in T037. Dataset cases A-03 and A-04 were added to T012 (26 cases), before any run. |
| I1 | The naming rule `test_us<N>_*` is required in every story test subsection, and T059 enforces it. |
| D1 | New T001 records owner approval and sets the spec status to Approved before any code. |

Tasks were renumbered: 62 became 66. The task IDs quoted in the findings table above use the old numbering.
