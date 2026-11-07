"""User Story 4 - Update and delete tasks (AC-33-AC-45, AC-58; task T044)."""

import pytest
from conftest import task


@pytest.fixture
def milk(write_store, data_bytes):
    """Store with task 1 "Buy milk" (medium, tag home); returns the file bytes."""
    write_store(2, [task(1, "Buy milk", tags=["home"])])
    return data_bytes()


def assert_rejected(result, err, data_bytes, before):
    assert result == (1, "", err)
    assert data_bytes() == before


def test_AC33_update_title(run, milk):
    assert run("update", "1", "--title", "Buy oat milk") == (0, "Updated task 1.\n", "")
    assert run("list") == (0, "1 [todo] (medium) Buy oat milk #home\n", "")


def test_AC34_update_priority(run, write_store):
    write_store(2, [task(1, "Buy milk")])
    assert run("update", "1", "--priority", "low") == (0, "Updated task 1.\n", "")
    assert run("list") == (0, "1 [todo] (low) Buy milk\n", "")


def test_AC35_update_tags_replaces_set(run, milk):
    result = run("update", "1", "--tag", "work", "--tag", "urgent")
    assert result == (0, "Updated task 1.\n", "")
    assert run("list") == (0, "1 [todo] (medium) Buy milk #work #urgent\n", "")


def test_AC36_clear_tags(run, milk):
    assert run("update", "1", "--clear-tags") == (0, "Updated task 1.\n", "")
    assert run("list") == (0, "1 [todo] (medium) Buy milk\n", "")


def test_AC37_update_without_options_rejected(run, milk, data_bytes):
    err = "Error: nothing to update (use --title, --priority, --tag or --clear-tags).\n"
    assert_rejected(run("update", "1"), err, data_bytes, milk)


def test_AC38_tag_and_clear_tags_conflict(run, milk, data_bytes):
    err = "Error: --tag and --clear-tags cannot be used together.\n"
    assert_rejected(run("update", "1", "--tag", "work", "--clear-tags"), err, data_bytes, milk)


def test_AC39_update_empty_title_rejected(run, milk, data_bytes):
    err = "Error: title must be 1-100 characters on a single line.\n"
    assert_rejected(run("update", "1", "--title", ""), err, data_bytes, milk)


def test_AC40_update_invalid_priority_rejected(run, milk, data_bytes):
    err = "Error: invalid priority 'urgent' (expected: low, medium, high).\n"
    assert_rejected(run("update", "1", "--priority", "urgent"), err, data_bytes, milk)


def test_AC41_update_unknown_id_rejected(run, milk, data_bytes):
    err = "Error: task 99 not found.\n"
    assert_rejected(run("update", "99", "--title", "X"), err, data_bytes, milk)


def test_AC42_delete_task(run, write_store):
    write_store(3, [task(1, "A"), task(2, "B")])
    assert run("delete", "2") == (0, "Deleted task 2.\n", "")
    assert run("list") == (0, "1 [todo] (medium) A\n", "")


def test_AC43_delete_unknown_id_rejected(run, milk, data_bytes):
    assert_rejected(run("delete", "99"), "Error: task 99 not found.\n", data_bytes, milk)


def test_AC44_delete_non_numeric_id_rejected(run, milk, data_bytes):
    assert_rejected(run("delete", "abc"), "Error: invalid task ID 'abc'.\n", data_bytes, milk)


def test_AC45_delete_zero_id_rejected(run, milk, data_bytes):
    assert_rejected(run("delete", "0"), "Error: invalid task ID '0'.\n", data_bytes, milk)


def test_AC58_update_done_task_keeps_status(run, write_store):
    write_store(2, [task(1, "Buy milk", status="done")])
    result = run("update", "1", "--title", "Buy oat milk", "--priority", "high")
    assert result == (0, "Updated task 1.\n", "")
    assert run("list") == (0, "1 [done] (high) Buy oat milk\n", "")
