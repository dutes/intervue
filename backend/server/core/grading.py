from __future__ import annotations

import json
from typing import Any, Dict, List

from server.core import state
from server.llm import cli_gemini, cli_openai
from server.llm.schemas import ReportSummary


def _call_llm_with_retries(prompt: str, provider: str, fix_prompt: str) -> Dict[str, Any]:
    """Helper to call LLM and parse JSON, similar to analysis.py"""
    last_exc = None
    for _ in range(3):
        try:
            if provider == "openai":
                raw = cli_openai.call_openai(prompt)
            elif provider == "gemini":
                raw = cli_gemini.call_gemini(prompt)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Basic cleanup
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            last_exc = e
            # If JSON decode error, we could try to feed it back to LLM to fix,
            # but for now we just retry the generation or fail.
            print(f"LLM generation failed: {e}")

    raise RuntimeError(f"Failed to generate valid JSON after retries: {last_exc}")



def generate_report(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a final report for the given session.
    """
    provider = session_data.get("provider", "mock")
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
        f"{cli_openai.REPORT_PROMPT if provider == 'openai' else cli_gemini.REPORT_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n\n"
        f"Persona:\n{persona_json}\n\n"
        f"Interview Transcript:\n{transcript}\n"
    )

    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT

    try:
        raw_data = _call_llm_with_retries(prompt, provider, fix_prompt)
        # Validate against schema
        report = ReportSummary.model_validate(raw_data)
        return report.model_dump()
    except Exception as exc:
        print(f"Error generating report: {exc}")
        # Return a fallback or re-raise
        raise RuntimeError(f"Failed to generate report: {exc}") from exc
