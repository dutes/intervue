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
        "count": 3,
        "goal": "Establish baseline fit and core experience.",
    },
    {
        "name": "deep_dive",
        "label": "Round 2",
        "count": 4,
        "goal": "Explore depth, impact, and technical decision-making.",
    },
    {
        "name": "challenge",
        "label": "Round 3",
        "count": 3,
        "goal": "Stress-test claims and assess judgment under pressure.",
    },
]

DEFAULT_PERSONA = "neutral"

# Each round is conducted by a different panel persona, so the candidate experiences a
# realistic shift in questioning stance: a warm screen, a neutral deep-dive, a hostile challenge.
ROUND_PERSONA: Dict[str, str] = {
    "screening": "positive",
    "deep_dive": "neutral",
    "challenge": "hostile",
}

# Total budget across all rounds. Set to the sum of round counts so the interview reaches the
# final challenge round; lower it for shorter sessions.
MAX_TOTAL_QUESTIONS = 10


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


def _select_target_competency(session: Dict[str, Any], index: int) -> Dict[str, Any] | None:
    """Pick one rubric competency to probe, rotating so coverage spreads across questions.

    Competencies are ordered by weight (most important first) so that with a small question
    budget the highest-weight competencies are still covered.
    """
    rubric = session.get("rubric") or {}
    competencies = rubric.get("competencies") or []
    if not competencies:
        return None
    ordered = sorted(competencies, key=lambda c: c.get("weight", 0), reverse=True)
    return ordered[index % len(ordered)]


def _previous_qa_block(session: Dict[str, Any]) -> str:
    """Render prior questions paired with the candidate's answers and any follow-up signal."""
    questions = session.get("questions", [])
    if not questions:
        return "None"

    answers_by_id = {a.get("question_id"): a for a in session.get("answers", [])}
    # Prefer the neutral persona scorecard for follow-up signal; fall back to any.
    scores_by_id: Dict[str, Dict[str, Any]] = {}
    for score in session.get("scores", []):
        qid = score.get("question_id")
        if qid not in scores_by_id or score.get("persona") == "neutral":
            scores_by_id[qid] = score

    lines: List[str] = []
    for item in questions:
        qid = item.get("question_id")
        if not item.get("text"):
            continue
        lines.append(f"Q ({qid}): {item['text']}")
        answer = answers_by_id.get(qid)
        if answer and answer.get("answer_text"):
            lines.append(f"  A: {answer['answer_text']}")
            scorecard = (scores_by_id.get(qid) or {}).get("scorecard") or {}
            issues = scorecard.get("issues") or {}
            signals = []
            if issues.get("vagueness", 0) >= 2:
                signals.append("answer was vague")
            if issues.get("missing_example"):
                signals.append("no concrete example given")
            if issues.get("contradiction_with_cv"):
                signals.append("contradicted the CV")
            follow_up = scorecard.get("follow_up_suggestion")
            if follow_up:
                signals.append(f"suggested follow-up: {follow_up}")
            if signals:
                lines.append(f"  [Drill here: {'; '.join(signals)}]")
        else:
            lines.append("  A: (not yet answered)")
    return "\n".join(lines)


def build_question_prompt(session: Dict[str, Any], round_info: Dict[str, Any], persona: str, question_id: str, index: int = 0) -> str:
    rubric_json = json.dumps(session["rubric"], indent=2)

    # The questioning stance rotates per round (warm screen -> neutral deep-dive -> hostile
    # challenge). Layer it on top of the generated persona's identity so the panel both keeps a
    # consistent character and shifts its tone as the interview progresses.
    stance = persona_style(persona)
    persona_data = session.get("persona")
    if persona_data:
        interviewer_identity = (
            f"Interviewer Name: {persona_data.get('name', 'Interviewer')}\n"
            f"Role: {persona_data.get('role', 'Hiring Manager')}\n"
            f"Tone: {persona_data.get('tone', 'Professional')}\n"
            f"Key Concerns: {', '.join(persona_data.get('key_concerns', []))}\n"
            f"Questioning stance for this round ({persona}): {stance}\n"
        )
    else:
        interviewer_identity = f"Persona: {persona} ({stance})\n"

    cv_analysis = session.get("cv_analysis")
    analysis_context = ""
    if cv_analysis:
        analysis_context = (
            f"CV Analysis:\n"
            f"Summary: {cv_analysis.get('summary')}\n"
            f"Key Missing Info: {', '.join(cv_analysis.get('missing_info', []))}\n"
            f"Areas to Probe: {', '.join(cv_analysis.get('weaknesses', []))}\n\n"
        )

    target = _select_target_competency(session, index)
    if target:
        competency_context = (
            f"Target competency for THIS question: {target.get('name')}\n"
            f"What good looks like: {target.get('what_good_looks_like')}\n"
            f"Red flags to probe: {', '.join(target.get('red_flags', []))}\n\n"
        )
    else:
        competency_context = ""

    qa_block = _previous_qa_block(session)

    return (
        f"Job Spec:\n{session['job_spec']}\n\n"
        f"CV:\n{session['cv_text']}\n\n"
        f"Rubric JSON:\n{rubric_json}\n\n"
        f"{interviewer_identity}\n"
        f"{analysis_context}"
        f"{competency_context}"
        f"Round: {round_info['name']} - {round_info['goal']}\n"
        f"Question ID: {question_id}\n\n"
        f"Conversation so far (questions, the candidate's answers, and where to drill):\n{qa_block}\n\n"
        "If the most recent answer was vague, lacked a concrete example or metric, or contradicted "
        "the CV, ask a sharp follow-up that drills into it. Otherwise probe the target competency "
        "using a specific detail from the CV or job spec.\n\n"
        "Generate exactly one interview question."
    )


def parse_question(payload: Dict[str, Any]) -> Question:
    return Question.model_validate(payload)


from server.llm import dispatch, mock, prompts


# Questions use a higher temperature than scoring/analysis so repeated sessions on the same CV
# produce varied phrasing rather than near-identical questions.
QUESTION_TEMPERATURE = 0.6


def _call_and_validate(prompt: str, cfg: dispatch.LLMConfig, temperature: float = 0.2) -> Dict[str, Any]:
    fix_prompt = prompts.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw = dispatch.call_llm(cfg, prompt, temperature=temperature)
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


def generate_question(session: Dict[str, Any], index: int, api_key: str | None = None) -> Dict[str, Any]:
    start_round = session.get("start_round", 1)
    round_info, _round_num = round_for_index(index, start_round)
    persona = ROUND_PERSONA.get(round_info["name"], DEFAULT_PERSONA)
    question_id = f"q{index + 1}"

    if dispatch.normalize_provider(session.get("provider", "")) == "mock":
        question = mock.generate_question(session["session_id"], round_info["name"], persona, index)
        question["prompt"] = "MOCK: question generation"
        question["raw_response"] = json.dumps(question)
        return question

    prompt = (
        f"{prompts.QUESTION_PROMPT}\n\n"
        f"{build_question_prompt(session, round_info, persona, question_id, index)}"
    )
    cfg = dispatch.config_from_session(session, api_key=api_key)
    return _call_and_validate(prompt, cfg, temperature=QUESTION_TEMPERATURE)

