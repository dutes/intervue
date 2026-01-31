from __future__ import annotations

import hashlib
import random
from typing import Dict, List

from server.llm.schemas import Competency, Rubric, Scorecard

MOCK_COMPETENCIES = [
    ("Problem Solving", 0.18),
    ("Communication", 0.16),
    ("Technical Depth", 0.18),
    ("Collaboration", 0.14),
    ("Product Thinking", 0.18),
    ("Ownership", 0.16),
]


def _rng(seed: str) -> random.Random:
    hashed = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(hashed[:8], 16))


def generate_rubric() -> Rubric:
    competencies = [
        Competency(
            name=name,
            weight=weight,
            what_good_looks_like=f"Demonstrates strong {name.lower()} with clear examples.",
            red_flags=[f"Lacks evidence of {name.lower()}"],
        )
        for name, weight in MOCK_COMPETENCIES
    ]
    return Rubric(competencies=competencies)


def generate_question(session_id: str, round_name: str, persona: str, index: int) -> Dict[str, str]:
    return {
        "question_id": f"q{index+1}",
        "text": f"({persona.title()}) Tell me about a time you demonstrated {round_name} skills relevant to this role.",
        "round": round_name,
        "persona": persona,
    }


def score_answer(session_id: str, question_id: str, rubric: Rubric) -> Scorecard:
    rng = _rng(f"{session_id}:{question_id}")
    competency_scores: Dict[str, int] = {}
    for comp in rubric.competencies:
        competency_scores[comp.name] = rng.randint(1, 4)
    evidence = {
        "star_complete": rng.choice([True, False]),
        "metrics_present": rng.choice([True, False]),
        "specificity": rng.randint(0, 3),
    }
    issues = {
        "vagueness": rng.randint(0, 3),
        "contradiction_with_cv": rng.choice([True, False]),
        "missing_example": rng.choice([True, False]),
    }
    return Scorecard(
        competency_scores=competency_scores,
        evidence_flags=evidence,
        issues=issues,
        follow_up_suggestion="Ask for a concrete metric or outcome.",
    )


def persona_feedback(persona: str, strengths: List[str], weaknesses: List[str]) -> Dict[str, object]:
    return {
        "persona": persona,
        "positives": [f"Shows promise in {strengths[0]}.", f"Solid examples in {strengths[1]}.", "Communicated clearly."],
        "concerns": [f"Needs stronger evidence in {weaknesses[0]}.", f"Consider improving {weaknesses[1]}.", "Examples lacked detail."],
        "next_step": "Prepare a STAR story with metrics for a recent project.",
    }


def test_connection() -> None:
    return None
