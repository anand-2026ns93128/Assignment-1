"""User Story 3 - Status transitions (AC-24-AC-32; task T037)."""

import pytest
from conftest import task


@pytest.fixture
def seeded(write_store, data_bytes):
    """Store with task 1 "Buy milk" in the given status; returns the file bytes."""

    def _seed(status):
        write_store(2, [task(1, "Buy milk", status=status)])
        return data_bytes()

    return _seed


def assert_rejected(result, err, data_bytes, before):
    assert result == (1, "", err)
    assert data_bytes() == before


def test_AC24_todo_to_in_progress(run, seeded):
    seeded("todo")
    assert run("status", "1", "in_progress") == (0, "Task 1: todo -> in_progress\n", "")
    assert run("list") == (0, "1 [in_progress] (medium) Buy milk\n", "")


def test_AC25_in_progress_to_done(run, seeded):
    seeded("in_progress")
    assert run("status", "1", "done") == (0, "Task 1: in_progress -> done\n", "")


def test_AC26_todo_to_done(run, seeded):
    seeded("todo")
    assert run("status", "1", "done") == (0, "Task 1: todo -> done\n", "")


def test_AC27_done_to_todo_rejected(run, seeded, data_bytes):
    before = seeded("done")
    err = "Error: cannot change status of task 1 from done to todo.\n"
    assert_rejected(run("status", "1", "todo"), err, data_bytes, before)


def test_AC28_in_progress_to_todo_rejected(run, seeded, data_bytes):
    before = seeded("in_progress")
    err = "Error: cannot change status of task 1 from in_progress to todo.\n"
    assert_rejected(run("status", "1", "todo"), err, data_bytes, before)


def test_AC29_done_to_in_progress_rejected(run, seeded, data_bytes):
    before = seeded("done")
    err = "Error: cannot change status of task 1 from done to in_progress.\n"
    assert_rejected(run("status", "1", "in_progress"), err, data_bytes, before)


def test_AC30_same_status_rejected(run, seeded, data_bytes):
    before = seeded("todo")
    err = "Error: cannot change status of task 1 from todo to todo.\n"
    assert_rejected(run("status", "1", "todo"), err, data_bytes, before)


def test_AC31_invalid_status_value_rejected(run, seeded, data_bytes):
    before = seeded("todo")
    err = "Error: invalid status 'finished' (expected: todo, in_progress, done).\n"
    assert_rejected(run("status", "1", "finished"), err, data_bytes, before)


def test_AC32_unknown_id_rejected(run, seeded, data_bytes):
    before = seeded("todo")
    assert_rejected(run("status", "99", "done"), "Error: task 99 not found.\n", data_bytes, before)
