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
- 6 to 8 competencies, each drawn from the ACTUAL requirements in this job spec (not generic
  interview traits). Name the skills and responsibilities the role really calls for.
- "what_good_looks_like" must describe an OBSERVABLE behaviour in an answer — what a strong
  candidate would concretely say or demonstrate — not an abstract trait.
- "red_flags" must be concrete, answer-level warning signs (e.g. "no metrics", "blames others",
  "only describes team work, not their own contribution").
- "weight" reflects how critical the competency is TO THIS ROLE: weight the must-haves from the
  job spec highest. Weights must sum to 1.0.
- Do not include any extra keys.
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

FOLLOWUP_PROMPT = """
You are the interviewer. The candidate just gave a WEAK answer and you want to probe deeper
before moving on. Generate ONE short, pointed follow-up question. Return STRICT JSON only.
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
- Drill into the SPECIFIC gap in their answer — the missing detail, the absent metric, the vague
  claim, or the unsupported assertion. Reference what they actually said.
- One sentence, conversational, like a real interviewer pressing for substance
  (e.g. "What was the actual impact in numbers?" or "What did YOU personally do there?").
- Do not start a new topic; stay on the same question they just answered.
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
Scoring scale for EACH competency (integers 0..4) — score ONLY on evidence present in the answer:
- 0 = did not address this competency at all
- 1 = claimed/asserted but with no supporting detail
- 2 = relevant but generic; no specific example or actions
- 3 = a specific, concrete example with the candidate's own actions
- 4 = a specific example WITH a measurable outcome/result and reflection
Rules:
- Include every competency from the rubric. If the answer gives no evidence for one, score it 0
  rather than guessing — do not reward an answer for competencies it never touched.
- "specificity" (0..3): 0 = vague throughout, 3 = concrete names/numbers/decisions throughout.
- "vagueness" (0..3): 0 = precise, 3 = hand-wavy and non-committal.
- "star_complete": true only if Situation, Task, Action AND Result are all present.
- "metrics_present": true only if the answer contains a concrete number/measurable outcome.
- "contradiction_with_cv": true only if the answer conflicts with the provided CV.
- "missing_example": true if the answer stays abstract with no concrete example.
- "follow_up_suggestion": the single sharpest follow-up question to expose the biggest gap.
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

PANEL_PERSONA_PROMPT = """
You are designing a panel of THREE distinct interviewers for a job interview, based on the job spec. Return STRICT JSON only.
Schema:
{
  "positive": {"name": "string", "role": "string", "tone": "string", "key_concerns": ["string"]},
  "neutral":  {"name": "string", "role": "string", "tone": "string", "key_concerns": ["string"]},
  "hostile":  {"name": "string", "role": "string", "tone": "string", "key_concerns": ["string"]}
}
Rules:
- The three interviewers are DIFFERENT people with different names; together they form one hiring panel for this role.
- "positive" is warm and encouraging; "neutral" is professional and balanced; "hostile" is skeptical and challenging.
- Each interviewer's name MUST clearly read as the gender specified for them below — this matches their speaking voice, so a mismatch is jarring.
- Roles and key concerns should fit the role and company culture implied by the job spec; key concerns should be specific.
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
  "rewrite": "string",
  "ideal_answer": "string"
}
Rules:
- Base every point on what the candidate ACTUALLY said; reference specific details, claims, or
  numbers from their answer. Never give generic feedback that could apply to any answer.
- 2 to 3 strengths and 2 to 3 improvements, each one sentence.
- "rewrite" must be an improved version of the candidate's OWN answer using STAR (Situation,
  Task, Action, Result) with concrete metrics where they implied them. Keep their actual facts;
  do NOT invent achievements or experience they did not mention.
- "ideal_answer" is different: a concise MODEL answer to this question that would score top
  marks against the rubric — an exemplar a strong candidate might give, in STAR form with a
  plausible concrete outcome. It is illustrative (not attributed to the candidate), so it may use
  example specifics. Keep it tight (3-6 sentences).
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
- Every strength and weakness MUST be grounded in the transcript: reference the specific
  question or quote/paraphrase what the candidate actually said. Do NOT give generic feedback
  that could apply to any candidate (e.g. avoid "good communication skills" with no evidence).
- persona_feedback should analyze how well the candidate matched the target persona; its
  concerns should likewise cite specific moments from the transcript.
- next_step should be a recommendation (e.g., "Hire", "No Hire", "Follow-up")
"""
