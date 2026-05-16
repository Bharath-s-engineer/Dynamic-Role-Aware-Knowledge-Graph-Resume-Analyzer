"""
app/parsing/jd_parser.py
AI-powered structured extraction from Job Description text.

Defensive against:
  - Model returning a bare list of skills instead of the wrapper object
  - Missing top-level keys
  - Invalid experience_level values
  - Extra/unexpected fields in skill objects
"""

import logging
from app.core.llm_client import call_llm_for_json
from app.core.config import settings
from app.models.jd_models import JDProfile, SkillNode, SkillImportance, ExperienceLevel

logger = logging.getLogger(__name__)

_SYSTEM = """You are an expert technical recruiter and skills taxonomist.
Parse the Job Description and return ONLY a valid JSON object — no prose, no markdown fences.

REQUIRED schema (return exactly this shape):
{
  "job_title": "exact title from JD",
  "job_role": "canonical role, e.g. Backend Engineer | Data Scientist | DevOps Engineer",
  "experience_level": "intern",
  "required_skills": [
    {
      "name": "canonical skill name",
      "category": "language|framework|database|cloud|devops|ml_ai|testing|tool|concept|soft_skill",
      "importance": "required",
      "aliases": []
    }
  ],
  "preferred_skills": []
}

experience_level MUST be one of: intern | junior | mid | senior | lead | principal
  - intern/junior: 0-2 years or internship role
  - mid: 2-4 years
  - senior: 5-8 years
  - lead/principal: 9+ years

Rules:
- ALWAYS return the wrapper object — NEVER a bare array of skills
- required_skills: mentioned as mandatory / must-have / required
- preferred_skills: nice-to-have / bonus / preferred
- Canonical names: "PostgreSQL" not "postgres db", "React" not "ReactJS"
- Include 5-20 required_skills maximum
- Keep aliases list short (0-3 items)
"""

_VALID_LEVELS = {e.value for e in ExperienceLevel}


def _safe_skill(raw: dict, importance: SkillImportance) -> SkillNode | None:
    """Convert a raw dict to SkillNode, returning None on failure."""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "")).strip()
    if not name:
        return None
    try:
        return SkillNode(
            name=name,
            category=str(raw.get("category", "concept")).strip(),
            importance=importance,
            aliases=[str(a) for a in raw.get("aliases", []) if a],
        )
    except Exception as exc:
        logger.warning("Skipping invalid skill %r: %s", name, exc)
        return None


def _coerce_level(raw: str) -> ExperienceLevel:
    """Map the model's level string to an ExperienceLevel, with fallbacks."""
    val = str(raw).strip().lower()
    if val in _VALID_LEVELS:
        return ExperienceLevel(val)
    # Common model mistakes
    mapping = {
        "entry": ExperienceLevel.JUNIOR,
        "entry-level": ExperienceLevel.JUNIOR,
        "associate": ExperienceLevel.JUNIOR,
        "staff": ExperienceLevel.LEAD,
        "manager": ExperienceLevel.LEAD,
        "director": ExperienceLevel.PRINCIPAL,
    }
    return mapping.get(val, ExperienceLevel.MID)


def parse_jd(jd_text: str) -> JDProfile:
    """
    Parse a job description into a validated JDProfile.

    Handles the case where the model returns a bare list of skills
    instead of the full wrapper object.
    """
    user_content = f"Parse this Job Description:\n\n{jd_text[:6000]}"

    raw = call_llm_for_json(
        system=_SYSTEM,
        user=user_content,
        max_tokens=settings.llm_max_tokens_parse,
    )

    # ── Bug fix: model returned bare list of skill objects ───────────────────
    if isinstance(raw, list):
        logger.warning(
            "jd_parser: model returned a bare list (%d items) instead of wrapper object. "
            "Treating all items as required_skills with unknown role/level.",
            len(raw),
        )
        required = [s for s in (_safe_skill(item, SkillImportance.REQUIRED) for item in raw) if s]
        return JDProfile(
            job_title="Unknown Role",
            job_role="Engineer",
            experience_level=ExperienceLevel.MID,
            required_skills=required,
            preferred_skills=[],
            raw_text_preview=jd_text[:500],
        )

    # ── Expected: dict ────────────────────────────────────────────────────────
    if not isinstance(raw, dict):
        raise ValueError(
            f"jd_parser: expected dict from LLM, got {type(raw).__name__}. Raw: {raw!r}"
        )

    required_raw = raw.get("required_skills") or []
    preferred_raw = raw.get("preferred_skills") or []

    # Guard: sometimes model puts all skills in required_skills as a flat list of strings
    if required_raw and isinstance(required_raw[0], str):
        required_raw = [{"name": s, "category": "concept", "importance": "required", "aliases": []}
                        for s in required_raw]

    required = [s for s in (_safe_skill(r, SkillImportance.REQUIRED) for r in required_raw) if s]
    preferred = [s for s in (_safe_skill(r, SkillImportance.PREFERRED) for r in preferred_raw) if s]

    profile = JDProfile(
        job_title=str(raw.get("job_title") or "Unknown Role").strip(),
        job_role=str(raw.get("job_role") or "Engineer").strip(),
        experience_level=_coerce_level(raw.get("experience_level") or "mid"),
        required_skills=required,
        preferred_skills=preferred,
        raw_text_preview=jd_text[:500],
    )

    logger.info(
        "JD parsed: role=%s level=%s required=%d preferred=%d",
        profile.job_role,
        profile.experience_level.value,
        len(profile.required_skills),
        len(profile.preferred_skills),
    )
    return profile
