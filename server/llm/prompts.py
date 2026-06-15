"""Shared LLM prompts.

These are provider-agnostic: every provider (OpenAI, Anthropic, Gemini, and any
OpenAI-compatible local model) is given the same instructions. Keeping them in one
place means a prompt change applies everywhere and adding a provider needs no prompt
edits.
"""
from __future__ import annotations

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
You are an interviewer generating ONE pointed interview question. Return STRICT JSON only.
Schema:
{
  "question_id": "string",
  "text": "string",
  "round": "string",
  "persona": "string",
  "anchor": "string",
  "competency": "string"
}
Rules:
- "anchor" MUST quote a specific phrase, project, technology, or number from the CV, or a
  specific requirement from the job spec, that this question targets.
- "competency" MUST be the name of the target competency provided below.
- If a previous answer was vague, lacked metrics, or contradicted the CV, ask a follow-up that
  drills into that specific gap rather than moving to a new topic.
- Reference concrete details from the CV or job spec. NEVER ask a question that could be asked of
  any candidate for any job.
- BANNED phrasings: "tell me about a time", "what is your greatest strength/weakness",
  "where do you see yourself", "walk me through your background".
- Use the persona style provided. Keep it natural and conversational.
- Ask one focused question (avoid multi-part checklists).
- Do not repeat topics or phrasing from previously asked questions.
- Do not include any extra keys.
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

COACHING_PROMPT = """
You are an interview coach giving feedback on ONE specific answer. Return STRICT JSON only.
Schema:
{
  "strengths": ["string"],
  "improvements": ["string"],
  "rewrite": "string"
}
Rules:
- Base every point on what the candidate ACTUALLY said; reference specific details, claims, or
  numbers from their answer. Never give generic feedback that could apply to any answer.
- 2 to 3 strengths and 2 to 3 improvements, each one sentence.
- "rewrite" must be an improved version of the candidate's OWN answer using STAR (Situation,
  Task, Action, Result) with concrete metrics where they implied them. Keep their actual facts;
  do NOT invent achievements or experience they did not mention.
- If the answer is empty, off-topic, or too vague to assess, say so plainly in the improvements.
"""


REPORT_PROMPT = """
You are an expert interviewer. Generate a final interview report based on the session transcript and scores. Return STRICT JSON only.
Schema:
{
  "overall_score": 0.0,
  "strengths": ["string"],
  "weaknesses": ["string"],
  "persona_feedback": [
    {
      "persona": "string",
      "positives": ["string"],
      "concerns": ["string"],
      "next_step": "string"
    }
  ]
}
Rules:
- overall_score should be a float 0.0-1.0
- persona_feedback should analyze how well the candidate matched the target persona
- next_step should be a recommendation (e.g., "Hire", "No Hire", "Follow-up")
"""
