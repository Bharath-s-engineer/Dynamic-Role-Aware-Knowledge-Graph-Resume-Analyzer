"""
app/models/response_models.py
Final API response shape for /analyze endpoint.

Fix applied:
  - BUG: ReadinessResult had no field for missing preferred skills, so the
    recommendations engine couldn't surface them. Added `missing_preferred_skills`
    as an optional list (defaults to empty so existing callers aren't broken).
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from app.models.graph_models import GraphData


class PartialMatch(BaseModel):
    skill: str
    coverage: float


class ReadinessResult(BaseModel):
    readiness_score: float = Field(ge=0.0, le=100.0)
    matched_skills: list[str] = Field(default_factory=list)
    inferred_skills: list[PartialMatch] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    # FIX: New field — preferred skills that are absent from the resume.
    # Kept separate from missing_skills (which are hard requirements) so the
    # frontend and recommendations engine can treat them differently.
    missing_preferred_skills: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    job_title: str
    job_role: str
    experience_level: str
    resume_skills: list[str]
    jd_required_skills: list[str]
    jd_preferred_skills: list[str]
    readiness: ReadinessResult
    recommendations: list[str]
    graph_data: GraphData
