"""Client for Piper (rhasspy/piper), a local offline neural TTS.

Piper ships as a self-contained binary that reads text on stdin and writes a WAV stream
to stdout. We shell out to it the same way the LLM clients shell out to ``curl`` — keeping
the "no SDK, no network" ethos and making the binary path the only thing the container
needs to provide.

A single multi-speaker voice model (``en_GB-aru-medium``) gives each interview persona its
own distinct voice via Piper's ``--speaker`` flag. NOTE: the ``--speaker`` value is a
0-based index into the model's ``speaker_id_map``, NOT the dataset speaker label. The aru
dataset labels (01..12) map to indices via that table, so the labels Brian picked translate
as: positive=label 09 -> index 4, neutral=label 10 -> index 2, hostile=label 12 -> index 8.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict

# Persona -> Piper --speaker index for the en_GB-aru-medium model. See module docstring for
# the label->index mapping; passing a raw label (e.g. 12) would exceed the max index (11).
# Each speaker's gender is declared in server/core/personas.PANEL_VOICE_GENDER so generated
# interviewer names match the voice — keep the two maps in sync if you change a speaker.
PERSONA_SPEAKERS: Dict[str, int] = {
    "positive": 4,  # aru dataset label "09" (warm/nice interviewer)
    "neutral": 2,   # aru dataset label "10"
    "hostile": 8,   # aru dataset label "12" (cold/hostile interviewer)
}
DEFAULT_SPEAKER = PERSONA_SPEAKERS["neutral"]

# Binary + voice model locations, overridable via env (set in the Docker image).
PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_VOICE = os.getenv("PIPER_VOICE", "/app/voices/en_GB-aru-medium.onnx")
# Synthesis of a short question is fast on CPU, but allow headroom + env tuning.
REQUEST_TIMEOUT = int(os.getenv("TTS_REQUEST_TIMEOUT", "60"))


class PiperUnavailable(RuntimeError):
    """The Piper binary or voice model is not present (e.g. bare local dev, no Docker)."""


def _resolve_binary() -> str:
    # An explicit absolute path may be given; otherwise look it up on PATH.
    if os.path.isfile(PIPER_BIN) and os.access(PIPER_BIN, os.X_OK):
        return PIPER_BIN
    found = shutil.which(PIPER_BIN)
    if found:
        return found
    raise PiperUnavailable(f"Piper binary not found: {PIPER_BIN!r}")


def synthesize(text: str, persona: str = "neutral") -> bytes:
    """Render ``text`` to WAV bytes using the persona's assigned speaker."""
    if not text or not text.strip():
        raise ValueError("No text to synthesize")

    binary = _resolve_binary()
    if not os.path.isfile(PIPER_VOICE):
        raise PiperUnavailable(f"Piper voice model not found: {PIPER_VOICE!r}")

    speaker = PERSONA_SPEAKERS.get((persona or "").strip().lower(), DEFAULT_SPEAKER)
    cmd = [
        binary,
        "--model", PIPER_VOICE,
        "--speaker", str(speaker),
        "--output_file", "-",  # write WAV to stdout
    ]
    result = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=REQUEST_TIMEOUT,
        check=False,
    )
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"Piper synthesis failed: {err[:500]}")
    if not result.stdout:
        raise RuntimeError("Piper produced no audio")
    return result.stdout


def is_available() -> bool:
    """True if the binary and voice model are both present."""
    try:
        _resolve_binary()
    except PiperUnavailable:
        return False
    return os.path.isfile(PIPER_VOICE)
