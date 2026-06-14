from __future__ import annotations

import json
from typing import Any, Dict

from server.core.json_utils import parse_json_response
from server.core.personas import persona_style
from server.llm import dispatch, mock, prompts
from server.llm.schemas import Rubric, Scorecard


def build_scoring_prompt(session: Dict[str, Any], question: Dict[str, Any], answer_text: str, persona: str) -> str:
    rubric_json = json.dumps(session["rubric"], indent=2)
    style = persona_style(persona)
    return (
        f"Rubric JSON:\n{rubric_json}\n\n"
        f"Question:\n{question['text']}\n\n"
        f"Answer:\n{answer_text}\n\n"
        f"Persona: {persona} ({style})\n\n"
        "Score the answer against the rubric."
    )


def _call_and_validate(prompt: str, cfg: dispatch.LLMConfig) -> tuple[Scorecard, str, str]:
    fix_prompt = prompts.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw = dispatch.call_llm(cfg, prompt)
        try:
            parsed = parse_json_response(raw)
            scorecard = Scorecard.model_validate(parsed)
            return scorecard, raw, prompt
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            prompt = f"{fix_prompt}\n\nValidation Error: {error_message}\n\nInvalid Output:\n{raw}"
    raise RuntimeError(error_message or "LLM JSON validation failed")


def score_answer(session: Dict[str, Any], question: Dict[str, Any], answer_text: str, persona: str, api_key: str | None = None) -> Dict[str, Any]:
    rubric = Rubric.model_validate(session["rubric"])
    provider = dispatch.normalize_provider(session.get("provider", ""))
    prompt_text = ""
    raw_response = ""

    if provider == "mock":
        scorecard = mock.score_answer(session["session_id"], question["question_id"], rubric)
        prompt_text = "MOCK: scoring"
        raw_response = json.dumps(scorecard.model_dump())
    else:
        prompt_text = (
            f"{prompts.SCORE_PROMPT}\n\n"
            f"{build_scoring_prompt(session, question, answer_text, persona)}"
        )
        cfg = dispatch.config_from_session(session, api_key=api_key)
        scorecard, raw_response, prompt_text = _call_and_validate(prompt_text, cfg)

    weighted_total = 0.0
    weight_sum = 0.0
    for comp in rubric.competencies:
        score = scorecard.competency_scores.get(comp.name, 0)
        weighted_total += score * comp.weight
        weight_sum += comp.weight
    overall = (weighted_total / weight_sum) * 25 if weight_sum else 0.0

    return {
        "scorecard": scorecard.model_dump(),
        "overall_score": round(overall, 2),
        "prompt": prompt_text,
        "raw_response": raw_response,
    }

