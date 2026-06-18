"""Mock TTS provider.

Returns a tiny, valid WAV (a short burst of near-silence) without needing the Piper
binary. Used by the test suite / CI and as a deterministic stand-in when ``TTS_PROVIDER``
is set to ``mock``. The byte length varies a little by persona so tests can tell the
speaker mapping is being threaded through.
"""
from __future__ import annotations

import io
import wave

_SAMPLE_RATE = 22050

# A hair of "audio" per persona, just enough to differentiate the output deterministically.
_PERSONA_MILLIS = {"positive": 120, "neutral": 100, "hostile": 140}


def synthesize(text: str, persona: str = "neutral") -> bytes:
    if not text or not text.strip():
        raise ValueError("No text to synthesize")
    millis = _PERSONA_MILLIS.get((persona or "").strip().lower(), 100)
    frames = int(_SAMPLE_RATE * millis / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(_SAMPLE_RATE)
        wav.writeframes(b"\x00\x00" * frames)  # silence
    return buf.getvalue()


def is_available() -> bool:
    return True
