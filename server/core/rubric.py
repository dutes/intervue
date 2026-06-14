from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from server.llm import dispatch, mock, prompts
from server.llm.schemas import Rubric
from server.core.json_utils import parse_json_response


class LLMResult:
    def __init__(self, parsed: Dict[str, Any], raw: str, prompt: str) -> None:
        self.parsed = parsed
        self.raw = raw
        self.prompt = prompt


def _call_and_validate(prompt: str, cfg: dispatch.LLMConfig) -> Tuple[Dict[str, Any], str, str]:
    fix_prompt = prompts.JSON_FIX_PROMPT
    attempts = 3
    raw = ""
    error_message = ""
    for _ in range(attempts):
        raw = dispatch.call_llm(cfg, prompt)
        try:
            parsed = parse_json_response(raw)
            rubric = Rubric.model_validate(parsed)
            return rubric.model_dump(), raw, prompt
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            prompt = f"{fix_prompt}\n\nValidation Error: {error_message}\n\nInvalid Output:\n{raw}"
    raise RuntimeError(error_message or "LLM JSON validation failed")


def generate_rubric(
    job_spec: str,
    cv_text: str,
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMResult:
    if dispatch.normalize_provider(provider) == "mock":
        rubric = mock.generate_rubric()
        prompt = "MOCK: rubric generation"
        return LLMResult(parsed=rubric.model_dump(), raw=json.dumps(rubric.model_dump()), prompt=prompt)

    prompt = (
        f"{prompts.RUBRIC_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n\nCV:\n{cv_text}\n"
    )
    cfg = dispatch.LLMConfig(provider=dispatch.normalize_provider(provider), api_key=api_key, model=model, base_url=base_url)
    parsed, raw, prompt_used = _call_and_validate(prompt, cfg)
    return LLMResult(parsed=parsed, raw=raw, prompt=prompt_used)

