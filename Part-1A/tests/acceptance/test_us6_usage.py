"""User Story 6 - Clear feedback on command misuse (AC-52-AC-54; task T055)."""

from conftest import task


def assert_usage_error(result):
    assert result.code == 2
    assert result.out == ""
    assert result.err.splitlines()[0].startswith("usage: todo")
    assert "Traceback" not in result.err


def test_AC52_unknown_command_shows_usage(run, write_store, data_bytes):
    write_store(2, [task(1, "A")])
    before = data_bytes()
    assert_usage_error(run("frobnicate"))
    assert data_bytes() == before


def test_AC53_no_arguments_shows_usage(run):
    assert_usage_error(run())


def test_AC54_add_without_title_shows_usage(run, write_store, data_bytes):
    write_store(2, [task(1, "A")])
    before = data_bytes()
    assert_usage_error(run("add"))
    assert data_bytes() == before
