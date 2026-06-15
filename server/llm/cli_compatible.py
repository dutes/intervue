"""Client for any OpenAI-compatible Chat Completions endpoint.

This covers local model runners (Ollama, LM Studio, vLLM, llama.cpp server, etc.) and
any third-party host that implements the OpenAI `/chat/completions` API. The user supplies
a base URL (e.g. http://localhost:11434/v1) and a model name; the API key is optional because
most local servers don't require one.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

# Env-tunable generation timeout; local models can be slow. Listing models stays short.
REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    # Allow the user to pass either ".../v1" or the full ".../v1/chat/completions".
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _run_curl(url: str, payload: Dict[str, Any], api_key: str | None = None) -> str:
    headers = ["-H", "Content-Type: application/json"]
    if api_key:
        headers += ["-H", f"Authorization: Bearer {api_key}"]
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        url,
        *headers,
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Local LLM curl error: {result.stderr.strip()}")
    return result.stdout


def call_compatible(
    prompt: str,
    temperature: float = 0.2,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    if not base_url:
        raise RuntimeError("A base URL is required for a local/custom OpenAI-compatible model")
    if not model:
        raise RuntimeError("A model name is required for a local/custom OpenAI-compatible model")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        # Best-effort JSON mode; servers that don't support it ignore it, and the prompt
        # already instructs the model to return strict JSON.
        "response_format": {"type": "json_object"},
    }

    raw = _run_curl(_endpoint(base_url), payload, api_key=api_key)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Local LLM returned non-JSON response: {raw[:200]}") from exc

    err = data.get("error")
    if err:
        raise RuntimeError(f"Local LLM API error: {err}")

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Local LLM response missing choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Local LLM response missing message content")

    return content.strip()


def test_connection(api_key: str | None = None, model: str | None = None, base_url: str | None = None) -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_compatible(prompt, temperature=0, api_key=api_key, model=model, base_url=base_url)


def _models_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/models"):
        return base
    return f"{base}/models"


def list_models(api_key: str | None = None, base_url: str | None = None) -> list[str]:
    if not base_url:
        raise RuntimeError("A base URL is required to list local/custom models")
    headers = []
    if api_key:
        headers = ["-H", f"Authorization: Bearer {api_key}"]
    cmd = ["curl", "-sS", _models_endpoint(base_url), *headers]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Local LLM curl error: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Local LLM returned non-JSON for model list: {result.stdout[:200]}") from exc
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Local LLM API error: {data['error']}")
    return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
