from __future__ import annotations

import os
import time
import json
from typing import Dict, Optional, List, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server.core import questions as question_core
from server.core import reports as report_core
from server.core import rubric as rubric_core
from server.core import scoring as scoring_core
from server.core import analysis as analysis_core
from server.core import storage as storage_core
from server.core.state import SessionState, load_session_state
from server.llm import cli_gemini, cli_openai

from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"   # points at interview_game/.env
load_dotenv(dotenv_path=ENV_PATH, override=True)


BASE_DIR = Path(__file__).resolve().parent
# Check if we are running in Docker (./web sibling to server package in /app) or local (../client_web/dist)
# In Dockerfile: COPY --from=frontend /app/client_web/dist ./web  -> /app/web. 
# main.py is in /app/server/main.py. So BASE_DIR is /app/server. 
# We want /app/web.
if (BASE_DIR.parent / "web").exists():
    WEB_DIR = BASE_DIR.parent / "web"
else:
    # fallback for local dev if dist exists, otherwise use src? 
    # Actually for local dev we usually use Vite dev server on 5173.
    # But if we wanted to serve built files locally:
    WEB_DIR = BASE_DIR.parent / "client_web" / "dist"

# If WEB_DIR doesn't exist (e.g. local dev without build), we might crash on mount.
# But let's assume for this step we are focusing on Docker support.

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Run migration
    try:
        storage_core.migrate_json_to_db()
    except Exception as e:
        print(f"Migration failed: {e}")

# Debug: Log paths
print(f"DEBUG: BASE_DIR={BASE_DIR}")
print(f"DEBUG: WEB_DIR={WEB_DIR} (Exists: {WEB_DIR.exists()})")

# Ensure directories exist before mounting
try:
    storage_core.ensure_dirs()
    print(f"DEBUG: Created/Ensured data directories at {storage_core.DATA_DIR}")
except Exception as e:
    print(f"ERROR: Failed to ensure directories: {e}")

# Serves /assets from the build
if (WEB_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
    print("DEBUG: Mounted /assets")
else:
    print(f"WARNING: Assets directory not found at {WEB_DIR / 'assets'}")

# Serve reports (charts)
try:
    if storage_core.REPORTS_DIR.exists():
        app.mount("/reports", StaticFiles(directory=storage_core.REPORTS_DIR), name="reports")
        print(f"DEBUG: Mounted /reports from {storage_core.REPORTS_DIR}")
    else:
        print(f"WARNING: Reports directory not found at {storage_core.REPORTS_DIR}")
except Exception as e:
    print(f"ERROR: Failed to mount /reports: {e}")

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

# API routes are defined below... specific routes take precedence.

# Catch-all for SPA: Serve index.html for any path that isn't an API call or file
# We place this at the END of the file (conceptually) or use a clever route.
# However, FastAPI matches in order. 
# We need to make sure API routes come first (which they do).
# But we need this catch-all to be *after* the API routes. 
# Since we are editing the top of the file, we can't easily put it at the bottom without moving everything.
# Alternative: A route that matches /{full_path:path} but we check if it starts with /api or /sessions.
# EASIER: Just define the specific routes first (which they are), then add the catch-all at the bottom.


SESSIONS: Dict[str, SessionState] = {}


class StartRequest(BaseModel):
    job_spec: str = Field(min_length=10)
    cv_text: str = Field(min_length=10)
    provider: str
    api_key: Optional[str] = None
    start_round: int = Field(default=1, ge=1)


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(min_length=1)


class StartResponse(BaseModel):
    session_id: str
    total_questions: int


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
    state = SessionState(
        payload["job_spec"],
        payload["cv_text"],
        payload["provider"],
        payload.get("start_round", 1),
    )
    state.session_id = payload["session_id"]
    state.created_at = payload["created_at"]
    state.rubric = payload.get("rubric")
    state.persona = payload.get("persona")
    state.cv_analysis = payload.get("cv_analysis")
    state.start_round = payload.get("start_round", 1)
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


@app.post("/sessions/start", response_model=StartResponse)
async def start_session(request: StartRequest) -> StartResponse:
    provider = _normalize_provider(request.provider)
    try:
        _verify_provider(provider, request.api_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.start_round > len(question_core.ROUNDS):
        raise HTTPException(status_code=400, detail="Unsupported round selection")

    session = SessionState(request.job_spec, request.cv_text, provider, request.start_round)

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

    # 1. Generate Persona
    try:
        persona = analysis_core.generate_persona(request.job_spec, provider)
        session.persona = persona
        session.logs.append(
            {
                "type": "persona",
                "parsed": persona,
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        print(f"Error generating persona: {e}")
        # Proceed without persona, falling back to default behavior

    # 2. Analyze CV (requires persona)
    if session.persona:
        try:
            cv_analysis = analysis_core.analyze_cv(request.cv_text, request.job_spec, session.persona, provider)
            session.cv_analysis = cv_analysis
            session.logs.append(
                {
                    "type": "cv_analysis",
                    "parsed": cv_analysis,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            print(f"Error analyzing CV: {e}")

    session.save()
    SESSIONS[session.session_id] = session
    return StartResponse(
        session_id=session.session_id,
        total_questions=question_core.total_questions(request.start_round),
    )


@app.post("/sessions/{session_id}/next_question")
async def next_question(session_id: str) -> Dict[str, str]:
    session = _get_session(session_id)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    index = len(session.questions)
    if index >= question_core.total_questions(session.start_round):
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


@app.get("/sessions/{session_id}/report")
async def get_report(session_id: str) -> Dict[str, Any]:
    try:
        report_path = report_core.REPORTS_DIR / session_id / "report.json"
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- New Endpoints ---

from fastapi import UploadFile, File
from server.core.files import parse_file

class FileUploadResponse(BaseModel):
    filename: str
    text_preview: str
    text_length: int

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    content = await file.read()
    try:
        text = parse_file(content, file.filename or "unknown")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    return FileUploadResponse(
        filename=file.filename or "unknown",
        text_preview=text[:200] + "..." if len(text) > 200 else text,
        text_length=len(text)
    )

@app.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    return storage_core.list_sessions()

@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    try:
        session = _get_session(session_id)
        # We return the raw dict, but we could filter or separate rubric
        return session.to_dict()
    except Exception:
         # Fallback if _get_session expects it to be in memory or loaded
         try:
            return storage_core.load_session(session_id)
         except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Session not found")


# SPA Catch-all
from fastapi.responses import FileResponse

# Debug: Print WEB_DIR and check assets
print(f"DEBUG: WEB_DIR is {WEB_DIR}")
if (WEB_DIR / "assets").exists():
    print(f"DEBUG: Assets directory found at {WEB_DIR / 'assets'}")
    # List a few files to verify
    try:
        print(f"DEBUG: Assets content: {[f.name for f in (WEB_DIR / 'assets').iterdir()]}")
    except Exception as e:
        print(f"DEBUG: Failed to list assets: {e}")
else:
    print(f"DEBUG: Assets directory NOT found at {WEB_DIR / 'assets'}")

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # If the path is a file in WEB_DIR, serve it correctly
    file_path = WEB_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Otherwise return index.html for client-side routing
    if (WEB_DIR / "index.html").exists():
        return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))
    
    return {"error": "Frontend not found. Did you run npm run build?"}

