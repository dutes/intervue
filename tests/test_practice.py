from sys import exc_info

from requests import session

import pytest
from server.core import questions
from server.core import analysis
from server.llm import dispatch


@pytest.mark.parametrize("start_round, expected", [
    (1,10),
    (2,7),
    (3,3),
])


def test_total_questions(start_round,expected):
    assert questions.total_questions(start_round) == expected


def test_first_round_has_ten_questions():
    result = questions.total_questions(1)
    assert result == 10


def test_generate_persona_parses_llm_json(monkeypatch):
    def fake_call_llm(cfg,promt, temperature=0.2):
        return '{"name": "Dana", "role": "EM", "tone": "Direct", "key_concerns": ["scale"]}'
    
    monkeypatch.setattr(dispatch, "call_llm", fake_call_llm)

    result = analysis.generate_persona("a job spec", "openai")

    assert result["name"] == "Dana"
    assert result["role"] == "EM"


def test_generate_persona_raises_on_bad_json(monkeypatch):
    def fake_bad(cfg, prompt, temperature=0.2):
        return "not valid json at all"
    
    monkeypatch.setattr(dispatch, "call_llm", fake_bad)
    with pytest.raises(RuntimeError, match="Failed to generate persona"):
        analysis.generate_persona("a job spec", "openai")

    monkeypatch.setattr(dispatch, "call_llm", fake_bad)
    with pytest.raises(RuntimeError) as exc_info:
        analysis.generate_persona("a job spec", "openai")
        assert "Failed to generate persona" in str(exc_info.value)

def test_config_from_session_maps_fields_and_normalises():
    session={"provider": " OpenAI ", "model": "gpt-5.2", "base_url": "http://x"}
    cfg = dispatch.config_from_session(session, api_key="secret_key")

    assert cfg["provider"] == "openai"
    assert cfg["api_key"] == "secret_key"
    assert cfg["model"] == "gpt-5.2"
    assert cfg["base_url"] == "http://x"

def test_config_from_session_defaults():
    # session={"provider": "mock", "model": None, "base_url": None} 
    cfg = dispatch.config_from_session({}, api_key=None)

    assert cfg["provider"] == "mock"
    assert cfg["api_key"] is None
    assert cfg["model"] is None
    assert cfg["base_url"] is None