from __future__ import annotations

import os
import time
import json
import hashlib
from typing import Dict, Optional, List, Any

from fastapi import FastAPI, HTTPException, Response
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
from server.core import coaching as coaching_core
from server.core import delivery as delivery_core
from server.core.state import SessionState, load_session_state
from server.llm import dispatch
from server.tts import dispatch as tts_dispatch

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
SESSION_API_KEYS: Dict[str, str] = {}


class StartRequest(BaseModel):
    job_spec: str = Field(min_length=10)
    cv_text: str = Field(min_length=10)
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    start_round: int = Field(default=1, ge=1)


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(min_length=1)
    # Delivery signals from the client: seconds spent composing and whether voice input was used.
    duration_seconds: Optional[float] = None
    used_voice: bool = False


class ModelsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


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
        model=payload.get("model"),
        base_url=payload.get("base_url"),
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
    return dispatch.normalize_provider(provider)


def _persona_name(session: SessionState, stance: str) -> str:
    """Name of the panelist conducting this stance (falls back to the primary persona)."""
    persona_data = session.persona or {}
    panel = persona_data.get("panel") or {}
    entry = panel.get(stance) or persona_data
    return entry.get("name", "") if isinstance(entry, dict) else ""


def _verify_provider(provider: str, api_key: Optional[str], model: Optional[str] = None, base_url: Optional[str] = None) -> None:
    provider = _normalize_provider(provider)
    if provider not in dispatch.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    cfg = dispatch.LLMConfig(provider=provider, api_key=api_key, model=model, base_url=base_url)
    dispatch.test_connection(cfg)


@app.post("/providers/models")
async def list_provider_models(request: ModelsRequest) -> Dict[str, Any]:
    provider = _normalize_provider(request.provider)
    if provider not in dispatch.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    cfg = dispatch.LLMConfig(provider=provider, api_key=request.api_key, base_url=request.base_url)
    try:
        models = dispatch.list_models(cfg)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not load models: {exc}") from exc
    return {"models": models}


@app.post("/sessions/start", response_model=StartResponse)
async def start_session(request: StartRequest) -> StartResponse:
    provider = _normalize_provider(request.provider)
    try:
        _verify_provider(provider, request.api_key, request.model, request.base_url)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.start_round > len(question_core.ROUNDS):
        raise HTTPException(status_code=400, detail="Unsupported round selection")

    session = SessionState(
        request.job_spec,
        request.cv_text,
        provider,
        request.start_round,
        model=request.model,
        base_url=request.base_url,
    )

    rubric_result = rubric_core.generate_rubric(
        request.job_spec, request.cv_text, provider, api_key=request.api_key, model=request.model, base_url=request.base_url
    )
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

    # 1. Generate the interviewer panel — three distinct named personas (one per stance), each
    # with a name matching its assigned voice's gender. The neutral panelist doubles as the
    # primary identity for back-compat consumers (CV analysis, grading); the full panel is
    # nested under "panel" so it persists in the existing persona JSON column (no migration).
    try:
        panel = analysis_core.generate_persona_panel(request.job_spec, provider, api_key=request.api_key, model=request.model, base_url=request.base_url)
        primary = dict(panel["neutral"])
        primary["panel"] = panel
        session.persona = primary
        session.logs.append(
            {
                "type": "persona",
                "parsed": primary,
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        print(f"Error generating persona panel: {e}")
        # Proceed without persona, falling back to default behavior

    # 2. Analyze CV (requires persona)
    if session.persona:
        try:
            cv_analysis = analysis_core.analyze_cv(request.cv_text, request.job_spec, session.persona, provider, api_key=request.api_key, model=request.model, base_url=request.base_url)
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
    if request.api_key:
        SESSION_API_KEYS[session.session_id] = request.api_key
    return StartResponse(
        session_id=session.session_id,
        total_questions=question_core.total_questions(request.start_round),
    )


@app.post("/sessions/{session_id}/next_question")
async def next_question(session_id: str) -> Dict[str, Any]:
    session = _get_session(session_id)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    total = question_core.total_questions(session.start_round)
    main_count = question_core.main_question_count(session.to_dict())
    api_key = SESSION_API_KEYS.get(session_id)

    # Resume: if the most recent question hasn't been answered yet (e.g. the page was
    # refreshed or the session was reopened), return that question instead of generating a
    # new one — otherwise we'd skip the question the candidate was on.
    answered_ids = {a.get("question_id") for a in session.answers}
    if session.questions and session.questions[-1].get("question_id") not in answered_ids:
        pending = session.questions[-1]
        return {
            "question_id": pending.get("question_id", ""),
            "persona": pending.get("persona", ""),
            "persona_name": _persona_name(session, pending.get("persona", "")),
            "round": pending.get("round", ""),
            "text": pending.get("text", ""),
            "anchor": pending.get("anchor", ""),
            "competency": pending.get("competency", ""),
            "number": main_count,
            "total": total,
            "is_follow_up": pending.get("kind") == "follow_up",
        }

    # If the last answer was weak, probe it with a follow-up before advancing.
    parent = question_core.needs_follow_up(session.to_dict())
    if parent is not None:
        question = question_core.generate_followup(session.to_dict(), parent, api_key=api_key)
        is_follow_up = True
    else:
        if main_count >= total:
            raise HTTPException(status_code=400, detail="Interview already complete")
        question = question_core.generate_question(session.to_dict(), main_count, api_key=api_key)
        is_follow_up = False

    question_fields = ["question_id", "text", "round", "persona", "anchor", "competency"]
    parsed_question = {k: question.get(k, "") for k in question_fields}
    parsed_question["kind"] = "follow_up" if is_follow_up else "main"
    if is_follow_up:
        parsed_question["parent_id"] = parent["question_id"]
    session.questions.append(parsed_question)
    session.logs.append(
        {
            "type": "question",
            "prompt": question.get("prompt"),
            "raw_response": question.get("raw_response"),
            "parsed": parsed_question,
            "timestamp": time.time(),
        }
    )
    session.save()

    return {
        "question_id": question["question_id"],
        "persona": question["persona"],
        "persona_name": _persona_name(session, question["persona"]),
        "round": question["round"],
        "text": question["text"],
        "anchor": question.get("anchor", ""),
        "competency": question.get("competency", ""),
        # A follow-up belongs to the current main question, so the counter holds steady.
        "number": main_count if is_follow_up else main_count + 1,
        "total": total,
        "is_follow_up": is_follow_up,
    }


@app.post("/sessions/{session_id}/answer")
async def answer_question(session_id: str, request: AnswerRequest) -> Dict[str, Any]:
    session = _get_session(session_id)
    question = next((q for q in session.questions if q["question_id"] == request.question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    personas = ["positive", "neutral", "hostile"]
    api_key = SESSION_API_KEYS.get(session_id)
    score_payloads = [
        scoring_core.score_answer(session.to_dict(), question, request.answer_text, persona, api_key=api_key)
        for persona in personas
    ]
    delivery = delivery_core.analyze_delivery(
        request.answer_text, duration_seconds=request.duration_seconds, used_voice=request.used_voice
    )
    session.answers.append(
        {
            "question_id": request.question_id,
            "answer_text": request.answer_text,
            "delivery": delivery,
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

    competency_scores = coaching_core.aggregate_competencies(score_payloads)
    star_feedback = coaching_core.aggregate_star(score_payloads)
    coaching = coaching_core.build_coaching(
        question_text=question.get("text", ""),
        answer_text=request.answer_text,
        competency_scores=competency_scores,
        star_feedback=star_feedback,
        session=session.to_dict(),
        api_key=api_key,
        score_payloads=score_payloads,
    )
    avg_overall = round(sum(p["overall_score"] for p in score_payloads) / len(score_payloads), 2)

    session.logs.append(
        {
            "type": "coaching",
            "question_id": request.question_id,
            "parsed": {
                "competency_scores": competency_scores,
                "star_feedback": star_feedback,
                "coaching": coaching,
                "average_overall": avg_overall,
            },
            "timestamp": time.time(),
        }
    )

    session.save()
    return {
        "ok": True,
        "average_overall_score": avg_overall,
        "competency_scores": competency_scores,
        "star_feedback": star_feedback,
        "coaching": coaching,
        "delivery": delivery,
    }

@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> Dict[str, object]:
    session = _get_session(session_id)
    api_key = SESSION_API_KEYS.get(session_id)
    report_payload, report_paths = report_core.build_report(session.to_dict(), api_key=api_key)
    session.status = "completed"
    session.save()

    # The interview is over; drop the in-memory API key so it doesn't linger for the
    # process lifetime.
    SESSION_API_KEYS.pop(session_id, None)

    summary = {
        "overall_score": report_payload["overall_score"],
        "strengths": report_payload["strengths"],
        "weaknesses": report_payload["weaknesses"],
        "persona_feedback": report_payload["persona_feedback"],
    }


    return {"summary": summary, "report_paths": report_paths}


TTS_CACHE_DIR = storage_core.DATA_DIR / "tts_cache"


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    # Interviewer persona, used to pick a distinct voice. Falls back to neutral.
    persona: str = "neutral"


@app.post("/tts")
async def text_to_speech(request: TTSRequest) -> Response:
    """Synthesize a question to speech. Server-side provider (Piper by default); keyless.

    Returns audio bytes. Re-synthesizing the same text+persona is avoided via an on-disk
    cache (questions get spoken again on replay / re-toggle). If the provider can't run in
    this environment (e.g. the Piper binary isn't bundled), returns 503 so the client can
    disable the voice UI.
    """
    cfg = tts_dispatch.default_config()
    provider = cfg.get("provider", "")
    key = hashlib.sha256(f"{provider}:{request.persona}:{request.text}".encode("utf-8")).hexdigest()
    cache_path = TTS_CACHE_DIR / f"{key}.wav"
    if cache_path.exists():
        return Response(content=cache_path.read_bytes(), media_type=tts_dispatch.WAV_CONTENT_TYPE)

    try:
        audio, content_type = tts_dispatch.synthesize(cfg, request.text, request.persona)
    except tts_dispatch.TTSUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"Text-to-speech unavailable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {exc}") from exc

    try:
        TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(audio)
    except Exception as exc:  # noqa: BLE001 — caching is best-effort
        print(f"WARNING: failed to cache TTS audio: {exc}")

    return Response(content=audio, media_type=content_type)


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
    text: str
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
        text=text,
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








