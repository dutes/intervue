from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

OPENAI_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")

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


def _run_curl(payload: Dict[str, Any]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = [
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
    ]
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        OPENAI_URL,
        *headers,
        "-d",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"OpenAI curl error: {result.stderr.strip()}")
    return result.stdout


def call_openai(prompt: str, temperature: float = 0.2) -> str:
    payload = {
        "model": DEFAULT_MODEL,
        "input": prompt,
        "temperature": temperature,
        "text": {"format": {"type": "json_object"}},
    }

    raw = _run_curl(payload)
    data = json.loads(raw)

    # Responses API includes "error": null on success, so only fail if it's truthy.
    err = data.get("error")
    if err:
        raise RuntimeError(f"OpenAI API error: {err}")

    output = ""
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                output += content.get("text", "")

    if not output:
        raise RuntimeError("OpenAI response missing output text")

    return output.strip()

def test_connection() -> None:
    prompt = "Return STRICT JSON only: {\"ok\": true}"
    _ = call_openai(prompt, temperature=0)
