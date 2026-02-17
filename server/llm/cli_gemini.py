from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

RUBRIC_PROMPT = """
You are generating a hiring rubric from a job spec and CV. Return STRICT JSON only.
Schema:
{
  "competencies": [
    {
      "name": "string",
      "weight": 0.0,
      "what_good_looks_like": "string",
      "red_flags": ["string"]
    }
  ]
}
Rules:
- 6 to 8 competencies
- weights must sum to 1.0
"""

QUESTION_PROMPT = """
You are an interviewer generating a single interview question. Return STRICT JSON only.
Schema:
{
  "question_id": "string",
  "text": "string",
  "round": "string",
  "persona": "string"
}
Rules:
- Make the question specific to job spec + CV + rubric
- Use the persona style provided
- Avoid repeating topics or phrasing from previously asked questions
- Keep it natural and conversational, like a real interview
- Ask one focused question (avoid multi-part checklists)
- Do not include any extra keys
"""

SCORE_PROMPT = """
You are scoring a candidate answer using a rubric. Return STRICT JSON only.
Schema:
{
  "competency_scores": {"Competency Name": 0},
  "evidence_flags": {
    "star_complete": false,
    "metrics_present": false,
    "specificity": 0
  },
  "issues": {
    "vagueness": 0,
    "contradiction_with_cv": false,
    "missing_example": false
  },
  "follow_up_suggestion": "string"
}
Rules:
- competency scores are integers 0..4
- include every competency from the rubric
"""

JSON_FIX_PROMPT = """
Your previous output was invalid JSON. Fix it and return ONLY valid JSON that matches the schema.
"""


PERSONA_PROMPT = """
You are an expert hiring manager. Generate a persona for the interviewer based on the job spec. Return STRICT JSON only.
Schema:
{
  "name": "string",
  "role": "string",
  "tone": "string",
  "key_concerns": ["string"]
}
Rules:
- The persona should be appropriate for the role and company culture implied by the job spec.
- Key concerns should be specific aspects the hiring manager would be worried about given the job spec.
"""


CV_ANALYSIS_PROMPT = """
You are the hiring manager defined by the persona. Analyze the candidate's CV against the job spec. Return STRICT JSON only.
Schema:
{
  "summary": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "missing_info": ["string"]
}
Rules:
- Be critical and realistic.
- Identify specific gaps or red flags in the CV relative to the job requirements.
- Highlight areas that need probing during the interview.
"""


def _run_curl(payload: Dict[str, Any]) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent?key={api_key}"
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Gemini curl error: {result.stderr.strip()}")
    return result.stdout


def call_gemini(prompt: str, temperature: float = 0.2) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    raw = _run_curl(payload)
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"Gemini API error: {data['error']}")
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini response missing candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini response missing parts")
    text = parts[0].get("text", "")
    if not text:
        raise RuntimeError("Gemini response missing text")
    return text.strip()


def test_connection() -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_gemini(prompt, temperature=0)
