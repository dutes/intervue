from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from server.llm import dispatch, prompts
from server.llm.schemas import Persona, CVAnalysis
from server.core.json_utils import parse_json_response
from server.core.personas import PANEL_STANCES, PANEL_VOICE_GENDER


def _call_llm_with_retries(prompt: str, cfg: dispatch.LLMConfig, fix_prompt: str, attempts: int = 3) -> str:
    responses = []
    last_error: str | None = None
    for _ in range(attempts):
        try:
            response = dispatch.call_llm(cfg, prompt)
            responses.append(response)
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            prompt = f"{fix_prompt}\n\nOriginal Error: {last_error}\n\nInvalid Output:\n{responses[-1] if responses else ''}"
    raise RuntimeError(last_error or "LLM call failed")


def generate_persona(
    job_spec: str,
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> Dict[str, Any]:
    if dispatch.normalize_provider(provider) == "mock":
        return {
            "name": "Alex Mercer",
            "role": "Senior Engineering Manager",
            "tone": "Professional but demanding",
            "key_concerns": ["Scalability", "Team fit"],
        }

    prompt = (
        f"{prompts.PERSONA_PROMPT}\n\n"
        f"Job Spec:\n{job_spec}\n"
    )
    cfg = dispatch.LLMConfig(provider=dispatch.normalize_provider(provider), api_key=api_key, model=model, base_url=base_url)

    try:
        raw = _call_llm_with_retries(prompt, cfg, prompts.JSON_FIX_PROMPT)
        parsed = parse_json_response(raw)
        persona = Persona.model_validate(parsed)
        return persona.model_dump()
    except Exception as exc:
        raise RuntimeError(f"Failed to generate persona: {exc}") from exc


_MOCK_PANEL = {
    # Names chosen to match each stance's voice gender (positive=female, neutral=male,
    # hostile=male) so the mock provider stays coherent with real voices.
    "positive": {
        "name": "Hannah Lewis",
        "role": "Engineering Manager",
        "tone": "Warm and encouraging",
        "key_concerns": ["Team fit", "Growth mindset"],
    },
    "neutral": {
        "name": "Alex Mercer",
        "role": "Senior Engineering Manager",
        "tone": "Professional and balanced",
        "key_concerns": ["Scalability", "Evidence of impact"],
    },
    "hostile": {
        "name": "Daniel Cole",
        "role": "Principal Engineer",
        "tone": "Skeptical and challenging",
        "key_concerns": ["Depth of ownership", "Inconsistencies"],
    },
}


def generate_persona_panel(
    job_spec: str,
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Generate three distinct interviewer personas, one per stance.

    Each persona's name is constrained to match the gender of the Piper voice assigned to that
    stance (see server/core/personas.PANEL_VOICE_GENDER), so the spoken voice and the displayed
    name agree. Returns a dict keyed by stance ("positive"/"neutral"/"hostile").
    """
    if dispatch.normalize_provider(provider) == "mock":
        return {stance: dict(p) for stance, p in _MOCK_PANEL.items()}

    gender_lines = "\n".join(f"- {stance}: {PANEL_VOICE_GENDER[stance]}" for stance in PANEL_STANCES)
    prompt = (
        f"{prompts.PANEL_PERSONA_PROMPT}\n\n"
        f"Required gender for each interviewer's name:\n{gender_lines}\n\n"
        f"Job Spec:\n{job_spec}\n"
    )
    cfg = dispatch.LLMConfig(provider=dispatch.normalize_provider(provider), api_key=api_key, model=model, base_url=base_url)

    try:
        raw = _call_llm_with_retries(prompt, cfg, prompts.JSON_FIX_PROMPT)
        parsed = parse_json_response(raw)
        panel: Dict[str, Dict[str, Any]] = {}
        for stance in PANEL_STANCES:
            entry = parsed.get(stance)
            if not entry:
                raise ValueError(f"Persona panel missing stance: {stance}")
            panel[stance] = Persona.model_validate(entry).model_dump()
        return panel
    except Exception as exc:
        raise RuntimeError(f"Failed to generate persona panel: {exc}") from exc


def analyze_cv(
    cv_text: str,
    job_spec: str,
    persona: Dict[str, Any],
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> Dict[str, Any]:
    if dispatch.normalize_provider(provider) == "mock":
        return {
            "summary": "Strong candidate with relevant experience.",
            "strengths": ["Python", "FastAPI"],
            "weaknesses": ["No cloud experience"],
            "missing_info": ["Education dates"],
        }

    persona_json = json.dumps(persona, indent=2)
    prompt = (
        f"{prompts.CV_ANALYSIS_PROMPT}\n\n"
        f"Persona:\n{persona_json}\n\n"
        f"Job Spec:\n{job_spec}\n\n"
        f"CV:\n{cv_text}\n"
    )
    cfg = dispatch.LLMConfig(provider=dispatch.normalize_provider(provider), api_key=api_key, model=model, base_url=base_url)

    try:
        raw = _call_llm_with_retries(prompt, cfg, prompts.JSON_FIX_PROMPT)
        parsed = parse_json_response(raw)
        analysis = CVAnalysis.model_validate(parsed)
        return analysis.model_dump()
    except Exception as exc:
        raise RuntimeError(f"Failed to analyze CV: {exc}") from exc

