"""User Story 2 - Reliable persistence (AC-14-AC-23, AC-59; task T028)."""

from conftest import task

from smart_todo import store

CORRUPT = "Error: data file 'todo.json' is corrupt or unreadable; it was not modified.\n"
SAVE_FAILED = "Error: could not save data file 'todo.json'; previous data was kept.\n"


def test_AC14_task_persists_between_runs(run):
    assert run("add", "Buy milk").code == 0
    assert run("list") == (0, "1 [todo] (medium) Buy milk\n", "")


def test_AC15_id_not_reused_after_deleting_highest(run, write_store):
    write_store(4, [task(1, "One"), task(2, "Two")])  # task 3 existed and was deleted
    assert run("add", "New") == (0, "Added task 4: New\n", "")


def test_AC16_id_not_reused_after_deleting_all(run, write_store):
    write_store(3, [])  # tasks 1 and 2 existed and were deleted
    assert run("add", "Again") == (0, "Added task 3: Again\n", "")


def test_AC17_list_on_fresh_store_creates_no_file(run, data_bytes):
    assert run("list") == (0, "No tasks found.\n", "")
    assert data_bytes() is None


def test_AC18_list_refuses_non_json_file(run, write_raw, data_bytes):
    write_raw("{not json")
    assert run("list") == (3, "", CORRUPT)
    assert data_bytes() == b"{not json"


def test_AC19_add_refuses_non_json_file(run, write_raw, data_bytes):
    write_raw("{not json")
    assert run("add", "Buy milk") == (3, "", CORRUPT)
    assert data_bytes() == b"{not json"


def test_AC20_list_refuses_wrong_shape_json(run, write_raw, data_bytes):
    write_raw("[]")
    assert run("list") == (3, "", CORRUPT)
    assert data_bytes() == b"[]"


def test_AC21_failed_save_keeps_previous_data(run, write_store, data_bytes, tmp_path, monkeypatch):
    write_store(2, [task(1, "First")])
    before = data_bytes()

    def refuse(src, dst):
        raise OSError("replace refused")

    with monkeypatch.context() as patch:
        patch.setattr(store.os, "replace", refuse)
        assert run("add", "Second") == (3, "", SAVE_FAILED)
    assert data_bytes() == before
    assert not (tmp_path / "todo.json.tmp").exists()
    assert run("list") == (0, "1 [todo] (medium) First\n", "")


def test_AC59_interrupt_during_save_keeps_previous_data(
    run, write_store, data_bytes, tmp_path, monkeypatch
):
    write_store(2, [task(1, "First")])
    before = data_bytes()

    def interrupt(src, dst):
        raise KeyboardInterrupt

    monkeypatch.setattr(store.os, "replace", interrupt)
    assert run("add", "Second") == (130, "", "Error: interrupted.\n")
    assert data_bytes() == before
    assert not (tmp_path / "todo.json.tmp").exists()


def test_AC22_file_option_uses_given_path(run, data_bytes):
    assert run("--file", "work.json", "add", "Report") == (0, "Added task 1: Report\n", "")
    assert run("--file", "work.json", "list") == (0, "1 [todo] (medium) Report\n", "")
    assert data_bytes() is None
    assert data_bytes("work.json") is not None


def test_AC23_same_input_gives_identical_results(run, write_store, tmp_path, monkeypatch):
    seed = [task(1, "Café ✓", "high", tags=["x"]), task(2, "B", status="done")]
    results = []
    for name in ("first", "second"):
        folder = tmp_path / name
        folder.mkdir()
        write_store(3, seed, name=f"{name}/todo.json")
        monkeypatch.chdir(folder)
        outcome = run("add", "Same", "--priority", "low", "--tag", "T")
        results.append((outcome, (folder / "todo.json").read_bytes()))
    assert results[0] == results[1]
    assert results[0][0].code == 0
