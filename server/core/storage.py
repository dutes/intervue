from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from server.db.database import SessionLocal, engine, Base
from server.db.models import InterviewSession

# Create tables
Base.metadata.create_all(bind=engine)

DATA_DIR = Path("data")
SESSIONS_DIR = DATA_DIR / "sessions"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_db_session() -> Session:
    return SessionLocal()


def save_session(session_id: str, payload: Dict[str, Any]) -> None:
    # We still keep directory ensures for reports/other assets
    ensure_dirs()
    
    db = get_db_session()
    try:
        # Check if exists
        db_obj = db.query(InterviewSession).filter(InterviewSession.session_id == session_id).first()
        
        if not db_obj:
            db_obj = InterviewSession(session_id=session_id)
            db.add(db_obj)
        
        # Update fields
        db_obj.created_at = payload.get("created_at")
        db_obj.status = payload.get("status")
        db_obj.job_spec = payload.get("job_spec")
        db_obj.cv_text = payload.get("cv_text")
        db_obj.provider = payload.get("provider")
        db_obj.start_round = payload.get("start_round")
        
        # Extract overall score if present in scores (usually in the summary/report, kept in payload?)
        # payload doesn't always have overall_score at top level in SessionState.
        # It might be calculated. For now, let's rely on payload.
        # If the session is finished, maybe we put it there? 
        # Actually SessionState doesn't have overall_score field, it's in the report.
        # But list_sessions used to extract it.
        # Let's see if we can extract it from the last score or similar?
        # For now, let's just save what we have.
        
        db_obj.rubric = payload.get("rubric")
        db_obj.persona = payload.get("persona")
        db_obj.cv_analysis = payload.get("cv_analysis")
        db_obj.questions = payload.get("questions")
        db_obj.answers = payload.get("answers")
        db_obj.scores = payload.get("scores")
        db_obj.logs = payload.get("logs")
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def load_session(session_id: str) -> Dict[str, Any]:
    db = get_db_session()
    try:
        db_obj = db.query(InterviewSession).filter(InterviewSession.session_id == session_id).first()
        if not db_obj:
            raise FileNotFoundError(f"Session {session_id} not found")
        
        return {
            "session_id": db_obj.session_id,
            "created_at": db_obj.created_at,
            "status": db_obj.status,
            "job_spec": db_obj.job_spec,
            "cv_text": db_obj.cv_text,
            "provider": db_obj.provider,
            "start_round": db_obj.start_round,
            "rubric": db_obj.rubric,
            "persona": db_obj.persona,
            "cv_analysis": db_obj.cv_analysis,
            "questions": db_obj.questions,
            "answers": db_obj.answers,
            "scores": db_obj.scores,
            "logs": db_obj.logs,
        }
    finally:
        db.close()


def save_report(session_id: str, payload: Dict[str, Any]) -> Path:
    ensure_dirs()
    report_dir = REPORTS_DIR / session_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    
    # Also update overall_score in DB if present
    if "overall_score" in payload:
        db = get_db_session()
        try:
            db_obj = db.query(InterviewSession).filter(InterviewSession.session_id == session_id).first()
            if db_obj:
                db_obj.overall_score = payload["overall_score"]
                db.commit()
        except:
            pass # Non-critical
        finally:
            db.close()

    return report_path


def list_sessions() -> List[Dict[str, Any]]:
    db = get_db_session()
    try:
        sessions = db.query(
            InterviewSession.session_id,
            InterviewSession.created_at,
            InterviewSession.job_spec,
            InterviewSession.status,
            InterviewSession.overall_score
        ).order_by(InterviewSession.created_at.desc()).all()
        
        return [{
            "session_id": s.session_id,
            "created_at": s.created_at,
            "job_spec": s.job_spec[:50] + "..." if s.job_spec else "",
            "status": s.status,
            "overall_score": s.overall_score
        } for s in sessions]
    finally:
        db.close()


def migrate_json_to_db():
    if not SESSIONS_DIR.exists():
        return
        
    print("Checking for legacy JSON sessions to migrate...")
    count = 0
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            session_id = payload.get("session_id")
            if not session_id:
                continue
            
            # Check if exists in DB to avoid rewrite
            # Actually save_session handles upsert logic somewhat, but let's be explicitly careful
            # We just call save_session.
            save_session(session_id, payload)
            
            # Check if report exists and update score
            report_path = REPORTS_DIR / session_id / "report.json"
            if report_path.exists():
                try:
                    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
                    if "overall_score" in report_payload:
                        save_report(session_id, report_payload) # Re-saves file but also updates DB
                except:
                    pass
            
            count += 1
            # Optional: Rename/Move migrated file? 
            # path.rename(path.with_suffix('.json.bak'))
        except Exception as e:
            print(f"Failed to migrate {path}: {e}")
    
    if count > 0:
        print(f"Migrated {count} sessions to SQLite.")
