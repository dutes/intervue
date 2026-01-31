from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

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
