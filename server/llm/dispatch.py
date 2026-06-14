"""Single point of LLM provider dispatch.

Every core module (questions, scoring, rubric, analysis, grading) routes its LLM calls
through here so that adding a provider is a one-file change rather than editing a branch in
each module. A call is described by an ``LLMConfig``:

    provider:  one of SUPPORTED_PROVIDERS
    api_key:   per-session secret (never persisted); optional for local/mock
    model:     free-text model id; falls back to the provider default if blank
    base_url:  only used by the "local" (OpenAI-compatible) provider
"""
from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from server.llm import cli_anthropic, cli_compatible, cli_gemini, cli_openai
from server.llm.prompts import JSON_FIX_PROMPT  # noqa: F401  (re-exported for callers)


class LLMConfig(TypedDict, total=False):
    provider: str
    api_key: Optional[str]
    model: Optional[str]
    base_url: Optional[str]


# Provider id -> default model used when the user leaves the model field blank.
DEFAULT_MODELS: Dict[str, str] = {
    "openai": cli_openai.DEFAULT_MODEL,
    "anthropic": cli_anthropic.DEFAULT_MODEL,
    "gemini": cli_gemini.DEFAULT_MODEL,
    "local": "",  # no sensible default; the user must name their local model
    "mock": "mock",
}

SUPPORTED_PROVIDERS = set(DEFAULT_MODELS.keys())


def normalize_provider(provider: str) -> str:
    return (provider or "").strip().lower()


def config_from_session(session: Dict[str, Any], api_key: Optional[str] = None) -> LLMConfig:
    """Build an LLMConfig from a session dict plus the per-request api_key."""
    return LLMConfig(
        provider=normalize_provider(session.get("provider", "mock")),
        api_key=api_key,
        model=session.get("model"),
        base_url=session.get("base_url"),
    )


def call_llm(cfg: LLMConfig, prompt: str, temperature: float = 0.2) -> str:
    provider = normalize_provider(cfg.get("provider", ""))
    api_key = cfg.get("api_key")
    model = cfg.get("model") or DEFAULT_MODELS.get(provider) or None
    base_url = cfg.get("base_url")

    if provider == "openai":
        return cli_openai.call_openai(prompt, temperature=temperature, api_key=api_key, model=model)
    if provider == "anthropic":
        return cli_anthropic.call_anthropic(prompt, temperature=temperature, api_key=api_key, model=model)
    if provider == "gemini":
        return cli_gemini.call_gemini(prompt, temperature=temperature, api_key=api_key, model=model)
    if provider == "local":
        return cli_compatible.call_compatible(
            prompt, temperature=temperature, api_key=api_key, model=model, base_url=base_url
        )
    raise ValueError(f"Unsupported provider for LLM call: {provider!r}")


# Substrings that mark a model as non-conversational (embeddings, audio, image, etc.).
# Used to keep the model dropdown focused on chat-capable models for providers (OpenAI,
# local) whose model lists include many non-chat entries.
_NON_CHAT_MARKERS = (
    "embed",
    "whisper",
    "tts",
    "dall-e",
    "moderation",
    "transcribe",
    "audio",
    "image",
    "vision-instruct",  # leave general vision chat models, drop pure image pipelines
    "rerank",
    "search",
    "similarity",
    "guard",
)


def _filter_chat_models(model_ids: list[str]) -> list[str]:
    seen = set()
    result = []
    for mid in model_ids:
        low = mid.lower()
        if any(marker in low for marker in _NON_CHAT_MARKERS):
            continue
        if mid not in seen:
            seen.add(mid)
            result.append(mid)
    return sorted(result)


def list_models(cfg: LLMConfig) -> list[str]:
    """Return the available model IDs for a provider, filtered to chat-capable ones."""
    provider = normalize_provider(cfg.get("provider", ""))
    api_key = cfg.get("api_key")
    base_url = cfg.get("base_url")

    if provider == "mock":
        return ["mock"]
    if provider == "openai":
        return _filter_chat_models(cli_openai.list_models(api_key=api_key))
    if provider == "anthropic":
        return _filter_chat_models(cli_anthropic.list_models(api_key=api_key))
    if provider == "gemini":
        return _filter_chat_models(cli_gemini.list_models(api_key=api_key))
    if provider == "local":
        return _filter_chat_models(cli_compatible.list_models(api_key=api_key, base_url=base_url))
    raise ValueError(f"Unsupported provider: {provider!r}")


def test_connection(cfg: LLMConfig) -> None:
    """Validate that a provider is reachable with the given credentials/config.

    Raises ValueError for misconfiguration the user can fix, or propagates the provider
    error from the underlying client.
    """
    provider = normalize_provider(cfg.get("provider", ""))
    api_key = cfg.get("api_key")
    model = cfg.get("model") or DEFAULT_MODELS.get(provider) or None
    base_url = cfg.get("base_url")

    if provider == "mock":
        return
    # For hosted providers the underlying client falls back to an env var and raises a clear
    # "<PROVIDER>_API_KEY is not set" error if no key is found, so no pre-check is needed here.
    if provider == "openai":
        cli_openai.test_connection(api_key=api_key, model=model)
        return
    if provider == "anthropic":
        cli_anthropic.test_connection(api_key=api_key, model=model)
        return
    if provider == "gemini":
        cli_gemini.test_connection(api_key=api_key, model=model)
        return
    if provider == "local":
        if not base_url:
            raise ValueError("A base URL is required for a local/custom model")
        if not model:
            raise ValueError("A model name is required for a local/custom model")
        cli_compatible.test_connection(api_key=api_key, model=model, base_url=base_url)
        return

    raise ValueError(f"Unsupported provider: {provider!r}")
