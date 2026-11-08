"""Command-line interface (task T032; contracts/interfaces.md section 2; spec FR-002).

Exit codes: 0 decision, 2 usage error, 3 input_error, 4 infra_error.
The decision goes to stdout as one JSON line; errors go to stderr as error JSON.
The API key is never accepted as a flag.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from .agent import run_agent
from .client import ModelClient
from .config import ConfigError, load_config

EXIT_OK, EXIT_USAGE, EXIT_INPUT_ERROR, EXIT_INFRA_ERROR = 0, 2, 3, 4


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reminder-agent",
        description="Turn a natural-language request into one reminder decision (JSON).")
    parser.add_argument("--text", help="the user's request")
    parser.add_argument("--now", help="current datetime, ISO-8601")
    parser.add_argument("--timezone", help="IANA timezone name, e.g. Asia/Kolkata")
    parser.add_argument("--reminders", type=Path,
                        help="JSON file with existing reminders [{id, task, due_at}]")
    parser.add_argument("--stdin", action="store_true",
                        help='read {"text","now","timezone","existing_reminders"} JSON from stdin')
    parser.add_argument("--model")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--config", type=Path, help="alternative settings.toml")
    return parser


def main(argv: list[str] | None = None, *, client: ModelClient | None = None,
         stdin: TextIO | None = None, stdout: TextIO | None = None,
         stderr: TextIO | None = None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.stdin:
        try:
            payload = json.loads(stdin.read())
        except json.JSONDecodeError as exc:
            print(f"reminder-agent: invalid JSON on stdin: {exc.msg}", file=stderr)
            return EXIT_USAGE
        text, now, timezone = payload.get("text"), payload.get("now"), payload.get("timezone")
        reminders = payload.get("existing_reminders")
    else:
        if args.text is None or args.now is None or args.timezone is None:
            print("reminder-agent: --text, --now and --timezone are required (or use --stdin)",
                  file=stderr)
            return EXIT_USAGE
        text, now, timezone = args.text, args.now, args.timezone
        reminders = None
        if args.reminders is not None:
            try:
                reminders = json.loads(args.reminders.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"reminder-agent: cannot read --reminders: {exc}", file=stderr)
                return EXIT_USAGE

    try:
        config = load_config(path=args.config, overrides={
            "model": args.model, "max_tokens": args.max_tokens, "temperature": args.temperature})
    except ConfigError as exc:
        print(f"reminder-agent: configuration error: {exc}", file=stderr)
        return EXIT_USAGE

    outcome = run_agent(text, now, timezone, reminders, client=client, config=config)
    if outcome.error is not None:
        print(json.dumps(outcome.error.to_json(), ensure_ascii=False), file=stderr)
        return EXIT_INPUT_ERROR if outcome.error.status == "input_error" else EXIT_INFRA_ERROR
    print(json.dumps(outcome.decision.to_json(), ensure_ascii=False), file=stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
