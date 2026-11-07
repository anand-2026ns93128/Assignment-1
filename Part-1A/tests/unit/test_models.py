"""Unit tests for the value rules in smart_todo.models (tasks T010, T019, T038)."""

import pytest

from smart_todo import models
from smart_todo.errors import InputError

# --------------------------------------------------------------- shared validators (T010)


@pytest.mark.parametrize(("raw", "expected"), [("1", 1), ("01", 1), ("42", 42)])
def test_parse_task_id_accepts_positive_ascii_integers(raw, expected):
    assert models.parse_task_id(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "+1", " 1", "1_0", "abc", "", "١"])
def test_parse_task_id_rejects_everything_else(raw):
    with pytest.raises(InputError) as exc:
        models.parse_task_id(raw)
    assert exc.value.message == f"Error: invalid task ID '{raw}'."


@pytest.mark.parametrize("raw", ["todo", "in_progress", "done"])
def test_validate_status_accepts_the_three_statuses(raw):
    assert models.validate_status(raw) == raw


@pytest.mark.parametrize("raw", ["Done", "finished"])
def test_validate_status_rejects_other_values(raw):
    with pytest.raises(InputError) as exc:
        models.validate_status(raw)
    assert exc.value.message == (
        f"Error: invalid status '{raw}' (expected: todo, in_progress, done)."
    )


# --------------------------------------------------------------- US1 validators (T019)

TITLE_ERROR = "Error: title must be 1-100 characters on a single line."


@pytest.mark.parametrize(
    "raw", ["a\nb", "a\rb", "a\tb", "a\x00b", "a\x7fb", "a\x85b", "Buy milk\n", "\tBuy milk"]
)
def test_validate_title_rejects_control_characters_anywhere(raw):
    with pytest.raises(InputError) as exc:
        models.validate_title(raw)
    assert exc.value.message == TITLE_ERROR


def test_validate_title_trims_surrounding_spaces():
    assert models.validate_title("  Buy milk  ") == "Buy milk"


@pytest.mark.parametrize("title", ["a", "a" * 100, "é" * 100])
def test_validate_title_accepts_1_to_100_code_points(title):
    assert models.validate_title(title) == title


@pytest.mark.parametrize("raw", ["", "   ", "a" * 101, "é" * 101])
def test_validate_title_rejects_0_or_101_code_points(raw):
    with pytest.raises(InputError) as exc:
        models.validate_title(raw)
    assert exc.value.message == TITLE_ERROR


@pytest.mark.parametrize("raw", ["low", "medium", "high"])
def test_validate_priority_accepts_three_values(raw):
    assert models.validate_priority(raw) == raw


@pytest.mark.parametrize("raw", ["High", "urgent", ""])
def test_validate_priority_rejects_other_values(raw):
    with pytest.raises(InputError) as exc:
        models.validate_priority(raw)
    assert exc.value.message == f"Error: invalid priority '{raw}' (expected: low, medium, high)."


@pytest.mark.parametrize("raw", ["a b", "", "a" * 21, "é", "tag!"])
def test_normalize_tags_rejects_invalid_tags_showing_raw_value(raw):
    with pytest.raises(InputError) as exc:
        models.normalize_tags(["ok", raw])
    assert exc.value.message == (
        f"Error: invalid tag '{raw}' (tags must be 1-20 characters: letters, digits, '-' or '_')."
    )


def test_normalize_tags_accepts_20_chars_and_dedupes_case_insensitively():
    assert models.normalize_tags(["a" * 20]) == ("a" * 20,)
    assert models.normalize_tags(["home", "HOME", "errand", "my-tag_2"]) == (
        "home",
        "errand",
        "my-tag_2",
    )


def test_normalize_tags_none_is_empty():
    assert models.normalize_tags(None) == ()


# --------------------------------------------------------------- transitions (T038)

ALLOWED = {("todo", "in_progress"), ("in_progress", "done"), ("todo", "done")}


@pytest.mark.parametrize("old", models.STATUSES)
@pytest.mark.parametrize("new", models.STATUSES)
def test_check_transition_matrix(old, new):
    if (old, new) in ALLOWED:
        models.check_transition(7, old, new)
        return
    with pytest.raises(InputError) as exc:
        models.check_transition(7, old, new)
    assert exc.value.message == f"Error: cannot change status of task 7 from {old} to {new}."


def test_exactly_three_transitions_are_allowed():
    assert models.ALLOWED_TRANSITIONS == ALLOWED
