from __future__ import annotations

import math
import textwrap
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


def build_7_day_plan(weak_competencies: List[str], strong_competencies: List[str]) -> List[Dict[str, str]]:
    # Use short competency names as focus topics so the tasks read cleanly.
    weak_focus = weak_competencies[0] if weak_competencies else "Answer clarity"
    secondary_focus = weak_competencies[1] if len(weak_competencies) > 1 else "Structured storytelling"
    strong_focus = strong_competencies[0] if strong_competencies else "Communication"

    return [
        {"day": "Day 1", "focus": weak_focus, "task": f"Write 5 STAR stories that demonstrate {weak_focus}."},
        {"day": "Day 2", "focus": "Metrics", "task": "Add measurable outcomes to 5 past-project examples."},
        {"day": "Day 3", "focus": secondary_focus, "task": f"Record 20 minutes of answers and tighten weak spots in {secondary_focus}."},
        {"day": "Day 4", "focus": weak_focus, "task": f"Run a mock round targeting {weak_focus} and review your mistakes."},
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


def generate_charts(session_id: str, competency_avgs: Dict[str, float], overall_scores: List[float]) -> Dict[str, str]:
    report_dir = REPORTS_DIR / session_id
    report_dir.mkdir(parents=True, exist_ok=True)

    labels = list(competency_avgs.keys())
    values = list(competency_avgs.values())
    radar_path = report_dir / "competency_radar.png"
    if labels:
        angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
        loop_values = values + values[:1]
        loop_angles = angles + angles[:1]

        # Larger canvas + start at top, going clockwise, so labels have room.
        fig = plt.figure(figsize=(9, 9))
        ax = plt.subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.plot(loop_angles, loop_values, "o-", linewidth=2, color="#6366f1")
        ax.fill(loop_angles, loop_values, alpha=0.25, color="#6366f1")

        # Wrap long competency names onto multiple lines and push them off the plot.
        wrapped = ["\n".join(textwrap.wrap(lbl, 16)) for lbl in labels]
        ax.set_thetagrids([math.degrees(a) for a in angles], wrapped, fontsize=9)
        ax.tick_params(axis="x", pad=22)

        # Align each label to the side it sits on so it leans away from the chart.
        for label, angle in zip(ax.get_xticklabels(), angles):
            deg = math.degrees(angle)
            if deg in (0, 180):
                label.set_horizontalalignment("center")
            elif deg < 180:
                label.set_horizontalalignment("left")
            else:
                label.set_horizontalalignment("right")

        ax.set_ylim(0, 100)
        fig.subplots_adjust(left=0.22, right=0.78, top=0.82, bottom=0.18)
        plt.savefig(radar_path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    fig = plt.figure(figsize=(7, 4))
    ax = plt.gca()
    xs = list(range(1, len(overall_scores) + 1))
    ax.plot(xs, overall_scores, marker="o", color="#6366f1", linewidth=2)
    ax.fill_between(xs, overall_scores, color="#6366f1", alpha=0.12)
    ax.set_xlabel("Question #")
    ax.set_ylabel("Overall Score")
    ax.set_ylim(0, 100)
    if xs:
        ax.set_xticks(xs)
    ax.set_title("Score Over Time")
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    line_path = report_dir / "score_over_time.png"
    plt.tight_layout()
    plt.savefig(line_path, dpi=120)
    plt.close(fig)

    return {
        "competency_radar": str(radar_path),
        "score_over_time": str(line_path),
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


def build_transcript(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assemble the per-question record (question, the answer, score and coaching) from data
    already stored on the session — no extra LLM calls."""
    answers_by_id = {a.get("question_id"): a for a in session.get("answers", [])}
    coaching_by_id: Dict[str, Dict[str, Any]] = {}
    for log in session.get("logs", []):
        if log.get("type") == "coaching":
            coaching_by_id[log.get("question_id")] = log.get("parsed", {})

    transcript: List[Dict[str, Any]] = []
    for question in session.get("questions", []):
        qid = question.get("question_id")
        answer = answers_by_id.get(qid)
        if not answer:
            continue  # only include questions the candidate actually answered
        parsed = coaching_by_id.get(qid, {})
        coaching = parsed.get("coaching", {}) or {}
        star = parsed.get("star_feedback", {}) or {}
        transcript.append(
            {
                "question_id": qid,
                "question": question.get("text", ""),
                "round": question.get("round", ""),
                "competency": question.get("competency", ""),
                "anchor": question.get("anchor", ""),
                "answer": answer.get("answer_text", ""),
                "score": parsed.get("average_overall"),
                "star_summary": star.get("summary", ""),
                "strengths": coaching.get("strengths", []),
                "improvements": coaching.get("improvements", []),
                "rewrite": coaching.get("rewrite", ""),
                "delivery_notes": (answer.get("delivery") or {}).get("notes", []),
                "ideal_answer": coaching.get("ideal_answer", ""),
            }
        )
    return transcript


def build_report(session: Dict[str, Any], api_key: str | None = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    scores = session.get("scores", [])
    overall_scores = compute_question_overall_scores(scores)
    heuristic_score = round(_avg(overall_scores), 2)

    competency_avgs = compute_competency_averages(scores)
    persona_avgs = compute_persona_averages(scores)
    report_paths = generate_charts(session["session_id"], competency_avgs, overall_scores)

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

    # Drive the practice plan off short competency names (weakest first) so tasks read cleanly,
    # regardless of whether strengths/weaknesses came back as full sentences from the LLM.
    ranked_competencies = sorted(competency_avgs.items(), key=lambda item: item[1])
    weak_competencies = [name for name, _ in ranked_competencies[:2]]
    strong_competencies = [name for name, _ in reversed(ranked_competencies[-2:])]
    practice_plan = build_7_day_plan(weak_competencies, strong_competencies)

    report_payload = {
        "session_id": session["session_id"],
        "overall_score": overall_score,
        "competency_averages": competency_avgs,
        "transcript": build_transcript(session),
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
