# Implementation Plan: Smart Todo CLI

**Branch**: `001-smart-todo-cli` (work is on `main`; see spec header) | **Date**: 2026-11-07 |
**Spec**: [spec.md](./spec.md) | **Status**: Approved (2026-11-07)

**Input**: Feature specification from `specs/001-smart-todo-cli/spec.md` (AC-01–AC-59, FR-001–FR-019,
clarification session and change log 2026-11-07)

## Summary

A single-user command-line todo manager, `todo`, with five commands: `add`, `list`, `update`,
`delete` and `status`. Tasks live in one JSON file. The spec fixes the exact output, messages
and exit codes, so the work is mainly about doing those exactly and in a fixed check order. The
technical approach is Python 3.11 standard library only:

- `argparse` for parsing, with value checks done by hand so exit codes and messages match
  (research R1–R2).
- A small layered package: CLI → service → models/store.
- Strict schema validation on every load (R5).
- Atomic saves using a fixed temp file name and `os.replace` (R6).
- Forced UTF-8 and LF output for byte-identical results on every OS (R7).

Tests are named `test_ACNN_*` and call `main(argv)` in-process. A small subprocess suite covers
the real process boundary. All quality gates run through one harness, `.harness/run_harness.py`,
which saves its evidence for every run (R11). Users start the program with the `todo` /
`todo.cmd` launchers at the repository root, with no setup (R8).

## Technical Context

**Language/Version**: Python 3.11 (`requires-python = ">=3.11"`, ruff `target-version = "py311"`).
This machine has 3.13.2 and no 3.11 interpreter; see research R10.

**Primary Dependencies**: None at runtime (standard library: `argparse`, `json`, `os`, `sys`,
`dataclasses`, `re`, `unicodedata`). Dev only: `pytest`, `pytest-cov`, `ruff`, `bandit`.

**Storage**: One local JSON file, default `./todo.json`, overridable with `--file`. Format in
[contracts/data-file.md](./contracts/data-file.md).

**Testing**: pytest + pytest-cov. Acceptance tests (one per AC, `test_ACNN_*`), unit tests, and a
small subprocess suite.

**Target Platform**: Any OS with CPython 3.11. Developed on Windows 11; behaviour must also match
on Linux and macOS (LF output, UTF-8).

**Project Type**: CLI (single project).

**Performance Goals**: Each command finishes in < 1 s with 1,000 tasks (SC-003). One full JSON read
and at most one write per command is far within this.

**Constraints**: Deterministic (no randomness, network or clock). Atomic writes. No traceback ever
shown. Exact message text. Read-only commands never create or modify the file.

**Scale/Scope**: One user and one data file. Expected size is 10²–10³ tasks. About 5 source
modules and roughly 60–80 tests.

## Constitution Check

*GATE: checked before Phase 0 and re-checked after Phase 1. Result: **PASS** both times.*

| # | Principle | How this plan complies | Status |
|---|-----------|------------------------|--------|
| I | Spec-first | All behaviour traces to AC-/FR- IDs, and every task references them. The harness and the launchers are part of this plan (Project Structure, R8, R11). Spec and plan are marked Approved. Code is written only after tasks exist. | ✅ |
| II | Quality gates | All gates run through `.harness/run_harness.py` (R11): `ruff check .`, `bandit -r src tests .harness` (any MEDIUM/HIGH fails), `pytest` over `tests/` and `.harness/tests/`, and coverage ≥ 90% of `smart_todo` (also `fail_under = 90` in `pyproject.toml`). Results go to `evidence/harness-results/<timestamp>/`. Commits happen only at phase checkpoints after the harness passes (tasks.md commit rule), so every commit leaves all gates passing. | ✅ |
| III | Test integrity | Each AC-NN gets a `test_ACNN_<desc>` function. The quickstart includes a traceability script. No `skip`/`xfail`/`noqa`/`nosec`, no coverage omissions, no rule ignores in config. | ✅ |
| IV | Deterministic | No `random`/`uuid`/`secrets`/`tempfile` (fixed `.tmp` name, R6). No network. No clock is used at all, so nothing needs to be injectable. Sort key `(priority_rank, id)`. Canonical JSON serialisation. UTF-8 + LF output (R7). | ✅ |
| V | Safe persistence | Single JSON file. Temp file in the same directory → flush → fsync → `os.replace`. Missing file means an empty store. Corrupt/unreadable/off-schema files get exit 3 and are never written (R5, R6). | ✅ |
| VI | Graceful errors | One `TodoError` hierarchy. Top-level catch-all prevents tracebacks. Exit codes 0/1/2/3/130 are all defined in the spec (130 added by the spec change log, 2026-11-07) and restated in [contracts/cli.md](./contracts/cli.md). | ✅ |
| VII | No secrets | The app needs none. `.gitignore` adds `todo.json`, `*.json.tmp`, `.env`, `.venv/`, and caches/coverage output. | ✅ |
| VIII | Controlled changes | The clarification session is recorded in spec.md with its date. Later requirement changes go through spec → plan → tasks. | ✅ |
| Tech | Python 3.11, stdlib only, CLI, single JSON file | Met. No build backend is declared; the `todo`/`todo.cmd` launchers need no dependency (R8). The final harness run uses `--final`, which fails on any interpreter other than 3.11 (R10). | ✅ (see note) |

**Note (not a violation)**: The local interpreter is 3.13.2. Harness runs during development only
warn about this; the final run (`run_harness.py --final`) must use Python 3.11 (R10).

## Project Structure

### Documentation (this feature)

```text
specs/001-smart-todo-cli/
├── spec.md              # Feature spec (clarified 2026-11-07)
├── plan.md              # This file
├── research.md          # Phase 0: technical decisions R1–R10
├── data-model.md        # Phase 1: Task, Task Store, state machine
├── quickstart.md        # Phase 1: run + validation guide
├── contracts/
│   ├── cli.md           # Commands, streams, exit codes, check order, value grammar
│   └── data-file.md     # JSON format, validity rules, atomic write
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root `Part-1A/`)

```text
pyproject.toml            # [project] metadata (no deps), ruff / pytest / coverage config; no [build-system]
.gitignore
.gitattributes            # LF for `todo`, CRLF for `*.cmd`
todo                      # POSIX launcher: PYTHONPATH=src python3 -m smart_todo "$@"   (R8)
todo.cmd                  # Windows launcher                                           (R8)
.harness/
├── run_harness.py        # ruff, bandit, pytest + coverage; writes evidence; exit 0 iff all PASS (R11)
├── README.md
└── tests/
    └── test_run_harness.py   # self-tests of the harness helpers (collected by the pytest gate)
evidence/
└── harness-results/<UTC timestamp>/   # *.stdout.txt, *.stderr.txt, bandit.json, junit.xml, coverage.json, summary.json
src/
└── smart_todo/
    ├── __init__.py
    ├── __main__.py       # `python -m smart_todo` → sys.exit(cli.main())
    ├── cli.py            # argparse (prog="todo"), FR-019 pipeline, output formatting, exit codes, stream setup
    ├── errors.py         # TodoError, InputError (1), UsageError (2), DataFileError (3)
    ├── models.py         # Priority/Status constants, Task dataclass, validators (ID, title, tag, priority, status), transitions
    ├── store.py          # Store dataclass, load (strict schema), save (atomic), serialise
    └── service.py        # find_task / add / list (filter + sort) / update / delete / set_status on a Store; pure, no I/O
tests/
├── conftest.py           # `run(*argv)` fixture → (code, stdout, stderr) in tmp cwd; `seed()` helper; `data_bytes()`
├── acceptance/
│   ├── test_us1_add_list.py        # AC-01–AC-13, AC-56, AC-57
│   ├── test_us2_persistence.py     # AC-14–AC-23, AC-59
│   ├── test_us3_status.py          # AC-24–AC-32
│   ├── test_us4_update_delete.py   # AC-33–AC-45, AC-58
│   ├── test_us5_filter.py          # AC-46–AC-51, AC-55
│   ├── test_us6_usage.py           # AC-52–AC-54
│   ├── test_subprocess.py          # AC-14, AC-23, AC-52–AC-54 via `python -m smart_todo`
│   └── test_launcher.py            # SC-002 via the `todo` / `todo.cmd` launcher
└── unit/
    ├── test_models.py    # validators, transitions, tag normalisation
    ├── test_store.py     # each validity rule in contracts/data-file.md, canonical bytes, save failure cleanup
    └── test_service.py   # sort/filter, next_id behaviour
```

**Structure Decision**: Single project with a `src/` layout. The layers:

- `cli.py` does all I/O on standard streams and decides exit codes.
- `service.py` holds the business rules as pure functions over an in-memory `Store`.
- `store.py` handles all file-system access.
- `models.py` holds the value rules shared by input validation and load validation, so both
  paths check exactly the same rules (FR-002–FR-004 vs contracts/data-file.md rules 8–10).

Tests import from `src` via pytest `pythonpath = ["src"]`; nothing is installed. Pytest's
`testpaths = ["tests", ".harness/tests"]`, so the harness self-tests are part of the pytest gate.

### Control flow per command

```text
main(argv)
 ├─ configure stdout/stderr (UTF-8, LF)                         R7
 ├─ parse (argparse subclass raising UsageError)       → exit 2  step 1
 ├─ validate values: ID → status → priority → title → tags → 1   step 2
 ├─ store = store.load(path)                            → 3      step 3
 ├─ result = service.<op>(store, …)  (lookup, rules)    → 1      steps 4–5
 ├─ if mutating: store.save(path, result.store)         → 3      step 6
 └─ write result.lines to stdout; return 0
 except TodoError → stderr message, its code
 except KeyboardInterrupt → "Error: interrupted.", 130
 except Exception → "Error: unexpected internal error.", 1
```

## Phase 0 / Phase 1 outputs

- [research.md](./research.md): R1–R11, no NEEDS CLARIFICATION left.
- [data-model.md](./data-model.md)
- [contracts/cli.md](./contracts/cli.md), [contracts/data-file.md](./contracts/data-file.md)
- [quickstart.md](./quickstart.md)

## Risks

| Risk | Mitigation |
|------|-----------|
| Windows text streams emit CRLF or a legacy code page → byte-exact tests fail | R7 reconfigure; subprocess tests compare raw bytes |
| `os.replace` fails on Windows if the target is open elsewhere | Report the save error (exit 3); previous file is kept (FR-015) |
| Gates run on 3.13 instead of the 3.11 the constitution requires | `run_harness.py --final` fails on any interpreter other than 3.11 (R10) |
| argparse wording differs slightly between Python versions | ACs only assert `usage: todo` as the first line, exit 2 and no `Traceback` |

## Complexity Tracking

No constitution violations. Nothing to justify.
