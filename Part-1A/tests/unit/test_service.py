"""Unit tests for smart_todo.service (tasks T010, T020, T045)."""

import pytest

from smart_todo import service
from smart_todo.errors import TodoError
from smart_todo.models import Task
from smart_todo.store import Store

STORE = Store(3, (Task(1, "A", "low", "todo", ()), Task(2, "B", "high", "done", ("x",))))

# --------------------------------------------------------------- find_task (T010)


def test_find_task_returns_matching_task():
    assert service.find_task(STORE, 2) == Task(2, "B", "high", "done", ("x",))


def test_find_task_unknown_id_raises_not_found():
    with pytest.raises(TodoError) as exc:
        service.find_task(STORE, 99)
    assert exc.value.message == "Error: task 99 not found."
    assert exc.value.exit_code == 1


# --------------------------------------------------------------- add / list / format (T020)


def test_add_task_assigns_next_id_and_todo_status():
    new_store, created = service.add_task(STORE, "C", "medium", ("y",))
    assert created == Task(3, "C", "medium", "todo", ("y",))
    assert new_store.next_id == 4
    assert new_store.tasks[-1] == created
    assert STORE.next_id == 3  # the input store is not modified


def test_list_tasks_sorts_by_priority_rank_then_id():
    data = Store(
        5,
        (
            Task(1, "A", "low", "todo", ()),
            Task(2, "B", "high", "todo", ()),
            Task(3, "C", "medium", "todo", ()),
            Task(4, "D", "high", "todo", ()),
        ),
    )
    assert [t.id for t in service.list_tasks(data)] == [2, 4, 3, 1]


def test_format_line():
    line = service.format_line(Task(2, "Pay rent", "high", "todo", ("home", "bills")))
    assert line == "2 [todo] (high) Pay rent #home #bills"
    assert service.format_line(Task(1, "A", "low", "done", ())) == "1 [done] (low) A"


# --------------------------------------------------------------- update / delete (T045)


def test_delete_task_keeps_next_id():
    after = service.delete_task(STORE, 2)
    assert after == Store(3, (Task(1, "A", "low", "todo", ()),))


def test_delete_unknown_task_raises_not_found():
    with pytest.raises(TodoError) as exc:
        service.delete_task(STORE, 99)
    assert exc.value.message == "Error: task 99 not found."


def test_update_task_changes_only_given_fields_and_never_status():
    after = service.update_task(STORE, 2, title="B2")
    assert service.find_task(after, 2) == Task(2, "B2", "high", "done", ("x",))
    after = service.update_task(STORE, 2, priority="low")
    assert service.find_task(after, 2) == Task(2, "B", "low", "done", ("x",))
    assert after.next_id == STORE.next_id


def test_update_task_tags_replace_whole_set_and_clear_tags_empties_it():
    after = service.update_task(STORE, 2, tags=("y", "z"))
    assert service.find_task(after, 2).tags == ("y", "z")
    after = service.update_task(STORE, 2, clear_tags=True)
    assert service.find_task(after, 2).tags == ()


def test_update_task_requires_a_change():
    with pytest.raises(TodoError) as exc:
        service.update_task(STORE, 1)
    assert exc.value.message == (
        "Error: nothing to update (use --title, --priority, --tag or --clear-tags)."
    )


def test_update_task_rejects_tags_with_clear_tags():
    with pytest.raises(TodoError) as exc:
        service.update_task(STORE, 1, tags=("a",), clear_tags=True)
    assert exc.value.message == "Error: --tag and --clear-tags cannot be used together."


def test_update_task_unknown_id_is_checked_before_other_rules():
    for kwargs in ({}, {"tags": ("a",), "clear_tags": True}):
        with pytest.raises(TodoError) as exc:
            service.update_task(STORE, 99, **kwargs)
        assert exc.value.message == "Error: task 99 not found."
