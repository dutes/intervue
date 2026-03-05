from __future__ import annotations

from typing import Any, Dict, List


def _round2(value: float) -> float:
    return round(value, 2)


def aggregate_competencies(score_payloads: List[Dict[str, Any]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for payload in score_payloads:
        scorecard = payload.get("scorecard", {})
        comp_scores = scorecard.get("competency_scores", {})
        for name, score in comp_scores.items():
            totals[name] = totals.get(name, 0.0) + float(score)
            counts[name] = counts.get(name, 0) + 1
    return {name: _round2((totals[name] / counts[name]) * 25.0) for name in totals}


def aggregate_star(score_payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not score_payloads:
        return {
            "star_complete": False,
            "metrics_present": False,
            "specificity": 0,
            "summary": "No STAR signal available.",
        }

    total = len(score_payloads)
    star_true = 0
    metrics_true = 0
    specificity_total = 0

    for payload in score_payloads:
        scorecard = payload.get("scorecard", {})
        flags = scorecard.get("evidence_flags", {})
        if flags.get("star_complete"):
            star_true += 1
        if flags.get("metrics_present"):
            metrics_true += 1
        specificity_total += int(flags.get("specificity", 0))

    star_complete = star_true >= 2
    metrics_present = metrics_true >= 2
    specificity = _round2(specificity_total / total)

    if star_complete and metrics_present and specificity >= 2:
        summary = "Strong STAR structure with concrete outcomes."
    elif not star_complete:
        summary = "Incomplete STAR story. Add clearer situation, action, and result."
    elif not metrics_present:
        summary = "Good structure, but add measurable impact."
    else:
        summary = "Decent structure. Increase specificity with concrete details."

    return {
        "star_complete": star_complete,
        "metrics_present": metrics_present,
        "specificity": specificity,
        "summary": summary,
    }


def build_coaching(
    question_text: str,
    answer_text: str,
    competency_scores: Dict[str, float],
    star_feedback: Dict[str, Any],
) -> Dict[str, Any]:
    ranked = sorted(competency_scores.items(), key=lambda item: item[1], reverse=True)
    top = [name for name, _ in ranked[:2]]
    low = [name for name, _ in ranked[-2:]] if ranked else []

    strengths = [
        f"You showed solid evidence in {top[0]}." if top else "You addressed the question directly.",
        f"You also demonstrated {top[1]}." if len(top) > 1 else "Your answer had a clear structure.",
    ]

    improvements = [
        f"Improve {low[0]} with one specific example." if low else "Add one concrete example.",
        "Quantify impact with at least one metric."
        if not star_feedback.get("metrics_present")
        else "Tighten phrasing to be more concise and specific.",
    ]

    rewritten_answer = (
        "Situation: In my previous role, we faced a time-sensitive challenge similar to this area. "
        "Task: I was responsible for leading the resolution and aligning stakeholders. "
        "Action: I defined a clear plan, executed it with the team, and tracked execution with explicit checkpoints. "
        "Result: We delivered the outcome on time and improved quality, with measurable impact against our baseline."
    )

    if answer_text.strip():
        rewritten_answer = (
            f"{answer_text.strip()}\n\n"
            "Improved STAR rewrite:\n"
            f"{rewritten_answer}"
        )

    return {
        "question": question_text,
        "strengths": strengths,
        "improvements": improvements,
        "rewrite": rewritten_answer,
    }
