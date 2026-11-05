# Smart Todo CLI Constitution

## Core Principles

### I. Spec-First Development (NON-NEGOTIABLE)

- No production code or test code MAY be written unless it traces to an approved feature
  specification (`spec.md`), an approved implementation plan (`plan.md`), and a specific task
  in `tasks.md`.
- Every code change MUST reference the task ID it implements.
- Work that is not covered by a task MUST first be added to the spec artifacts (see
  Principle VIII) before it is implemented.

**Rationale**: The spec artifacts are the single source of truth; code without a traceable
requirement cannot be verified against acceptance criteria.

### II. Automated Quality Gates (NON-NEGOTIABLE)

A change is complete only when all of the following pass on the full codebase:

- `ruff check` reports **0** errors.
- `bandit -r` reports **0** issues of MEDIUM or HIGH severity.
- `pytest` passes **100%** of tests (no failures, no errors).
- `pytest-cov` reports **≥ 90%** line coverage of the application package.

**Rationale**: Objective, tool-enforced thresholds remove ambiguity about "done" and catch
regressions in style, security, and behaviour before they land.

### III. Test Integrity (NON-NEGOTIABLE)

- Every acceptance criterion in a spec MUST be covered by at least one test whose name
  includes the criterion ID, in the form `test_AC<NN>_<description>` (e.g.
  `test_AC01_add_task_with_title`).
- No agent or contributor MAY delete, skip (`skip`, `skipif`, `xfail`), or weaken an existing
  test, lower the coverage threshold, add coverage exclusions, or disable/suppress lint or
  security rules (`# noqa`, `# nosec`, config ignores) in order to make a gate pass.
- When a gate fails, the fix MUST be made in the application code, or the requirement MUST be
  changed through Principle VIII; the test or rule is never the thing that gives way.

**Rationale**: Gates are only meaningful if the tests behind them cannot be quietly eroded;
ID-named tests make acceptance-criterion coverage auditable by inspection.

### IV. Deterministic Behaviour

- Given the same command-line input and the same data file contents, the program MUST
  produce byte-identical output and the same resulting data file.
- The program MUST NOT use randomness (`random`, `uuid4`, `secrets`, etc.) and MUST NOT make
  any network access.
- Any ordering of output MUST be explicitly defined (e.g. sorted by a stated key) rather than
  relying on incidental ordering.
- Where the current date/time affects behaviour, it MUST be injectable (e.g. a parameter or
  environment override) so tests are reproducible.

**Rationale**: Determinism makes behaviour testable, debuggable, and verifiable against the spec.

### V. Safe Persistence

- Task data MUST be stored in a single JSON file.
- Every write MUST be atomic: serialise to a temporary file in the same directory, flush and
  close it, then replace the target with `os.replace`.
- If the data file is missing, the program MUST treat it as an empty task list. If it is
  unreadable, not valid JSON, or does not match the expected schema, the program MUST stop
  with a clear error message and a non-zero exit code, and MUST NOT overwrite, truncate, or
  otherwise modify the existing file.

**Rationale**: A todo list is the user's data; an interrupted write or a malformed file must
never result in silent data loss.

### VI. Graceful Error Handling

- Invalid input (unknown command, bad arguments, missing or invalid IDs, invalid values)
  MUST produce a clear, human-readable message on standard error and a non-zero exit code.
- Successful operations MUST exit with code 0.
- The program MUST NOT terminate with an uncaught exception or print a Python traceback to the
  user under any input; expected failures are handled explicitly and documented exit codes are
  defined in the plan.

**Rationale**: A CLI is used by people and scripts; both need predictable exit codes and
actionable messages rather than stack traces.

### VII. No Secrets in Code or Repository

- Credentials, API keys, tokens, passwords, and other secrets MUST NOT appear in source code,
  tests, configuration, spec artifacts, commit history, or any other file in the repository.
- Local, user-specific files (e.g. real task data files, `.env`) MUST be excluded via
  `.gitignore`.

**Rationale**: The application needs no secrets; keeping the repository free of them removes a
whole class of security risk.

### VIII. Controlled Requirement Changes

- Requirements change only by editing the spec artifacts (`spec.md`, `plan.md`, `tasks.md`)
  through the Spec Kit workflow, never by changing code or tests alone.
- Every requirement change MUST be recorded with its date, what changed, and why (e.g. a
  change-log entry in the affected spec), and affected acceptance criteria, tests, and tasks
  MUST be updated consistently.

**Rationale**: Recorded, artifact-first changes keep the spec, tests, and code in agreement and
leave an audit trail.

## Technology Constraints

- **Language/runtime**: Python 3.11.
- **Runtime dependencies**: Python standard library only. No third-party runtime packages.
- **Development dependencies** (permitted, not shipped): `pytest`, `pytest-cov`, `ruff`,
  `bandit`. Adding any other dependency requires a constitution amendment.
- **Interface**: Command-line program; output on standard output, errors on standard error.
- **Storage**: A single local JSON data file (Principle V); no databases or network services.

## Development Workflow & Quality Gates

1. `/speckit-specify` → spec with numbered acceptance criteria (`AC01`, `AC02`, …).
2. `/speckit-clarify` as needed → `/speckit-plan` → plan MUST pass the Constitution Check
   against every principle above, with any deviation justified in writing.
3. `/speckit-tasks` → each task references the acceptance criteria it satisfies.
4. `/speckit-implement` → tests for an acceptance criterion are written alongside or before the
   code that satisfies it, and named per Principle III.
5. Before a task is marked complete, all Principle II gates MUST be run and pass; the results
   (ruff, bandit, pytest pass count, coverage %) are reported.
6. Every commit MUST leave all gates passing.

## Governance

- This constitution supersedes all other project practices and guidance. Where a spec, plan,
  task, or agent instruction conflicts with it, the constitution wins.
- **Amendments** MUST be made by editing this file, with a written rationale, a version bump,
  and an updated **Last Amended** date. Amendments MUST NOT be made to unblock a failing gate.
- **Versioning** follows semantic versioning:
  - MAJOR: removal or backward-incompatible redefinition of a principle or gate.
  - MINOR: a new principle or section, or materially expanded guidance.
  - PATCH: clarifications and wording fixes with no change in meaning.
- **Compliance review**: every plan MUST include a Constitution Check; every implementation
  review MUST confirm all quality gates pass and that no test, coverage threshold, or lint/security
  rule was weakened (Principle III).

**Version**: 1.0.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-05
