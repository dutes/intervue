"""Tests for question-flow logic — round math, persona rotation, prompt assembly."""
import pytest

from server.core import questions


@pytest.mark.parametrize(
    "start_round, expected_total",
    [(1, 10), (2, 7), (3, 3)],  # 3+4+3 from round 1; 4+3 from round 2; 3 from round 3
)
def test_total_questions_by_start_round(start_round, expected_total):
    assert questions.total_questions(start_round) == expected_total


@pytest.mark.parametrize(
    "index, expected_round",
    [
        (0, "screening"),
        (2, "screening"),
        (3, "deep_dive"),
        (6, "deep_dive"),
        (7, "challenge"),
        (9, "challenge"),
    ],
)
def test_round_for_index(index, expected_round):
    round_info, _round_num = questions.round_for_index(index, start_round=1)
    assert round_info["name"] == expected_round


def test_persona_rotates_per_round():
    assert questions.ROUND_PERSONA["screening"] == "positive"
    assert questions.ROUND_PERSONA["deep_dive"] == "neutral"
    assert questions.ROUND_PERSONA["challenge"] == "hostile"


def test_target_competency_is_highest_weight_first(sample_session):
    # Technical Depth has the highest weight (0.5), so index 0 should target it.
    target = questions._select_target_competency(sample_session, index=0)
    assert target["name"] == "Technical Depth"


def test_previous_qa_block_surfaces_drill_signals(sample_session):
    # Simulate a weak answer: vague, no example, with a follow-up suggestion.
    scorecard = sample_session["scores"][0]["scorecard"]
    scorecard["issues"] = {"vagueness": 3, "missing_example": True, "contradiction_with_cv": False}
    scorecard["follow_up_suggestion"] = "Ask for the specific bottleneck."

    block = questions._previous_qa_block(sample_session)

    assert "I profiled queries" in block          # the answer is included
    assert "Drill here" in block                  # weak-answer signal fired
    assert "Ask for the specific bottleneck." in block
