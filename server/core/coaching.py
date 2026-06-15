from __future__ import annotations

from typing import Any, Dict, List, Optional

from server.llm import dispatch, prompts
from server.llm.schemas import CoachingFeedback
from server.core.json_utils import parse_json_response


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


def _heuristic_coaching(
    question_text: str,
    answer_text: str,
    competency_scores: Dict[str, float],
    star_feedback: Dict[str, Any],
) -> Dict[str, Any]:
    """Template-based fallback used for the mock provider or when the LLM call fails."""
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


def _build_coaching_prompt(
    question_text: str,
    answer_text: str,
    session: Dict[str, Any],
    star_feedback: Dict[str, Any],
    score_payloads: Optional[List[Dict[str, Any]]],
) -> str:
    rubric = session.get("rubric") or {}
    comps = rubric.get("competencies", [])
    comp_lines = "\n".join(
        f"- {c.get('name')}: {c.get('what_good_looks_like', '')}" for c in comps
    ) or "(none)"

    # Pull the scorers' follow-up notes so coaching can target the same gaps.
    suggestions = []
    for payload in score_payloads or []:
        note = (payload.get("scorecard") or {}).get("follow_up_suggestion")
        if note:
            suggestions.append(note)
    signal = "; ".join(dict.fromkeys(suggestions)) or "none"

    return (
        f"Question:\n{question_text}\n\n"
        f"Candidate's answer:\n{answer_text.strip() or '(no answer given)'}\n\n"
        f"Rubric competencies:\n{comp_lines}\n\n"
        f"STAR assessment: {star_feedback.get('summary', '')}\n"
        f"Scorer follow-up notes: {signal}\n\n"
        "Give specific coaching on THIS answer."
    )


def build_coaching(
    question_text: str,
    answer_text: str,
    competency_scores: Dict[str, float],
    star_feedback: Dict[str, Any],
    session: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    score_payloads: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    provider = dispatch.normalize_provider((session or {}).get("provider", "mock"))

    # Mock or no session context -> use the template fallback.
    if not session or provider == "mock":
        return _heuristic_coaching(question_text, answer_text, competency_scores, star_feedback)

    try:
        prompt = (
            f"{prompts.COACHING_PROMPT}\n\n"
            f"{_build_coaching_prompt(question_text, answer_text, session, star_feedback, score_payloads)}"
        )
        cfg = dispatch.config_from_session(session, api_key=api_key)
        raw = dispatch.call_llm(cfg, prompt, temperature=0.3)
        feedback = CoachingFeedback.model_validate(parse_json_response(raw))
        data = feedback.model_dump()
        data["question"] = question_text
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"LLM coaching failed, falling back to heuristics: {exc}")
        return _heuristic_coaching(question_text, answer_text, competency_scores, star_feedback)
