# Contract: Data File (`todo.json`)

**Spec**: FR-012–FR-015, clarification Q2 | **Model**: [../data-model.md](../data-model.md)

## Canonical form (what the program writes)

```json
{
  "version": 1,
  "next_id": 4,
  "tasks": [
    {
      "id": 1,
      "title": "Pay rent",
      "priority": "high",
      "status": "todo",
      "tags": [
        "home",
        "bills"
      ]
    }
  ]
}
```

- UTF-8 without BOM. Non-ASCII characters are written as-is (`ensure_ascii=False`).
- 2-space indentation, LF line endings, one trailing `\n`.
- Top-level key order: `version`, `next_id`, `tasks`. Task key order: `id`, `title`, `priority`,
  `status`, `tags`. Tasks are in ascending `id` order.
- The same store always serialises to the same bytes.

## Validity rules (checked on every load)

A file is a **valid task store** only if **all** of these hold. Any violation raises
`Error: data file 'PATH' is corrupt or unreadable; it was not modified.` with exit 3, and the
file is not touched.

1. The bytes can be read, and they decode as strict UTF-8.
2. They parse as JSON, and no object contains duplicate keys.
3. The top level is an object with exactly the keys `version`, `next_id`, `tasks`.
4. `version` is the integer `1`.
5. `next_id` is an integer (not a boolean) and ≥ 1.
6. `tasks` is an array. Each element is an object with exactly the keys `id`, `title`,
   `priority`, `status`, `tags`.
7. `id` is an integer (not a boolean) and ≥ 1. All `id`s are unique. `next_id` > every `id`.
8. `title` is a string with no `Cc` characters, equal to its own `strip()`, length 1–100.
9. `priority` ∈ {`low`, `medium`, `high`}. `status` ∈ {`todo`, `in_progress`, `done`}.
10. `tags` is an array of strings, each matching `^[a-z0-9_-]{1,20}$`, with no duplicates.

Task order in the file is not checked on load. It is normalised to ascending `id` on the next
save.

## Lifecycle

| Situation | Behaviour |
|-----------|-----------|
| File missing | Empty store (`next_id` 1). Read-only commands create nothing (AC-17). |
| File valid | Loaded. Mutating commands rewrite it atomically. |
| File invalid / unreadable | Exit 3, file unchanged (AC-18–AC-20). |
| Save fails | Target unchanged; temp file `PATH.tmp` removed if possible; exit 3 with `Error: could not save data file 'PATH'; previous data was kept.` (AC-21) |
| Save interrupted (Ctrl+C) | Target unchanged; temp file `PATH.tmp` removed if possible; exit 130 with `Error: interrupted.` (AC-59) |

## Atomic write procedure

1. Serialise to bytes in memory.
2. Open `PATH.tmp` (same directory) with mode `wb`. Write the bytes, flush, `os.fsync`, close.
3. `os.replace(PATH.tmp, PATH)`.
4. If any of steps 2–3 fails, delete `PATH.tmp` (ignore errors) and report the save error.
