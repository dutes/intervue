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


# --- adaptive follow-up logic ---

def _session_with_answer(*, overall, missing_example=False, kind="main"):
    """A one-question session where q1 was answered with the given score/flags."""
    return {
        "questions": [{"question_id": "q1", "text": "How did you scale it?", "round": "screening",
                       "persona": "positive", "competency": "X", "kind": kind}],
        "answers": [{"question_id": "q1", "answer_text": "we did stuff"}],
        "scores": [{"question_id": "q1", "persona": "neutral", "overall_score": overall,
                    "scorecard": {"issues": {"vagueness": 0, "missing_example": missing_example}}}],
    }


def test_needs_follow_up_triggers_on_low_score():
    session = _session_with_answer(overall=40.0)
    parent = questions.needs_follow_up(session)
    assert parent is not None and parent["question_id"] == "q1"


def test_needs_follow_up_triggers_on_missing_example_even_if_score_ok():
    session = _session_with_answer(overall=80.0, missing_example=True)
    assert questions.needs_follow_up(session) is not None


def test_needs_follow_up_none_for_strong_answer():
    session = _session_with_answer(overall=85.0)
    assert questions.needs_follow_up(session) is None


def test_needs_follow_up_not_twice_for_same_question():
    session = _session_with_answer(overall=40.0)
    # A follow-up to q1 already exists -> don't follow up again.
    session["questions"].append({"question_id": "q1-f", "text": "deeper?", "kind": "follow_up", "parent_id": "q1"})
    assert questions.needs_follow_up(session) is None


def test_needs_follow_up_respects_global_cap():
    session = _session_with_answer(overall=40.0)
    session["questions"] = [{"question_id": f"f{i}", "kind": "follow_up"} for i in range(questions.MAX_FOLLOWUPS)] + session["questions"]
    assert questions.needs_follow_up(session) is None


def test_main_question_count_excludes_follow_ups():
    session = {"questions": [
        {"question_id": "q1", "kind": "main"},
        {"question_id": "q1-f", "kind": "follow_up"},
        {"question_id": "q2", "kind": "main"},
    ]}
    assert questions.main_question_count(session) == 2
