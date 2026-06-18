"""Tests for the hardened report generation retry loop (no real LLM calls)."""
import json

import pytest

from server.core import grading
from server.llm import dispatch

_VALID_REPORT = json.dumps({
    "overall_score": 0.8,
    "strengths": ["Clear examples"],
    "weaknesses": ["Add metrics"],
    "persona_feedback": [
        {"persona": "neutral", "positives": ["p"], "concerns": ["c"], "next_step": "Hire"}
    ],
})


def test_generate_report_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_call_llm(cfg, prompt, temperature=0.2):
        calls["n"] += 1
        # First response is unparseable; the retry (with the error fed back) returns valid JSON.
        return "sorry, here is your report" if calls["n"] == 1 else _VALID_REPORT

    monkeypatch.setattr(grading.dispatch, "call_llm", fake_call_llm)
    result = grading._generate_report_with_retries("PROMPT", dispatch.LLMConfig(provider="openai"), attempts=3)

    assert calls["n"] == 2  # it retried exactly once
    assert result["overall_score"] == 0.8
    assert result["persona_feedback"][0]["persona"] == "neutral"


def test_generate_report_gives_up_after_attempts(monkeypatch):
    monkeypatch.setattr(grading.dispatch, "call_llm", lambda *a, **k: "never valid json")
    with pytest.raises(RuntimeError):
        grading._generate_report_with_retries("PROMPT", dispatch.LLMConfig(provider="openai"), attempts=2)
