"""SC-002: the `todo` / `todo.cmd` launcher works with no setup (task T021).

The launcher is chosen by platform inside the test; nothing is skipped.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _launcher():
    if os.name == "nt":
        return [str(ROOT / "todo.cmd")]
    return ["sh", str(ROOT / "todo")]


def _env_without_pythonpath():
    env = {k: v for k, v in os.environ.items() if k.upper() != "PYTHONPATH"}
    path_key = next((k for k in env if k.upper() == "PATH"), "PATH")
    env[path_key] = str(Path(sys.executable).parent) + os.pathsep + env.get(path_key, "")
    return env


def test_SC002_launcher_adds_and_lists_with_no_setup(tmp_path):
    env = _env_without_pythonpath()
    added = subprocess.run(
        [*_launcher(), "add", "Buy milk"], cwd=tmp_path, env=env, capture_output=True, check=False
    )
    assert added.returncode == 0, added.stderr
    assert added.stdout == b"Added task 1: Buy milk\n"
    listed = subprocess.run(
        [*_launcher(), "list"], cwd=tmp_path, env=env, capture_output=True, check=False
    )
    assert listed.returncode == 0, listed.stderr
    assert listed.stdout == b"1 [todo] (medium) Buy milk\n"
    assert (tmp_path / "todo.json").exists()
