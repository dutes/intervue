"""Lightweight delivery analysis for an answer (Tier 1 + 2).

This works from the answer text plus an optional spoken duration — no audio capture. It measures
length, pace (words-per-minute, only meaningful for spoken answers), and hedging/filler phrases.
True "um/uh" and pause analysis would need raw audio (a later upgrade); the recognizer strips
those from the transcript.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Multi-word hedges, matched as substrings.
PHRASE_HEDGES = ("kind of", "sort of", "you know", "i guess", "i mean", "to be honest", "a little bit")
# Single-word fillers/hedges, matched as whole tokens.
WORD_HEDGES = ("um", "uh", "erm", "basically", "literally", "actually", "kinda", "gonna")


def analyze_delivery(
    answer_text: str,
    duration_seconds: Optional[float] = None,
    used_voice: bool = False,
) -> Dict[str, Any]:
    text = (answer_text or "").strip()
    words = text.split()
    word_count = len(words)
    lower = text.lower()

    hedge_count = sum(lower.count(phrase) for phrase in PHRASE_HEDGES)
    tokens = re.findall(r"[a-z']+", lower)
    hedge_count += sum(1 for t in tokens if t in WORD_HEDGES)

    # Pace is only meaningful for a spoken answer with a measured duration.
    wpm: Optional[int] = None
    if used_voice and duration_seconds and duration_seconds > 0 and word_count > 0:
        wpm = round(word_count / (duration_seconds / 60.0))

    notes = []
    if word_count == 0:
        notes.append("No answer captured.")
    else:
        if word_count < 50:
            notes.append("Short answer — develop your example with more specific detail.")
        elif word_count > 320:
            notes.append("Long answer — tighten it to the most relevant points.")

        if wpm is not None:
            if wpm >= 170:
                notes.append(f"Fast pace (~{wpm} wpm) — slow down so each point lands.")
            elif wpm <= 95:
                notes.append(f"Measured pace (~{wpm} wpm) — keep your energy up.")
            else:
                notes.append(f"Good speaking pace (~{wpm} wpm).")

        # Flag hedging by density (so a few in a long answer don't trip it) or a high absolute count.
        hedge_dense = hedge_count >= 3 and (hedge_count / max(word_count, 1)) >= 0.03
        if hedge_dense or hedge_count >= 5:
            notes.append(f"{hedge_count} hedging/filler phrases — sound more assertive (cut 'kind of', 'you know', etc.).")

        if not notes:
            notes.append("Clear length and confident phrasing.")

    return {
        "word_count": word_count,
        "wpm": wpm,
        "hedge_count": hedge_count,
        "used_voice": used_voice,
        "notes": notes,
    }
