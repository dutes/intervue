"""Tests for the LLM dispatch layer — all pure functions, no network."""
import pytest

from server.llm import dispatch


# @pytest.mark.parametrize runs this ONE test body once per (raw, expected) pair.
# Each pair is reported as a separate test, so a failure tells you exactly which input broke.
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("openai", "openai"),
        ("  OpenAI ", "openai"),  # trims + lowercases
        ("GEMINI", "gemini"),
        ("", ""),
    ],
)
def test_normalize_provider(raw, expected):
    assert dispatch.normalize_provider(raw) == expected


def test_filter_chat_models_drops_non_chat_and_sorts():
    # Arrange
    models = ["gpt-5.2", "text-embedding-3-large", "whisper-1", "gpt-4o", "dall-e-3"]
    # Act
    result = dispatch._filter_chat_models(models)
    # Assert: embedding/whisper/dall-e removed, remainder sorted alphabetically
    assert result == ["gpt-4o", "gpt-5.2"]


def test_filter_chat_models_dedupes():
    assert dispatch._filter_chat_models(["a", "a", "b"]) == ["a", "b"]


def test_call_llm_rejects_unknown_provider():
    # pytest.raises asserts that the block raises the given exception type.
    with pytest.raises(ValueError):
        dispatch.call_llm(dispatch.LLMConfig(provider="bogus"), "hello")


def test_test_connection_mock_is_a_noop():
    # The mock provider needs no key/network — this should simply not raise.
    dispatch.test_connection(dispatch.LLMConfig(provider="mock"))


def test_test_connection_local_requires_base_url():
    cfg = dispatch.LLMConfig(provider="local", model="llama3", base_url=None)
    # `match` checks the error message contains this substring (regex).
    with pytest.raises(ValueError, match="base URL"):
        dispatch.test_connection(cfg)
