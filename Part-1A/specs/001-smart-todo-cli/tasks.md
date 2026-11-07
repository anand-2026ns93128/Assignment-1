---

description: "Task list for Smart Todo CLI"
---

# Tasks: Smart Todo CLI

**Input**: Design documents from `specs/001-smart-todo-cli/`: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md), [contracts/cli.md](./contracts/cli.md),
[contracts/data-file.md](./contracts/data-file.md), [quickstart.md](./quickstart.md)

**Tests**: Required. Constitution III and the user's request say: test-first, and every AC-NN has a
test named `test_ACNN_<description>`. In each story phase the test tasks come first, followed by a
"confirm red" task, and only then the implementation tasks.

**Organization**: Phase 1 is setup plus the quality-gate harness. Phase 2 is the foundation every
story needs. Phases 3–8 are one per user story, in spec priority order (US1, US2 = P1; US3 = P2;
US4, US5, US6 = P3). Phase 9 is polish.

## Format: `- [ ] [ID] [P?] [Story?] Description — Covers: <AC/FR IDs>`

- **[P]**: can run in parallel (different file, no dependency on an unfinished task)
- **[USn]**: user story from spec.md
- Paths are relative to the repository root `Part-1A/`
- "Run the harness" always means `python .harness/run_harness.py` (built in T005). A story is done
  only when all four gates are PASS (Constitution II).

## Shared conventions for every task

- Messages, exit codes and output formats are copied **verbatim** from spec.md (*Error Messages*,
  *Exit Codes*, *Command Interface*). Do not reword them.
- Check order is FR-019 / [contracts/cli.md](./contracts/cli.md#check-order-fr-019):
  `usage(2) → values: ID → status → priority → title → tags (1) → load file (3) → task exists (1)
  → transition / nothing-to-update / --tag+--clear-tags (1) → save (3)`.
- Never use `skip`, `skipif`, `xfail`, `# noqa`, `# nosec`, coverage `omit`/`exclude_lines`, or rule
  ignores (Constitution III).
- No `random`, `uuid`, `secrets`, `tempfile`, network or clock in `src/` (Constitution IV).
- Each commit message names the task ID(s) it implements (Constitution I).

---

## Phase 1: Setup (Shared Infrastructure + Quality-Gate Harness)

**Purpose**: Project skeleton, tool configuration, and the harness that proves the gates.

- [ ] T001 Create the package and test skeleton:
  - `src/smart_todo/__init__.py`, containing only a module docstring `"""Smart Todo CLI."""` and
    `__version__ = "0.1.0"`.
  - Empty directories `tests/acceptance/` and `tests/unit/`. No `__init__.py` files in `tests/`;
    all test module basenames must be unique.
  - **Covers**: FR-012 (plan structure), all FR (layout per plan.md).
- [ ] T002 Create `pyproject.toml` with **no** `[build-system]` table (research R8):
  - `[project]`: `name = "smart-todo"`, `version = "0.1.0"`, `requires-python = ">=3.11"`,
    `dependencies = []`.
  - `[project.optional-dependencies] dev = ["pytest", "pytest-cov", "ruff", "bandit"]`.
  - `[tool.ruff]`: `target-version = "py311"`, `line-length = 100`.
    `[tool.ruff.lint] select = ["E", "F", "W", "I", "B", "UP"]`, with no `ignore` or
    `per-file-ignores`.
  - `[tool.pytest.ini_options]`: `pythonpath = ["src"]`, `testpaths = ["tests"]`,
    `addopts = "--strict-markers"`.
  - `[tool.coverage.run]`: `source = ["smart_todo"]`.
  - `[tool.coverage.report]`: `fail_under = 90`, `show_missing = true`, with no `omit` and no
    `exclude_lines`.
  - **Covers**: FR-016 (stdlib only, Constitution Technology Constraints), SC-001.
- [ ] T003 [P] Create `.gitignore` listing: `todo.json`, `*.json.tmp`, `.env`, `.venv/`,
  `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `coverage.xml`,
  `htmlcov/`. Do **not** ignore `evidence/`; harness results are kept as evidence.
  - **Covers**: FR-012 (default data file stays local, Constitution VII).
- [ ] T004 [P] Write the harness self-tests **first** in `.harness/tests/test_run_harness.py`. They
  test only pure helper functions of `run_harness.py` and **never** start the real gates. Import
  the script via `importlib.util.spec_from_file_location` from `Path(__file__).parents[1] /
  "run_harness.py"`. Required tests:
  - `test_bandit_gate_passes_with_only_low_findings`: bandit JSON with one `LOW` result → PASS.
  - `test_bandit_gate_fails_on_medium_or_high`: one `MEDIUM` → FAIL; one `HIGH` → FAIL.
  - `test_bandit_gate_fails_on_bandit_errors`: non-empty `errors` list → FAIL.
  - `test_pytest_gate_from_junit`: write junit XML to `tmp_path` with
    `tests=3 failures=0 errors=0 skipped=0` → PASS; `failures=1` → FAIL; `skipped=1` → FAIL
    (Constitution III); `tests=0` → FAIL.
  - `test_coverage_gate_threshold`: `{"totals": {"percent_covered": 90.0}}` → PASS; `89.99` → FAIL;
    missing file → FAIL.
  - `test_overall_and_exit_code`: all PASS → `"PASS"`, exit 0; any FAIL → `"FAIL"`, exit 1.
  - `test_unique_run_dir`: when `<timestamp>/` already exists the helper returns `<timestamp>-1/`.
  - **Covers**: SC-001, FR-017 (gate evidence for every AC-01–AC-58).
- [ ] T005 Implement `.harness/run_harness.py`. Standard library only; it is run by the developer's
  Python, never imported by `src/`. Requirements:
  1. `ROOT = Path(__file__).resolve().parent.parent`. Every gate runs with `cwd=ROOT` using
     `sys.executable -m <tool>` and `subprocess.run(..., capture_output=True, text=True,
     encoding="utf-8", errors="replace")`, with a list of arguments (no `shell=True`).
  2. Run directory: `ROOT / "evidence" / "harness-results" / <UTC timestamp
     "%Y%m%dT%H%M%SZ">`. If it already exists, append `-1`, `-2`, …. Create it with
     `parents=True`.
  3. Gates, in this order. All four always run, even after an earlier failure.
     - **ruff**: `-m ruff check .` → PASS iff exit code 0.
     - **bandit**: `-m bandit -r src tests .harness -f json`. Its stdout is the JSON report;
       also save it as `bandit.json`. PASS iff the JSON parses, `errors` is empty, and no result
       has `issue_severity` of `MEDIUM` or `HIGH` (Constitution II). LOW findings are counted
       and reported, not failed.
     - **pytest**: `-m pytest --cov=smart_todo --cov-report=term-missing
       --cov-report=json:<run_dir>/coverage.json --junitxml=<run_dir>/junit.xml`. PASS iff the
       junit totals show `tests > 0`, `failures == 0`, `errors == 0`, `skipped == 0`. Do not
       pass any `--cov-fail-under` override.
     - **coverage**: read `<run_dir>/coverage.json` → `totals.percent_covered`. PASS iff ≥
       `COVERAGE_THRESHOLD = 90.0` (module constant; never lowered).
  4. For each process-based gate, write `<gate>.stdout.txt`, `<gate>.stderr.txt`, and keep the
     exit code. If the tool is not installed (`No module named …` in stderr, or exit code
     `None`/`FileNotFoundError`), the gate is FAIL with `"note": "tool not installed"`.
  5. Write `summary.json` (UTF-8, `indent=2`, `sort_keys=True`, trailing newline):
     `{"timestamp", "python_version", "platform", "overall": "PASS"|"FAIL", "gates": {"ruff":
     {"status", "exit_code", "command"}, "bandit": {"status", "exit_code", "command",
     "medium_high_count", "low_count"}, "pytest": {"status", "exit_code", "command", "tests",
     "failures", "errors", "skipped"}, "coverage": {"status", "percent", "threshold"}},
     "warnings": [...]}`. Add the warning `"python_version is not 3.11"` when
     `sys.version_info[:2] != (3, 11)` (research R10). This is a warning, not a gate.
  6. Print a 4-line table `<gate>  PASS|FAIL  <detail>`, the overall result and the run
     directory path to stdout.
  7. Exit `0` iff every gate is PASS, otherwise `1`. On an unexpected harness exception, write
     what is known, print the error and exit `2`.
  8. Split the code into pure helpers so T004 can test them: `bandit_status(report)`,
     `pytest_status(junit_path)`, `coverage_status(coverage_json_path, threshold)`,
     `overall(gates)`, `unique_run_dir(base, stamp)`, plus `main()` guarded by
     `if __name__ == "__main__":`.
  - **Covers**: SC-001, FR-017; Constitution II gates for AC-01–AC-58.
- [ ] T006 [P] Write `.harness/README.md`:
  - Purpose.
  - Install: `python -m pip install pytest pytest-cov ruff bandit`.
  - Run: `python .harness/run_harness.py`.
  - The files written per run: `ruff|bandit|pytest .stdout.txt/.stderr.txt`, `bandit.json`,
    `junit.xml`, `coverage.json`, `summary.json`.
  - Exit codes 0/1/2.
  - Self-tests: `python -m pytest .harness/tests -p no:cacheprovider`. They sit outside
    `testpaths`, so the gate run does not collect them.
  - **Covers**: SC-001.
- [ ] T007 Run `python -m pytest .harness/tests`: all harness self-tests must pass. Then run
  `python .harness/run_harness.py` once on the skeleton. Expect overall FAIL, because pytest
  collects 0 tests and coverage has no data. Confirm the run directory holds every file listed in
  T005 step 4–5 and that the exit code is 1.
  - **Covers**: SC-001.

**Checkpoint**: The harness works and records evidence.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Errors, shared constants, test fixtures, a minimal store and the CLI pipeline that
every story plugs into.

**⚠️ CRITICAL**: No user-story work starts until this phase is complete.

- [ ] T008 [P] Create `tests/conftest.py` with fixtures and helpers. Tests must use these and must
  not re-implement them:
  - `run` fixture: `monkeypatch.chdir(tmp_path)`, then returns a callable `run(*argv) ->
    Result(code, out, err)`. It calls `smart_todo.cli.main(list(argv))` and reads
    `capsys.readouterr()`. `Result` is a `NamedTuple`.
  - `data_bytes(name="todo.json") -> bytes | None` (in `tmp_path`; `None` if missing).
  - `write_store(next_id, tasks, name="todo.json")`: writes the canonical form from
    contracts/data-file.md, i.e. `json.dumps({"version": 1, "next_id": …, "tasks": […]},
    ensure_ascii=False, indent=2) + "\n"` as UTF-8 bytes, where each task is a dict
    `{"id", "title", "priority", "status", "tags"}`.
  - `write_raw(text_or_bytes, name="todo.json")`.
  - `run_proc(*argv, cwd)`: `subprocess.run([sys.executable, "-m", "smart_todo", *argv],
    cwd=cwd, env={**os.environ, "PYTHONPATH": str(SRC_DIR)}, capture_output=True)`. It returns
    raw **bytes** stdout/stderr and the return code.
  - **Covers**: FR-012, FR-016, FR-017 (test infrastructure for AC-01–AC-58).
- [ ] T009 [P] Write foundational unit tests **first** in `tests/unit/test_core.py`:
  - `InputError`/`DataFileError`/`UsageError` carry exit codes 1/3/2 and their message.
  - `main` turns an unexpected exception into stderr `Error: unexpected internal error.\n`, exit 1,
    and no `Traceback`. Use monkeypatch to make a handler raise `RuntimeError`.
  - `main` turns `KeyboardInterrupt` into stderr `Error: interrupted.\n`, exit 130.
  - A missing data file loads as an empty store with `next_id == 1` and creates no file.
  - The canonical serialisation of a sample store equals an exact expected byte string
    (contracts/data-file.md, *Canonical form*).
  - **Covers**: FR-013, FR-016, FR-017.
- [ ] T010 [P] Implement `src/smart_todo/errors.py`:
  - `class TodoError(Exception)` with `message: str` and `exit_code: int`.
  - Subclasses `InputError` (exit 1), `UsageError` (exit 2; also carries `usage: str`) and
    `DataFileError` (exit 3).
  - Helper constructors that return the exact spec messages, e.g.
    `corrupt_file(path) -> DataFileError("Error: data file '{path}' is corrupt or unreadable; it
    was not modified.")`, `save_failed(path)`, `task_not_found(n)`, `invalid_task_id(x)`,
    `invalid_priority(x)`, `invalid_status(x)`, `invalid_tag(x)`, `invalid_title()`,
    `invalid_transition(n, old, new)`, `nothing_to_update()`, `tag_clear_conflict()`.
  - **Covers**: FR-017, FR-011, FR-014, FR-015.
- [ ] T011 [P] Implement the shared constants and entity in `src/smart_todo/models.py`. Validators
  are added per story:
  - `PRIORITIES = ("low", "medium", "high")`.
  - `PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}`.
  - `STATUSES = ("todo", "in_progress", "done")`.
  - `DEFAULT_PRIORITY = "medium"`.
  - `@dataclass(frozen=True) class Task: id: int; title: str; priority: str; status: str;
    tags: tuple[str, ...]`.
  - **Covers**: FR-001, FR-003, FR-005, FR-010.
- [ ] T012 Implement a minimal `src/smart_todo/store.py`. US2 hardens it later:
  - `@dataclass(frozen=True) class Store: next_id: int; tasks: tuple[Task, ...]`.
  - `EMPTY = Store(1, ())`.
  - `load(path: str) -> Store`: `FileNotFoundError` → `EMPTY`. Otherwise read bytes, decode
    UTF-8, `json.loads`, and build `Task`s. **Any** exception while reading or building →
    `errors.corrupt_file(path)`.
  - `serialise(store) -> bytes`: canonical form per contracts/data-file.md. Tasks are sorted by
    `id`, key order `version, next_id, tasks` / `id, title, priority, status, tags`,
    `ensure_ascii=False`, `indent=2`, plus `"\n"`, UTF-8.
  - `save(path, store)`: plain write of `serialise(store)` (made atomic in T030).
  - **Covers**: FR-012, FR-013, FR-016 (depends on T010, T011).
- [ ] T013 Implement the pipeline skeleton in `src/smart_todo/cli.py`:
  - `class _Parser(argparse.ArgumentParser)`. `error(message)` raises
    `UsageError(usage=self.format_usage(), message=f"{self.prog}: error: {message}\n")`;
    `exit(status=0, message=None)` raises an internal `_Exit(status, message)` (for `--help`).
  - `build_parser()`: `prog="todo"`, `allow_abbrev=False`, global `--file` (default
    `"todo.json"`), `add_subparsers(dest="command", required=True, parser_class=_Parser)` with
    every command and option from contracts/cli.md. **All values are plain `str`**: no `choices=`
    and no `type=`. `--tag` uses `action="append"`, `default=None`; `--clear-tags` uses
    `action="store_true"`.
  - `main(argv=None) -> int`:
    1. `_configure_streams()` calls `reconfigure(encoding="utf-8", newline="\n")` on
       stdout/stderr when available (research R7).
    2. Parse.
    3. Dispatch through a dict `{"add": _cmd_add, …}`. Each handler returns `list[str]` of
       stdout lines and raises `TodoError` on failure. Handlers not built yet raise
       `NotImplementedError`.
    4. Write the lines, each ending in `"\n"`, and return 0.
    5. `except UsageError` → write `usage + message` to stderr, return 2.
    6. `_Exit` → write message to stdout if status 0, otherwise to stderr; return status.
    7. `except TodoError as e` → write `e.message + "\n"` to stderr, return `e.exit_code`.
    8. `except KeyboardInterrupt` → `Error: interrupted.`, return 130.
    9. `except Exception` → `Error: unexpected internal error.`, return 1.
  - **Covers**: FR-017, FR-019 step 1, FR-012 (`--file`) (depends on T010–T012).
- [ ] T014 Implement `src/smart_todo/__main__.py`: `import sys; from smart_todo.cli import main;
  sys.exit(main())`.
  - **Covers**: FR-017.
- [ ] T015 Run the harness. T009 tests must pass and ruff/bandit must be PASS. Coverage may still be
  below 90%; record the run directory.
  - **Covers**: FR-013, FR-016, FR-017.

**Checkpoint**: Pipeline in place. Story phases can now begin.

---

## Phase 3: User Story 1 - Add and list tasks (Priority: P1) 🎯 MVP

**Goal**: `todo add` with title, priority and tags; `todo list` sorted by priority, then ID.

**Independent Test**: From a fresh store, add tasks with mixed priorities and tags, then compare
`todo list` output line by line (AC-01–AC-13, AC-56, AC-57).

### Tests for User Story 1 (write first) ⚠️

- [ ] T016 [P] [US1] Write acceptance tests in `tests/acceptance/test_us1_add_list.py` using the
  `run` fixture. Each asserts exact stdout, exact stderr, the exit code, and, for error cases,
  `data_bytes()` before == after (`None` == `None` for a fresh store):
  - `test_AC01_add_task_with_defaults`
  - `test_AC02_add_with_priority_and_tags`
  - `test_AC03_empty_title_rejected`
  - `test_AC04_spaces_only_title_rejected`
  - `test_AC05_title_is_trimmed`
  - `test_AC06_title_of_100_chars_accepted`
  - `test_AC07_title_of_101_chars_rejected`
  - `test_AC08_title_with_line_break_rejected`
  - `test_AC09_invalid_priority_rejected`
  - `test_AC10_invalid_tag_rejected`
  - `test_AC11_duplicate_tags_ignore_case`
  - `test_AC12_list_sorted_by_priority_then_id`
  - `test_AC13_list_empty_store_prints_no_tasks`. Use `write_store(1, [])` for "a store
    containing no tasks".
  - `test_AC56_title_with_tab_rejected`
  - `test_AC57_unicode_title_of_100_chars_accepted`. Use `"é" * 100`.
  - **Covers**: AC-01–AC-13, AC-56, AC-57.
- [ ] T017 [P] [US1] Write unit tests in `tests/unit/test_models.py` for the US1 validators:
  - `validate_title`:
    - Rejects raw values containing `"\n"`, `"\r"`, `"\t"`, `"\x00"`, `"\x7f"` or `"\x85"`, even
      at the ends (`"Buy milk\n"`).
    - Trims surrounding spaces.
    - Accepts lengths 1 and 100; rejects 0 and 101, counting code points.
  - `validate_priority`: accepts only `low|medium|high`; rejects `High` and `urgent`.
  - `normalize_tags`: rejects `"a b"`, `""`, a 21-char tag and `"é"`; accepts a 20-char tag; turns
    `["home", "HOME", "errand"]` into `("home", "errand")`; `None` → `()`; the error message
    shows the raw tag.
  - **Covers**: FR-002, FR-003, FR-004.
- [ ] T018 [P] [US1] Write unit tests in `tests/unit/test_service.py` for `add_task`, `list_tasks`
  (no filters) and `format_line`:
  - The new task gets `id == store.next_id`, `status == "todo"`, and the new store has
    `next_id + 1`.
  - Sorting uses `(PRIORITY_RANK[priority], id)`.
  - `format_line(Task(2, "Pay rent", "high", "todo", ("home", "bills")))` ==
    `"2 [todo] (high) Pay rent #home #bills"`.
  - **Covers**: FR-001, FR-005, FR-007.
- [ ] T019 [US1] Run `python -m pytest tests/acceptance/test_us1_add_list.py tests/unit/test_models.py
  tests/unit/test_service.py` and confirm the new tests **fail** (red) before any implementation.
  Note the failure count in the commit message.
  - **Covers**: AC-01–AC-13, AC-56, AC-57.

### Implementation for User Story 1

- [ ] T020 [US1] Add validators to `src/smart_todo/models.py`. Each raises the matching `errors.*`
  helper:
  - `validate_title(raw: str) -> str`: if any `unicodedata.category(ch) == "Cc"` → invalid title;
    `t = raw.strip()`; require `1 <= len(t) <= 100`; return `t`.
  - `validate_priority(raw: str) -> str`: must be in `PRIORITIES`; case-sensitive.
  - `normalize_tags(raws: list[str] | None) -> tuple[str, ...]`: each raw must fully match
    `re.compile(r"[A-Za-z0-9_-]{1,20}")` (use `fullmatch`; ASCII only). Lowercase it, drop
    duplicates, keep first-seen order.
  - **Covers**: FR-002, FR-003, FR-004 (depends on T017).
- [ ] T021 [US1] Add to `src/smart_todo/service.py`:
  - `add_task(store, title, priority, tags) -> tuple[Store, Task]`: new `id = store.next_id`,
    status `"todo"`; returns a new `Store(next_id + 1, tasks + (task,))`.
  - `list_tasks(store, tag=None, status=None) -> list[Task]`: sorted by
    `(PRIORITY_RANK[t.priority], t.id)`; filters come in T048.
  - `format_line(task) -> str`: `f"{id} [{status}] ({priority}) {title}"` +
    `"".join(f" #{t}" for t in tags)`.
  - **Covers**: FR-001, FR-005, FR-007 (depends on T018, T020).
- [ ] T022 [US1] Implement `_cmd_add` and `_cmd_list` in `src/smart_todo/cli.py`:
  - **add**: validate in FR-019 order. Priority is `args.priority or DEFAULT_PRIORITY`, then
    title, then tags. Then `store.load(args.file)`, then `service.add_task`, then
    `store.save(args.file, …)`. Return `[f"Added task {id}: {title}"]`.
  - **list**: `store.load` → `service.list_tasks`. Return the formatted lines, or
    `["No tasks found."]`. **Never** call `save` (FR-013).
  - **Covers**: AC-01–AC-13, AC-56, AC-57, FR-001–FR-005, FR-019 (depends on T021).
- [ ] T023 [US1] Run the harness. The US1 tests from T016–T018 must be green, ruff/bandit PASS.
  Record the run directory.
  - **Covers**: AC-01–AC-13, AC-56, AC-57.

**Checkpoint**: MVP. Tasks can be added and listed.

---

## Phase 4: User Story 2 - Reliable persistence (Priority: P1)

**Goal**: Data survives between runs, IDs are never reused, corrupt files are refused, and saves
are atomic.

**Independent Test**: Add tasks, run again in a new process and list; delete and add to observe
IDs; corrupt the file and confirm commands refuse to touch it (AC-14–AC-23).

### Tests for User Story 2 (write first) ⚠️

- [ ] T024 [P] [US2] Write acceptance tests in `tests/acceptance/test_us2_persistence.py`:
  - `test_AC14_task_persists_between_runs`: two separate `run` calls.
  - `test_AC15_id_not_reused_after_deleting_highest`: `write_store(4, [tasks 1, 2])` stands in
    for "task 3 deleted".
  - `test_AC16_id_not_reused_after_deleting_all`: `write_store(3, [])`.
  - `test_AC17_list_on_fresh_store_creates_no_file`
  - `test_AC18_list_refuses_non_json_file`: `write_raw("{not json")`; assert stdout empty and
    bytes unchanged.
  - `test_AC19_add_refuses_non_json_file`
  - `test_AC20_list_refuses_wrong_shape_json`: `[]`.
  - `test_AC21_interrupted_save_keeps_previous_data`: monkeypatch `smart_todo.store.os.replace`
    to raise `OSError`. Assert exit 3, stderr
    `Error: could not save data file 'todo.json'; previous data was kept.\n`, bytes unchanged, no
    `todo.json.tmp` left, and a following `todo list` prints task 1.
  - `test_AC21_keyboard_interrupt_during_save_keeps_previous_data`: patch `os.replace` to raise
    `KeyboardInterrupt`. Assert exit 130, bytes unchanged, no `.tmp` left.
  - `test_AC22_file_option_uses_given_path`: assert `todo.json` does not exist afterwards.
  - `test_AC23_same_input_gives_identical_results`: run the same `update`/`add` on two
    identical copies in two sub-directories; compare stdout, stderr, code and resulting bytes.
  - **Covers**: AC-14–AC-23.
- [ ] T025 [P] [US2] Write unit tests in `tests/unit/test_store.py`. Each data-file validity rule
  in contracts/data-file.md gets at least one test asserting `DataFileError` with the
  corrupt-file message and an unchanged file. Name them `test_FR014_rule<N>_<case>`:
  - Rule 1: invalid UTF-8 bytes `b"\xff"`; a path that is a directory.
  - Rule 2: UTF-8 BOM plus valid JSON; duplicate keys `{"version":1,"version":1,…}`.
  - Rule 3: an extra top-level key; a missing `tasks`.
  - Rule 4: `version` = 2.
  - Rule 5: `next_id` = 0, `true`, `"3"`.
  - Rule 6: a task with an extra key; a missing `tags`.
  - Rule 7: `id` = 0 or `true`; duplicate ids; `next_id` equal to the max id.
  - Rule 8: untrimmed title `" x"`; a title containing `"\t"`; a 101-char title.
  - Rule 9: priority `urgent`; status `finished`.
  - Rule 10: tag `Home` (uppercase); duplicate tags; tag `"a b"`.
  - Also:
    - `test_FR014_valid_store_round_trips`: `load(serialise(s)) == s`.
    - `test_FR015_save_removes_tmp_on_failure`.
    - `test_FR015_save_overwrites_stale_tmp`: a pre-existing `todo.json.tmp` is replaced and then
      gone.
    - `test_FR016_serialise_is_canonical_and_sorted`: tasks given out of order are written in
      ascending `id`.
  - **Covers**: FR-014, FR-015, FR-016, FR-007.
- [ ] T026 [P] [US2] Create `tests/acceptance/test_subprocess.py` with two tests that use
  `run_proc`:
  - `test_AC14_persists_across_processes`: real separate processes `add` then `list`.
  - `test_AC23_byte_identical_across_processes`: the same command twice on identical file copies.
    Raw stdout/stderr bytes, exit codes and resulting files are identical, and stdout contains no
    `b"\r\n"` (research R7).
  - **Covers**: AC-14, AC-23, FR-016.
- [ ] T027 [US2] Run `python -m pytest tests/acceptance/test_us2_persistence.py tests/unit/test_store.py
  tests/acceptance/test_subprocess.py` and confirm the strict-validation and atomic-save tests
  **fail** (red). Some tests, e.g. AC-14 and AC-22, may already pass thanks to T012/T013; list
  them in the commit message.
  - **Covers**: AC-14–AC-23.

### Implementation for User Story 2

- [ ] T028 [US2] Replace the lenient loader in `src/smart_todo/store.py` with strict validation, in
  this order (rules 1–10 of contracts/data-file.md):
  - Read bytes (`OSError` → corrupt).
  - `bytes.decode("utf-8")` (strict).
  - `json.loads(text, object_pairs_hook=_no_duplicate_keys)`.
  - Top level is a `dict` with keys exactly `{"version", "next_id", "tasks"}`; `version == 1`
    (type `int`, not `bool`).
  - `next_id`: an `int` that is not a `bool`, ≥ 1.
  - Each task is a `dict` with keys exactly `{"id", "title", "priority", "status", "tags"}`.
  - `id`: an `int` that is not a `bool`, ≥ 1, unique; `next_id > max(id)`.
  - `title`: a `str`, `models.validate_title(title) == title`.
  - Priority in `PRIORITIES`; status in `STATUSES`.
  - `tags`: a `list` of `str`; `models.normalize_tags(tags) == tuple(tags)`.
  - Catch every `TodoError`/`ValueError`/`TypeError`/`KeyError` raised during validation and
    re-raise `errors.corrupt_file(path)`, keeping the path exactly as typed.
  - **Covers**: FR-014, FR-007, AC-18–AC-20 (depends on T025).
- [ ] T029 [US2] Add `_no_duplicate_keys(pairs)` in `src/smart_todo/store.py`. It raises
  `ValueError` on a repeated key; otherwise it returns `dict(pairs)`.
  - **Covers**: FR-014.
- [ ] T030 [US2] Make `save(path, store)` in `src/smart_todo/store.py` atomic (research R6):
  - `tmp = path + ".tmp"`.
  - `open(tmp, "wb")` → write `serialise(store)` → `flush()` → `os.fsync(f.fileno())` → close →
    `os.replace(tmp, path)`.
  - On `OSError`: remove `tmp` (suppress `OSError`), raise `errors.save_failed(path)`.
  - On `BaseException` (e.g. `KeyboardInterrupt`): remove `tmp`, re-raise.
  - No `tempfile` and no random names.
  - **Covers**: FR-015, AC-21 (depends on T028).
- [ ] T031 [US2] Check `src/smart_todo/cli.py`:
  - `list` never calls `save` (AC-17).
  - Every handler passes `args.file` unchanged to `load`/`save`, so messages show the path as
    typed (spec Assumptions).
  - Nothing reads the clock or environment.
  - Fix anything the T024/T026 tests expose.
  - **Covers**: FR-012, FR-013, FR-016, AC-17, AC-22, AC-23.
- [ ] T032 [US2] Run the harness. All US1 and US2 tests are green; ruff/bandit PASS. Record the run
  directory.
  - **Covers**: AC-14–AC-23.

**Checkpoint**: US1 + US2 together are a trustworthy MVP.

---

## Phase 5: User Story 3 - Track progress with status transitions (Priority: P2)

**Goal**: `todo status ID S`, with only `todo→in_progress`, `in_progress→done` and `todo→done`
allowed.

**Independent Test**: Seed tasks, apply every valid and invalid transition, and check the output
and the resulting `todo list` (AC-24–AC-32).

### Tests for User Story 3 (write first) ⚠️

- [ ] T033 [P] [US3] Write acceptance tests in `tests/acceptance/test_us3_status.py`. Seed with
  `write_store`; error cases assert the bytes are unchanged:
  - `test_AC24_todo_to_in_progress`: includes the `todo list` line
    `1 [in_progress] (medium) Buy milk`.
  - `test_AC25_in_progress_to_done`
  - `test_AC26_todo_to_done`
  - `test_AC27_done_to_todo_rejected`
  - `test_AC28_in_progress_to_todo_rejected`
  - `test_AC29_done_to_in_progress_rejected`
  - `test_AC30_same_status_rejected`
  - `test_AC31_invalid_status_value_rejected`
  - `test_AC32_unknown_id_rejected`
  - **Covers**: AC-24–AC-32.
- [ ] T034 [P] [US3] Add unit tests to `tests/unit/test_models.py`:
  - `parse_task_id`: accepts `"1"` and `"01"` (→ 1) and `"42"`; rejects `"0"`, `"-1"`, `"+1"`,
    `" 1"`, `"1_0"`, `"abc"`, `""` and `"١"`. The message shows the raw value.
  - `validate_status`: accepts the 3 values; rejects `Done` and `finished`.
  - `check_transition`: the full 3×3 matrix from data-model.md. Exactly 3 allowed; the other 6
    raise `invalid_transition`.
  - **Covers**: FR-010, FR-011.
- [ ] T035 [US3] Run `python -m pytest tests/acceptance/test_us3_status.py tests/unit/test_models.py`
  and confirm the new tests **fail** (red).
  - **Covers**: AC-24–AC-32.

### Implementation for User Story 3

- [ ] T036 [US3] Add to `src/smart_todo/models.py`:
  - `parse_task_id(raw: str) -> int`: `re.fullmatch(r"[0-9]+", raw, flags=re.ASCII)` and
    `int(raw) >= 1`, otherwise `errors.invalid_task_id(raw)`.
  - `validate_status(raw) -> str`: in `STATUSES`, case-sensitive.
  - `ALLOWED_TRANSITIONS = frozenset({("todo", "in_progress"), ("in_progress", "done"),
    ("todo", "done")})`.
  - `check_transition(task_id, old, new)`: if the pair is not in the set →
    `errors.invalid_transition(task_id, old, new)`.
  - **Covers**: FR-010, FR-011 (depends on T034).
- [ ] T037 [US3] Add to `src/smart_todo/service.py`:
  - `find_task(store, task_id) -> Task`: raises `errors.task_not_found(task_id)`.
  - `set_status(store, task_id, new) -> tuple[Store, str, str]`: find → `check_transition` →
    return the new store with the task replaced via `dataclasses.replace`, plus `(old, new)`.
  - **Covers**: FR-010, FR-011 (depends on T036).
- [ ] T038 [US3] Implement `_cmd_status` in `src/smart_todo/cli.py`:
  - `parse_task_id` → `validate_status` → `load` → `service.set_status` → `save`.
  - Return `[f"Task {id}: {old} -> {new}"]`.
  - **Covers**: AC-24–AC-32, FR-010, FR-011, FR-019 (depends on T037).
- [ ] T039 [US3] Run the harness. US1–US3 tests are green; ruff/bandit PASS.
  - **Covers**: AC-24–AC-32.

**Checkpoint**: Status tracking works.

---

## Phase 6: User Story 4 - Update and delete tasks (Priority: P3)

**Goal**: `todo update ID [--title] [--priority] [--tag…] [--clear-tags]` and `todo delete ID`.

**Independent Test**: Create a task, apply each kind of update and a delete, and verify with
`todo list`; then try every invalid input (AC-33–AC-45, AC-58).

### Tests for User Story 4 (write first) ⚠️

- [ ] T040 [P] [US4] Write acceptance tests in `tests/acceptance/test_us4_update_delete.py`:
  - `test_AC33_update_title`
  - `test_AC34_update_priority`
  - `test_AC35_update_tags_replaces_set`
  - `test_AC36_clear_tags`
  - `test_AC37_update_without_options_rejected`
  - `test_AC38_tag_and_clear_tags_conflict`
  - `test_AC39_update_empty_title_rejected`
  - `test_AC40_update_invalid_priority_rejected`
  - `test_AC41_update_unknown_id_rejected`
  - `test_AC42_delete_task`
  - `test_AC43_delete_unknown_id_rejected`
  - `test_AC44_delete_non_numeric_id_rejected`
  - `test_AC45_delete_zero_id_rejected`
  - `test_AC58_update_done_task_keeps_status`
  - Error cases assert the bytes are unchanged.
  - **Covers**: AC-33–AC-45, AC-58.
- [ ] T041 [P] [US4] Add unit tests to `tests/unit/test_service.py`:
  - `delete_task` keeps `next_id` unchanged (FR-007).
  - `update_task`: changes only the given fields; never changes `status`; `--tag` replaces the
    whole set; `clear_tags` gives `()`; no change requested → `nothing_to_update`; `tags` +
    `clear_tags` → `tag_clear_conflict`; an unknown id → `task_not_found`, checked **before** the
    other two (FR-019 step 4 before step 5).
  - **Covers**: FR-007, FR-008, FR-009, FR-019.
- [ ] T042 [US4] Run `python -m pytest tests/acceptance/test_us4_update_delete.py tests/unit/test_service.py`
  and confirm the new tests **fail** (red).
  - **Covers**: AC-33–AC-45, AC-58.

### Implementation for User Story 4

- [ ] T043 [US4] Add to `src/smart_todo/service.py`:
  - `update_task(store, task_id, title=None, priority=None, tags=None, clear_tags=False) ->
    Store`, in this order:
    1. `find_task`.
    2. If `title is None and priority is None and tags is None and not clear_tags` →
       `nothing_to_update`.
    3. If `tags is not None and clear_tags` → `tag_clear_conflict`.
    4. Build with `dataclasses.replace`; status is never touched (AC-58).
  - `delete_task(store, task_id) -> Store`: `find_task`, then remove it; `next_id` unchanged.
  - **Covers**: FR-007, FR-008, FR-009, FR-019 (depends on T041).
- [ ] T044 [US4] Implement `_cmd_update` and `_cmd_delete` in `src/smart_todo/cli.py`:
  - **update**:
    1. `parse_task_id`.
    2. If `--priority` was given, `validate_priority`.
    3. If `--title` was given, `validate_title`. An empty `--title ""` counts as given and is
       rejected (AC-39).
    4. If `--tag` was given, `normalize_tags`.
    5. `load` → `service.update_task` → `save` → `["Updated task {id}."]`.
  - **delete**: `parse_task_id` → `load` → `service.delete_task` → `save` →
    `["Deleted task {id}."]`.
  - **Covers**: AC-33–AC-45, AC-58, FR-008, FR-009, FR-011, FR-019 (depends on T043).
- [ ] T045 [US4] Run the harness. US1–US4 tests are green; ruff/bandit PASS.
  - **Covers**: AC-33–AC-45, AC-58.

**Checkpoint**: Full CRUD works.

---

## Phase 7: User Story 5 - Filter the list (Priority: P3)

**Goal**: `todo list --tag TAG` and/or `--status S`.

**Independent Test**: Seed the four-task store from spec US5 and run each filter combination
(AC-46–AC-51, AC-55).

### Tests for User Story 5 (write first) ⚠️

- [ ] T046 [P] [US5] Write acceptance tests in `tests/acceptance/test_us5_filter.py`:
  - A module-level fixture seeds, via `write_store(5, …)`:
    `1 "A" high [work] todo`, `2 "B" low [home] in_progress`, `3 "C" medium [work, home] done`,
    `4 "D" high [] in_progress`.
  - Tests:
    - `test_AC46_filter_by_tag`
    - `test_AC47_filter_by_status`
    - `test_AC48_filter_by_tag_and_status`
    - `test_AC49_tag_filter_ignores_case`
    - `test_AC50_filter_with_no_match`
    - `test_AC51_invalid_status_filter_rejected`
    - `test_AC51_invalid_status_reported_before_corrupt_file`: corrupt `todo.json` + `--status
      finished` → invalid status, exit 1 (FR-019).
    - `test_AC55_invalid_tag_filter_rejected`
  - **Covers**: AC-46–AC-51, AC-55, FR-019.
- [ ] T047 [US5] Run `python -m pytest tests/acceptance/test_us5_filter.py` and confirm the new tests
  **fail** (red).
  - **Covers**: AC-46–AC-51, AC-55.

### Implementation for User Story 5

- [ ] T048 [US5] Extend `list_tasks(store, tag=None, status=None)` in `src/smart_todo/service.py`:
  - Keep tasks where `(tag is None or tag in t.tags) and (status is None or t.status == status)`.
    `tag` is already lowercase.
  - Then apply the existing sort.
  - **Covers**: FR-005, FR-006 (depends on T046).
- [ ] T049 [US5] Update `_cmd_list` in `src/smart_todo/cli.py`:
  - If `--status` was given, `validate_status`.
  - Then, if `--tag` was given, `normalize_tags([tag])[0]`.
  - Both happen **before** `load` (FR-019 step 2 order: status before tags).
  - Pass both to `list_tasks`; still never save.
  - **Covers**: AC-46–AC-51, AC-55, FR-006, FR-019 (depends on T048).
- [ ] T050 [US5] Run the harness. US1–US5 tests are green; ruff/bandit PASS.
  - **Covers**: AC-46–AC-51, AC-55.

**Checkpoint**: Filtering works.

---

## Phase 8: User Story 6 - Clear feedback on command misuse (Priority: P3)

**Goal**: Malformed commands give a `usage: todo` message and exit 2, never a traceback.

**Independent Test**: Run malformed commands and check the exit code and stderr (AC-52–AC-54).

### Tests for User Story 6 (write first) ⚠️

- [ ] T051 [P] [US6] Write acceptance tests in `tests/acceptance/test_us6_usage.py`, in-process via
  `run`:
  - `test_AC52_unknown_command_shows_usage`: code 2, stdout `""`, stderr first line starts with
    `usage: todo`, no `Traceback`, bytes unchanged.
  - `test_AC53_no_arguments_shows_usage`
  - `test_AC54_add_without_title_shows_usage`
  - **Covers**: AC-52–AC-54.
- [ ] T052 [US6] Append three subprocess tests to `tests/acceptance/test_subprocess.py`:
  - `test_AC52_unknown_command_in_real_process`
  - `test_AC53_no_arguments_in_real_process`
  - `test_AC54_add_without_title_in_real_process`
  - Each asserts the return code is 2, `stderr.decode("utf-8").splitlines()[0].startswith("usage:
    todo")` and `b"Traceback" not in stderr`.
  - This task runs after T026 because it edits the same file.
  - **Covers**: AC-52–AC-54, FR-017.
- [ ] T053 [US6] Run `python -m pytest tests/acceptance/test_us6_usage.py tests/acceptance/test_subprocess.py`.
  These tests may already be green because the parser came in T013. If so, record that they pass
  without code changes. Otherwise confirm red.
  - **Covers**: AC-52–AC-54.

### Implementation for User Story 6

- [ ] T054 [US6] Fix anything T051/T052 expose in `_Parser`/`main` in `src/smart_todo/cli.py`. The
  usage text goes to stderr only (stdout stays empty), the message line follows it, the exit code
  is 2, and `--help` still exits 0 to stdout.
  - **Covers**: AC-52–AC-54, FR-017.
- [ ] T055 [US6] Run the harness. All AC tests are green; ruff/bandit PASS.
  - **Covers**: AC-52–AC-54.

**Checkpoint**: All six user stories work independently.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T056 [P] Write `tests/unit/test_check_order.py`. One test per row of the *Check order*
  examples table in contracts/cli.md, named `test_FR019_<case>`:
  - `status 99 finished` → invalid status.
  - `status abc finished` → invalid ID.
  - `list --status finished` with a corrupt file → invalid status.
  - `add "" --priority urgent` → invalid priority.
  - `update 99` → not found.
  - `update 1 --tag "a b" --clear-tags` → invalid tag.
  - Also: `delete 99` with a corrupt file → exit 3 (load before lookup).
  - Fix `src/smart_todo/cli.py` if any test fails.
  - **Covers**: FR-019, FR-017.
- [ ] T057 [P] Write `tests/unit/test_performance.py::test_SC003_commands_under_one_second_with_1000_tasks`:
  - `write_store(1001, [1000 tasks])`.
  - Time `list`, `add`, `update`, `status` and `delete` in-process with `time.perf_counter()`.
  - Assert each is < 1.0 s.
  - **Covers**: SC-003, FR-005, FR-012.
- [ ] T058 Check traceability with the script in quickstart.md (*Traceability check*). Expected
  output: `58 ACs, missing tests: none`. Then grep `src/` and `tests/` for `skip`, `xfail`,
  `noqa`, `nosec`, `random`, `uuid`, `secrets` and `tempfile`; there must be no hits.
  - **Covers**: AC-01–AC-58, FR-016, FR-017 (Constitution III, IV).
- [ ] T059 Run the smoke scenarios from quickstart.md by hand in a scratch directory and confirm each
  commented output.
  - **Covers**: AC-01, AC-02, AC-12, AC-15, AC-18, AC-24, AC-28, AC-42, AC-49, AC-52.
- [ ] T060 Final gate run, on a Python 3.11 interpreter if one is available (research R10):
  - `python .harness/run_harness.py` must exit 0 with all four gates PASS.
  - Commit the resulting `evidence/harness-results/<timestamp>/` directory.
  - Report ruff errors, bandit MEDIUM/HIGH count, the pytest pass count and the coverage %
    (Constitution workflow step 5).
  - **Covers**: SC-001, SC-004, SC-005, SC-006, all AC-01–AC-58.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 Setup**: none. T004 comes before T005 (test-first); T007 needs T005.
- **Phase 2 Foundational**: needs Phase 1. T010/T011 → T012 → T013 → T014 → T015. T008 and T009
  can be written in parallel with T010/T011.
- **Phases 3–8 (stories)**: all need Phase 2.
- **Phase 9 Polish**: needs every story phase.

### User story dependencies

| Story | Depends on | Why |
|-------|-----------|-----|
| US1 (P1) | Foundational | — |
| US2 (P1) | US1 | Its ACs use `add`/`list`; T028 reuses the US1 validators |
| US3 (P2) | Foundational (+ US1 `list` for AC-24) | Seeds with `write_store`; AC-24 runs `todo list` |
| US4 (P3) | US3 | Reuses `parse_task_id`/`find_task` from T036/T037 |
| US5 (P3) | US1, US3 | Extends `list_tasks`; uses `validate_status` from T036 |
| US6 (P3) | Foundational | Parser only |

Recommended order: US1 → US2 → US3 → US4 → US5 → US6. US6 may run any time after Phase 2.

### Within each story

Tests ([P], separate files) → confirm red → models → service → CLI handler → harness run.

### Same-file sequencing (not parallel)

- `src/smart_todo/cli.py`: T013 → T022 → T031 → T038 → T044 → T049 → T054.
- `src/smart_todo/models.py`: T011 → T020 → T036.
- `src/smart_todo/service.py`: T021 → T037 → T043 → T048.
- `src/smart_todo/store.py`: T012 → T028 → T029 → T030.
- `tests/unit/test_models.py`: T017 → T034. `tests/unit/test_service.py`: T018 → T041.
- `tests/acceptance/test_subprocess.py`: T026 → T052.

---

## Parallel Examples

```text
# Phase 1
T003 .gitignore  ‖  T004 harness self-tests  ‖  T006 harness README

# Phase 2
T008 conftest.py  ‖  T009 test_core.py  ‖  T010 errors.py  ‖  T011 models.py constants

# US1 tests
T016 test_us1_add_list.py  ‖  T017 test_models.py  ‖  T018 test_service.py

# US2 tests
T024 test_us2_persistence.py  ‖  T025 test_store.py  ‖  T026 test_subprocess.py

# US3 tests
T033 test_us3_status.py  ‖  T034 test_models.py additions

# US4 tests
T040 test_us4_update_delete.py  ‖  T041 test_service.py additions

# Polish
T056 test_check_order.py  ‖  T057 test_performance.py
```

---

## Implementation Strategy

### MVP first (US1 + US2, both P1)

1. Phase 1 (harness in place) → Phase 2.
2. US1 → harness → **validate**: add and list work.
3. US2 → harness → **validate**: data persists and is never lost. This is the MVP.

### Incremental delivery

US3 (status) → US4 (update/delete) → US5 (filter) → US6 (usage). Each ends with a harness run whose
`evidence/harness-results/<timestamp>/summary.json` is the proof for that increment.

### Gate discipline

Coverage may fall below 90% until enough stories exist. That is expected mid-way, but nothing is
called "complete" and no final commit is made until all four gates PASS (Constitution II, workflow
step 6). Fix code, never tests or thresholds (Constitution III).

---

## Notes

- Every task names its AC/FR coverage. Every AC-01…AC-58 appears in at least one test task:
  US1 → T016, US2 → T024/T026, US3 → T033, US4 → T040, US5 → T046, US6 → T051/T052.
- `[P]` = different file and no dependency on an unfinished task.
- Commit after each task or logical group, citing the task ID.
