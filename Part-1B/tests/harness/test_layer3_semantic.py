"""US3 tests for harness layer 3, semantic scoring (T041).

Covers FR-036, AC-41 to AC-44 and AC-58; whole-word keyword matching per research R-12.
"""

from __future__ import annotations

import layer3_semantic as l3
import pytest
from conftest import decision


def _case(intent="create", due="2026-11-11T09:00:00+05:30", keywords=("call", "mom")):
    return {"expected_intent": intent, "expected_due_at": due,
            "expected_task_keywords": list(keywords)}


def test_us3_ac41_full_score_with_59s_offset_and_half_recall():
    """AC-41: intent match, due_at 59 s off, recall 0.5 -> score 1.0."""
    d = decision(intent="create", task="call the bank", due_at="2026-11-11T09:00:59+05:30")
    s = l3.semantic_score(d, _case())
    assert (s["intent"], s["due_at"], s["recall"], s["keywords"], s["score"]) == \
        (0.4, 0.4, 0.5, 0.2, 1.0)


def test_us3_ac42_due_at_two_minutes_off():
    """AC-42: intent match, due_at 2 min off, recall 1.0 -> score 0.6."""
    d = decision(intent="create", task="call mom", due_at="2026-11-11T09:02:00+05:30")
    assert l3.semantic_score(d, _case())["score"] == 0.6


def test_us3_ac43_both_due_at_null():
    """AC-43: expected and actual due_at both null -> the due_at component gives 0.4."""
    d = decision(intent="clarify", clarification_question="When?")
    s = l3.semantic_score(d, _case(intent="clarify", due=None, keywords=()))
    assert s["due_at"] == 0.4 and s["score"] == 1.0


def test_us3_ac44_empty_keywords_full_recall():
    """AC-44: an empty keyword list gives recall 1.0 and the 0.2 component."""
    d = decision(intent="refuse", refusal_reason="No.")
    s = l3.semantic_score(d, _case(intent="refuse", due=None, keywords=()))
    assert s["recall"] == 1.0 and s["keywords"] == 0.2


def test_us3_ac58_low_recall_scores_08():
    """AC-58: intent and due_at match but recall < 0.5 -> score 0.8."""
    d = decision(intent="create", task="phone her", due_at="2026-11-11T09:00:00+05:30")
    s = l3.semantic_score(d, _case())
    assert s["recall"] == 0.0 and s["score"] == 0.8


def test_us3_null_task_has_zero_recall():
    """FR-036: a null task has recall 0 (when keywords are expected)."""
    assert l3.keyword_recall(None, ["call"]) == 0.0


@pytest.mark.parametrize("task, keywords, recall", [
    ("recall the order", ["call"], 0.0),          # whole word only
    ("Call Mom", ["call", "mom"], 1.0),           # case-insensitive
    ("buy milk.", ["milk"], 1.0),                 # punctuation boundary
    ("stand-up meeting", ["stand-up"], 1.0),       # keyword with a hyphen
])
def test_us3_keyword_matching_rules(task, keywords, recall):
    """R-12, FR-036: whole-word, case-insensitive keyword matching."""
    assert l3.keyword_recall(task, keywords) == recall


def test_us3_one_null_due_at_scores_zero_component():
    """FR-036: one of expected/actual due_at null and the other not -> 0 for due_at."""
    d = decision(intent="clarify", clarification_question="When?")
    assert l3.semantic_score(d, _case(intent="clarify"))["due_at"] == 0.0
