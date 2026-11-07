"""Unit tests for strict loading and atomic saving (contracts/data-file.md; task T029)."""

import json

import pytest
from conftest import canonical_bytes, task

from smart_todo import store
from smart_todo.errors import DataFileError
from smart_todo.models import Task


def valid_doc(**overrides):
    doc = {"version": 1, "next_id": 3, "tasks": [task(1, "A"), task(2, "B", tags=["x"])]}
    doc.update(overrides)
    return doc


def with_task(**fields):
    item = task(1, "A")
    item.update(fields)
    return valid_doc(next_id=2, tasks=[item])


def assert_corrupt(tmp_path, content):
    path = tmp_path / "todo.json"
    data = content if isinstance(content, bytes) else json.dumps(content).encode("utf-8")
    path.write_bytes(data)
    with pytest.raises(DataFileError) as exc:
        store.load(str(path))
    assert exc.value.message == (
        f"Error: data file '{path}' is corrupt or unreadable; it was not modified."
    )
    assert exc.value.exit_code == 3
    assert path.read_bytes() == data


# --------------------------------------------------------------- rule 1: readable, UTF-8


def test_FR014_rule1_invalid_utf8(tmp_path):
    assert_corrupt(tmp_path, b"\xff")


def test_FR014_rule1_path_is_a_directory(tmp_path):
    folder = tmp_path / "todo.json"
    folder.mkdir()
    with pytest.raises(DataFileError):
        store.load(str(folder))
    assert folder.is_dir()


# --------------------------------------------------------------- rule 2: JSON, no duplicate keys


def test_FR014_rule2_utf8_bom(tmp_path):
    assert_corrupt(tmp_path, b"\xef\xbb\xbf" + canonical_bytes(1, []))


def test_FR014_rule2_duplicate_keys(tmp_path):
    assert_corrupt(tmp_path, b'{"version": 1, "version": 1, "next_id": 1, "tasks": []}')


def test_FR014_rule2_deeply_nested_json(tmp_path):
    assert_corrupt(tmp_path, b"[" * 100000 + b"]" * 100000)


# --------------------------------------------------------------- rule 3: top-level keys


def test_FR014_rule3_extra_top_level_key(tmp_path):
    assert_corrupt(tmp_path, valid_doc(extra=True))


def test_FR014_rule3_missing_tasks(tmp_path):
    doc = valid_doc()
    del doc["tasks"]
    assert_corrupt(tmp_path, doc)


# --------------------------------------------------------------- rule 4: version


def test_FR014_rule4_version_2(tmp_path):
    assert_corrupt(tmp_path, valid_doc(version=2))


# --------------------------------------------------------------- rule 5: next_id


@pytest.mark.parametrize("next_id", [0, True, "3"])
def test_FR014_rule5_bad_next_id(tmp_path, next_id):
    assert_corrupt(tmp_path, valid_doc(next_id=next_id))


# --------------------------------------------------------------- rule 6: task keys


def test_FR014_rule6_task_with_extra_key(tmp_path):
    assert_corrupt(tmp_path, with_task(due="today"))


def test_FR014_rule6_task_missing_tags(tmp_path):
    item = task(1, "A")
    del item["tags"]
    assert_corrupt(tmp_path, valid_doc(next_id=2, tasks=[item]))


def test_FR014_rule6_task_not_an_object(tmp_path):
    assert_corrupt(tmp_path, valid_doc(tasks=["A"]))


# --------------------------------------------------------------- rule 7: ids


@pytest.mark.parametrize("task_id", [0, True])
def test_FR014_rule7_bad_id(tmp_path, task_id):
    assert_corrupt(tmp_path, with_task(id=task_id))


def test_FR014_rule7_duplicate_ids(tmp_path):
    assert_corrupt(tmp_path, valid_doc(tasks=[task(1, "A"), task(1, "B")]))


def test_FR014_rule7_next_id_equal_to_max_id(tmp_path):
    assert_corrupt(tmp_path, valid_doc(next_id=2))


# --------------------------------------------------------------- rule 8: title


@pytest.mark.parametrize("title", [" x", "a\tb", "a" * 101, "", 5])
def test_FR014_rule8_bad_title(tmp_path, title):
    assert_corrupt(tmp_path, with_task(title=title))


# --------------------------------------------------------------- rule 9: priority / status


def test_FR014_rule9_bad_priority(tmp_path):
    assert_corrupt(tmp_path, with_task(priority="urgent"))


def test_FR014_rule9_bad_status(tmp_path):
    assert_corrupt(tmp_path, with_task(status="finished"))


# --------------------------------------------------------------- rule 10: tags


@pytest.mark.parametrize("tags", [["Home"], ["home", "home"], ["a b"], "home", [5]])
def test_FR014_rule10_bad_tags(tmp_path, tags):
    assert_corrupt(tmp_path, with_task(tags=tags))


# --------------------------------------------------------------- valid files and saving


def test_FR014_valid_store_round_trips(tmp_path):
    original = store.Store(
        7, (Task(1, "A", "low", "done", ()), Task(6, "Ünï", "high", "todo", ("a",)))
    )
    path = tmp_path / "todo.json"
    path.write_bytes(store.serialise(original))
    assert store.load(str(path)) == original


def test_FR014_task_order_in_file_is_not_checked(tmp_path):
    path = tmp_path / "todo.json"
    path.write_bytes(canonical_bytes(3, [task(2, "B"), task(1, "A")]))
    loaded = store.load(str(path))
    assert [t.id for t in loaded.tasks] == [1, 2]


def test_FR015_save_removes_tmp_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "todo.json"
    path.write_bytes(b"previous")

    def refuse(src, dst):
        raise OSError("refused")

    monkeypatch.setattr(store.os, "replace", refuse)
    with pytest.raises(DataFileError) as exc:
        store.save(str(path), store.Store(1, ()))
    assert exc.value.message == (
        f"Error: could not save data file '{path}'; previous data was kept."
    )
    assert path.read_bytes() == b"previous"
    assert not (tmp_path / "todo.json.tmp").exists()


def test_FR015_save_overwrites_stale_tmp(tmp_path):
    path = tmp_path / "todo.json"
    (tmp_path / "todo.json.tmp").write_bytes(b"stale leftover from a crash")
    data = store.Store(2, (Task(1, "A", "medium", "todo", ()),))
    store.save(str(path), data)
    assert path.read_bytes() == store.serialise(data)
    assert not (tmp_path / "todo.json.tmp").exists()


def test_FR015_save_into_missing_directory_fails_cleanly(tmp_path):
    path = tmp_path / "missing" / "todo.json"
    with pytest.raises(DataFileError):
        store.save(str(path), store.Store(1, ()))
    assert not path.exists()


def test_FR016_serialise_is_canonical_and_sorted():
    data = store.Store(4, (Task(3, "C", "low", "todo", ()), Task(1, "A", "high", "done", ())))
    assert store.serialise(data) == canonical_bytes(
        4, [task(1, "A", "high", "done"), task(3, "C", "low")]
    )
