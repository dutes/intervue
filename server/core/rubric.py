from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from server.llm import cli_gemini, cli_openai, mock
from server.llm.schemas import Rubric


class LLMResult:
    def __init__(self, parsed: Dict[str, Any], raw: str, prompt: str) -> None:
        self.parsed = parsed
        self.raw = raw
        self.prompt = prompt


def _call_llm_with_retries(prompt: str, provider: str, fix_prompt: str, attempts: int = 3) -> Tuple[str, list[str]]:
    responses = []
    last_error: str | None = None
    for _ in range(attempts):
        try:
            if provider == "openai":
                response = cli_openai.call_openai(prompt)
            elif provider == "gemini":
                response = cli_gemini.call_gemini(prompt)
            else:
                raise ValueError("Unsupported provider for LLM call")
            responses.append(response)
            return response, responses
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            prompt = f"{fix_prompt}\n\nOriginal Error: {last_error}\n\nInvalid Output:\n{responses[-1] if responses else ''}"
    raise RuntimeError(last_error or "LLM call failed")


def _call_and_validate(prompt: str, provider: str) -> Tuple[Dict[str, Any], str, str]:
    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw, _responses = _call_llm_with_retries(prompt, provider, fix_prompt, attempts=1)
        try:
            parsed = json.loads(raw)
            rubric = Rubric.model_validate(parsed)
            return rubric.model_dump(), raw, prompt
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            prompt = f\"{fix_prompt}\\n\\nValidation Error: {error_message}\\n\\nInvalid Output:\\n{raw}\"
    raise RuntimeError(error_message or \"LLM JSON validation failed\")


def generate_rubric(job_spec: str, cv_text: str, provider: str) -> LLMResult:
    if provider == "mock":
        rubric = mock.generate_rubric()
        prompt = "MOCK: rubric generation"
        return LLMResult(parsed=rubric.model_dump(), raw=json.dumps(rubric.model_dump()), prompt=prompt)

    prompt = (
        f"{cli_openai.RUBRIC_PROMPT if provider == 'openai' else cli_gemini.RUBRIC_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n\nCV:\n{cv_text}\n"
    )
    parsed, raw, prompt_used = _call_and_validate(prompt, provider)
    return LLMResult(parsed=parsed, raw=raw, prompt=prompt_used)
