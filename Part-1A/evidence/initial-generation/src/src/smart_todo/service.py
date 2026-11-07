"""Business rules as pure functions over an in-memory Store (no I/O).

Tasks T014 (find_task), T024 (add_task, list_tasks, format_line), T041 (set_status)
and T047 (update_task, delete_task).
"""

from __future__ import annotations

from dataclasses import replace

from smart_todo import errors
from smart_todo.models import PRIORITY_RANK, Task, check_transition
from smart_todo.store import Store


def find_task(store: Store, task_id: int) -> Task:
    for task in store.tasks:
        if task.id == task_id:
            return task
    raise errors.task_not_found(task_id)


def add_task(
    store: Store, title: str, priority: str, tags: tuple[str, ...]
) -> tuple[Store, Task]:
    """New task gets ``store.next_id`` and status ``todo``; next_id advances (FR-001, FR-007)."""
    task = Task(store.next_id, title, priority, "todo", tags)
    return Store(store.next_id + 1, (*store.tasks, task)), task


def list_tasks(store: Store, tag: str | None = None, status: str | None = None) -> list[Task]:
    """Filter by tag (already lowercase) and/or status, then sort by priority and id.

    FR-005, FR-006 (tasks T024, T052): when both filters are given a task must match both.
    """
    matching = [
        t
        for t in store.tasks
        if (tag is None or tag in t.tags) and (status is None or t.status == status)
    ]
    return sorted(matching, key=lambda t: (PRIORITY_RANK[t.priority], t.id))


def format_line(task: Task) -> str:
    tags = "".join(f" #{tag}" for tag in task.tags)
    return f"{task.id} [{task.status}] ({task.priority}) {task.title}{tags}"


def set_status(store: Store, task_id: int, new: str) -> tuple[Store, str, str]:
    """Change one task's status if the transition is allowed (FR-010; task T041)."""
    task = find_task(store, task_id)
    check_transition(task_id, task.status, new)
    return _replace_task(store, replace(task, status=new)), task.status, new


def _replace_task(store: Store, updated: Task) -> Store:
    tasks = tuple(updated if t.id == updated.id else t for t in store.tasks)
    return Store(store.next_id, tasks)


def update_task(
    store: Store,
    task_id: int,
    title: str | None = None,
    priority: str | None = None,
    tags: tuple[str, ...] | None = None,
    clear_tags: bool = False,
) -> Store:
    """Edit title/priority/tags; never status (FR-008, AC-58; task T047).

    Order (FR-019): task exists -> something to change -> --tag/--clear-tags conflict.
    """
    task = find_task(store, task_id)
    if title is None and priority is None and tags is None and not clear_tags:
        raise errors.nothing_to_update()
    if tags is not None and clear_tags:
        raise errors.tag_clear_conflict()
    updated = replace(
        task,
        title=task.title if title is None else title,
        priority=task.priority if priority is None else priority,
        tags=() if clear_tags else (task.tags if tags is None else tags),
    )
    return _replace_task(store, updated)


def delete_task(store: Store, task_id: int) -> Store:
    """Remove one task; next_id is unchanged so the ID is never reused (FR-007, FR-009)."""
    find_task(store, task_id)
    return Store(store.next_id, tuple(t for t in store.tasks if t.id != task_id))
