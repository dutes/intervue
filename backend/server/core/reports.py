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

    # Radar chart
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

    # Line chart
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

    # Persona bar chart
    fig = plt.figure(figsize=(6, 4))
    ax = plt.gca()
    personas = list(persona_avgs.keys())
    scores = list(persona_avgs.values())
    ax.bar(personas, scores, color=["#4caf50", "#2196f3", "#f44336"])
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
        return [mock.persona_feedback(persona, strengths or ["Execution", "Communication"], weaknesses or ["Clarity", "Depth"]) for persona in ["positive", "neutral", "hostile"]]

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

def build_report(session: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    scores = session.get("scores", [])
    overall_scores = compute_question_overall_scores(scores)
    # Heuristic overall score (kept for charts/fallback)
    heuristic_score = round(_avg(overall_scores), 2)

    competency_avgs = compute_competency_averages(scores)
    
    persona_avgs = compute_persona_averages(scores)
    report_paths = generate_charts(session["session_id"], competency_avgs, overall_scores, persona_avgs)

    # Call LLM for qualitative feedback & final score
    try:
        grading_result = grading.generate_report(session)
        overall_score = grading_result["overall_score"] * 100  # Convert 0-1 to 0-100 if needed, or keep 0-1
        # Re-scale if grading returns 0.0-1.0 and we want 0-100. Schema says 0.0-1.0. App uses 0-100 usually?
        # heuristic_score is 0-100 (avg of rubrics).
        # Rubric scores are 0-4? compute_question_overall_scores seems to return 0-100?
        # compute_question_overall_scores uses "overall_score" from score_payload.
        # scoring.py: overall_score is calculate_score() -> which returns 0-100.
        # So heuristic_score is 0-100.
        # grading_result["overall_score"] is 0.0-1.0 (per prompt rules).
        # Let's multiply by 100 to match conventions.
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

    report_payload = {
        "session_id": session["session_id"],
        "overall_score": overall_score,
        "competency_averages": competency_avgs,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overall_scores": overall_scores,
        "persona_averages": persona_avgs,
        "persona_feedback": persona_feedback,
        "report_paths": report_paths,
    }
    save_report(session["session_id"], report_payload)
    return report_payload, report_paths
