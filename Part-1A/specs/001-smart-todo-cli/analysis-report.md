# Specification Analysis Report: Smart Todo CLI

**Command**: `/speckit-analyze` (read-only) | **Date**: 2026-11-07

**Artifacts analysed**:
- [spec.md](./spec.md), [plan.md](./plan.md), [tasks.md](./tasks.md)
- [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/),
  [quickstart.md](./quickstart.md)
- `.specify/memory/constitution.md` v1.0.0

**Extension hooks**: `.specify/extensions.yml` does not exist, so no hooks were run.

> **Resolution (2026-11-07)**: All 10 CRITICAL, HIGH and MEDIUM findings (C1–C3, I1–I3, U1, U2,
> F1, G1) have been fixed in the spec, plan, research, contracts, quickstart and tasks. The 7 LOW
> findings are still open. Task IDs in this report are the **pre-fix** numbers (T001–T060); fixing
> the findings added four tasks, so `tasks.md` now runs T001–T064.

There are 3 critical problems, all from the constitution, and they must be fixed before
`/speckit-implement`. Coverage is otherwise complete: every FR and every acceptance criterion
maps to at least one task.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution | **CRITICAL** | tasks.md T015, T019, T027, T035, T042, T047; "Gate discipline"; Notes ("Commit after each task") vs constitution workflow steps 5–6 | The constitution says every commit must leave all gates passing, and a task can't be marked complete until all gates pass. The tasks break both rules: the "confirm red" tasks end with a commit containing failing tests, T015 allows coverage under 90%, and the plan only promises passing gates at the "final" commit. | Treat each story as one unit: run the red tests locally (optionally keep that harness run as evidence), but only mark tasks complete and commit once that story's harness run passes all four gates. Remove "note the failure count in the commit message" and "no final commit is made until". |
| C2 | Constitution | **CRITICAL** | plan.md *Project Structure*, quickstart.md vs tasks.md T004–T007, T060 | Constitution I: no code or test code without an approved spec, plan **and** task. The harness files (`.harness/run_harness.py`, `.harness/tests/`, `evidence/harness-results/`) appear only in tasks.md, not in the plan. | Add `.harness/` and `evidence/` to the plan's source tree, add a harness section to research/quickstart, and make quickstart's gate commands point to `run_harness.py`. |
| C3 | Constitution | **CRITICAL** | spec.md:7 `**Status**: Draft`; plan.md has no status | Constitution I requires an *approved* spec and plan before any code is written. Neither is marked approved. | After review, set the spec's status to `Approved (2026-11-07)` and add a status/approval line to the plan header. |
| I1 | Inconsistency | HIGH | spec.md *Exit Codes*, *Error Messages*, FR-015, FR-017 vs research R3, contracts/cli.md, tasks T009, T024 (`test_AC21_keyboard_interrupt…`) | The plan adds exit code 130 and the message `Error: interrupted.`, which the spec doesn't have. FR-017 says every failure must use "the exact message and exit code defined above", and those tables list only 0–3. FR-015 also says an interrupted save reports with exit 3, but the plan says 130. Tests built from the plan would contradict the spec. | Add 130 and `Error: interrupted.` to the spec's tables and say in FR-015 that a Ctrl+C during a save exits 130 (with a dated change note, per Constitution VIII). Or drop 130 and send interrupts to exit 1 with the internal-error message. |
| I2 | Inconsistency | MEDIUM | spec SC-002 ("with no configuration"), spec Assumptions (`todo`) vs research R8, quickstart.md | The spec says a new user can use `todo` with no configuration. The plan has no `todo` command: users have to set `PYTHONPATH` and define a shell function, which is configuration. | Add stdlib-only launcher files at the repo root (`todo` for POSIX and `todo.cmd` for Windows, each running `python -m smart_todo` with `src` on the path), with a task. Or reword SC-002. |
| I3 | Inconsistency | MEDIUM | quickstart.md and plan.md Constitution Check (`bandit -r src tests`) vs T005 (`bandit -r src tests .harness`) | The bandit command differs between files. | Use one command everywhere, `src tests .harness`, to match the constitution's "full codebase". |
| U1 | Underspecification | MEDIUM | T004, T006 (`.harness/tests` sits outside `testpaths`) vs Constitution II ("pytest passes 100% of tests") | The harness self-tests live in the repo but no gate runs them, so they could break without anyone noticing. | Have `run_harness.py` also run `pytest .harness/tests` as part of the pytest gate (or a fifth gate) and record it in `summary.json`. |
| U2 | Underspecification | MEDIUM | Constitution Technology Constraints (Python 3.11) vs research R10, T005 (warning only), T060 ("if available") | Gates can be reported as PASS on 3.13 even though the constitution names 3.11 as the runtime. | Make running on a Python other than 3.11 fail the final run (T060), or require 3.11 to be installed before T060. Keep the warning for runs during development. |
| F1 | Inconsistency | MEDIUM | tasks.md *User story dependencies* (US4 depends on US3, US5 depends on US1+US3) vs spec ("each story independently testable") | `parse_task_id` and `validate_status` are introduced in US3, so US4 and US5 can't be built without it. | Move `parse_task_id`, `validate_status` and `find_task` (with their unit tests) into Phase 2. |
| G1 | Coverage | MEDIUM | FR-018 | No task mentions FR-018 by ID. It is still tested, because every error-case test checks the file bytes are unchanged, but you can't trace it from the task list. | Add `FR-018` to the Covers line of T016, T024, T033, T040 and T046. |
| U3 | Underspecification | LOW | T012 ("**Any** exception → corrupt") vs T028 (only `TodoError/ValueError/TypeError/KeyError`) | The strict loader catches fewer error types. Deeply nested JSON (`RecursionError`) or a non-dict task (`AttributeError`) would end as exit 1 "internal error" instead of exit 3 "corrupt". | In T028, catch `Exception` (excluding `KeyboardInterrupt`) during load and report it as corrupt. |
| I4 | Inconsistency | LOW | spec.md:3 (branch `main`) vs plan.md header (`001-smart-todo-cli`) | The two files name the branch differently. | Use one wording in both. |
| I5 | Inconsistency | LOW | checklists/requirements.md Notes ("FR-001 to FR-018") | The checklist is out of date after the clarifications (FR-019, AC-55 to AC-58). | Update the note. |
| D1 | Duplication | LOW | FR-016 / SC-006 / AC-23; FR-017 / SC-005 | The same requirement is stated twice in each pair. It does no harm because they cite each other. | No action needed. |
| A1 | Ambiguity | LOW | SC-003 ("typical laptop"); T057 times in-process, without Python start-up | Neither "typical laptop" nor what counts toward the 1-second limit is defined. | Define it as "in-process command time on the dev machine". |
| A2 | Ambiguity | LOW | SC-002 ("new user … under 1 minute") | This can't be tested automatically. | Accept it as a qualitative goal, or turn it into a check in quickstart T059. |
| U4 | Underspecification | LOW | T001 Covers "all FR"; T002 maps stdlib-only to FR-016 | The Covers references for these setup tasks are weak. | Cite the constitution sections, or SC-001, explicitly. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 | ✅ | T011, T016, T018, T021, T022 | |
| FR-002 | ✅ | T016, T017, T020 | |
| FR-003 | ✅ | T011, T017, T020 | |
| FR-004 | ✅ | T017, T020 | |
| FR-005 | ✅ | T018, T021, T022, T048, T057 | |
| FR-006 | ✅ | T046, T048, T049 | |
| FR-007 | ✅ | T018, T021, T025, T028, T041, T043 | |
| FR-008 | ✅ | T041, T043, T044 | |
| FR-009 | ✅ | T041, T043, T044 | |
| FR-010 | ✅ | T034, T036, T037, T038 | |
| FR-011 | ✅ | T034, T036, T037, T038, T044 | |
| FR-012 | ✅ | T008, T012, T013, T031 | |
| FR-013 | ✅ | T009, T012, T022, T031 | |
| FR-014 | ✅ | T025, T028, T029 | |
| FR-015 | ✅ | T025, T030 | Exit-code conflict, see I1 |
| FR-016 | ✅ | T012, T025, T026, T031, T058 | |
| FR-017 | ✅ | T009, T010, T013, T052, T054, T056 | |
| FR-018 | ⚠️ implicit | T016, T024, T033, T040, T046 (via ACs) | Not cited by ID, see G1 |
| FR-019 | ✅ | T013, T022, T038, T043, T044, T049, T056 | |
| SC-001 | ✅ | T004–T007, T060 | |
| SC-003 | ✅ | T057 | |
| SC-004 | ✅ | T024, T025, T060 | |
| SC-005 / SC-006 | ✅ | T051–T052, T026, T060 | |
| AC-01 to AC-58 | ✅ 58/58 | T016, T024, T026, T033, T040, T046, T051, T052 | Every AC has a named `test_ACNN_` |

## Constitution Problems

- **C1**: Principle II and workflow steps 5–6 (every commit leaves all gates passing; a task is
  complete only when the gates pass).
- **C2**: Principle I (the harness code is not traced in plan.md).
- **C3**: Principle I (the spec and plan are not marked approved).

## Unmapped Tasks

None. Every task T001–T060 has a Covers line.

## Metrics

- Requirements: 19 FRs + 5 buildable success criteria = 24. Acceptance criteria: 58.
- Tasks: 60.
- Coverage: 100% of requirements have at least one task (FR-018 only through its ACs).
- Ambiguity: 2 · Duplication: 1 · Critical: 3 · High: 1 · Medium: 6 · Low: 7.

## Next Actions

- **Before `/speckit-implement`:** fix C1–C3 and I1.
  - C1 and C2: edit tasks.md (the commit and completion rules) and plan.md/quickstart.md (add
    the harness).
  - C3: mark the spec and plan approved once they have been reviewed.
  - I1: update the spec's exit-code and message tables with a dated change note, then match the
    plan.
- **Medium items (recommended):** add the `todo` launcher files (I2), make the bandit command
  consistent (I3), have the harness run its own self-tests (U1), and move the shared validators
  into Phase 2 (F1).
- **Low items:** can be fixed at any time.
