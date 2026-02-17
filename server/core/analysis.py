from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from server.llm import cli_gemini, cli_openai, mock
from server.llm.schemas import Persona, CVAnalysis
from server.core.json_utils import parse_json_response


def _call_llm_with_retries(prompt: str, provider: str, fix_prompt: str, attempts: int = 3) -> str:
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
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            prompt = f"{fix_prompt}\n\nOriginal Error: {last_error}\n\nInvalid Output:\n{responses[-1] if responses else ''}"
    raise RuntimeError(last_error or "LLM call failed")


def generate_persona(job_spec: str, provider: str) -> Dict[str, Any]:
    if provider == "mock":
        return {
            "name": "Alex Mercer",
            "role": "Senior Engineering Manager",
            "tone": "Professional but demanding",
            "key_concerns": ["Scalability", "Team fit"],
        }

    prompt = (
        f"{cli_openai.PERSONA_PROMPT if provider == 'openai' else cli_gemini.PERSONA_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n"
    )
    
    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT
    
    try:
        raw = _call_llm_with_retries(prompt, provider, fix_prompt)
        parsed = parse_json_response(raw)
        persona = Persona.model_validate(parsed)
        return persona.model_dump()
    except Exception as exc:
        raise RuntimeError(f"Failed to generate persona: {exc}") from exc


def analyze_cv(cv_text: str, job_spec: str, persona: Dict[str, Any], provider: str) -> Dict[str, Any]:
    if provider == "mock":
        return {
            "summary": "Strong candidate with relevant experience.",
            "strengths": ["Python", "FastAPI"],
            "weaknesses": ["No cloud experience"],
            "missing_info": ["Education dates"],
        }

    persona_json = json.dumps(persona, indent=2)
    prompt = (
        f"{cli_openai.CV_ANALYSIS_PROMPT if provider == 'openai' else cli_gemini.CV_ANALYSIS_PROMPT}\n\n"
        f"Persona:\n{persona_json}\n\n"
        f"Job Spec:\n{job_spec}\n\n"
        f"CV:\n{cv_text}\n"
    )

    fix_prompt = cli_openai.JSON_FIX_PROMPT if provider == "openai" else cli_gemini.JSON_FIX_PROMPT

    try:
        raw = _call_llm_with_retries(prompt, provider, fix_prompt)
        parsed = parse_json_response(raw)
        analysis = CVAnalysis.model_validate(parsed)
        return analysis.model_dump()
    except Exception as exc:
        raise RuntimeError(f"Failed to analyze CV: {exc}") from exc
