"""Foundational unit tests: errors, CLI pipeline, minimal store (task T009)."""

from conftest import canonical_bytes, task

from smart_todo import cli, store
from smart_todo.errors import DataFileError, InputError, TodoError, UsageError
from smart_todo.models import Task

INTERNAL = "Error: unexpected internal error.\n"


def test_error_types_carry_exit_codes_and_messages():
    assert InputError("Error: x.").exit_code == 1
    assert UsageError("todo: error: x\n", usage="usage: todo\n").exit_code == 2
    assert DataFileError("Error: y.").exit_code == 3
    err = InputError("Error: x.")
    assert isinstance(err, TodoError)
    assert err.message == "Error: x."


def test_handler_output_is_written_with_newlines(run, monkeypatch):
    monkeypatch.setitem(cli._HANDLERS, "list", lambda args: ["first", "second"])
    result = run("list")
    assert result == (0, "first\nsecond\n", "")


def test_todo_error_is_reported_with_its_exit_code(run, monkeypatch):
    def fail(args):
        raise DataFileError("Error: boom.")

    monkeypatch.setitem(cli._HANDLERS, "list", fail)
    assert run("list") == (3, "", "Error: boom.\n")


def test_unexpected_exception_becomes_internal_error(run, monkeypatch):
    def crash(args):
        raise RuntimeError("bug")

    monkeypatch.setitem(cli._HANDLERS, "list", crash)
    result = run("list")
    assert result.code == 1
    assert result.out == ""
    assert result.err == INTERNAL
    assert "Traceback" not in result.err


def test_keyboard_interrupt_exits_130(run, monkeypatch):
    def interrupt(args):
        raise KeyboardInterrupt

    monkeypatch.setitem(cli._HANDLERS, "list", interrupt)
    assert run("list") == (130, "", "Error: interrupted.\n")


def test_help_exits_0_to_stdout(run):
    result = run("--help")
    assert result.code == 0
    assert result.out.startswith("usage: todo")
    assert result.err == ""


def test_usage_error_exits_2_to_stderr(run):
    result = run("frobnicate")
    assert result.code == 2
    assert result.out == ""
    assert result.err.startswith("usage: todo")
    assert "todo: error:" in result.err


def test_missing_file_loads_empty_store_without_creating_it(tmp_path):
    path = tmp_path / "todo.json"
    assert store.load(str(path)) == store.Store(1, ())
    assert not path.exists()


def test_valid_file_loads_expected_store(tmp_path):
    path = tmp_path / "todo.json"
    path.write_bytes(
        canonical_bytes(3, [task(1, "A", "high", tags=["work"]), task(2, "B", status="done")])
    )
    assert store.load(str(path)) == store.Store(
        3,
        (Task(1, "A", "high", "todo", ("work",)), Task(2, "B", "medium", "done", ())),
    )


def test_save_then_load_round_trips(tmp_path):
    path = str(tmp_path / "todo.json")
    original = store.Store(5, (Task(4, "Pay rent", "high", "in_progress", ("home",)),))
    store.save(path, original)
    assert store.load(path) == original


def test_serialise_is_canonical():
    data = store.Store(
        3, (Task(2, "Café ✓", "low", "done", ()), Task(1, "Pay rent", "high", "todo", ("home",)))
    )
    expected = (
        "{\n"
        '  "version": 1,\n'
        '  "next_id": 3,\n'
        '  "tasks": [\n'
        "    {\n"
        '      "id": 1,\n'
        '      "title": "Pay rent",\n'
        '      "priority": "high",\n'
        '      "status": "todo",\n'
        '      "tags": [\n'
        '        "home"\n'
        "      ]\n"
        "    },\n"
        "    {\n"
        '      "id": 2,\n'
        '      "title": "Café ✓",\n'
        '      "priority": "low",\n'
        '      "status": "done",\n'
        '      "tags": []\n'
        "    }\n"
        "  ]\n"
        "}\n"
    ).encode()
    assert store.serialise(data) == expected
