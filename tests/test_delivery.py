"""Tests for the Tier 1+2 delivery analysis (length, pace, hedging)."""
from server.core import delivery


def test_wpm_computed_for_spoken_answer():
    # 60 words in 30 seconds -> 120 wpm
    text = " ".join(["word"] * 60)
    result = delivery.analyze_delivery(text, duration_seconds=30, used_voice=True)
    assert result["wpm"] == 120


def test_wpm_is_none_for_typed_answer():
    text = " ".join(["word"] * 60)
    result = delivery.analyze_delivery(text, duration_seconds=30, used_voice=False)
    assert result["wpm"] is None  # pace is meaningless for typed answers


def test_short_answer_is_flagged():
    result = delivery.analyze_delivery("Too short.", used_voice=False)
    assert any("Short answer" in n for n in result["notes"])


def test_dense_hedging_is_flagged():
    result = delivery.analyze_delivery("um I kind of just did the thing you know", used_voice=False)
    assert result["hedge_count"] >= 3
    assert any("hedging" in n for n in result["notes"])


def test_sparse_hedging_not_flagged_in_long_answer():
    # One "kind of" buried in a long, substantive answer should not trip the flag.
    text = "kind of " + " ".join(["substantive"] * 100)
    result = delivery.analyze_delivery(text, used_voice=False)
    assert not any("hedging" in n for n in result["notes"])
