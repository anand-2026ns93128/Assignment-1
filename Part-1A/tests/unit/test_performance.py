"""SC-003: every command completes in under 1 second with 1,000 tasks (task T061).

Measured in-process (without interpreter start-up) on the development machine.
"""

import time

from conftest import task

LIMIT_SECONDS = 1.0


def test_SC003_commands_under_one_second_with_1000_tasks(run, write_store):
    priorities = ("low", "medium", "high")
    write_store(
        1001,
        [task(i, f"Task {i}", priorities[i % 3], tags=[f"t{i % 7}"]) for i in range(1, 1001)],
    )
    commands = [
        ("list",),
        ("list", "--tag", "t3", "--status", "todo"),
        ("add", "One more", "--priority", "high", "--tag", "new"),
        ("update", "500", "--title", "Renamed", "--priority", "low"),
        ("status", "501", "in_progress"),
        ("delete", "502"),
    ]
    for argv in commands:
        start = time.perf_counter()
        result = run(*argv)
        elapsed = time.perf_counter() - start
        assert result.code == 0, (argv, result.err)
        assert elapsed < LIMIT_SECONDS, (argv, elapsed)
