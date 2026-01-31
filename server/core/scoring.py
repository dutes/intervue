from __future__ import annotations

import json
from typing import Any, Dict

from server.llm import cli_gemini, cli_openai, mock
from server.llm.schemas import Rubric, Scorecard


def build_scoring_prompt(session: Dict[str, Any], question: Dict[str, Any], answer_text: str) -> str:
    rubric_json = json.dumps(session["rubric"], indent=2)
    return (
        f"Rubric JSON:\n{rubric_json}\n\n"
        f"Question:\n{question['text']}\n\n"
        f"Answer:\n{answer_text}\n\n"
        "Score the answer against the rubric."
    )


def _call_llm_with_retries(prompt: str, provider: str, fix_prompt: str, attempts: int = 3) -> str:
    responses = []
    last_error: str | None = None
    for _ in range(attempts):
        try:
            if provider == "openai":
                response = cli_openai.call_openai(prompt)
            elif provider == "gemini":
                response = cli_gemini.call_gemini(prompt)
            else:
                raise ValueError("Unsupported provider for LLM call")
            responses.append(response)
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            prompt = f"{fix_prompt}\n\nOriginal Error: {last_error}\n\nInvalid Output:\n{responses[-1] if responses else ''}"
    raise RuntimeError(last_error or "LLM call failed")


def _call_and_validate(prompt: str, provider: str) -> tuple[Scorecard, str, str]:
    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw = _call_llm_with_retries(prompt, provider, fix_prompt, attempts=1)
        try:
            parsed = json.loads(raw)
            scorecard = Scorecard.model_validate(parsed)
            return scorecard, raw, prompt
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            prompt = f"{fix_prompt}\n\nValidation Error: {error_message}\n\nInvalid Output:\n{raw}"
    raise RuntimeError(error_message or "LLM JSON validation failed")


def score_answer(session: Dict[str, Any], question: Dict[str, Any], answer_text: str) -> Dict[str, Any]:
    rubric = Rubric.model_validate(session["rubric"])
    provider = session["provider"]
    prompt_text = ""
    raw_response = ""

    if provider == "mock":
        scorecard = mock.score_answer(session["session_id"], question["question_id"], rubric)
        prompt_text = "MOCK: scoring"
        raw_response = json.dumps(scorecard.model_dump())
    else:
        prompt_text = (
            f"{cli_openai.SCORE_PROMPT if provider == 'openai' else cli_gemini.SCORE_PROMPT}\n\n"
            f"{build_scoring_prompt(session, question, answer_text)}"
        )
        scorecard, raw_response, prompt_text = _call_and_validate(prompt_text, provider)

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
