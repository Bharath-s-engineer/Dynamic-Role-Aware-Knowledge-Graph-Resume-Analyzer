"""
tests/test_all.py
Full unit test suite — runs without any API calls.
Run: pytest tests/test_all.py -v
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# json_parser
# ─────────────────────────────────────────────────────────────────────────────

class TestJsonParser:
    def test_plain(self):
        from app.core.json_parser import parse_llm_json
        assert parse_llm_json('{"x": 1}') == {"x": 1}

    def test_fenced(self):
        from app.core.json_parser import parse_llm_json
        assert parse_llm_json('```json\n{"x": 1}\n```') == {"x": 1}

    def test_preamble(self):
        from app.core.json_parser import parse_llm_json
        assert parse_llm_json('Here you go:\n{"x": 1}') == {"x": 1}

    def test_array(self):
        from app.core.json_parser import parse_llm_json
        assert parse_llm_json('```\n[1,2,3]\n```') == [1, 2, 3]

    def test_invalid_raises(self):
        from app.core.json_parser import parse_llm_json
        with pytest.raises(ValueError):
            parse_llm_json("not json at all")


# ─────────────────────────────────────────────────────────────────────────────
# text_cleaner
# ─────────────────────────────────────────────────────────────────────────────

class TestTextCleaner:
    def test_ligatures(self):
        from app.extraction.text_cleaner import clean_extracted_text
        assert "fi" in clean_extracted_text("\ufb01le")

    def test_hyphenation(self):
        from app.extraction.text_cleaner import clean_extracted_text
        result = clean_extracted_text("develop-\nment")
        assert "development" in result

    def test_no_double_spaces(self):
        from app.extraction.text_cleaner import clean_extracted_text
        result = clean_extracted_text("hello   world")
        assert "  " not in result


# ─────────────────────────────────────────────────────────────────────────────
# models
# ─────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_skill_node_matches(self):
        from app.models.jd_models import SkillNode
        n = SkillNode(name="PostgreSQL", category="database", aliases=["postgres"])
        assert n.matches_text("use postgres in production")
        assert not n.matches_text("only mysql here")

    def test_jd_profile_properties(self):
        from app.models.jd_models import JDProfile, SkillNode, ExperienceLevel
        p = JDProfile(
            job_title="SDE",
            job_role="Backend",
            experience_level=ExperienceLevel.MID,
            required_skills=[SkillNode(name="Python", category="language")],
            preferred_skills=[SkillNode(name="Rust", category="language")],
        )
        assert len(p.all_skills) == 2
        assert "Python" in p.required_skill_names

    def test_resume_profile(self):
        from app.models.resume_models import ResumeProfile
        r = ResumeProfile(skills=["Python", "FastAPI"], years_experience=2.5)
        assert "python" in r.skill_set


# ─────────────────────────────────────────────────────────────────────────────
# graph_builder + propagation
# ─────────────────────────────────────────────────────────────────────────────

class TestGraph:
    def _make_profile(self):
        from app.models.jd_models import JDProfile, SkillNode, ExperienceLevel
        return JDProfile(
            job_title="Backend Engineer",
            job_role="Backend Engineer",
            experience_level=ExperienceLevel.MID,
            required_skills=[
                SkillNode(name="Python", category="language"),
                SkillNode(name="FastAPI", category="framework"),
                SkillNode(name="PostgreSQL", category="database"),
            ],
            preferred_skills=[],
        )

    def test_graph_nodes(self):
        from app.graph.graph_builder import build_jd_graph
        p = self._make_profile()
        G = build_jd_graph(p, [], [])
        assert "Python" in G.nodes
        assert "FastAPI" in G.nodes

    def test_graph_edges(self):
        from app.graph.graph_builder import build_jd_graph
        p = self._make_profile()
        edges = [{"source": "Python", "target": "FastAPI", "edge_type": "prerequisite"}]
        G = build_jd_graph(p, [], edges)
        assert G.has_edge("Python", "FastAPI")

    def test_propagation_direct(self):
        from app.graph.graph_builder import build_jd_graph
        from app.graph.propagation import propagate_skills
        p = self._make_profile()
        edges = [{"source": "Python", "target": "FastAPI", "edge_type": "prerequisite"}]
        G = build_jd_graph(p, [], edges)
        coverage = propagate_skills(G, ["Python"])
        assert coverage["Python"] == 1.0
        assert 0 < coverage["FastAPI"] < 1.0
        assert coverage["PostgreSQL"] == 0.0

    def test_propagation_decay(self):
        from app.graph.graph_builder import build_jd_graph
        from app.graph.propagation import propagate_skills
        p = self._make_profile()
        edges = [
            {"source": "Python", "target": "FastAPI", "edge_type": "prerequisite"},
            {"source": "FastAPI", "target": "PostgreSQL", "edge_type": "related"},
        ]
        G = build_jd_graph(p, [], edges)
        cov = propagate_skills(G, ["Python"])
        # Each hop decays by 0.6
        assert abs(cov["FastAPI"] - 0.6) < 0.01
        assert abs(cov["PostgreSQL"] - 0.36) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestScoring:
    def test_perfect_score(self):
        from app.models.jd_models import JDProfile, SkillNode, ExperienceLevel
        from app.scoring.readiness import calculate_readiness
        p = JDProfile(
            job_title="SDE", job_role="Backend",
            experience_level=ExperienceLevel.MID,
            required_skills=[SkillNode(name="Python", category="language")],
        )
        coverage = {"Python": 1.0}
        r = calculate_readiness(p, coverage)
        assert r.readiness_score == 100.0
        assert "Python" in r.matched_skills

    def test_zero_score(self):
        from app.models.jd_models import JDProfile, SkillNode, ExperienceLevel
        from app.scoring.readiness import calculate_readiness
        p = JDProfile(
            job_title="SDE", job_role="Backend",
            experience_level=ExperienceLevel.MID,
            required_skills=[SkillNode(name="Rust", category="language")],
        )
        coverage = {"Rust": 0.0}
        r = calculate_readiness(p, coverage)
        assert r.readiness_score == 0.0
        assert "Rust" in r.missing_skills

    def test_partial_score(self):
        from app.models.jd_models import JDProfile, SkillNode, ExperienceLevel
        from app.scoring.readiness import calculate_readiness
        p = JDProfile(
            job_title="SDE", job_role="Backend",
            experience_level=ExperienceLevel.MID,
            required_skills=[
                SkillNode(name="Python", category="language"),
                SkillNode(name="Rust", category="language"),
            ],
        )
        coverage = {"Python": 1.0, "Rust": 0.0}
        r = calculate_readiness(p, coverage)
        assert 0 < r.readiness_score < 100


# ─────────────────────────────────────────────────────────────────────────────
# recommendations
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendations:
    def test_missing_skills_appear(self):
        from app.recommendations.engine import generate_recommendations
        from app.models.response_models import ReadinessResult
        r = ReadinessResult(
            readiness_score=30.0,
            matched_skills=[],
            inferred_skills=[],
            missing_skills=["Kubernetes", "Terraform"],
        )
        recs = generate_recommendations(r)
        assert any("Kubernetes" in rec for rec in recs)

    def test_high_score_positive(self):
        from app.recommendations.engine import generate_recommendations
        from app.models.response_models import ReadinessResult
        r = ReadinessResult(
            readiness_score=90.0,
            matched_skills=["Python", "FastAPI", "Docker"],
            inferred_skills=[],
            missing_skills=[],
        )
        recs = generate_recommendations(r)
        assert any("portfolio" in rec.lower() or "strong" in rec.lower() for rec in recs)
