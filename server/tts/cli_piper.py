"""Client for Piper (rhasspy/piper), a local offline neural TTS.

Piper ships as a self-contained binary that reads text on stdin and writes a WAV stream to
stdout. We shell out to it the same way the LLM clients shell out to ``curl`` — keeping the
"no SDK, no network" ethos.

Voice: ``en_US-libritts_r-medium``, a 904-speaker multi-speaker model. Each interview gets a
distinct three-person panel chosen per session (see ``speakers_for_session``): the asking
interviewer rotates per question, and each stance is voiced by a speaker whose gender matches
the generated interviewer name (positive=female, neutral/hostile=male). The gender-verified
speaker pools were built by cross-referencing the model's ``speaker_id_map`` (reader-id ->
index) against the LibriSpeech ``SPEAKERS.TXT`` gender labels, so name and voice always agree.
"""
from __future__ import annotations

import hashlib
import os
import random
import re
import shutil
import subprocess
from typing import Dict, List, Optional

# Gender of the voice assigned to each panel stance. MUST stay in sync with
# server/core/personas.PANEL_VOICE_GENDER (which constrains the generated name's gender).
PERSONA_GENDER: Dict[str, str] = {
    "positive": "female",
    "neutral": "male",
    "hostile": "male",
}


def _pool_from_env(name: str, default: List[int]) -> List[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        return default


# Curated, gender-verified speaker indices for en_US-libritts_r-medium (904 speakers). Built by
# cross-referencing the model's speaker_id_map against LibriSpeech SPEAKERS.TXT gender labels,
# then spreading across the verified set for variety. Override (e.g. after auditioning to drop
# any duds) via PIPER_FEMALE_SPEAKERS / PIPER_MALE_SPEAKERS (comma-separated indices).
FEMALE_SPEAKERS = _pool_from_env(
    "PIPER_FEMALE_SPEAKERS",
    [0, 54, 95, 142, 185, 238, 281, 325, 382, 453, 524, 576, 635, 698, 757, 832],
)
MALE_SPEAKERS = _pool_from_env(
    "PIPER_MALE_SPEAKERS",
    [2, 67, 137, 208, 278, 341, 398, 441, 498, 544, 607, 660, 718, 767, 812, 856],
)
_POOLS = {"female": FEMALE_SPEAKERS, "male": MALE_SPEAKERS}

# Binary + voice model locations, overridable via env (set in the Docker image).
PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_VOICE = os.getenv("PIPER_VOICE", "/app/voices/en_US-libritts_r-medium.onnx")
# Synthesis of a short question is fast on CPU, but allow headroom + env tuning.
REQUEST_TIMEOUT = int(os.getenv("TTS_REQUEST_TIMEOUT", "60"))

# Prosody/quality knobs (env-tunable, passed straight to the binary). length_scale > 1 slows
# speech slightly for clarity; sentence_silence inserts a pause between sentences. These nudge
# toward a calmer, more natural interview cadence than the bare defaults (length 1.0 /
# silence 0.2). noise_scale/noise_w are Piper's expressiveness defaults.
LENGTH_SCALE = os.getenv("PIPER_LENGTH_SCALE", "1.05")
NOISE_SCALE = os.getenv("PIPER_NOISE_SCALE", "0.667")
NOISE_W = os.getenv("PIPER_NOISE_W", "0.8")
SENTENCE_SILENCE = os.getenv("PIPER_SENTENCE_SILENCE", "0.3")

# Markdown / formatting characters espeak-ng would otherwise read aloud or stumble over.
_SPEECH_NOISE = re.compile(r"[*_`#>|]+")


def _normalize_for_speech(text: str) -> str:
    """Light cleanup so the voice reads cleanly: drop markdown marks and collapse whitespace.
    Sentence punctuation is preserved so Piper keeps natural prosody and inter-sentence pauses."""
    cleaned = _SPEECH_NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


class PiperUnavailable(RuntimeError):
    """The Piper binary or voice model is not present (e.g. bare local dev, no Docker)."""


def speakers_for_session(session_id: str) -> Dict[str, int]:
    """Assign a distinct speaker per stance for this session, drawn from the gender pool that
    matches each stance's interviewer name. Deterministic in the session id, so a session keeps
    a consistent panel while different sessions sound different (neutral & hostile stay distinct)."""
    rng = random.Random(hashlib.sha256((session_id or "").encode("utf-8")).hexdigest())
    female = rng.choice(FEMALE_SPEAKERS)
    males = rng.sample(MALE_SPEAKERS, 2) if len(MALE_SPEAKERS) >= 2 else MALE_SPEAKERS * 2
    return {"positive": female, "neutral": males[0], "hostile": males[1]}


def default_speaker(persona: str) -> int:
    """A stable speaker for a stance when there's no session context (e.g. previews)."""
    gender = PERSONA_GENDER.get((persona or "").strip().lower(), "male")
    pool = _POOLS.get(gender) or MALE_SPEAKERS
    return pool[0]


def _resolve_binary() -> str:
    # An explicit absolute path may be given; otherwise look it up on PATH.
    if os.path.isfile(PIPER_BIN) and os.access(PIPER_BIN, os.X_OK):
        return PIPER_BIN
    found = shutil.which(PIPER_BIN)
    if found:
        return found
    raise PiperUnavailable(f"Piper binary not found: {PIPER_BIN!r}")


def synthesize(text: str, persona: str = "neutral", session_id: Optional[str] = None) -> bytes:
    """Render ``text`` to WAV bytes. The speaker is chosen for the session+stance so the panel
    is consistent within a session and varied across sessions; without a session id it falls
    back to the stance's default speaker."""
    if not text or not text.strip():
        raise ValueError("No text to synthesize")

    binary = _resolve_binary()
    if not os.path.isfile(PIPER_VOICE):
        raise PiperUnavailable(f"Piper voice model not found: {PIPER_VOICE!r}")

    stance = (persona or "").strip().lower()
    if session_id:
        speaker = speakers_for_session(session_id).get(stance, default_speaker(stance))
    else:
        speaker = default_speaker(stance)

    cmd = [
        binary,
        "--model", PIPER_VOICE,
        "--speaker", str(speaker),
        "--length_scale", LENGTH_SCALE,
        "--noise_scale", NOISE_SCALE,
        "--noise_w", NOISE_W,
        "--sentence_silence", SENTENCE_SILENCE,
        "--output_file", "-",  # write WAV to stdout
    ]
    result = subprocess.run(
        cmd,
        input=_normalize_for_speech(text).encode("utf-8"),
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
