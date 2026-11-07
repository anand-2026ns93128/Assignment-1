"""FR-019 check order: only the first failing check is reported (task T060).

One test per row of the *Check order* examples in contracts/cli.md, plus load-before-lookup.
"""

import pytest
from conftest import task

INVALID_STATUS = "Error: invalid status 'finished' (expected: todo, in_progress, done).\n"
CORRUPT = "Error: data file 'todo.json' is corrupt or unreadable; it was not modified.\n"


@pytest.fixture
def one_task(write_store):
    write_store(2, [task(1, "A")])


def test_FR019_status_value_checked_before_task_exists(run, one_task):
    assert run("status", "99", "finished") == (1, "", INVALID_STATUS)


def test_FR019_id_format_checked_before_status_value(run, one_task):
    assert run("status", "abc", "finished") == (1, "", "Error: invalid task ID 'abc'.\n")


def test_FR019_values_checked_before_loading_corrupt_file(run, write_raw):
    write_raw("{not json")
    assert run("list", "--status", "finished") == (1, "", INVALID_STATUS)


def test_FR019_priority_checked_before_title(run):
    err = "Error: invalid priority 'urgent' (expected: low, medium, high).\n"
    assert run("add", "", "--priority", "urgent") == (1, "", err)


def test_FR019_task_exists_checked_before_nothing_to_update(run, one_task):
    assert run("update", "99") == (1, "", "Error: task 99 not found.\n")


def test_FR019_tag_value_checked_before_tag_clear_conflict(run, one_task):
    err = "Error: invalid tag 'a b' (tags must be 1-20 characters: letters, digits, '-' or '_').\n"
    assert run("update", "1", "--tag", "a b", "--clear-tags") == (1, "", err)


def test_FR019_file_loaded_before_task_lookup(run, write_raw):
    write_raw("{not json")
    assert run("delete", "99") == (3, "", CORRUPT)
