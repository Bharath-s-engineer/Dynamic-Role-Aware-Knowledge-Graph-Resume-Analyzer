"""
app/scoring/readiness.py
Weighted readiness scoring — JD skills dominate the score.

Weights (emphasise JD over everything else):
  Required skill matched directly  → 4.0  (highest)
  Required skill inferred          → 4.0 × coverage
  Preferred skill matched          → 1.5
  Preferred skill inferred         → 1.5 × coverage
  AI-inferred additional skills    → NOT counted in score (they are context only)

Score = weighted_sum / max_possible × 100

Fix applied:
  - BUG: Missing preferred skills were silently discarded — they never appeared
    in ReadinessResult.missing_skills, so the recommendations engine could not
    suggest learning them. Now tracked in a separate `missing_preferred_skills`
    field so recommendations can surface them as secondary priorities.
"""

import logging
from app.core.config import settings
from app.models.jd_models import JDProfile
from app.models.response_models import ReadinessResult, PartialMatch

logger = logging.getLogger(__name__)

# JD required skills are 2.7x more important than preferred
REQUIRED_WEIGHT  = 4.0
PREFERRED_WEIGHT = 1.5


def calculate_readiness(
    jd_profile: JDProfile,
    coverage: dict[str, float],
) -> ReadinessResult:
    """
    Compute readiness score against JD skills only.
    AI-inferred additional nodes are excluded from scoring
    (they are context/graph structure, not hiring criteria).
    """
    match_t = settings.match_threshold
    infer_t = settings.infer_threshold

    matched: list[str] = []
    inferred: list[PartialMatch] = []
    missing: list[str] = []
    # FIX: Track missing preferred skills so recommendations can surface them.
    missing_preferred: list[str] = []

    weighted_sum = 0.0
    max_possible = 0.0

    # ── Required skills — primary scoring axis ───────────────────────────────
    for skill in jd_profile.required_skills:
        w = REQUIRED_WEIGHT
        max_possible += w
        # Defensive clamp: coverage should always be in [0,1] but guard anyway
        cov = min(coverage.get(skill.name, 0.0), 1.0)
        weighted_sum += cov * w

        if cov >= match_t:
            matched.append(skill.name)
        elif cov >= infer_t:
            inferred.append(PartialMatch(skill=skill.name, coverage=round(cov, 3)))
        else:
            missing.append(skill.name)

    # ── Preferred skills — bonus scoring ─────────────────────────────────────
    for skill in jd_profile.preferred_skills:
        w = PREFERRED_WEIGHT
        max_possible += w
        cov = min(coverage.get(skill.name, 0.0), 1.0)
        weighted_sum += cov * w

        if cov >= match_t:
            matched.append(skill.name)
        elif cov >= infer_t:
            inferred.append(PartialMatch(skill=skill.name, coverage=round(cov, 3)))
        else:
            # FIX: Capture missing preferred skills separately so recommendations
            # can mention them as secondary priorities (they are nice-to-have, not
            # hard blockers, so we don't put them in the primary `missing` list).
            missing_preferred.append(skill.name)

    score = (weighted_sum / max_possible * 100) if max_possible > 0 else 0.0

    logger.info(
        "Readiness: %.1f%% | required_weight=%.1f | preferred_weight=%.1f | "
        "matched=%d inferred=%d missing=%d missing_preferred=%d",
        score, REQUIRED_WEIGHT, PREFERRED_WEIGHT,
        len(matched), len(inferred), len(missing), len(missing_preferred),
    )

    return ReadinessResult(
        readiness_score=round(score, 1),
        matched_skills=matched,
        inferred_skills=inferred,
        missing_skills=missing,
        missing_preferred_skills=missing_preferred,
    )
