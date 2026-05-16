"""
app/models/jd_models.py
Pydantic models for Job Description data.
"""

from __future__ import annotations
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator


class ExperienceLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class SkillImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    INFERRED = "inferred"


class SkillNode(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    category: Annotated[str, Field(min_length=1, max_length=60)]
    importance: SkillImportance = SkillImportance.REQUIRED
    aliases: list[str] = Field(default_factory=list)

    @field_validator("name", "category", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("aliases", mode="before")
    @classmethod
    def _normalise_aliases(cls, v: list) -> list[str]:
        return [a.strip().lower() for a in v if str(a).strip()]

    def matches_text(self, text: str) -> bool:
        lower = text.lower()
        if self.name.lower() in lower:
            return True
        return any(a in lower for a in self.aliases)


class JDProfile(BaseModel):
    job_title: Annotated[str, Field(min_length=1, max_length=200)]
    job_role: Annotated[str, Field(min_length=1, max_length=100)]
    experience_level: ExperienceLevel
    required_skills: list[SkillNode] = Field(default_factory=list)
    preferred_skills: list[SkillNode] = Field(default_factory=list)
    raw_text_preview: str = Field(default="", exclude=True)

    @property
    def all_skills(self) -> list[SkillNode]:
        return self.required_skills + self.preferred_skills

    @property
    def required_skill_names(self) -> list[str]:
        return [s.name for s in self.required_skills]

    @property
    def preferred_skill_names(self) -> list[str]:
        return [s.name for s in self.preferred_skills]
