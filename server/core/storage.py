from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
SESSIONS_DIR = DATA_DIR / "sessions"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_session(session_id: str, payload: Dict[str, Any]) -> None:
    ensure_dirs()
    path = SESSIONS_DIR / f"{session_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session(session_id: str) -> Dict[str, Any]:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Session {session_id} not found")
    return json.loads(path.read_text(encoding="utf-8"))



def save_report(session_id: str, payload: Dict[str, Any]) -> Path:
    ensure_dirs()
    report_dir = REPORTS_DIR / session_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


def list_sessions() -> List[Dict[str, Any]]:
    if not SESSIONS_DIR.exists():
        return []
    
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            # Basic summary
            sessions.append({
                "session_id": payload.get("session_id"),
                "created_at": payload.get("created_at"),
                "job_spec": payload.get("job_spec")[:50] + "..." if payload.get("job_spec") else "",
                "status": payload.get("status"),
                "overall_score": payload.get("overall_score") # Might not exist if not finished
            })
        except Exception:
            continue
    
    # Sort by created_at desc
    sessions.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return sessions
