from __future__ import annotations

from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from server.core.storage import REPORTS_DIR, save_report
from server.llm import mock
from server.llm.schemas import PersonaFeedback


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_competency_averages(scores: List[Dict[str, Any]]) -> Dict[str, float]:
    totals: Dict[str, List[float]] = {}
    for entry in scores:
        for name, score in entry["scorecard"]["competency_scores"].items():
            totals.setdefault(name, []).append(score)
    return {name: round(_avg(vals) * 25, 2) for name, vals in totals.items()}


def compute_competency_trends(scores: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    per_question: Dict[str, Dict[str, List[float]]] = {}
    for score in scores:
        qid = score["question_id"]
        comp_scores = score.get("scorecard", {}).get("competency_scores", {})
        if qid not in per_question:
            per_question[qid] = {}
        for competency, value in comp_scores.items():
            per_question[qid].setdefault(competency, []).append(float(value))

    ordered_qids = sorted(per_question.keys())
    series_map: Dict[str, List[float]] = {}
    for qid in ordered_qids:
        for competency, values in per_question[qid].items():
            avg_score = round(_avg(values) * 25, 2)
            series_map.setdefault(competency, []).append(avg_score)

    trends: Dict[str, Dict[str, Any]] = {}
    for competency, series in series_map.items():
        if len(series) < 2:
            delta = 0.0
            trend = "stable"
        else:
            delta = round(series[-1] - series[0], 2)
            if delta >= 5:
                trend = "improving"
            elif delta <= -5:
                trend = "declining"
            else:
                trend = "stable"
        trends[competency] = {"series": series, "delta": delta, "trend": trend}

    return trends


def build_7_day_plan(strengths: List[str], weaknesses: List[str], competency_trends: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    weak_focus = weaknesses[0] if weaknesses else "Answer clarity"
    secondary_focus = weaknesses[1] if len(weaknesses) > 1 else "Structured storytelling"

    declining = [name for name, item in competency_trends.items() if item.get("trend") == "declining"]
    decline_focus = declining[0] if declining else weak_focus

    strong_focus = strengths[0] if strengths else "Communication"

    return [
        {"day": "Day 1", "focus": weak_focus, "task": f"Write 5 STAR stories focused on {weak_focus}."},
        {"day": "Day 2", "focus": "Metrics", "task": "Add measurable outcomes to 5 past-project examples."},
        {"day": "Day 3", "focus": secondary_focus, "task": f"Record 20 minutes of answers and tighten weak spots in {secondary_focus}."},
        {"day": "Day 4", "focus": decline_focus, "task": f"Run a mock round targeting {decline_focus} and review mistakes."},
        {"day": "Day 5", "focus": "Pressure mode", "task": "Practice 30 minutes with timed answers and no pauses."},
        {"day": "Day 6", "focus": strong_focus, "task": f"Leverage your strength in {strong_focus} with deeper examples and tradeoff discussion."},
        {"day": "Day 7", "focus": "Full simulation", "task": "Complete a full interview session and compare score deltas by competency."},
    ]


def compute_persona_averages(scores: List[Dict[str, Any]]) -> Dict[str, float]:
    bucket: Dict[str, List[float]] = {}
    for score in scores:
        persona = score.get("persona", "neutral")
        bucket.setdefault(persona, []).append(score["overall_score"])
    return {persona: round(_avg(vals), 2) for persona, vals in bucket.items()}


def compute_question_overall_scores(scores: List[Dict[str, Any]]) -> List[float]:
    buckets: Dict[str, List[float]] = {}
    for score in scores:
        question_id = score["question_id"]
        buckets.setdefault(question_id, []).append(score["overall_score"])
    return [round(_avg(values), 2) for _qid, values in sorted(buckets.items())]


def generate_charts(session_id: str, competency_avgs: Dict[str, float], overall_scores: List[float], persona_avgs: Dict[str, float]) -> Dict[str, str]:
    report_dir = REPORTS_DIR / session_id
    report_dir.mkdir(parents=True, exist_ok=True)

    labels = list(competency_avgs.keys())
    values = list(competency_avgs.values())
    if labels:
        angles = [n / float(len(labels)) * 2 * 3.14159 for n in range(len(labels))]
        values += values[:1]
        angles += angles[:1]
        fig = plt.figure(figsize=(6, 6))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles, values, "o-", linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids([a * 180 / 3.14159 for a in angles[:-1]], labels)
        ax.set_ylim(0, 100)
        radar_path = report_dir / "competency_radar.png"
        plt.tight_layout()
        plt.savefig(radar_path)
        plt.close(fig)
    else:
        radar_path = report_dir / "competency_radar.png"

    fig = plt.figure(figsize=(7, 4))
    ax = plt.gca()
    ax.plot(range(1, len(overall_scores) + 1), overall_scores, marker="o")
    ax.set_xlabel("Question #")
    ax.set_ylabel("Overall Score")
    ax.set_ylim(0, 100)
    ax.set_title("Score Over Time")
    line_path = report_dir / "score_over_time.png"
    plt.tight_layout()
    plt.savefig(line_path)
    plt.close(fig)

    fig = plt.figure(figsize=(6, 4))
    ax = plt.gca()
    personas = list(persona_avgs.keys())
    persona_scores = list(persona_avgs.values())
    ax.bar(personas, persona_scores, color=["#4caf50", "#2196f3", "#f44336"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Average Score")
    ax.set_title("Persona Comparison")
    bar_path = report_dir / "persona_comparison.png"
    plt.tight_layout()
    plt.savefig(bar_path)
    plt.close(fig)

    return {
        "competency_radar": str(radar_path),
        "score_over_time": str(line_path),
        "persona_comparison": str(bar_path),
    }


def _safe_label(items: List[str], index: int, fallback: str) -> str:
    return items[index] if len(items) > index else fallback


def generate_persona_feedback(session: Dict[str, Any], strengths: List[str], weaknesses: List[str]) -> List[Dict[str, Any]]:
    if session["provider"] == "mock":
        return [
            mock.persona_feedback(persona, strengths or ["Execution", "Communication"], weaknesses or ["Clarity", "Depth"])
            for persona in ["positive", "neutral", "hostile"]
        ]

    feedback: List[Dict[str, Any]] = []
    strength_one = _safe_label(strengths, 0, "Execution")
    strength_two = _safe_label(strengths, 1, "Communication")
    weakness_one = _safe_label(weaknesses, 0, "Clarity")
    weakness_two = _safe_label(weaknesses, 1, "Depth")
    for persona in ["positive", "neutral", "hostile"]:
        positives = [f"Strong {strength_one} evidence.", f"Clear communication in {strength_two}.", "Good engagement."]
        concerns = [f"Needs more detail in {weakness_one}.", f"Improve clarity on {weakness_two}.", "Examples could be tighter."]
        feedback.append(
            PersonaFeedback(
                persona=persona,
                positives=positives,
                concerns=concerns,
                next_step="Prepare one quantified example for your next interview.",
            ).model_dump()
        )
    return feedback


from server.core import grading


def build_report(session: Dict[str, Any], api_key: str | None = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    scores = session.get("scores", [])
    overall_scores = compute_question_overall_scores(scores)
    heuristic_score = round(_avg(overall_scores), 2)

    competency_avgs = compute_competency_averages(scores)
    competency_trends = compute_competency_trends(scores)
    persona_avgs = compute_persona_averages(scores)
    report_paths = generate_charts(session["session_id"], competency_avgs, overall_scores, persona_avgs)

    try:
        grading_result = grading.generate_report(session, api_key=api_key)
        overall_score = round(grading_result["overall_score"] * 100, 2)
        strengths = grading_result["strengths"]
        weaknesses = grading_result["weaknesses"]
        persona_feedback = grading_result["persona_feedback"]
    except Exception as e:
        print(f"LLM Grading failed, falling back to heuristics: {e}")
        overall_score = heuristic_score
        sorted_competencies = sorted(competency_avgs.items(), key=lambda item: item[1], reverse=True)
        strengths = [name for name, _ in sorted_competencies[:3]]
        weaknesses = [name for name, _ in sorted_competencies[-3:]]
        persona_feedback = generate_persona_feedback(session, strengths, weaknesses)

    practice_plan = build_7_day_plan(strengths, weaknesses, competency_trends)

    report_payload = {
        "session_id": session["session_id"],
        "overall_score": overall_score,
        "competency_averages": competency_avgs,
        "competency_trends": competency_trends,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overall_scores": overall_scores,
        "persona_averages": persona_avgs,
        "persona_feedback": persona_feedback,
        "practice_plan_7_day": practice_plan,
        "report_paths": report_paths,
    }
    save_report(session["session_id"], report_payload)
    return report_payload, report_paths
