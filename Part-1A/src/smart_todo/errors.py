"""Error types and the exact user-facing messages (spec: Exit Codes, Error Messages).

Task T011. Every message here is copied verbatim from the spec.
"""

from __future__ import annotations

INTERRUPTED = "Error: interrupted."
INTERNAL_ERROR = "Error: unexpected internal error."
INTERRUPTED_EXIT_CODE = 130
INTERNAL_ERROR_EXIT_CODE = 1


class TodoError(Exception):
    """An expected failure with a user-facing message and an exit code."""

    exit_code = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InputError(TodoError):
    """Invalid input or a rule violation (exit code 1)."""

    exit_code = 1


class UsageError(TodoError):
    """Command-line usage error (exit code 2); carries the usage text."""

    exit_code = 2

    def __init__(self, message: str, usage: str = "") -> None:
        super().__init__(message)
        self.usage = usage


class DataFileError(TodoError):
    """Data file corrupt, unreadable or not saved (exit code 3)."""

    exit_code = 3


def corrupt_file(path: str) -> DataFileError:
    return DataFileError(
        f"Error: data file '{path}' is corrupt or unreadable; it was not modified."
    )


def save_failed(path: str) -> DataFileError:
    return DataFileError(f"Error: could not save data file '{path}'; previous data was kept.")


def task_not_found(task_id: int) -> InputError:
    return InputError(f"Error: task {task_id} not found.")


def invalid_task_id(raw: str) -> InputError:
    return InputError(f"Error: invalid task ID '{raw}'.")


def invalid_priority(raw: str) -> InputError:
    return InputError(f"Error: invalid priority '{raw}' (expected: low, medium, high).")


def invalid_status(raw: str) -> InputError:
    return InputError(f"Error: invalid status '{raw}' (expected: todo, in_progress, done).")


def invalid_tag(raw: str) -> InputError:
    return InputError(
        f"Error: invalid tag '{raw}' (tags must be 1-20 characters: letters, digits, '-' or '_')."
    )


def invalid_title() -> InputError:
    return InputError("Error: title must be 1-100 characters on a single line.")


def invalid_transition(task_id: int, old: str, new: str) -> InputError:
    return InputError(f"Error: cannot change status of task {task_id} from {old} to {new}.")


def nothing_to_update() -> InputError:
    return InputError("Error: nothing to update (use --title, --priority, --tag or --clear-tags).")


def tag_clear_conflict() -> InputError:
    return InputError("Error: --tag and --clear-tags cannot be used together.")
