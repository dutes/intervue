from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from server.core.storage import save_session


class SessionState:
    def __init__(self, job_spec: str, cv_text: str, provider: str, start_round: int = 1) -> None:
        self.session_id = str(uuid.uuid4())
        self.job_spec = job_spec
        self.cv_text = cv_text
        self.provider = provider
        self.start_round = start_round
        self.created_at = time.time()
        self.rubric: Optional[Dict[str, Any]] = None
        self.questions: List[Dict[str, Any]] = []
        self.answers: List[Dict[str, Any]] = []
        self.scores: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.status = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "job_spec": self.job_spec,
            "cv_text": self.cv_text,
            "provider": self.provider,
            "start_round": self.start_round,
            "created_at": self.created_at,
            "rubric": self.rubric,
            "questions": self.questions,
            "answers": self.answers,
            "scores": self.scores,
            "logs": self.logs,
            "status": self.status,
        }

    def save(self) -> None:
        save_session(self.session_id, self.to_dict())


def load_session_state(session_id: str) -> Dict[str, Any]:
    from server.core.storage import load_session

    return load_session(session_id)
