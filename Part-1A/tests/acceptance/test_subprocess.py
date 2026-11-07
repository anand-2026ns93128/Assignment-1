"""Behaviour across real, separate program runs (tasks T030, T056)."""

from conftest import canonical_bytes, task


def test_AC14_persists_across_processes(tmp_path, run_proc):
    added = run_proc("add", "Buy milk", cwd=tmp_path)
    assert (added.code, added.out, added.err) == (0, b"Added task 1: Buy milk\n", b"")
    listed = run_proc("list", cwd=tmp_path)
    assert (listed.code, listed.out, listed.err) == (0, b"1 [todo] (medium) Buy milk\n", b"")


def test_AC23_byte_identical_across_processes(tmp_path, run_proc):
    seed = canonical_bytes(3, [task(1, "Café ✓", "high", tags=["x"]), task(2, "B")])
    outcomes = []
    for name in ("first", "second"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "todo.json").write_bytes(seed)
        added = run_proc("add", "Thé", "--tag", "Y", cwd=folder)
        listed = run_proc("list", cwd=folder)
        outcomes.append((added, listed, (folder / "todo.json").read_bytes()))
    assert outcomes[0] == outcomes[1]
    added, listed, _ = outcomes[0]
    assert added.code == 0
    expected = "1 [todo] (high) Café ✓ #x\n2 [todo] (medium) B\n3 [todo] (medium) Thé #y\n"
    assert listed.out == expected.encode()
    assert b"\r\n" not in listed.out


def assert_usage_error(result):
    assert result.code == 2
    assert result.out == b""
    assert result.err.decode("utf-8").splitlines()[0].startswith("usage: todo")
    assert b"Traceback" not in result.err


def test_AC52_unknown_command_in_real_process(tmp_path, run_proc):
    assert_usage_error(run_proc("frobnicate", cwd=tmp_path))
    assert not (tmp_path / "todo.json").exists()


def test_AC53_no_arguments_in_real_process(tmp_path, run_proc):
    assert_usage_error(run_proc(cwd=tmp_path))


def test_AC54_add_without_title_in_real_process(tmp_path, run_proc):
    assert_usage_error(run_proc("add", cwd=tmp_path))
    assert not (tmp_path / "todo.json").exists()
