from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class Competency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    weight: float = Field(ge=0.0, le=1.0)
    what_good_looks_like: str
    red_flags: List[str]


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competencies: List[Competency]


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    text: str
    round: str
    persona: str


class EvidenceFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    star_complete: bool
    metrics_present: bool
    specificity: int = Field(ge=0, le=3)


class Issues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vagueness: int = Field(ge=0, le=3)
    contradiction_with_cv: bool
    missing_example: bool


class Scorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competency_scores: Dict[str, int] = Field(default_factory=dict)
    evidence_flags: EvidenceFlags
    issues: Issues
    follow_up_suggestion: str


class PersonaFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: str
    positives: List[str]
    concerns: List[str]
    next_step: str


class ReportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    persona_feedback: List[PersonaFeedback]
