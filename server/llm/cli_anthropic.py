from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# Default to the latest, most capable Claude model. Users can override per session.
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))
# Env-tunable generation timeout (large prompts / slower models). Listing models stays short.
REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))

# Steer Claude toward returning bare JSON (it has no dedicated json_object mode).
SYSTEM_PROMPT = "You output only valid JSON with no surrounding prose, markdown, or code fences."


def _run_curl(payload: Dict[str, Any], api_key: str | None = None) -> str:
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        ANTHROPIC_URL,
        "-H",
        f"x-api-key: {api_key}",
        "-H",
        f"anthropic-version: {ANTHROPIC_VERSION}",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Anthropic curl error: {result.stderr.strip()}")
    return result.stdout


def call_anthropic(prompt: str, temperature: float = 0.2, api_key: str | None = None, model: str | None = None) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": temperature,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }

    raw = _run_curl(payload, api_key=api_key)
    data = json.loads(raw)

    err = data.get("error")
    if err:
        raise RuntimeError(f"Anthropic API error: {err}")

    output = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            output += block.get("text", "")

    if not output:
        raise RuntimeError("Anthropic response missing text content")

    return output.strip()


def test_connection(api_key: str | None = None, model: str | None = None) -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_anthropic(prompt, temperature=0, api_key=api_key, model=model)


def list_models(api_key: str | None = None) -> list[str]:
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    cmd = [
        "curl",
        "-sS",
        "https://api.anthropic.com/v1/models?limit=1000",
        "-H",
        f"x-api-key: {api_key}",
        "-H",
        f"anthropic-version: {ANTHROPIC_VERSION}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Anthropic curl error: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if data.get("error"):
        raise RuntimeError(f"Anthropic API error: {data['error']}")
    return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
