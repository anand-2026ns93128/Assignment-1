"""User Story 1 - Add and list tasks (AC-01-AC-13, AC-56, AC-57; task T018)."""

TITLE_ERROR = "Error: title must be 1-100 characters on a single line.\n"


def assert_rejected(result, err, data_bytes, before=None):
    assert result.code == 1
    assert result.out == ""
    assert result.err == err
    assert data_bytes() == before


def test_AC01_add_task_with_defaults(run):
    assert run("add", "Buy milk") == (0, "Added task 1: Buy milk\n", "")
    assert run("list") == (0, "1 [todo] (medium) Buy milk\n", "")


def test_AC02_add_with_priority_and_tags(run):
    result = run("add", "Pay rent", "--priority", "high", "--tag", "home", "--tag", "Bills")
    assert result == (0, "Added task 1: Pay rent\n", "")
    assert run("list") == (0, "1 [todo] (high) Pay rent #home #bills\n", "")


def test_AC03_empty_title_rejected(run, data_bytes):
    assert_rejected(run("add", ""), TITLE_ERROR, data_bytes)


def test_AC04_spaces_only_title_rejected(run, data_bytes):
    assert_rejected(run("add", "   "), TITLE_ERROR, data_bytes)


def test_AC05_title_is_trimmed(run):
    assert run("add", "  Buy milk  ") == (0, "Added task 1: Buy milk\n", "")


def test_AC06_title_of_100_chars_accepted(run):
    title = "a" * 100
    assert run("add", title) == (0, f"Added task 1: {title}\n", "")


def test_AC07_title_of_101_chars_rejected(run, data_bytes):
    assert_rejected(run("add", "a" * 101), TITLE_ERROR, data_bytes)


def test_AC08_title_with_line_break_rejected(run, data_bytes):
    assert_rejected(run("add", "Line1\nLine2"), TITLE_ERROR, data_bytes)


def test_AC09_invalid_priority_rejected(run, data_bytes):
    err = "Error: invalid priority 'urgent' (expected: low, medium, high).\n"
    assert_rejected(run("add", "Buy milk", "--priority", "urgent"), err, data_bytes)


def test_AC10_invalid_tag_rejected(run, data_bytes):
    err = "Error: invalid tag 'a b' (tags must be 1-20 characters: letters, digits, '-' or '_').\n"
    assert_rejected(run("add", "Buy milk", "--tag", "a b"), err, data_bytes)


def test_AC11_duplicate_tags_ignore_case(run):
    result = run("add", "Buy milk", "--tag", "home", "--tag", "HOME", "--tag", "errand")
    assert result.code == 0
    assert run("list") == (0, "1 [todo] (medium) Buy milk #home #errand\n", "")


def test_AC12_list_sorted_by_priority_then_id(run):
    run("add", "A", "--priority", "low")
    run("add", "B", "--priority", "high")
    run("add", "C")
    run("add", "D", "--priority", "high")
    expected = "2 [todo] (high) B\n4 [todo] (high) D\n3 [todo] (medium) C\n1 [todo] (low) A\n"
    assert run("list") == (0, expected, "")


def test_AC13_list_empty_store_prints_no_tasks(run, write_store):
    write_store(1, [])
    assert run("list") == (0, "No tasks found.\n", "")


def test_AC56_title_with_tab_rejected(run, data_bytes):
    assert_rejected(run("add", "Buy\tmilk"), TITLE_ERROR, data_bytes)


def test_AC57_unicode_title_of_100_chars_accepted(run):
    title = "é" * 100
    assert len(title.encode("utf-8")) == 200
    assert run("add", title) == (0, f"Added task 1: {title}\n", "")
