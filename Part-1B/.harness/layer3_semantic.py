"""Harness layer 3: semantic scoring (task T049; spec FR-036; research R-12).

score = 0.4 (intent match) + 0.4 (due_at within ±1 minute, or both null)
      + 0.2 (task keyword recall >= 0.5)
Keywords match as whole words or phrases, case-insensitively. Deterministic; no model judge.
"""

from __future__ import annotations

import re
from datetime import datetime

TOLERANCE_SECONDS = 60
W_INTENT, W_DUE, W_KEYWORDS = 0.4, 0.4, 0.2
RECALL_THRESHOLD = 0.5


def keyword_recall(task: str | None, keywords: list[str]) -> float:
    """Fraction of expected keywords present in ``task``; empty list -> 1.0, null task -> 0."""
    if not keywords:
        return 1.0
    if not task:
        return 0.0
    text = task.lower()
    hits = sum(1 for kw in keywords
               if re.search(r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)", text))
    return round(hits / len(keywords), 4)


def _due_matches(actual: str | None, expected: str | None) -> bool:
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    try:
        delta = datetime.fromisoformat(actual) - datetime.fromisoformat(expected)
    except (TypeError, ValueError):
        return False
    return abs(delta.total_seconds()) <= TOLERANCE_SECONDS


def semantic_score(decision: dict, case: dict) -> dict:
    """Components and total for one decision against its case's ground truth."""
    intent = W_INTENT if decision.get("intent") == case["expected_intent"] else 0.0
    due = W_DUE if _due_matches(decision.get("due_at"), case.get("expected_due_at")) else 0.0
    recall = keyword_recall(decision.get("task"), case.get("expected_task_keywords", []))
    keywords = W_KEYWORDS if recall >= RECALL_THRESHOLD else 0.0
    return {"intent": intent, "due_at": due, "keywords": keywords, "recall": recall,
            "score": round(intent + due + keywords, 4)}
