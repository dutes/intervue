"""Tests for the interviewer persona panel — three named personas, gender-matched to voices."""
from server.core import analysis, personas
from server.tts import cli_piper


def test_panel_maps_stay_in_sync_with_voices():
    # Every voiced stance must have a declared name-gender, and vice versa.
    assert set(personas.PANEL_VOICE_GENDER) == set(cli_piper.PERSONA_SPEAKERS)
    assert set(personas.PANEL_STANCES) == set(cli_piper.PERSONA_SPEAKERS)


def test_panel_voice_genders_are_the_verified_values():
    # Verified from the ARU corpus talker table: positive=label 09 (F), neutral=10 (M), hostile=12 (M).
    assert personas.PANEL_VOICE_GENDER == {"positive": "female", "neutral": "male", "hostile": "male"}


def test_mock_panel_has_three_distinct_named_personas():
    panel = analysis.generate_persona_panel("Senior Backend Engineer role.", "mock")
    assert set(panel) == set(personas.PANEL_STANCES)
    names = {p["name"] for p in panel.values()}
    assert len(names) == 3  # three different people
    for p in panel.values():
        assert p["name"] and p["role"] and p["tone"]
        assert isinstance(p["key_concerns"], list)
