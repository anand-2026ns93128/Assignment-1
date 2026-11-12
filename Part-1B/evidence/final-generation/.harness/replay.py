"""Replay client over saved raw responses (task T052; spec FR-041).

Each raw file stores the attempts of one case in order: a saved reply, or a saved infra error.
Replaying feeds them back through the same agent post-processing, so statuses, scores, fallback
flags and the verdict are reproduced without any model call.
"""

from __future__ import annotations

import json
from pathlib import Path

from reminder_agent.client import ModelCallError
from reminder_agent.models import ModelReply


def load_raw(run_dir: Path, case_id: str) -> dict:
    path = Path(run_dir) / "raw" / f"{case_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"raw response missing for case {case_id}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class _CaseReplay:
    def __init__(self, case_id: str, attempts: list[dict]) -> None:
        self.case_id = case_id
        self.attempts = list(attempts)

    def complete(self, request) -> ModelReply:
        if not self.attempts:
            raise RuntimeError(f"replay for {self.case_id} has no more saved attempts")
        item = self.attempts.pop(0)
        if "error" in item:
            err = item["error"]
            raise ModelCallError(err["category"], err["message"], bool(err.get("retryable")))
        return ModelReply.from_json(item["reply"])


class ReplayClient:
    """Factory for per-case replay clients over ``<run_dir>/raw/<case_id>.json``."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)

    def for_case(self, case_id: str) -> _CaseReplay:
        return _CaseReplay(case_id, load_raw(self.run_dir, case_id)["attempts"])
