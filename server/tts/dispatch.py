"""Single point of TTS provider dispatch.

Mirrors ``server/llm/dispatch.py``: callers route text-to-speech through ``synthesize`` so
adding a provider (OpenAI TTS, ElevenLabs, Azure neural, ...) is a one-file change. Unlike
the LLM layer, TTS is selected server-side via the ``TTS_PROVIDER`` env var rather than
per-session, because the default provider (Piper) is local and keyless.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple, TypedDict

from server.tts import cli_piper, mock

WAV_CONTENT_TYPE = "audio/wav"


class TTSConfig(TypedDict, total=False):
    provider: str
    api_key: Optional[str]  # reserved for future hosted providers (e.g. OpenAI TTS)


SUPPORTED_TTS_PROVIDERS = {"piper", "mock"}
DEFAULT_TTS_PROVIDER = os.getenv("TTS_PROVIDER", "piper").strip().lower()


class TTSUnavailable(RuntimeError):
    """The selected TTS provider can't run in this environment (e.g. Piper binary absent).

    The API turns this into a 503 so the client can disable the voice UI cleanly.
    """


def default_config() -> TTSConfig:
    return TTSConfig(provider=DEFAULT_TTS_PROVIDER)


def synthesize(cfg: TTSConfig, text: str, persona: str = "neutral") -> Tuple[bytes, str]:
    """Render ``text`` to audio bytes for the given persona. Returns (bytes, content_type)."""
    provider = (cfg.get("provider") or DEFAULT_TTS_PROVIDER).strip().lower()

    if provider == "mock":
        return mock.synthesize(text, persona), WAV_CONTENT_TYPE
    if provider == "piper":
        try:
            return cli_piper.synthesize(text, persona), WAV_CONTENT_TYPE
        except cli_piper.PiperUnavailable as exc:
            raise TTSUnavailable(str(exc)) from exc
    raise ValueError(f"Unsupported TTS provider: {provider!r}")


def is_available(cfg: Optional[TTSConfig] = None) -> bool:
    provider = ((cfg or default_config()).get("provider") or DEFAULT_TTS_PROVIDER).strip().lower()
    if provider == "mock":
        return mock.is_available()
    if provider == "piper":
        return cli_piper.is_available()
    return False
