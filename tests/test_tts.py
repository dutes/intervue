"""Tests for the TTS dispatch layer and providers — pure, no Piper binary required."""
import io
import wave

import pytest

from server.tts import cli_piper, dispatch, mock


def _is_wav(data: bytes) -> bool:
    return data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def test_mock_synthesize_returns_valid_wav():
    audio, content_type = dispatch.synthesize(dispatch.TTSConfig(provider="mock"), "Hello there", "neutral")
    assert content_type == dispatch.WAV_CONTENT_TYPE
    assert _is_wav(audio)
    # It should be parseable as a real WAV (mono, 16-bit).
    with wave.open(io.BytesIO(audio), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2


def test_mock_persona_threads_through_to_distinct_output():
    cfg = dispatch.TTSConfig(provider="mock")
    positive, _ = dispatch.synthesize(cfg, "same text", "positive")
    hostile, _ = dispatch.synthesize(cfg, "same text", "hostile")
    # Different personas produce different audio (proves persona is plumbed end to end).
    assert positive != hostile


def test_mock_empty_text_rejected():
    with pytest.raises(ValueError):
        mock.synthesize("   ", "neutral")


def test_unsupported_provider_raises():
    with pytest.raises(ValueError):
        dispatch.synthesize(dispatch.TTSConfig(provider="bogus"), "hi", "neutral")


# This is the load-bearing mapping: Piper's --speaker is a 0-based index into the model's
# speaker_id_map, NOT the dataset label. Brian picked aru labels 09/10/12, which translate to
# indices 4/2/8. Passing the labels directly (esp. 12) would exceed the max valid index (11).
def test_piper_persona_speaker_indices():
    assert cli_piper.PERSONA_SPEAKERS == {"positive": 4, "neutral": 2, "hostile": 8}
    assert max(cli_piper.PERSONA_SPEAKERS.values()) <= 11


def test_piper_unknown_persona_falls_back_to_neutral_speaker():
    assert cli_piper.DEFAULT_SPEAKER == cli_piper.PERSONA_SPEAKERS["neutral"]


def test_normalize_for_speech_strips_markdown_and_collapses_whitespace():
    raw = "**Bold**  and `code`  with\n\nbreaks and  spaces."
    cleaned = cli_piper._normalize_for_speech(raw)
    assert "*" not in cleaned and "`" not in cleaned
    assert "  " not in cleaned  # whitespace collapsed
    assert cleaned == "Bold and code with breaks and spaces."


def test_piper_unavailable_is_wrapped_as_tts_unavailable(monkeypatch):
    # Point the binary + voice at paths that don't exist so synthesis can't run.
    monkeypatch.setattr(cli_piper, "PIPER_BIN", "/nonexistent/piper-binary-xyz")
    monkeypatch.setattr(cli_piper, "PIPER_VOICE", "/nonexistent/voice.onnx")
    assert cli_piper.is_available() is False
    with pytest.raises(dispatch.TTSUnavailable):
        dispatch.synthesize(dispatch.TTSConfig(provider="piper"), "hi", "neutral")
