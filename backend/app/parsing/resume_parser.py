"""
app/parsing/resume_parser.py
AI-powered structured extraction from Resume text.

Changes vs previous version:
  - Shorter, cleaner system prompt (less likely to trigger empty response)
  - Hard character limit on resume text sent to model (3000 chars max)
  - Fallback: if LLM fails entirely, extract skills via simple keyword scan
  - All raw fields coerced defensively before Pydantic validation
"""

import logging
import re

from app.core.llm_client import call_llm_for_json
from app.core.config import settings
from app.models.resume_models import ResumeProfile

logger = logging.getLogger(__name__)

# Shorter prompt = fewer tokens = less chance of empty response
_SYSTEM = """Extract structured data from this resume. Return ONLY valid JSON, no markdown:
{
  "candidate_name": "full name or Unknown",
  "skills": ["skill1", "skill2"],
  "inferred_experience_level": "intern|junior|mid|senior|lead|principal",
  "years_experience": 0.0
}
Rules: canonical skill names (React not ReactJS, PostgreSQL not postgres).
Include all technical skills, tools, languages, frameworks mentioned.
years_experience = 0 for students."""

# Common tech skills for keyword-based fallback
_KEYWORD_SKILLS = [
    "python","java","javascript","typescript","c++","c#","go","rust","kotlin","swift",
    "react","angular","vue","nextjs","nodejs","express","fastapi","django","flask","spring",
    "sql","mysql","postgresql","mongodb","redis","sqlite","cassandra","dynamodb",
    "docker","kubernetes","aws","gcp","azure","terraform","ansible","jenkins","git","github",
    "linux","bash","html","css","graphql","rest","grpc","kafka","rabbitmq",
    "tensorflow","pytorch","scikit-learn","pandas","numpy","opencv","nlp",
    "agile","scrum","jira","figma","postman","vscode",
]


def _keyword_fallback(text: str) -> list[str]:
    """Extract skills by keyword matching when LLM fails."""
    lower = text.lower()
    found = [s for s in _KEYWORD_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', lower)]
    logger.info("Keyword fallback extracted %d skills", len(found))
    return [s.capitalize() if s.islower() else s for s in found]


def _coerce_level(val: str) -> str:
    """Map any model output to a valid experience level."""
    mapping = {
        "entry": "junior", "entry-level": "junior", "associate": "junior",
        "staff": "lead", "manager": "lead", "director": "principal",
        "fresher": "intern", "graduate": "intern",
    }
    v = str(val).strip().lower()
    valid = {"intern", "junior", "mid", "senior", "lead", "principal"}
    return v if v in valid else mapping.get(v, "junior")


def parse_resume(resume_text: str) -> ResumeProfile:
    """
    Parse resume text into a validated ResumeProfile.

    Falls back to keyword extraction if the LLM call fails.
    """
    # Hard cap: 3000 chars is plenty for skill extraction
    truncated = resume_text[:3000]
    user_content = f"Resume:\n\n{truncated}"

    raw = None
    try:
        raw = call_llm_for_json(
            system=_SYSTEM,
            user=user_content,
            max_tokens=settings.llm_max_tokens_parse,
        )
    except Exception as exc:
        logger.warning(
            "Resume LLM call failed (%s). Using keyword fallback.", exc
        )

    # ── Build profile from LLM output OR fallback ────────────────────────────
    if isinstance(raw, dict):
        skills_raw = raw.get("skills") or []
        # Guard: model sometimes returns list of dicts instead of strings
        skills = [
            str(s.get("name", s) if isinstance(s, dict) else s).strip()
            for s in skills_raw
            if s
        ]
        candidate_name = str(raw.get("candidate_name") or "Unknown").strip()
        exp_level = _coerce_level(raw.get("inferred_experience_level") or "intern")
        try:
            years = float(raw.get("years_experience") or 0.0)
        except (ValueError, TypeError):
            years = 0.0
    else:
        # LLM failed completely — use keyword scan
        logger.warning("LLM response was not a dict (%s). Using keyword fallback.", type(raw))
        skills = _keyword_fallback(resume_text)
        candidate_name = "Unknown"
        exp_level = "intern"
        years = 0.0

    if not skills:
        # Last resort: keyword scan even if we got a dict back
        logger.warning("LLM returned no skills. Supplementing with keyword fallback.")
        skills = _keyword_fallback(resume_text)

    profile = ResumeProfile(
        candidate_name=candidate_name,
        skills=skills,
        inferred_experience_level=exp_level,
        years_experience=years,
        raw_text_preview=resume_text[:500],
    )

    logger.info(
        "Resume parsed: name=%s level=%s skills=%d",
        profile.candidate_name,
        profile.inferred_experience_level,
        len(profile.skills),
    )
    return profile
