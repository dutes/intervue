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


def test_persona_gender_mapping():
    # positive=female, neutral/hostile=male — must match the generated interviewer name's gender.
    assert cli_piper.PERSONA_GENDER == {"positive": "female", "neutral": "male", "hostile": "male"}


def test_speaker_pools_are_nonempty_and_gender_disjoint():
    assert cli_piper.FEMALE_SPEAKERS and cli_piper.MALE_SPEAKERS
    assert not (set(cli_piper.FEMALE_SPEAKERS) & set(cli_piper.MALE_SPEAKERS))


def test_speakers_for_session_is_deterministic_and_gender_correct():
    a = cli_piper.speakers_for_session("session-xyz")
    b = cli_piper.speakers_for_session("session-xyz")
    assert a == b  # same session -> same panel
    assert set(a) == {"positive", "neutral", "hostile"}
    assert a["positive"] in cli_piper.FEMALE_SPEAKERS  # name is female -> female voice
    assert a["neutral"] in cli_piper.MALE_SPEAKERS and a["hostile"] in cli_piper.MALE_SPEAKERS
    assert a["neutral"] != a["hostile"]  # two distinct male voices


def test_speakers_for_session_varies_across_sessions():
    positives = {cli_piper.speakers_for_session(f"s{i}")["positive"] for i in range(20)}
    assert len(positives) > 1  # different interviews don't all sound identical


def test_default_speaker_matches_stance_gender():
    assert cli_piper.default_speaker("positive") in cli_piper.FEMALE_SPEAKERS
    assert cli_piper.default_speaker("hostile") in cli_piper.MALE_SPEAKERS


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
