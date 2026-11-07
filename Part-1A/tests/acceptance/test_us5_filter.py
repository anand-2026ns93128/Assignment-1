"""User Story 5 - Filter the list (AC-46-AC-51, AC-55; task T050)."""

import pytest
from conftest import task

INVALID_STATUS = "Error: invalid status 'finished' (expected: todo, in_progress, done).\n"
AC46_OUTPUT = "1 [todo] (high) A #work\n3 [done] (medium) C #work #home\n"


@pytest.fixture(autouse=True)
def four_tasks(write_store):
    write_store(
        5,
        [
            task(1, "A", "high", "todo", ["work"]),
            task(2, "B", "low", "in_progress", ["home"]),
            task(3, "C", "medium", "done", ["work", "home"]),
            task(4, "D", "high", "in_progress", []),
        ],
    )


def test_AC46_filter_by_tag(run):
    assert run("list", "--tag", "work") == (0, AC46_OUTPUT, "")


def test_AC47_filter_by_status(run):
    expected = "4 [in_progress] (high) D\n2 [in_progress] (low) B #home\n"
    assert run("list", "--status", "in_progress") == (0, expected, "")


def test_AC48_filter_by_tag_and_status(run):
    result = run("list", "--tag", "home", "--status", "done")
    assert result == (0, "3 [done] (medium) C #work #home\n", "")


def test_AC49_tag_filter_ignores_case(run):
    assert run("list", "--tag", "WORK") == (0, AC46_OUTPUT, "")


def test_AC50_filter_with_no_match(run):
    assert run("list", "--tag", "garden") == (0, "No tasks found.\n", "")


def test_AC51_invalid_status_filter_rejected(run):
    assert run("list", "--status", "finished") == (1, "", INVALID_STATUS)


def test_AC51_invalid_status_reported_before_corrupt_file(run, write_raw, data_bytes):
    write_raw("{not json")
    assert run("list", "--status", "finished") == (1, "", INVALID_STATUS)
    assert data_bytes() == b"{not json"


def test_AC55_invalid_tag_filter_rejected(run, data_bytes):
    before = data_bytes()
    err = "Error: invalid tag 'a b' (tags must be 1-20 characters: letters, digits, '-' or '_').\n"
    assert run("list", "--tag", "a b") == (1, "", err)
    assert data_bytes() == before
