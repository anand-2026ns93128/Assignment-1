"""Shared fixtures and helpers for all tests (task T008)."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from smart_todo.cli import main

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
TASK_KEYS = ("id", "title", "priority", "status", "tags")


class Result(NamedTuple):
    code: int
    out: str
    err: str


class ProcResult(NamedTuple):
    code: int
    out: bytes
    err: bytes


def task(task_id, title, priority="medium", status="todo", tags=()):
    """Build a task dict for ``write_store`` in canonical key order."""
    return {
        "id": task_id,
        "title": title,
        "priority": priority,
        "status": status,
        "tags": list(tags),
    }


def canonical_bytes(next_id, tasks):
    """Canonical data-file bytes (contracts/data-file.md)."""
    ordered = [{key: t[key] for key in TASK_KEYS} for t in tasks]
    data = {"version": 1, "next_id": next_id, "tasks": ordered}
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    """Call ``main(argv)`` in-process with ``tmp_path`` as the current directory."""
    monkeypatch.chdir(tmp_path)

    def _run(*argv):
        code = main(list(argv))
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)

    return _run


@pytest.fixture
def data_bytes(tmp_path):
    def _data_bytes(name="todo.json"):
        path = tmp_path / name
        return path.read_bytes() if path.exists() else None

    return _data_bytes


@pytest.fixture
def write_store(tmp_path):
    def _write_store(next_id, tasks, name="todo.json"):
        (tmp_path / name).write_bytes(canonical_bytes(next_id, tasks))

    return _write_store


@pytest.fixture
def write_raw(tmp_path):
    def _write_raw(content, name="todo.json"):
        data = content.encode("utf-8") if isinstance(content, str) else content
        (tmp_path / name).write_bytes(data)

    return _write_raw


@pytest.fixture
def run_proc():
    """Run ``python -m smart_todo`` as a real separate process; returns raw bytes."""

    def _run_proc(*argv, cwd):
        env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
        completed = subprocess.run(
            [sys.executable, "-m", "smart_todo", *argv],
            cwd=cwd,
            env=env,
            capture_output=True,
            check=False,
        )
        return ProcResult(completed.returncode, completed.stdout, completed.stderr)

    return _run_proc
