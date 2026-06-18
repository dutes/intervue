from __future__ import annotations

import json
from typing import Any, Dict, List

from server.core import state
from server.core.json_utils import parse_json_response
from server.llm import dispatch, prompts
from server.llm.schemas import ReportSummary


def _generate_report_with_retries(prompt: str, cfg: dispatch.LLMConfig, attempts: int = 3) -> Dict[str, Any]:
    """Call the LLM and parse + validate into a ReportSummary, retrying on failure with the
    error and previous (invalid) output fed back — so a flaky model gets a real chance to
    self-correct rather than just re-rolling the same prompt. Uses the shared, lenient JSON
    parser (handles code fences / stray prose) instead of a naive strip."""
    last_error = None
    last_raw = ""
    current = prompt
    for _ in range(attempts):
        try:
            last_raw = dispatch.call_llm(cfg, current)
            parsed = parse_json_response(last_raw)
            return ReportSummary.model_validate(parsed).model_dump()
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            print(f"Report generation attempt failed: {exc}")
            current = (
                f"{prompts.JSON_FIX_PROMPT}\n\n"
                f"Error: {last_error}\n\n"
                f"Your previous output (invalid):\n{last_raw}\n\n"
                f"Regenerate, strictly following the original request below.\n\n{prompt}"
            )
    raise RuntimeError(f"Failed to generate a valid report after {attempts} attempts: {last_error}")



def generate_report(session_data: Dict[str, Any], api_key: str | None = None) -> Dict[str, Any]:
    """
    Generates a final report for the given session.
    """
    provider = dispatch.normalize_provider(session_data.get("provider", "mock"))
    if provider == "mock":
        return {
            "overall_score": 0.85,
            "strengths": ["Clear communication", "Good technical depth"],
            "weaknesses": ["Could provide more concrete examples"],
            "persona_feedback": [
                {
                    "persona": "Hiring Manager",
                    "positives": ["Good fit for the team"],
                    "concerns": ["Might get bored with routine tasks"],
                    "next_step": "Hire"
                }
            ]
        }

    # 1. Prepare context for the LLM
    transcript = ""
    questions = session_data.get("questions", [])
    answers = session_data.get("answers", [])
    scores = session_data.get("scores", [])
    
    # We need to map answers/scores to questions. scores is a list of all scores (3 per question usually).
    # This is a bit tricky if the structure isn't 1:1.
    # In main.py: session.scores.append(...) happens 3 times per question (one per persona).
    # We should probably aggregate them or just dump them all.
    # Let's group scores by question_id.
    
    scores_by_q = {}
    for s in scores:
        qid = s["question_id"]
        if qid not in scores_by_q:
            scores_by_q[qid] = []
        scores_by_q[qid].append(s)

    for q, a in zip(questions, answers):
        qid = q["question_id"]
        transcript += f"\nRound: {q['round']}\n"
        transcript += f"Q: {q['text']}\n"
        transcript += f"A: {a.get('answer_text', '')}\n"
        
        # Add scores summary
        q_scores = scores_by_q.get(qid, [])
        for qs in q_scores:
            persona = qs.get("persona", "unknown")
            sc = qs.get("scorecard", {})
            transcript += f"  [{persona}] Scores: {json.dumps(sc.get('competency_scores', {}))}\n"
        
        transcript += "---\n"

    job_spec = session_data.get("job_spec", "")
    persona_data = session_data.get("persona")
    persona_json = json.dumps(persona_data, indent=2) if persona_data else "N/A"
    
    prompt = (
        f"{prompts.REPORT_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n\n"
        f"Persona:\n{persona_json}\n\n"
        f"Interview Transcript:\n{transcript}\n"
    )

    cfg = dispatch.config_from_session(session_data, api_key=api_key)

    try:
        return _generate_report_with_retries(prompt, cfg)
    except Exception as exc:
        print(f"Error generating report: {exc}")
        # build_report catches this and falls back to heuristic scoring.
        raise RuntimeError(f"Failed to generate report: {exc}") from exc

