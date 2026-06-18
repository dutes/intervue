PERSONAS = {
    "positive": {
        "label": "Positive",
        "style": "Warm, encouraging, and supportive. Ask open-ended questions that help the candidate shine.",
    },
    "neutral": {
        "label": "Neutral",
        "style": "Professional and balanced. Ask clear, structured questions focused on evidence.",
    },
    "hostile": {
        "label": "Hostile",
        "style": "Skeptical and challenging. Ask sharp follow-ups, probe for weak claims and inconsistencies.",
    },
}


def persona_style(persona: str) -> str:
    info = PERSONAS.get(persona)
    if not info:
        return "Professional and direct."
    return info["style"]


# The interview panel is three distinct named interviewers, one per stance, conducted across
# the rounds (screening=positive, deep_dive=neutral, challenge=hostile). Each stance is voiced
# by a fixed Piper speaker (see server/tts/cli_piper.PERSONA_SPEAKERS), so the generated name
# MUST match that voice's gender. Verified from the ARU corpus talker table:
#   positive -> aru label 09 = Female, neutral -> label 10 = Male, hostile -> label 12 = Male.
# If you change a speaker in cli_piper, update the matching gender here.
PANEL_VOICE_GENDER = {
    "positive": "female",
    "neutral": "male",
    "hostile": "male",
}
PANEL_STANCES = ["positive", "neutral", "hostile"]
