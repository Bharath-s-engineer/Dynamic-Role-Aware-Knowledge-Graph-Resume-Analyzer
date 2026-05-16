"""
app/recommendations/engine.py
Generate actionable learning recommendations from readiness results.

Fix applied:
  - BUG: Missing preferred skills were never mentioned in recommendations because
    they weren't stored anywhere in the original ReadinessResult. Now that
    ReadinessResult.missing_preferred_skills exists, we surface them as
    secondary (lower-priority) recommendations after the required gaps.
"""

from app.models.response_models import ReadinessResult


def generate_recommendations(result: ReadinessResult) -> list[str]:
    """
    Build a prioritised list of recommendations.

    Priority order:
      1. Missing required skills (highest impact — hard blockers)
      2. Inferred skills that are close but not confirmed (strengthen them)
      3. Missing preferred skills (nice-to-have gaps)  ← FIX: was silently dropped
      4. Positive reinforcement for matched skills

    Args:
        result: ReadinessResult from readiness calculator.

    Returns:
        List of recommendation strings, most important first.
    """
    recommendations: list[str] = []

    # 1. Missing required skills — must learn
    for skill in result.missing_skills:
        recommendations.append(
            f"Learn {skill} — required by this role and not found in your profile."
        )

    # 2. Inferred / partial — strengthen
    # Sort by lowest coverage first (needs the most work)
    partial_sorted = sorted(result.inferred_skills, key=lambda x: x.coverage)
    for item in partial_sorted:
        pct = round(item.coverage * 100)
        recommendations.append(
            f"Strengthen {item.skill} — partially inferred ({pct}% confidence). "
            f"Hands-on project experience would solidify this."
        )

    # 3. FIX: Missing preferred skills — were silently ignored before.
    # Show them as secondary suggestions so candidates know what would
    # make them stand out even if not strictly required.
    for skill in result.missing_preferred_skills:
        recommendations.append(
            f"Consider adding {skill} — listed as a preferred qualification. "
            f"It would strengthen your application even if not required."
        )

    # 4. Overall feedback based on score
    if result.readiness_score >= 80 and not result.missing_skills:
        recommendations.append(
            "Strong match overall! Focus on portfolio projects demonstrating "
            f"{', '.join(result.matched_skills[:3])} to stand out."
        )
    elif result.readiness_score < 40:
        recommendations.append(
            "Consider building 1-2 focused projects that use the required stack "
            "to bridge the experience gap before applying."
        )

    return recommendations
