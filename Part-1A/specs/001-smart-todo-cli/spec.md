# Feature Specification: Smart Todo CLI

**Feature Branch**: `main` (no feature branch created; spec directory `specs/001-smart-todo-cli`)

**Created**: 2026-11-05

**Status**: Approved (2026-11-07)

**Input**: User description: "Build a command-line Smart Todo app for a single user. Features:
(1) Add a task with a title (required, 1-100 chars), optional priority (low/medium/high, default
medium) and optional tags. (2) List tasks; filter by tag and/or status; sort by priority
(high > medium > low), ties broken by creation order. (3) Update a task's title, priority or tags;
delete a task by ID. (4) Status transitions: todo -> in_progress -> done, and todo -> done; any
other transition (e.g. done -> todo) is rejected with an error. (5) Tasks persist in a JSON file
between runs; IDs are unique integers that are never reused. Write each acceptance criterion as a
numbered, binary Given/When/Then statement (AC-01, AC-02, ...) with exact expected outputs, exit
codes and error messages, including invalid inputs (empty title, unknown ID, invalid priority,
invalid transition, corrupt JSON file)."

## Clarifications

### Session 2026-11-07

- Q: When one command breaks more than one rule, which error is reported first? → A: Fixed order: usage errors (exit 2) → argument values: ID format, status, priority, title, tags (exit 1) → load data file (exit 3) → task exists (exit 1) → transition / nothing-to-update / conflicting-option checks (exit 1).
- Q: Which data-file contents count as "not a valid task store" (exit 3)? → A: Strict validation: every field present with correct type and an allowed value (same title/priority/status/tag rules as input), IDs unique positive integers, next ID greater than every existing ID.
- Q: What happens when the `list --tag` filter value breaks the tag rules (e.g. `"a b"`)? → A: Rejected with the invalid-tag error, exit 1, stdout empty (new AC-55).
- Q: How are title characters counted, and which special characters are rejected? → A: Count Unicode characters (code points) after trimming; reject any title containing a control character (tab, CR, LF, other C0/C1 controls) (new AC-56, AC-57).
- Q: Can a task with status `done` still be edited with `todo update`? → A: Yes; `update` behaves the same for every status and never changes status (new AC-58).

## Change Log

- **2026-11-07 — Ctrl+C handling added to the spec (exit code 130).**
  - *What changed*: Added exit code `130` to *Exit Codes* and the message `Error: interrupted.` to
    *Error Messages*. FR-015 now separates a failed save (exit 3) from a user interruption (exit
    130), and FR-017 cites the new AC. AC-21 now states the exact stderr and exit code for a failed
    save. New AC-59 covers an interruption during a save. *Edge Cases*, SC-001 (now AC-01 to AC-59)
    and SC-004 were updated to match.
  - *Why*: Analysis finding I1 (`analysis-report.md`). The plan handled Ctrl+C with exit 130, but
    the spec's exit-code and message tables, which FR-017 makes exhaustive, had no such entry, and
    FR-015 implied exit 3 for any interrupted save. AC-21 also did not state its message or exit
    code, so it was not fully binary.
  - *Affected*: Tests `test_AC21_*` and the new `test_AC59_*` (tasks.md, User Story 2), plan
    research R3/R6, contracts/cli.md and contracts/data-file.md.
- **2026-11-07 — Status set to Approved.**
  - *What changed*: `Status: Draft` → `Approved (2026-11-07)`, after the clarification session and
    the analysis fixes.
  - *Why*: Constitution I requires an approved spec before any code is written (analysis finding
    C3).

## User Scenarios & Testing *(mandatory)*

### Conventions used by every acceptance criterion

- The program is invoked as `todo`. Commands are shown exactly as typed in a shell.
- "stdout" and "stderr" refer to the program's standard output and standard error. Each line of
  output ends with a single newline. Unless an AC says otherwise, a successful command writes
  nothing to stderr and a failed command writes nothing to stdout.
- Unless stated otherwise, the data file is the default `todo.json` in the current directory.
- "The data file is unchanged" means its bytes are identical before and after the command (or it
  still does not exist, if it did not exist before).
- A "fresh store" means no data file exists.
- Every AC is binary: it passes only if **all** stated outputs, exit code and side effects match
  exactly.
- Test naming (Constitution Principle III): the test(s) for `AC-NN` are named
  `test_ACNN_<description>` (e.g. AC-01 → `test_AC01_add_task_with_defaults`).

### User Story 1 - Add and list tasks (Priority: P1)

As the user, I add tasks with a title, an optional priority and optional tags, and I list them in
priority order so I can see what matters most first.

**Why this priority**: Adding and viewing tasks is the core value of a todo app; every other story
builds on it. Alone, it is a usable MVP.

**Independent Test**: From a fresh store, add several tasks with different priorities and tags,
then list them and compare the output line-for-line with the expected text.

**Acceptance Scenarios**:

- **AC-01**: **Given** a fresh store, **When** the user runs `todo add "Buy milk"`, **Then** stdout
  is `Added task 1: Buy milk`, exit code is 0, and `todo list` then prints exactly
  `1 [todo] (medium) Buy milk`.
- **AC-02**: **Given** a fresh store, **When** the user runs
  `todo add "Pay rent" --priority high --tag home --tag Bills`, **Then** stdout is
  `Added task 1: Pay rent`, exit code is 0, and `todo list` then prints exactly
  `1 [todo] (high) Pay rent #home #bills`.
- **AC-03**: **Given** a fresh store, **When** the user runs `todo add ""`, **Then** stderr is
  `Error: title must be 1-100 characters on a single line.`, exit code is 1, and the data file is
  unchanged.
- **AC-04**: **Given** a fresh store, **When** the user runs `todo add "   "` (spaces only),
  **Then** stderr is `Error: title must be 1-100 characters on a single line.`, exit code is 1,
  and the data file is unchanged.
- **AC-05**: **Given** a fresh store, **When** the user runs `todo add "  Buy milk  "`, **Then**
  stdout is `Added task 1: Buy milk` (leading/trailing whitespace removed) and exit code is 0.
- **AC-06**: **Given** a fresh store, **When** the user adds a task whose title is exactly 100
  characters (`"a"` repeated 100 times), **Then** stdout is `Added task 1: ` followed by those
  100 characters, and exit code is 0.
- **AC-07**: **Given** a fresh store, **When** the user adds a task whose title is 101 characters,
  **Then** stderr is `Error: title must be 1-100 characters on a single line.`, exit code is 1,
  and the data file is unchanged.
- **AC-08**: **Given** a fresh store, **When** the user adds a task whose title contains a line
  break (e.g. `"Line1<newline>Line2"`), **Then** stderr is
  `Error: title must be 1-100 characters on a single line.`, exit code is 1, and the data file is
  unchanged.
- **AC-56**: **Given** a fresh store, **When** the user adds a task whose title contains a tab
  character (e.g. `"Buy<tab>milk"`), **Then** stderr is
  `Error: title must be 1-100 characters on a single line.`, exit code is 1, and the data file is
  unchanged.
- **AC-57**: **Given** a fresh store, **When** the user adds a task whose title is `"é"` repeated
  100 times (100 characters, 200 UTF-8 bytes), **Then** stdout is `Added task 1: ` followed by
  those 100 characters, and exit code is 0.
- **AC-09**: **Given** a fresh store, **When** the user runs
  `todo add "Buy milk" --priority urgent`, **Then** stderr is
  `Error: invalid priority 'urgent' (expected: low, medium, high).`, exit code is 1, and the data
  file is unchanged.
- **AC-10**: **Given** a fresh store, **When** the user runs `todo add "Buy milk" --tag "a b"`,
  **Then** stderr is
  `Error: invalid tag 'a b' (tags must be 1-20 characters: letters, digits, '-' or '_').`, exit
  code is 1, and the data file is unchanged.
- **AC-11**: **Given** a fresh store, **When** the user runs
  `todo add "Buy milk" --tag home --tag HOME --tag errand`, **Then** exit code is 0 and
  `todo list` prints exactly `1 [todo] (medium) Buy milk #home #errand`.
- **AC-12**: **Given** tasks added in this order: `todo add A --priority low`,
  `todo add B --priority high`, `todo add C`, `todo add D --priority high`, **When** the user runs
  `todo list`, **Then** stdout is exactly the four lines below and exit code is 0:
  ```text
  2 [todo] (high) B
  4 [todo] (high) D
  3 [todo] (medium) C
  1 [todo] (low) A
  ```
- **AC-13**: **Given** a store containing no tasks, **When** the user runs `todo list`, **Then**
  stdout is `No tasks found.` and exit code is 0.

---

### User Story 2 - Reliable persistence (Priority: P1)

As the user, my tasks are still there the next time I run the program, task IDs never change
meaning, and a damaged data file is reported rather than silently overwritten.

**Why this priority**: A todo list that loses data or reuses IDs is not trustworthy; this is
required for Story 1 to be useful beyond a single run.

**Independent Test**: Add tasks, run the program again in a new process and list them; delete and
add to observe IDs; corrupt the data file and confirm every command refuses to touch it.

**Acceptance Scenarios**:

- **AC-14**: **Given** the user ran `todo add "Buy milk"` in one program run, **When** the user
  runs `todo list` in a separate, later program run, **Then** stdout is
  `1 [todo] (medium) Buy milk` and exit code is 0.
- **AC-15**: **Given** tasks 1, 2 and 3 exist and task 3 has been deleted, **When** the user runs
  `todo add "New"`, **Then** stdout is `Added task 4: New` and exit code is 0.
- **AC-16**: **Given** tasks 1 and 2 existed and both have been deleted, **When** the user runs
  `todo add "Again"`, **Then** stdout is `Added task 3: Again` and exit code is 0.
- **AC-17**: **Given** a fresh store, **When** the user runs `todo list`, **Then** stdout is
  `No tasks found.`, exit code is 0, and no data file is created.
- **AC-18**: **Given** the data file `todo.json` contains `{not json`, **When** the user runs
  `todo list`, **Then** stderr is
  `Error: data file 'todo.json' is corrupt or unreadable; it was not modified.`, exit code is 3,
  stdout is empty, and the data file is unchanged.
- **AC-19**: **Given** the data file `todo.json` contains `{not json`, **When** the user runs
  `todo add "Buy milk"`, **Then** stderr is
  `Error: data file 'todo.json' is corrupt or unreadable; it was not modified.`, exit code is 3,
  and the data file is unchanged.
- **AC-20**: **Given** the data file `todo.json` is valid JSON but not a task store (contents
  `[]`), **When** the user runs `todo list`, **Then** stderr is
  `Error: data file 'todo.json' is corrupt or unreadable; it was not modified.`, exit code is 3,
  and the data file is unchanged.
- **AC-21**: **Given** a store containing task 1, **When** saving the result of
  `todo add "Second"` fails before it completes (e.g. the file system refuses to replace the data
  file), **Then** stderr is `Error: could not save data file 'todo.json'; previous data was kept.`,
  exit code is 3, stdout is empty, and the data file still contains exactly its previous contents
  (task 1 only) and is readable by `todo list`.
- **AC-59**: **Given** a store containing task 1, **When** the user interrupts (Ctrl+C)
  `todo add "Second"` while its result is being saved, **Then** stderr is `Error: interrupted.`,
  exit code is 130, stdout is empty, and the data file still contains exactly its previous
  contents (task 1 only).
- **AC-22**: **Given** a fresh store, **When** the user runs
  `todo --file work.json add "Report"` and then `todo --file work.json list`, **Then** the second
  command prints `1 [todo] (medium) Report`, exit codes are 0, and no `todo.json` is created.
- **AC-23**: **Given** the same data file contents and the same command, **When** the command is
  run twice on identical copies of that data file, **Then** both runs produce byte-identical
  stdout, stderr, exit code and resulting data file.

---

### User Story 3 - Track progress with status transitions (Priority: P2)

As the user, I move tasks from `todo` to `in_progress` to `done` (or straight from `todo` to
`done`), and the program stops me from making invalid moves such as reopening a finished task.

**Why this priority**: Status tracking turns a list into a progress tool, but adding/listing is
still valuable without it.

**Independent Test**: Create tasks, apply each valid transition and each invalid one, and check
outputs and the resulting `todo list` status.

**Acceptance Scenarios**:

- **AC-24**: **Given** task 1 has status `todo`, **When** the user runs
  `todo status 1 in_progress`, **Then** stdout is `Task 1: todo -> in_progress`, exit code is 0,
  and `todo list` shows `1 [in_progress] (medium) Buy milk` (for a task titled "Buy milk").
- **AC-25**: **Given** task 1 has status `in_progress`, **When** the user runs
  `todo status 1 done`, **Then** stdout is `Task 1: in_progress -> done` and exit code is 0.
- **AC-26**: **Given** task 1 has status `todo`, **When** the user runs `todo status 1 done`,
  **Then** stdout is `Task 1: todo -> done` and exit code is 0.
- **AC-27**: **Given** task 1 has status `done`, **When** the user runs `todo status 1 todo`,
  **Then** stderr is `Error: cannot change status of task 1 from done to todo.`, exit code is 1,
  and the data file is unchanged.
- **AC-28**: **Given** task 1 has status `in_progress`, **When** the user runs
  `todo status 1 todo`, **Then** stderr is
  `Error: cannot change status of task 1 from in_progress to todo.`, exit code is 1, and the data
  file is unchanged.
- **AC-29**: **Given** task 1 has status `done`, **When** the user runs
  `todo status 1 in_progress`, **Then** stderr is
  `Error: cannot change status of task 1 from done to in_progress.`, exit code is 1, and the data
  file is unchanged.
- **AC-30**: **Given** task 1 has status `todo`, **When** the user runs `todo status 1 todo`,
  **Then** stderr is `Error: cannot change status of task 1 from todo to todo.`, exit code is 1,
  and the data file is unchanged.
- **AC-31**: **Given** task 1 exists, **When** the user runs `todo status 1 finished`, **Then**
  stderr is `Error: invalid status 'finished' (expected: todo, in_progress, done).`, exit code is
  1, and the data file is unchanged.
- **AC-32**: **Given** no task with ID 99 exists, **When** the user runs `todo status 99 done`,
  **Then** stderr is `Error: task 99 not found.`, exit code is 1, and the data file is unchanged.

---

### User Story 4 - Update and delete tasks (Priority: P3)

As the user, I correct a task's title, change its priority, replace or clear its tags, and delete
tasks I no longer need.

**Why this priority**: Editing is a convenience; users can work around it by deleting and
re-adding, so it ranks below creation and progress tracking.

**Independent Test**: Create a task, apply each kind of update and a delete, and verify via
`todo list`; then try each invalid input.

**Acceptance Scenarios**:

- **AC-33**: **Given** task 1 "Buy milk" exists, **When** the user runs
  `todo update 1 --title "Buy oat milk"`, **Then** stdout is `Updated task 1.`, exit code is 0,
  and `todo list` shows `1 [todo] (medium) Buy oat milk`.
- **AC-34**: **Given** task 1 "Buy milk" (medium) exists, **When** the user runs
  `todo update 1 --priority low`, **Then** stdout is `Updated task 1.`, exit code is 0, and
  `todo list` shows `1 [todo] (low) Buy milk`.
- **AC-35**: **Given** task 1 "Buy milk" with tag `home`, **When** the user runs
  `todo update 1 --tag work --tag urgent`, **Then** stdout is `Updated task 1.`, exit code is 0,
  and `todo list` shows `1 [todo] (medium) Buy milk #work #urgent`.
- **AC-36**: **Given** task 1 "Buy milk" with tag `home`, **When** the user runs
  `todo update 1 --clear-tags`, **Then** stdout is `Updated task 1.`, exit code is 0, and
  `todo list` shows `1 [todo] (medium) Buy milk`.
- **AC-58**: **Given** task 1 "Buy milk" has status `done`, **When** the user runs
  `todo update 1 --title "Buy oat milk" --priority high`, **Then** stdout is `Updated task 1.`,
  exit code is 0, and `todo list` shows `1 [done] (high) Buy oat milk`.
- **AC-37**: **Given** task 1 exists, **When** the user runs `todo update 1` with no options,
  **Then** stderr is
  `Error: nothing to update (use --title, --priority, --tag or --clear-tags).`, exit code is 1,
  and the data file is unchanged.
- **AC-38**: **Given** task 1 exists, **When** the user runs
  `todo update 1 --tag work --clear-tags`, **Then** stderr is
  `Error: --tag and --clear-tags cannot be used together.`, exit code is 1, and the data file is
  unchanged.
- **AC-39**: **Given** task 1 exists, **When** the user runs `todo update 1 --title ""`, **Then**
  stderr is `Error: title must be 1-100 characters on a single line.`, exit code is 1, and the
  data file is unchanged.
- **AC-40**: **Given** task 1 exists, **When** the user runs `todo update 1 --priority urgent`,
  **Then** stderr is `Error: invalid priority 'urgent' (expected: low, medium, high).`, exit code
  is 1, and the data file is unchanged.
- **AC-41**: **Given** no task with ID 99 exists, **When** the user runs
  `todo update 99 --title "X"`, **Then** stderr is `Error: task 99 not found.`, exit code is 1,
  and the data file is unchanged.
- **AC-42**: **Given** tasks 1 "A" and 2 "B" exist, **When** the user runs `todo delete 2`,
  **Then** stdout is `Deleted task 2.`, exit code is 0, and `todo list` prints only
  `1 [todo] (medium) A`.
- **AC-43**: **Given** no task with ID 99 exists, **When** the user runs `todo delete 99`,
  **Then** stderr is `Error: task 99 not found.`, exit code is 1, and the data file is unchanged.
- **AC-44**: **Given** any store, **When** the user runs `todo delete abc`, **Then** stderr is
  `Error: invalid task ID 'abc'.`, exit code is 1, and the data file is unchanged.
- **AC-45**: **Given** any store, **When** the user runs `todo delete 0`, **Then** stderr is
  `Error: invalid task ID '0'.`, exit code is 1, and the data file is unchanged.

---

### User Story 5 - Filter the list (Priority: P3)

As the user, I narrow the list to one tag and/or one status so I can focus on a context (e.g.
`#work`) or see only what's in progress.

**Why this priority**: Filtering adds focus once the list grows, but the full sorted list already
delivers the core value.

**Independent Test**: Seed tasks with varied tags and statuses, run each filter combination, and
compare output line-for-line.

For AC-46 to AC-51 and AC-55 the store contains, in creation order:
`1 "A" (high, tags: work, status: todo)`, `2 "B" (low, tags: home, status: in_progress)`,
`3 "C" (medium, tags: work home, status: done)`, `4 "D" (high, no tags, status: in_progress)`.

**Acceptance Scenarios**:

- **AC-46**: **When** the user runs `todo list --tag work`, **Then** stdout is exactly the two
  lines below and exit code is 0:
  ```text
  1 [todo] (high) A #work
  3 [done] (medium) C #work #home
  ```
- **AC-47**: **When** the user runs `todo list --status in_progress`, **Then** stdout is exactly
  the two lines below and exit code is 0:
  ```text
  4 [in_progress] (high) D
  2 [in_progress] (low) B #home
  ```
- **AC-48**: **When** the user runs `todo list --tag home --status done`, **Then** stdout is
  exactly `3 [done] (medium) C #work #home` and exit code is 0.
- **AC-49**: **When** the user runs `todo list --tag WORK`, **Then** stdout is identical to the
  output of AC-46 and exit code is 0.
- **AC-50**: **When** the user runs `todo list --tag garden`, **Then** stdout is
  `No tasks found.` and exit code is 0.
- **AC-51**: **When** the user runs `todo list --status finished`, **Then** stderr is
  `Error: invalid status 'finished' (expected: todo, in_progress, done).`, stdout is empty, and
  exit code is 1.
- **AC-55**: **When** the user runs `todo list --tag "a b"`, **Then** stderr is
  `Error: invalid tag 'a b' (tags must be 1-20 characters: letters, digits, '-' or '_').`, stdout
  is empty, exit code is 1, and the data file is unchanged.

---

### User Story 6 - Clear feedback on command misuse (Priority: P3)

As the user, when I type a command wrong I get a short usage message rather than a crash.

**Why this priority**: Protects every other story's usability; small in scope.

**Independent Test**: Run malformed commands and check exit code and stderr; confirm no Python
traceback ever appears.

**Acceptance Scenarios**:

- **AC-52**: **Given** any store, **When** the user runs `todo frobnicate`, **Then** exit code is
  2, stdout is empty, stderr's first line starts with `usage: todo`, stderr does not contain
  `Traceback`, and the data file is unchanged.
- **AC-53**: **Given** any store, **When** the user runs `todo` with no arguments, **Then** exit
  code is 2, stderr's first line starts with `usage: todo`, and stderr does not contain
  `Traceback`.
- **AC-54**: **Given** any store, **When** the user runs `todo add` with no title, **Then** exit
  code is 2, stderr's first line starts with `usage: todo`, stderr does not contain `Traceback`,
  and the data file is unchanged.

### Edge Cases

- Title of exactly 1 and exactly 100 characters (after trimming) is accepted; 0 or 101 is
  rejected (AC-03, AC-06, AC-07).
- Title with surrounding whitespace is trimmed before length validation (AC-04, AC-05).
- Title length counts characters, not bytes; any control character (including tab or a trailing
  newline) makes the title invalid (AC-08, AC-56, AC-57).
- Duplicate tags differing only in case are stored once, in first-seen order (AC-11).
- Deleting the highest-numbered task, or all tasks, does not cause its ID to be reused
  (AC-15, AC-16).
- Read-only commands on a missing data file do not create one (AC-17).
- A data file that is not JSON, or is JSON of the wrong shape, is never overwritten (AC-18–AC-20).
- A hand-edited data file with valid JSON but invalid content (e.g. priority `urgent`, duplicate
  IDs, or a next ID not greater than an existing ID) is treated as corrupt: exit 3, file
  unchanged (FR-014).
- A failed or interrupted save leaves the previous data intact (AC-21, AC-59).
- Changing a task to the status it already has is an invalid transition (AC-30).
- A `done` task can still have its title, priority or tags edited; it stays `done` (AC-58).
- IDs that are not positive integers are rejected (AC-44, AC-45).
- A filter that matches nothing prints `No tasks found.` with exit code 0 (AC-50).
- A tag filter value that is not a valid tag is an error, not an empty result (AC-55).
- Several errors at once: the first in the FR-019 order wins, e.g. `todo status 99 finished`
  reports the invalid status, and `todo list --status finished` reports the invalid status even
  when the data file is corrupt.

## Requirements *(mandatory)*

### Command Interface

| Command | Purpose | Success stdout |
|---------|---------|----------------|
| `todo [--file PATH] add TITLE [--priority P] [--tag TAG]...` | Create a task | `Added task <id>: <title>` |
| `todo [--file PATH] list [--tag TAG] [--status S]` | List tasks | one line per task, or `No tasks found.` |
| `todo [--file PATH] update ID [--title T] [--priority P] [--tag TAG]... [--clear-tags]` | Edit a task | `Updated task <id>.` |
| `todo [--file PATH] delete ID` | Remove a task | `Deleted task <id>.` |
| `todo [--file PATH] status ID S` | Change status | `Task <id>: <old> -> <new>` |

List line format: `<id> [<status>] (<priority>) <title>` followed by ` #<tag>` for each tag, in
stored order.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid input: bad title, priority, tag, status, ID, unknown ID, invalid transition, nothing to update, conflicting options |
| 2 | Command-line usage error: unknown command, missing required argument, unknown option |
| 3 | Data file problem: corrupt, unreadable or could not be saved |
| 130 | Interrupted by the user (Ctrl+C) |

### Error Messages

All error messages are written to stderr as a single line beginning with `Error: `, except
usage errors (exit code 2), which begin with a `usage: todo` line.

| Situation | Exact message |
|-----------|---------------|
| Invalid title | `Error: title must be 1-100 characters on a single line.` |
| Invalid priority `X` | `Error: invalid priority 'X' (expected: low, medium, high).` |
| Invalid tag `X` | `Error: invalid tag 'X' (tags must be 1-20 characters: letters, digits, '-' or '_').` |
| Invalid status `X` | `Error: invalid status 'X' (expected: todo, in_progress, done).` |
| Invalid ID `X` | `Error: invalid task ID 'X'.` |
| Unknown ID `N` | `Error: task N not found.` |
| Invalid transition | `Error: cannot change status of task N from OLD to NEW.` |
| Update with no changes | `Error: nothing to update (use --title, --priority, --tag or --clear-tags).` |
| `--tag` with `--clear-tags` | `Error: --tag and --clear-tags cannot be used together.` |
| Corrupt/unreadable data file `PATH` | `Error: data file 'PATH' is corrupt or unreadable; it was not modified.` |
| Data file could not be saved `PATH` | `Error: could not save data file 'PATH'; previous data was kept.` |
| Interrupted by the user (Ctrl+C) | `Error: interrupted.` (exit code 130) |
| Any other unexpected failure | `Error: unexpected internal error.` (exit code 1) |

### Functional Requirements

- **FR-001**: Users MUST be able to add a task with a title; the new task has status `todo`,
  priority `medium` unless given, and the tags given (none by default). (AC-01, AC-02)
- **FR-002**: The system MUST reject a title containing any control character (Unicode categories
  Cc, e.g. tab, CR, LF) anywhere in the value as given; otherwise it MUST trim leading/trailing
  whitespace and accept only titles of 1-100 characters, counted as Unicode code points.
  (AC-03–AC-08, AC-39, AC-56, AC-57)
- **FR-003**: The system MUST accept only priorities `low`, `medium`, `high` (case-sensitive).
  (AC-09, AC-40)
- **FR-004**: Tags MUST be 1-20 characters of letters, digits, `-` or `_`; they are stored in
  lowercase, duplicates (after lowercasing) removed, keeping first-seen order. The same character
  rules apply to `list --tag` filter values. (AC-02, AC-10, AC-11, AC-55)
- **FR-005**: `list` MUST show tasks sorted by priority (high, then medium, then low), ties broken
  by creation order (ascending ID), using the list line format; with no matching tasks it prints
  `No tasks found.` (AC-12, AC-13, AC-50)
- **FR-006**: `list` MUST support an optional tag filter (case-insensitive match) and an optional
  status filter; when both are given, a task must match both. A tag filter value MUST satisfy the
  tag rules of FR-004, otherwise the invalid-tag error is reported with exit code 1.
  (AC-46–AC-51, AC-55)
- **FR-007**: Task IDs MUST be positive integers assigned in increasing order starting at 1 and
  MUST never be reused, even after deletion of the highest or all tasks. (AC-15, AC-16)
- **FR-008**: Users MUST be able to update a task's title, priority and tags; `--tag` replaces the
  whole tag set; `--clear-tags` removes all tags; at least one change is required; `--tag` and
  `--clear-tags` are mutually exclusive. Update is allowed for a task of any status and never
  changes its status. (AC-33–AC-41, AC-58)
- **FR-009**: Users MUST be able to delete a task by ID. (AC-42, AC-43)
- **FR-010**: The only allowed status transitions are `todo → in_progress`,
  `in_progress → done` and `todo → done`; every other transition, including to the same status,
  MUST be rejected with no change. (AC-24–AC-31)
- **FR-011**: Any command referring to a non-existent ID MUST fail with `Error: task N not found.`
  and exit code 1; an ID that is not a positive integer MUST fail with
  `Error: invalid task ID 'X'.` and exit code 1. (AC-32, AC-41, AC-43–AC-45)
- **FR-012**: Tasks MUST persist in a JSON data file between runs; the default file is `todo.json`
  in the current directory, overridable with `--file PATH`. (AC-14, AC-22)
- **FR-013**: Commands that do not change data MUST NOT create or modify the data file. (AC-17)
- **FR-014**: A data file that is unreadable, not valid JSON, or not a valid task store MUST cause
  every command whose arguments pass validation (see FR-019) to fail with exit code 3 and the corrupt-file message, leaving the file
  unchanged. (AC-18–AC-20) A data file is a valid task store only if: it holds the next ID to
  assign (a positive integer) and a list of tasks; every task has all Task attributes with the
  correct type; every title, priority, status and tag satisfies the same rules as user input
  (FR-002–FR-004, FR-010 status values), with tags already lowercase and unique; task IDs are
  unique positive integers; and the next ID is greater than every existing task ID.
- **FR-015**: Saving MUST be all-or-nothing: an interrupted or failed save leaves the previous data
  file contents intact. A failed save reports the save error with exit code 3. An interruption by
  the user (Ctrl+C) at any point, including during a save, reports `Error: interrupted.` with exit
  code 130. (AC-21, AC-59)
- **FR-016**: Output MUST be deterministic: identical input and identical data file always yield
  identical output, exit code and resulting data file; the program uses no randomness and no
  network. (AC-23)
- **FR-017**: Every failure MUST produce the exact message and exit code defined above, and the
  program MUST never display a traceback. (AC-52–AC-54, AC-59, all error ACs)
- **FR-018**: Any failed command MUST leave the data file unchanged. (all error ACs)
- **FR-019**: When a command violates more than one rule, only the first failing check is
  reported, in this order: (1) command-line usage (exit 2); (2) argument values — ID format,
  status, priority, title, tags (exit 1); (3) loading the data file (exit 3); (4) task exists
  (exit 1); (5) transition validity, nothing-to-update and `--tag`/`--clear-tags` conflict
  (exit 1). Steps 1-2 never read the data file.

### Key Entities

- **Task**: A single todo item. Attributes: ID (positive integer, unique, never reused), title
  (1-100 Unicode characters, no control characters), priority (`low` | `medium` | `high`), status
  (`todo` | `in_progress` | `done`), tags (ordered list of unique lowercase tags). Creation order
  is the ascending order of IDs.
- **Task Store**: The persisted collection for the single user: all current tasks plus the next ID
  to assign (so deleted IDs are never reused). Stored as one JSON data file. Invariants checked on
  every load (FR-014): IDs unique, next ID > every task ID, every attribute valid per the Task rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of acceptance criteria AC-01 to AC-59 pass as automated checks.
- **SC-002**: A new user can add a task and see it in the list using two commands, with no
  configuration, in under 1 minute.
- **SC-003**: Every command completes in under 1 second for a store of up to 1,000 tasks on a
  typical laptop.
- **SC-004**: 0 instances of lost or partially written data across all interruption and
  corrupt-file scenarios (AC-18–AC-21, AC-59).
- **SC-005**: 100% of invalid inputs produce a one-line, human-readable error and a non-zero exit
  code; 0 tracebacks are shown to the user.
- **SC-006**: Running the same command on the same data file twice yields byte-identical results
  in 100% of trials.

## Assumptions

- Single user, single machine; no concurrent runs against the same data file are supported.
- No due dates, timestamps, search or undo in this feature; creation order is represented by ID.
- `list` shows tasks of all statuses (including `done`) unless filtered.
- Only one `--tag` filter and one `--status` filter are supported per `list` invocation.
- Status changes happen only through `todo status`; `update` cannot change status.
- Priority, status and command names are case-sensitive; tags are case-insensitive (stored
  lowercase).
- Error messages show the data file path exactly as the user gave it (default `todo.json`).
- Output is plain text with no colours, so it is identical in terminals and when redirected.
- The user-facing name of the program is `todo`.
