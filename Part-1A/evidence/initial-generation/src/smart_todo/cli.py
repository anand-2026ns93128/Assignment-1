"""Command-line interface: parsing, the FR-019 check pipeline, output and exit codes.

Task T015 (pipeline skeleton). Command handlers are added by the user-story tasks.
Every handler validates its arguments first (FR-019 step 2), then loads the store,
then applies the operation, and saves only when it changes data.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from smart_todo import errors, models, service, store
from smart_todo.errors import TodoError, UsageError

USAGE_WIDTH = 80  # fixed so usage text never depends on the terminal (Constitution IV)


class _Exit(Exception):
    """Raised instead of sys.exit() by the parser (e.g. after --help)."""

    def __init__(self, status: int, message: str | None) -> None:
        super().__init__(status, message)
        self.status = status
        self.message = message


class _Formatter(argparse.HelpFormatter):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, width=USAGE_WIDTH)


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("formatter_class", _Formatter)
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str):
        raise UsageError(f"{self.prog}: error: {message}\n", usage=self.format_usage())

    def exit(self, status: int = 0, message: str | None = None):
        raise _Exit(status, message)


def build_parser() -> argparse.ArgumentParser:
    """All values are plain strings; their rules are checked by hand (research R1)."""
    parser = _Parser(prog="todo", description="Smart Todo CLI")
    parser.add_argument("--file", default="todo.json", help="data file (default: todo.json)")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    add = commands.add_parser("add", help="create a task")
    add.add_argument("title")
    add.add_argument("--priority")
    add.add_argument("--tag", action="append", default=None)

    list_ = commands.add_parser("list", help="list tasks")
    list_.add_argument("--tag")
    list_.add_argument("--status")

    update = commands.add_parser("update", help="edit a task")
    update.add_argument("id")
    update.add_argument("--title")
    update.add_argument("--priority")
    update.add_argument("--tag", action="append", default=None)
    update.add_argument("--clear-tags", action="store_true")

    delete = commands.add_parser("delete", help="remove a task")
    delete.add_argument("id")

    status = commands.add_parser("status", help="change a task's status")
    status.add_argument("id")
    status.add_argument("status")
    return parser


Handler = Callable[[argparse.Namespace], list[str]]


def _cmd_add(args: argparse.Namespace) -> list[str]:
    """FR-019: priority -> title -> tags -> load -> add -> save (task T025)."""
    priority = models.validate_priority(
        models.DEFAULT_PRIORITY if args.priority is None else args.priority
    )
    title = models.validate_title(args.title)
    tags = models.normalize_tags(args.tag)
    data = store.load(args.file)
    data, task = service.add_task(data, title, priority, tags)
    store.save(args.file, data)
    return [f"Added task {task.id}: {task.title}"]


def _cmd_list(args: argparse.Namespace) -> list[str]:
    """FR-019: status -> tag -> load; read-only, never saves (FR-013; tasks T025, T053)."""
    status = None if args.status is None else models.validate_status(args.status)
    tag = None if args.tag is None else models.normalize_tags([args.tag])[0]
    data = store.load(args.file)
    tasks = service.list_tasks(data, tag=tag, status=status)
    return [service.format_line(t) for t in tasks] or ["No tasks found."]


def _cmd_status(args: argparse.Namespace) -> list[str]:
    """FR-019: ID -> status -> load -> task exists -> transition -> save (task T042)."""
    task_id = models.parse_task_id(args.id)
    new = models.validate_status(args.status)
    data = store.load(args.file)
    data, old, new = service.set_status(data, task_id, new)
    store.save(args.file, data)
    return [f"Task {task_id}: {old} -> {new}"]


def _cmd_update(args: argparse.Namespace) -> list[str]:
    """FR-019: ID -> priority -> title -> tags -> load -> update rules -> save (task T048)."""
    task_id = models.parse_task_id(args.id)
    priority = None if args.priority is None else models.validate_priority(args.priority)
    title = None if args.title is None else models.validate_title(args.title)
    tags = None if args.tag is None else models.normalize_tags(args.tag)
    data = store.load(args.file)
    data = service.update_task(data, task_id, title, priority, tags, args.clear_tags)
    store.save(args.file, data)
    return [f"Updated task {task_id}."]


def _cmd_delete(args: argparse.Namespace) -> list[str]:
    """FR-019: ID -> load -> task exists -> save (task T048)."""
    task_id = models.parse_task_id(args.id)
    data = store.load(args.file)
    data = service.delete_task(data, task_id)
    store.save(args.file, data)
    return [f"Deleted task {task_id}."]


_HANDLERS: dict[str, Handler] = {
    "add": _cmd_add,
    "list": _cmd_list,
    "update": _cmd_update,
    "delete": _cmd_delete,
    "status": _cmd_status,
}


def _configure_streams() -> None:
    """UTF-8 and LF on every OS, so output is byte-identical (research R7)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_streams()
    try:
        args = build_parser().parse_args(argv)
        lines = _HANDLERS[args.command](args)
        sys.stdout.write("".join(f"{line}\n" for line in lines))
        return 0
    except _Exit as exit_:
        if exit_.message:
            (sys.stdout if exit_.status == 0 else sys.stderr).write(exit_.message)
        return exit_.status
    except UsageError as exc:
        sys.stderr.write(exc.usage + exc.message)
        return exc.exit_code
    except TodoError as exc:
        sys.stderr.write(exc.message + "\n")
        return exc.exit_code
    except KeyboardInterrupt:
        sys.stderr.write(errors.INTERRUPTED + "\n")
        return errors.INTERRUPTED_EXIT_CODE
    except Exception:
        sys.stderr.write(errors.INTERNAL_ERROR + "\n")
        return errors.INTERNAL_ERROR_EXIT_CODE
