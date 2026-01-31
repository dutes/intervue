from __future__ import annotations

import os
import time
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server.core import questions as question_core
from server.core import reports as report_core
from server.core import rubric as rubric_core
from server.core import scoring as scoring_core
from server.core.state import SessionState, load_session_state
from server.llm import cli_gemini, cli_openai

from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"   # points at interview_game/.env
load_dotenv(dotenv_path=ENV_PATH, override=True)


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI()
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

SESSIONS: Dict[str, SessionState] = {}


class StartRequest(BaseModel):
    job_spec: str = Field(min_length=10)
    cv_text: str = Field(min_length=10)
    provider: str
    api_key: Optional[str] = None


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(min_length=1)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))


def _get_session(session_id: str) -> SessionState:
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    payload = load_session_state(session_id)
    state = SessionState(payload["job_spec"], payload["cv_text"], payload["provider"])
    state.session_id = payload["session_id"]
    state.created_at = payload["created_at"]
    state.rubric = payload.get("rubric")
    state.questions = payload.get("questions", [])
    state.answers = payload.get("answers", [])
    state.scores = payload.get("scores", [])
    state.logs = payload.get("logs", [])
    state.status = payload.get("status", "active")
    SESSIONS[state.session_id] = state
    return state


def _normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def _set_api_key(provider: str, api_key: Optional[str]) -> None:
    if not api_key:
        return
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "gemini":
        os.environ["GEMINI_API_KEY"] = api_key


def _verify_provider(provider: str, api_key: Optional[str]) -> None:
    provider = _normalize_provider(provider)
    if provider == "mock":
        return

    _set_api_key(provider, api_key)

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not set")
        cli_openai.test_connection()
        return
    if provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not set")
        cli_gemini.test_connection()
        return

    raise HTTPException(status_code=400, detail="Unsupported provider")


@app.post("/sessions/start")
async def start_session(request: StartRequest) -> Dict[str, str]:
    provider = _normalize_provider(request.provider)
    try:
        _verify_provider(provider, request.api_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = SessionState(request.job_spec, request.cv_text, provider)

    rubric_result = rubric_core.generate_rubric(request.job_spec, request.cv_text, provider)
    session.rubric = rubric_result.parsed
    session.logs.append(
        {
            "type": "rubric",
            "prompt": rubric_result.prompt,
            "raw_response": rubric_result.raw,
            "parsed": rubric_result.parsed,
            "timestamp": time.time(),
        }
    )
    session.save()
    SESSIONS[session.session_id] = session
    return {"session_id": session.session_id}


@app.post("/sessions/{session_id}/next_question")
async def next_question(session_id: str) -> Dict[str, str]:
    session = _get_session(session_id)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    index = len(session.questions)
    if index >= question_core.total_questions():
        raise HTTPException(status_code=400, detail="Interview already complete")

    question = question_core.generate_question(session.to_dict(), index)
    session.questions.append({k: question[k] for k in ["question_id", "text", "round", "persona"]})
    session.logs.append(
        {
            "type": "question",
            "prompt": question.get("prompt"),
            "raw_response": question.get("raw_response"),
            "parsed": {k: question[k] for k in ["question_id", "text", "round", "persona"]},
            "timestamp": time.time(),
        }
    )
    session.save()

    return {
        "question_id": question["question_id"],
        "persona": question["persona"],
        "round": question["round"],
        "text": question["text"],
    }


@app.post("/sessions/{session_id}/answer")
async def answer_question(session_id: str, request: AnswerRequest) -> Dict[str, bool]:
    session = _get_session(session_id)
    question = next((q for q in session.questions if q["question_id"] == request.question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    personas = ["positive", "neutral", "hostile"]
    score_payloads = [
        scoring_core.score_answer(session.to_dict(), question, request.answer_text, persona)
        for persona in personas
    ]
    session.answers.append(
        {
            "question_id": request.question_id,
            "answer_text": request.answer_text,
            "timestamp": time.time(),
        }
    )
    for persona, score_payload in zip(personas, score_payloads):
        session.scores.append(
            {
                "question_id": request.question_id,
                "persona": persona,
                "scorecard": score_payload["scorecard"],
                "overall_score": score_payload["overall_score"],
                "timestamp": time.time(),
            }
        )
        session.logs.append(
            {
                "type": "scoring",
                "persona": persona,
                "prompt": score_payload.get("prompt"),
                "raw_response": score_payload.get("raw_response"),
                "parsed": score_payload.get("scorecard"),
                "timestamp": time.time(),
            }
        )
    session.save()
    return {"ok": True}


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> Dict[str, object]:
    session = _get_session(session_id)
    report_payload, report_paths = report_core.build_report(session.to_dict())
    session.status = "completed"
    session.save()

    summary = {
        "overall_score": report_payload["overall_score"],
        "strengths": report_payload["strengths"],
        "weaknesses": report_payload["weaknesses"],
        "persona_feedback": report_payload["persona_feedback"],
    }
    return {"summary": summary, "report_paths": report_paths}
