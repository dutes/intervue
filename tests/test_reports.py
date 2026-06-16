"""Tests for report assembly — pure aggregation + transcript building."""
from server.core import reports


def test_compute_competency_averages():
    scores = [
        {"scorecard": {"competency_scores": {"QA": 4}}},
        {"scorecard": {"competency_scores": {"QA": 2}}},
    ]
    # mean of 4 and 2 is 3; the report scales 0-4 -> 0-100 (x25), so 75.0
    assert reports.compute_competency_averages(scores) == {"QA": 75.0}


def test_compute_question_overall_scores_groups_by_question_and_sorts():
    scores = [
        {"question_id": "q1", "overall_score": 60},
        {"question_id": "q1", "overall_score": 80},
        {"question_id": "q2", "overall_score": 50},
    ]
    # q1 averages to 70, q2 to 50; result ordered by question id
    assert reports.compute_question_overall_scores(scores) == [70.0, 50.0]


def test_build_7_day_plan_reads_cleanly():
    plan = reports.build_7_day_plan(["People Leadership"], ["QA Strategy"])
    assert len(plan) == 7
    assert "People Leadership" in plan[0]["task"]
    assert ".." not in plan[0]["task"]  # guards against the old double-period bug


def test_build_transcript_assembles_answered_questions(sample_session):
    transcript = reports.build_transcript(sample_session)

    assert len(transcript) == 1
    entry = transcript[0]
    assert entry["question"].startswith("How did you cut latency")
    assert entry["answer"] == "I profiled queries and added an index."
    assert entry["score"] == 75.0
    assert entry["rewrite"].startswith("Situation")


def test_build_transcript_skips_unanswered_questions(sample_session):
    # Add a second question with no matching answer — it must be excluded.
    sample_session["questions"].append(
        {"question_id": "q2", "text": "An unanswered question", "round": "screening"}
    )
    transcript = reports.build_transcript(sample_session)
    assert [entry["question_id"] for entry in transcript] == ["q1"]
