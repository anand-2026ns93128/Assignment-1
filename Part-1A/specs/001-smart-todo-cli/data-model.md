# Data Model: Smart Todo CLI

**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) | **Date**: 2026-11-07

## Enumerations

| Name | Values (exact, case-sensitive) | Order / rank |
|------|--------------------------------|--------------|
| Priority | `low`, `medium`, `high` | Sort rank: `high`=0, `medium`=1, `low`=2 |
| Status | `todo`, `in_progress`, `done` | — |

## Entity: Task

| Field | Type | Rules | Source |
|-------|------|-------|--------|
| `id` | int | ≥ 1; unique in the store; never reused; set at creation and never changed | FR-007 |
| `title` | str | No `Cc` control characters; trimmed; 1–100 code points | FR-002, R4 |
| `priority` | Priority | Defaults to `medium` | FR-001, FR-003 |
| `status` | Status | `todo` at creation; changed only by `status` | FR-001, FR-010 |
| `tags` | list[str] | Each tag matches `^[a-z0-9_-]{1,20}$` once stored (input is lowercased); no duplicates; first-seen order kept; may be empty | FR-004 |

Implemented as a frozen `@dataclass` (`models.Task`). Updates return a new instance
(`dataclasses.replace`), so a failed command cannot leave a half-changed task in memory.

### Tag normalisation (input → stored)

1. Check the raw tag against `^[A-Za-z0-9_-]{1,20}$`. The first failure raises the invalid-tag
   error, which shows the tag exactly as typed.
2. Lowercase it.
3. Drop it if already present. Keep first-seen order.

Example: `--tag home --tag HOME --tag errand` → `["home", "errand"]` (AC-11).

### Status state machine (FR-010)

```text
todo ──▶ in_progress ──▶ done
  └──────────────────────▲
```

| From \ To | todo | in_progress | done |
|-----------|------|-------------|------|
| todo | ✗ | ✓ | ✓ |
| in_progress | ✗ | ✗ | ✓ |
| done | ✗ | ✗ | ✗ |

Allowed set: `{(todo, in_progress), (in_progress, done), (todo, done)}`. Anything else, including
a move to the same status, raises
`Error: cannot change status of task N from OLD to NEW.` (AC-24–AC-31).
`update` never changes status and works on tasks of any status (AC-58).

## Entity: Task Store

| Field | Type | Rules |
|-------|------|-------|
| `next_id` | int | ≥ 1 and greater than every task `id`; incremented on each add; never decremented |
| `tasks` | list[Task] | Unique `id`s; kept and saved in ascending `id` order |

- **Empty store** (data file missing): `next_id = 1`, `tasks = []`.
- **Add**: the new task gets `id = next_id`, then `next_id += 1`. Deleting tasks never lowers
  `next_id`, so IDs are never reused (AC-15, AC-16).
- **Load / save**: see [contracts/data-file.md](./contracts/data-file.md). Every load validates
  every invariant above. Any violation means the file is corrupt (exit 3), and it is never
  written.

## Derived view: list output

1. Filter. Tag: the lowercased filter value is in `task.tags`. Status: equality. When both are
   given, both must match.
2. Sort by `(priority_rank, id)`.
3. Format each task as `f"{id} [{status}] ({priority}) {title}"` + `"".join(f" #{t}" for t in tags)`.
4. No tasks left → print `No tasks found.`

## Operations and what they change

| Operation | Reads store | Writes store | Changes |
|-----------|-------------|--------------|---------|
| add | yes | yes | append task, `next_id += 1` |
| list | yes | **never** | — |
| update | yes | yes | title / priority / tags of one task |
| delete | yes | yes | remove one task (`next_id` unchanged) |
| status | yes | yes | status of one task |

A mutating command writes only after every check has passed. A failed command writes nothing
(FR-018).
