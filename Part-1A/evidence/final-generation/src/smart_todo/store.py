"""Task store persistence (contracts/data-file.md).

Tasks T013 (canonical serialisation), T032-T033 (strict validation on every load) and
T034 (atomic save). A file that breaks any validity rule is reported as corrupt and is
never written (FR-014); a save either fully replaces the file or leaves it untouched
(FR-015).
"""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass

from smart_todo import errors, models
from smart_todo.models import Task

FORMAT_VERSION = 1
TOP_LEVEL_KEYS = frozenset({"version", "next_id", "tasks"})
TASK_KEYS = frozenset({"id", "title", "priority", "status", "tags"})


@dataclass(frozen=True)
class Store:
    next_id: int
    tasks: tuple[Task, ...]


EMPTY = Store(1, ())


# --------------------------------------------------------------------------- loading


def load(path: str) -> Store:
    """Load and validate the store; a missing file is an empty store and is not created."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return EMPTY
    except OSError as exc:  # unreadable, or the path is a directory (rule 1)
        raise errors.corrupt_file(path) from exc
    try:
        return _parse(raw)
    except Exception as exc:  # any rule violation, however it surfaces
        raise errors.corrupt_file(path) from exc


def _parse(raw: bytes) -> Store:
    text = raw.decode("utf-8")  # rule 1 (strict; a BOM then fails JSON parsing, rule 2)
    data = json.loads(text, object_pairs_hook=_no_duplicate_keys)  # rule 2
    _require(isinstance(data, dict) and set(data) == TOP_LEVEL_KEYS)  # rule 3
    _require(_is_int(data["version"]) and data["version"] == FORMAT_VERSION)  # rule 4
    next_id = data["next_id"]
    _require(_is_int(next_id) and next_id >= 1)  # rule 5
    _require(isinstance(data["tasks"], list))  # rule 6
    tasks = [_parse_task(item) for item in data["tasks"]]
    ids = [t.id for t in tasks]
    _require(len(ids) == len(set(ids)))  # rule 7: unique ids
    _require(all(next_id > task_id for task_id in ids))  # rule 7: next_id > every id
    return Store(next_id, tuple(sorted(tasks, key=lambda t: t.id)))


def _parse_task(item: object) -> Task:
    _require(isinstance(item, dict) and set(item) == TASK_KEYS)  # rule 6
    task_id = item["id"]
    _require(_is_int(task_id) and task_id >= 1)  # rule 7
    title = item["title"]
    _require(isinstance(title, str) and models.validate_title(title) == title)  # rule 8
    _require(item["priority"] in models.PRIORITIES)  # rule 9
    _require(item["status"] in models.STATUSES)  # rule 9
    tags = item["tags"]
    _require(isinstance(tags, list) and all(isinstance(t, str) for t in tags))  # rule 10
    _require(models.normalize_tags(tags) == tuple(tags))  # rule 10: valid, lowercase, unique
    return Task(task_id, title, item["priority"], item["status"], tuple(tags))


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key in JSON object")
    return dict(pairs)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("data file does not match the task store schema")


# --------------------------------------------------------------------------- saving


def serialise(store: Store) -> bytes:
    """Canonical bytes: fixed key order, tasks by ascending id, UTF-8, LF, trailing newline."""
    data = {
        "version": FORMAT_VERSION,
        "next_id": store.next_id,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
                "tags": list(t.tags),
            }
            for t in sorted(store.tasks, key=lambda t: t.id)
        ],
    }
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def save(path: str, store: Store) -> None:
    """Atomic: write ``PATH.tmp`` in the same directory, fsync, then ``os.replace`` (R6)."""
    payload = serialise(store)
    tmp = path + ".tmp"
    try:
        with open(tmp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        _remove_quietly(tmp)
        raise errors.save_failed(path) from exc
    except BaseException:  # e.g. KeyboardInterrupt: clean up, then let it propagate
        _remove_quietly(tmp)
        raise


def _remove_quietly(path: str) -> None:
    with contextlib.suppress(OSError):
        os.remove(path)
