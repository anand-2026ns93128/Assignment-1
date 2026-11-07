# Contract: `todo` Command-Line Interface

**Spec**: [../spec.md](../spec.md) — this contract restates the spec's interface in one place and
adds the plan-level details it leaves open. Where they differ, the spec wins.

## Invocation

```text
python -m smart_todo [--file PATH] <command> [args]      # program name shown to users: todo
```

Global option `--file PATH` (default `todo.json`, relative to the current directory) must come
**before** the command. The path appears in messages exactly as typed.

## Commands

| Command | Arguments / options | Success stdout (exit 0) |
|---------|---------------------|-------------------------|
| `add TITLE` | `--priority P` (once; last wins), `--tag TAG` (repeatable) | `Added task <id>: <title>` |
| `list` | `--tag TAG` (once), `--status S` (once) | one line per task, or `No tasks found.` |
| `update ID` | `--title T`, `--priority P`, `--tag TAG`…, `--clear-tags` | `Updated task <id>.` |
| `delete ID` | — | `Deleted task <id>.` |
| `status ID S` | — | `Task <id>: <old> -> <new>` |

- A title that starts with `-` must follow `--` (e.g. `todo add -- "-x"`). This is standard
  argparse behaviour.
- If a single-value option is repeated, the last value is used (argparse default).
- `<title>` in the `add` message is the stored title, after trimming.
- List line: `<id> [<status>] (<priority>) <title>` followed by ` #<tag>` for each tag, in
  stored order. Sorted by priority (high, medium, low), then ascending ID.

## Streams and encoding

- stdout carries only success output. stderr carries only error output. Each line ends with
  exactly `\n` (LF) on every OS, encoded as UTF-8.
- No colour or other terminal control codes are used.

## Exit codes

| Code | Meaning | Defined in |
|------|---------|-----------|
| 0 | Success | spec |
| 1 | Invalid input or rule violation; also `Error: unexpected internal error.` | spec |
| 2 | Usage error (argparse): stderr starts with `usage: todo` | spec |
| 3 | Data file corrupt / unreadable / could not be saved | spec |
| 130 | Interrupted by Ctrl+C: stderr `Error: interrupted.`, data file unchanged | **plan** (R3) |

## Error messages

Exactly as in the spec's *Error Messages* table. Each is one line on stderr, followed by `\n`.

## Check order (FR-019)

```text
1 usage (2) → 2 values: ID → status → priority → title → tags (1) → 3 load file (3)
  → 4 task exists (1) → 5 transition / nothing-to-update / --tag+--clear-tags (1) → 6 save (3)
```

Only the first failure is reported. Steps 1–2 never touch the file system.

| Example | Reported |
|---------|----------|
| `todo status 99 finished` | `Error: invalid status 'finished' (expected: todo, in_progress, done).` (1) |
| `todo status abc finished` | `Error: invalid task ID 'abc'.` (1) |
| `todo list --status finished` with corrupt `todo.json` | invalid status (1) |
| `todo add "" --priority urgent` | invalid priority (1) |
| `todo update 99` (no options) | `Error: task 99 not found.` (1) |
| `todo update 1 --tag "a b" --clear-tags` | invalid tag (1) |

## Value grammar

| Value | Accepted | Notes |
|-------|----------|-------|
| ID | `^[0-9]+$` (ASCII) with value ≥ 1 | `01` = 1; `0`, `-1`, `+1`, `abc`, `١` rejected |
| Priority | `low` \| `medium` \| `high` | case-sensitive |
| Status | `todo` \| `in_progress` \| `done` | case-sensitive |
| Tag | `^[A-Za-z0-9_-]{1,20}$` | stored and matched lowercase |
| Title | no `Cc` control chars (raw); trimmed length 1–100 code points | |
