from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

# Prompts are centralized in server/llm/prompts.py. They are re-exported here for any
# legacy imports, but new code should import them from prompts directly.
from server.llm.prompts import (  # noqa: F401
    RUBRIC_PROMPT,
    QUESTION_PROMPT,
    SCORE_PROMPT,
    JSON_FIX_PROMPT,
    PERSONA_PROMPT,
    CV_ANALYSIS_PROMPT,
    REPORT_PROMPT,
)

OPENAI_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")


def _run_curl(payload: Dict[str, Any], api_key: str | None = None) -> str:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = [
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
    ]
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        OPENAI_URL,
        *headers,
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"OpenAI curl error: {result.stderr.strip()}")
    return result.stdout


def call_openai(prompt: str, temperature: float = 0.2, api_key: str | None = None, model: str | None = None) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "input": prompt,
        "temperature": temperature,
        "text": {"format": {"type": "json_object"}},
    }

    raw = _run_curl(payload, api_key=api_key)
    data = json.loads(raw)

    # Responses API includes "error": null on success, so only fail if it's truthy.
    err = data.get("error")
    if err:
        raise RuntimeError(f"OpenAI API error: {err}")

    output = ""
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                output += content.get("text", "")

    if not output:
        raise RuntimeError("OpenAI response missing output text")

    return output.strip()


def test_connection(api_key: str | None = None, model: str | None = None) -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_openai(prompt, temperature=0, api_key=api_key, model=model)


def list_models(api_key: str | None = None) -> list[str]:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    cmd = [
        "curl",
        "-sS",
        "https://api.openai.com/v1/models",
        "-H",
        f"Authorization: Bearer {api_key}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"OpenAI curl error: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if data.get("error"):
        raise RuntimeError(f"OpenAI API error: {data['error']}")
    return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
