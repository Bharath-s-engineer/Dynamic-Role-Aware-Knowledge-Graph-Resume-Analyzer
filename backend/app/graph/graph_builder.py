"""
app/graph/graph_builder.py
Build a directed NetworkX graph — JD skills are primary, 5 AI skills are secondary.

Node weight / priority:
  required  → weight 3  (JD required: highest priority, always visible and prominent)
  preferred → weight 2  (JD preferred: important, shown clearly)
  inferred  → weight 1  (AI-added: supporting context, visually subdued)
"""

import logging
import networkx as nx
from app.models.jd_models import JDProfile, SkillNode

logger = logging.getLogger(__name__)

# Visual weight assigned to each importance level
IMPORTANCE_WEIGHT = {
    "required":  3,
    "preferred": 2,
    "inferred":  1,
}


def build_jd_graph(
    jd_profile: JDProfile,
    additional_nodes: list[SkillNode],
    edges: list[dict],
) -> nx.DiGraph:
    """
    Build a directed dependency graph for a specific JD.

    JD required skills are the primary nodes (weight=3).
    JD preferred skills are secondary (weight=2).
    AI-expanded nodes are supporting context (weight=1).

    All nodes carry: category, importance, is_jd_skill, weight, aliases.
    """
    G = nx.DiGraph()

    # ── JD required skills — primary nodes ──────────────────────────────────
    for skill in jd_profile.required_skills:
        G.add_node(
            skill.name,
            category=skill.category,
            importance="required",
            is_jd_skill=True,
            weight=IMPORTANCE_WEIGHT["required"],
            aliases=skill.aliases,
        )

    # ── JD preferred skills — secondary nodes ────────────────────────────────
    for skill in jd_profile.preferred_skills:
        G.add_node(
            skill.name,
            category=skill.category,
            importance="preferred",
            is_jd_skill=True,
            weight=IMPORTANCE_WEIGHT["preferred"],
            aliases=skill.aliases,
        )

    # ── AI-expanded nodes — exactly 5, supporting context ────────────────────
    for skill in additional_nodes:
        if skill.name not in G.nodes:
            G.add_node(
                skill.name,
                category=skill.category,
                importance="inferred",
                is_jd_skill=False,
                weight=IMPORTANCE_WEIGHT["inferred"],
                aliases=skill.aliases,
            )

    # ── Edges — case-insensitive matching ────────────────────────────────────
    node_lookup: dict[str, str] = {n.lower(): n for n in G.nodes()}

    for edge in edges:
        src = node_lookup.get(edge["source"].lower())
        tgt = node_lookup.get(edge["target"].lower())
        if src and tgt and src != tgt:
            G.add_edge(src, tgt, edge_type=edge.get("edge_type", "related"))

    logger.info(
        "Graph built: %d nodes (%d JD-required, %d JD-preferred, %d AI-inferred), %d edges",
        G.number_of_nodes(),
        len(jd_profile.required_skills),
        len(jd_profile.preferred_skills),
        len(additional_nodes),
        G.number_of_edges(),
    )
    return G
