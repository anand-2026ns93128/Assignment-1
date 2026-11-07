# Phase 0 Research: Smart Todo CLI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-07

The spec and constitution settle almost every product question. Each item below is a
technical decision needed to build those requirements with the Python 3.11 standard library
alone. None was left as NEEDS CLARIFICATION.

---

## R1. Command-line parsing

- **Decision**: Use `argparse` with `prog="todo"`, `allow_abbrev=False`, and one sub-parser per
  command (`add`, `list`, `update`, `delete`, `status`) with `required=True`. Add a small
  `ArgumentParser` subclass whose `error()` and `exit()` raise an internal exception rather than
  calling `sys.exit`. `main(argv) -> int` then always *returns* the exit code.
- **Rationale**: argparse is in the standard library, and its default error output already
  starts with `usage: todo` and uses exit code 2, which AC-52–AC-54 require. Raising instead of
  exiting lets tests call `main()` in-process, which coverage needs, without catching
  `SystemExit`. `allow_abbrev=False` stops `--tit` from silently meaning `--title`.
- **Value validation is not delegated to argparse**: priority, status, ID, title and tag are all
  declared as plain `str` options. argparse `choices=`/`type=` would fail with exit 2 and
  argparse's own wording, but the spec requires exit 1 and the exact messages in the Error
  Messages table. It would also break the FR-019 check order.
- **Alternatives considered**: `getopt` / hand-rolled parsing (more code and more bugs, and no
  free usage text); `click`/`typer` (third-party, forbidden).

## R2. Error-check order (FR-019)

- **Decision**: One fixed pipeline in `cli.main`:
  1. argparse (usage, exit 2)
  2. value validation in the fixed order ID → status → priority → title → tags (exit 1)
  3. `store.load(path)` (exit 3)
  4. task lookup (exit 1)
  5. operation rules: transition validity, nothing-to-update, `--tag` + `--clear-tags`
     (exit 1)
  6. `store.save()` for mutating commands only (exit 3 on failure)
- **Rationale**: This is the order fixed in the spec's clarification session. Steps 1–2 never
  touch the file system, so `todo list --status finished` reports the bad status even when the
  file is corrupt.
- **Alternatives considered**: Validating inside each service function. Rejected because it
  spreads the order across modules and makes it easy to break.

## R3. Error → exit-code mapping

- **Decision**: One exception hierarchy in `errors.py`: `TodoError(message, exit_code)` with
  subclasses `InputError` (1) and `DataFileError` (3). Usage errors carry 2. `main()` catches
  `TodoError` and writes `message + "\n"` to stderr. Anything else is caught at the top level as
  a last resort and becomes `Error: unexpected internal error.` with exit 1. `KeyboardInterrupt`
  becomes `Error: interrupted.` with exit 130. That exit code is defined here as allowed by
  Constitution VI (see contracts/cli.md).
- **Rationale**: The program never shows a traceback (FR-017), and every message comes from one
  table, so tests can compare exact strings.

## R4. ID, tag and title validation details

- **ID**: Accept only ASCII decimal digits (`^[0-9]+$`) whose integer value is ≥ 1. A leading
  zero is allowed (`01` → task 1). `int()` alone is too permissive: it accepts `+1`, ` 1`, `1_0`
  and non-ASCII digits such as `١`. `-1` reaches the parser as a positional argument (no option
  looks like a negative number) and is rejected as `invalid task ID '-1'`.
- **Tag**: `^[A-Za-z0-9_-]{1,20}$`, checked with an explicit ASCII class. Python's `\w` is
  Unicode-aware and would accept `é`. "Letters" in FR-004 is read as ASCII letters, so the
  case-insensitive comparison and lowercase storage are well-defined. Tags are normalised with
  `str.lower()`, which is exact for ASCII.
- **Title** (FR-002, clarification Q4):
  1. Reject if any code point has `unicodedata.category(ch) == "Cc"` (C0 controls, DEL, C1
     controls). This is checked on the raw value, before trimming.
  2. `str.strip()`.
  3. Require `1 <= len(title) <= 100`. `len` counts code points.
  All failures use the single title message.
- **Rationale**: These definitions turn the spec's English rules into checks that are exact and
  behave the same on every platform.

## R5. Data file format

- **Decision**: UTF-8 JSON object with exactly these keys:

  ```json
  {"version": 1, "next_id": 3, "tasks": [{"id": 1, "title": "…", "priority": "medium", "status": "todo", "tags": ["home"]}]}
  ```

  Full rules are in [contracts/data-file.md](./contracts/data-file.md).
- **Writing**: `json.dumps(obj, ensure_ascii=False, indent=2)` with fixed key order and tasks
  sorted by ascending `id`, followed by `"\n"`. The bytes are written as UTF-8 with `"\n"` line
  endings on every OS. Same store in, same bytes out (FR-016, AC-23).
- **Reading (strict, clarification Q2)**: read bytes → decode UTF-8 (strict) → `json.loads` with
  an `object_pairs_hook` that rejects duplicate keys → schema check. The schema check rejects
  unknown or missing keys, `bool` where an `int` is expected (`bool` is a subclass of `int`),
  duplicate IDs, `next_id <= max(id)`, `version != 1`, and any value that fails R4 or the
  priority/status sets. Stored tags must already be lowercase and unique. Stored titles must
  already be trimmed. Any failure, including `OSError` on read (permission denied, path is a
  directory), raises `DataFileError` with the corrupt-file message.
- **Missing file**: `FileNotFoundError` → an empty store (`next_id = 1`, no tasks) with nothing
  written (FR-013, AC-17).
- **Why `version`**: It costs nothing now and allows a later schema migration without guessing.
  A file with an unknown version is treated as corrupt and is never overwritten.
- **Alternatives considered**: Store a list of tasks only and derive `next_id` from the max ID.
  Rejected because it breaks FR-007 after deleting the highest task (AC-15, AC-16). Lenient
  parsing was rejected by clarification Q2.

## R6. Atomic save (Constitution V, FR-015, AC-21)

- **Decision**: Write to a deterministic sibling path `<target>.tmp` (same directory, so
  `os.replace` is a same-volume rename). Open it with mode `"wb"`, which overwrites any stale
  temp file left by an earlier crash. Write, `flush()`, `os.fsync()`, close, then
  `os.replace(tmp, target)`. On any failure before the replace, delete the temp file
  (best effort) and raise `DataFileError("Error: could not save data file 'PATH'; previous data
  was kept.")`.
- **Rationale**: `tempfile.NamedTemporaryFile` chooses random names. Constitution IV bans
  randomness, and a fixed name keeps every file-system effect deterministic. With a single user
  and no concurrent runs (spec Assumptions), the fixed name cannot collide in practice.
  `os.replace` is atomic on POSIX and Windows (NTFS) when source and target are on the same
  volume.
- **Testing AC-21**: monkeypatch `os.replace` (or the write step) to raise `OSError` or
  `KeyboardInterrupt` mid-save. Then assert the target bytes are unchanged, `todo list` still
  reads it, and no `.tmp` file remains.

## R7. Byte-exact output on Windows

- **Decision**: At the start of `main()`, call
  `sys.stdout.reconfigure(encoding="utf-8", newline="\n")` and the same for `sys.stderr`, when
  the stream supports `reconfigure`.
- **Rationale**: On Windows, text-mode streams turn `\n` into `\r\n`, and redirected output may
  use a legacy code page that cannot encode `é` or `✓`. Either one breaks "each line ends with a
  single newline" and AC-57. Pytest's capture streams also accept this call.

## R8. Program name and invocation

- **Decision**: The package is `smart_todo` under `src/`. Run it as `python -m smart_todo …`.
  The argparse `prog` is `todo`, so all user-visible text matches the spec. No build backend is
  declared, so the project is not installed as a package. `pyproject.toml` holds only
  `[project]` metadata (no dependencies) and tool configuration. The quickstart shows a one-line
  shell alias/function for typing `todo`.
- **Rationale**: Declaring `[build-system]` (setuptools/hatchling) to get a `todo` console script
  would add a build dependency outside the constitution's allowed list. Pytest's
  `pythonpath = ["src"]` makes the package importable for tests without installing it.
- **Alternatives considered**: An installable console script. Deferred because it needs a
  constitution amendment.

## R9. Testing approach (Constitution II, III)

- **Decision**:
  - Acceptance tests in `tests/acceptance/`, one module per user story, with one or more
    functions named `test_ACNN_<description>` for each AC-01…AC-58. They call
    `smart_todo.cli.main(argv)` in-process, with `monkeypatch.chdir(tmp_path)` and `capsys`, and
    compare stdout, stderr, the return code and the data-file bytes.
  - A small subprocess suite (`python -m smart_todo`) covers the real process boundary: AC-14
    (separate runs), AC-23 (byte-identical runs), AC-52–AC-54 (usage errors, no traceback).
  - Unit tests in `tests/unit/` cover validators, schema checks and sort order.
- **Rationale**: In-process tests are fast and count toward `pytest-cov` (≥ 90%). The subprocess
  tests prove the same behaviour across real program runs.
- **Gate commands**: `ruff check .`; `bandit -r src tests` (only MEDIUM/HIGH findings count; the
  LOW-severity B101 `assert` and B404/B603 `subprocess` findings in tests do not);
  `pytest --cov=smart_todo --cov-fail-under=90`.

## R10. Runtime version

- **Decision**: Target Python 3.11. Set `requires-python = ">=3.11"`, ruff
  `target-version = "py311"`, and use no 3.12+ syntax or APIs.
- **Observation**: This machine has Python 3.13.2, and no 3.11 interpreter was found
  (`py -3.11` fails). Code written for 3.11 runs on 3.13, but the constitution names 3.11 as the
  runtime. Gate results should be produced on a 3.11 interpreter (install via python.org or
  `py install 3.11`). Until then, they should be reported as run on 3.13.
