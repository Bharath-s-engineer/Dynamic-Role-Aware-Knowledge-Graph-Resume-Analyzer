"""
app/models/resume_models.py
Pydantic models for Resume data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    candidate_name: str = Field(default="Unknown")
    skills: list[str] = Field(default_factory=list)
    inferred_experience_level: str = Field(default="unknown")
    years_experience: float = Field(default=0.0, ge=0)
    raw_text_preview: str = Field(default="", exclude=True)

    @property
    def skill_set(self) -> set[str]:
        return {s.lower() for s in self.skills}
