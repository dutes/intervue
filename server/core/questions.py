from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from server.core.personas import persona_style
from server.core.json_utils import parse_json_response
from server.llm.schemas import Question

ROUNDS: List[Dict[str, Any]] = [
    {
        "name": "screening",
        "label": "Round 1",
        "count": 4,
        "goal": "Establish baseline fit and core experience.",
    },
    {
        "name": "deep_dive",
        "label": "Round 2",
        "count": 6,
        "goal": "Explore depth, impact, and technical decision-making.",
    },
    {
        "name": "challenge",
        "label": "Round 3",
        "count": 4,
        "goal": "Stress-test claims and assess judgment under pressure.",
    },
]

DEFAULT_PERSONA = "neutral"
MAX_TOTAL_QUESTIONS = 5


def _round_sequence(start_round: int) -> List[Dict[str, Any]]:
    if 1 <= start_round <= len(ROUNDS):
        return ROUNDS[start_round - 1 :]
    return ROUNDS


def total_questions(start_round: int = 1) -> int:
    return min(MAX_TOTAL_QUESTIONS, sum(r["count"] for r in _round_sequence(start_round)))


def round_for_index(index: int, start_round: int = 1) -> Tuple[Dict[str, Any], int]:
    running = 0
    rounds = _round_sequence(start_round)
    for round_index, round_info in enumerate(rounds, start=start_round):
        running += round_info["count"]
        if index < running:
            return round_info, round_index
    return rounds[-1], start_round + len(rounds) - 1


def build_question_prompt(session: Dict[str, Any], round_info: Dict[str, Any], persona: str, question_id: str) -> str:
    rubric_json = json.dumps(session["rubric"], indent=2)
    style = persona_style(persona)
    previous_questions = session.get("questions", [])
    if previous_questions:
        previous_text = "\n".join(
            f"- {item['question_id']}: {item['text']}" for item in previous_questions if item.get("text")
        )
    else:
        previous_text = "None"
    return (
        f"Job Spec:\n{session['job_spec']}\n\n"
        f"CV:\n{session['cv_text']}\n\n"
        f"Rubric JSON:\n{rubric_json}\n\n"
        f"Round: {round_info['name']} - {round_info['goal']}\n"
        f"Persona: {persona} ({style})\n"
        f"Question ID: {question_id}\n\n"
        f"Previously asked questions:\n{previous_text}\n\n"
        "Generate exactly one interview question."
    )


def parse_question(payload: Dict[str, Any]) -> Question:
    return Question.model_validate(payload)


from server.llm import cli_gemini, cli_openai, mock


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


def _call_and_validate(prompt: str, provider: str) -> Dict[str, Any]:
    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw = _call_llm_with_retries(prompt, provider, fix_prompt, attempts=1)
        try:
            parsed = parse_json_response(raw)
            question = parse_question(parsed)
            payload = question.model_dump()
            payload["prompt"] = prompt
            payload["raw_response"] = raw
            return payload
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            prompt = f"{fix_prompt}\n\nValidation Error: {error_message}\n\nInvalid Output:\n{raw}"
    raise RuntimeError(error_message or "LLM JSON validation failed")


def generate_question(session: Dict[str, Any], index: int) -> Dict[str, Any]:
    start_round = session.get("start_round", 1)
    round_info, _round_num = round_for_index(index, start_round)
    persona = DEFAULT_PERSONA
    question_id = f"q{index + 1}"

    if session["provider"] == "mock":
        question = mock.generate_question(session["session_id"], round_info["name"], persona, index)
        question["prompt"] = "MOCK: question generation"
        question["raw_response"] = json.dumps(question)
        return question

    prompt = (
        f"{cli_openai.QUESTION_PROMPT if session['provider'] == 'openai' else cli_gemini.QUESTION_PROMPT}\n\n"
        f"{build_question_prompt(session, round_info, persona, question_id)}"
    )
    return _call_and_validate(prompt, session["provider"])
