"""Shared pytest fixtures.

A fixture is reusable setup. Define it once here with @pytest.fixture, then any test
in the suite can receive it just by listing its name as a function argument — pytest
matches the argument name to the fixture and injects the return value.
"""
import pytest


@pytest.fixture
def sample_rubric():
    """A small rubric with deliberately unequal weights (so weight-ordering is testable)."""
    return {
        "competencies": [
            {"name": "Technical Depth", "weight": 0.5, "what_good_looks_like": "Explains tradeoffs", "red_flags": ["hand-wavy"]},
            {"name": "Communication", "weight": 0.3, "what_good_looks_like": "Clear and concise", "red_flags": ["rambling"]},
            {"name": "Ownership", "weight": 0.2, "what_good_looks_like": "Drives outcomes", "red_flags": ["passive"]},
        ]
    }


@pytest.fixture
def sample_session(sample_rubric):
    """A minimal but realistic session dict with one answered question.

    Note this fixture *uses another fixture* (sample_rubric) just by naming it as an
    argument — fixtures can depend on fixtures.
    """
    return {
        "session_id": "test-session",
        "provider": "mock",
        "start_round": 1,
        "job_spec": "Senior Backend Engineer scaling Postgres.",
        "cv_text": "Built payments API at Acme; cut latency 40%.",
        "rubric": sample_rubric,
        "persona": {"name": "Dana", "role": "EM", "tone": "Direct", "key_concerns": ["scale"]},
        "questions": [
            {
                "question_id": "q1",
                "text": "How did you cut latency 40%?",
                "round": "screening",
                "persona": "positive",
                "competency": "Technical Depth",
                "anchor": "cut latency 40%",
            },
        ],
        "answers": [
            {"question_id": "q1", "answer_text": "I profiled queries and added an index."},
        ],
        "scores": [
            {
                "question_id": "q1",
                "persona": "neutral",
                "overall_score": 75.0,
                "scorecard": {"competency_scores": {"Technical Depth": 3, "Communication": 3, "Ownership": 3}},
            },
        ],
        "logs": [
            {
                "type": "coaching",
                "question_id": "q1",
                "parsed": {
                    "average_overall": 75.0,
                    "star_feedback": {"summary": "Add a concrete metric."},
                    "coaching": {
                        "strengths": ["Clear, methodical approach"],
                        "improvements": ["Quantify the impact"],
                        "rewrite": "Situation: ... Result: cut p95 from 800ms to 480ms.",
                    },
                },
            },
        ],
    }
