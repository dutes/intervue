from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

# Prompts are centralized in server/llm/prompts.py. Re-exported for legacy imports.
from server.llm.prompts import (  # noqa: F401
    RUBRIC_PROMPT,
    QUESTION_PROMPT,
    SCORE_PROMPT,
    JSON_FIX_PROMPT,
    PERSONA_PROMPT,
    CV_ANALYSIS_PROMPT,
    REPORT_PROMPT,
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
# Generation can take a while for large prompts / slower (e.g. thinking) models, so allow a
# generous, env-tunable timeout. Listing models stays fast/short.
REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))


def _run_curl(payload: Dict[str, Any], model: str, api_key: str | None = None) -> str:
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Gemini curl error: {result.stderr.strip()}")
    return result.stdout


def call_gemini(prompt: str, temperature: float = 0.2, api_key: str | None = None, model: str | None = None) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    raw = _run_curl(payload, model or DEFAULT_MODEL, api_key=api_key)
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"Gemini API error: {data['error']}")
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini response missing candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini response missing parts")
    text = parts[0].get("text", "")
    if not text:
        raise RuntimeError("Gemini response missing text")
    return text.strip()


def test_connection(api_key: str | None = None, model: str | None = None) -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_gemini(prompt, temperature=0, api_key=api_key, model=model)


def list_models(api_key: str | None = None) -> list[str]:
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=1000"
    cmd = ["curl", "-sS", url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Gemini curl error: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if "error" in data:
        raise RuntimeError(f"Gemini API error: {data['error']}")
    models = []
    for m in data.get("models", []):
        # Only models that can generate content; strip the "models/" name prefix.
        if "generateContent" in m.get("supportedGenerationMethods", []):
            name = m.get("name", "")
            models.append(name.split("/", 1)[1] if name.startswith("models/") else name)
    return [m for m in models if m]
