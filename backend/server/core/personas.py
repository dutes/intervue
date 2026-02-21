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
