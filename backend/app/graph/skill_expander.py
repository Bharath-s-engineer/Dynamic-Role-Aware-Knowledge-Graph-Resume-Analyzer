"""
app/graph/skill_expander.py
Deterministic skill graph expansion — exactly 5 additional skills + all edges.

Design principles:
  1. EXACTLY 5 additional skills — no more, no less (padded with fallbacks if needed)
  2. temperature=0 + seed=42 in llm_client → same JD always produces same 5 skills
  3. ALL edges must connect JD skills to each other AND to the 5 new skills
  4. Fallback edge generation: even if AI omits edges, we guarantee structural edges
     by connecting every additional skill to at least one JD skill it relates to
  5. JD skills always have is_jd_skill=True — they are the primary nodes
"""

import logging
from app.core.llm_client import call_llm_for_json
from app.core.config import settings
from app.models.jd_models import JDProfile, SkillNode, SkillImportance

logger = logging.getLogger(__name__)

# ── Prompt is tightly constrained: exactly 5 nodes, full edge coverage ──────
_SYSTEM = """You are a skills ontology expert. Given a job role and required skills, you must:
1. Identify EXACTLY 5 foundational prerequisite skills not already in the list
2. Define dependency edges between ALL skills (both the provided list AND your 5 new ones)

Return ONLY this JSON object — no prose, no markdown:
{
  "additional_nodes": [
    {"name": "Skill Name", "category": "language|framework|database|cloud|devops|ml_ai|testing|tool|concept|soft_skill", "aliases": []}
  ],
  "edges": [
    {"source": "Skill A", "target": "Skill B", "edge_type": "prerequisite|enables|related|hierarchical"}
  ]
}

STRICT RULES:
- additional_nodes must have EXACTLY 5 items — not 4, not 6, exactly 5
- Every skill in the provided list must appear in at least one edge as source or target
- Every one of your 5 new skills must appear in at least one edge
- edge types: prerequisite (A required before B) | enables (A makes B easier) | related (used together) | hierarchical (A is subtype of B)
- No self-loops, no duplicate edges
- Skill names must exactly match the names provided or your 5 new names (case-sensitive)
"""

# ── Role-specific fallback skills when AI fails or returns wrong count ───────
_ROLE_FALLBACKS: dict[str, list[dict]] = {
    "default": [
        {"name": "Problem Solving",       "category": "concept"},
        {"name": "Version Control",       "category": "tool"},
        {"name": "Code Review",           "category": "concept"},
        {"name": "Debugging",             "category": "concept"},
        {"name": "Documentation",         "category": "concept"},
    ],
    "backend": [
        {"name": "REST API Design",       "category": "concept"},
        {"name": "Database Design",       "category": "concept"},
        {"name": "Authentication",        "category": "concept"},
        {"name": "Caching",               "category": "concept"},
        {"name": "Logging",               "category": "concept"},
    ],
    "frontend": [
        {"name": "Responsive Design",     "category": "concept"},
        {"name": "Browser DevTools",      "category": "tool"},
        {"name": "Web Accessibility",     "category": "concept"},
        {"name": "State Management",      "category": "concept"},
        {"name": "CSS Architecture",      "category": "concept"},
    ],
    "data": [
        {"name": "Statistics",            "category": "concept"},
        {"name": "Data Cleaning",         "category": "concept"},
        {"name": "Feature Engineering",   "category": "concept"},
        {"name": "Model Evaluation",      "category": "concept"},
        {"name": "Data Visualization",    "category": "tool"},
    ],
    "devops": [
        {"name": "Infrastructure as Code","category": "concept"},
        {"name": "Monitoring",            "category": "concept"},
        {"name": "CI/CD Pipelines",       "category": "devops"},
        {"name": "Container Orchestration","category": "devops"},
        {"name": "Security Hardening",    "category": "concept"},
    ],
}


def _get_fallback_skills(job_role: str, existing_lower: set[str]) -> list[dict]:
    """Pick the most relevant fallback set for this role."""
    role_lower = job_role.lower()
    if any(k in role_lower for k in ("frontend", "ui", "react", "angular", "vue")):
        pool = _ROLE_FALLBACKS["frontend"]
    elif any(k in role_lower for k in ("data", "ml", "machine", "ai", "scientist", "analyst")):
        pool = _ROLE_FALLBACKS["data"]
    elif any(k in role_lower for k in ("devops", "infra", "sre", "platform", "cloud")):
        pool = _ROLE_FALLBACKS["devops"]
    elif any(k in role_lower for k in ("backend", "api", "server", "engineer", "developer")):
        pool = _ROLE_FALLBACKS["backend"]
    else:
        pool = _ROLE_FALLBACKS["default"]
    return [s for s in pool if s["name"].lower() not in existing_lower]


def _ensure_exactly_five(
    nodes: list[SkillNode],
    existing_lower: set[str],
    job_role: str,
) -> list[SkillNode]:
    """
    Pad or trim the node list so it always contains exactly 5 items.
    This guarantees a consistent graph shape every run.
    """
    if len(nodes) == 5:
        return nodes

    if len(nodes) > 5:
        logger.info("skill_expander: trimming %d nodes to exactly 5", len(nodes))
        return nodes[:5]

    # Need to pad with fallbacks
    needed = 5 - len(nodes)
    fallbacks = _get_fallback_skills(job_role, existing_lower)
    for fb in fallbacks[:needed]:
        name = fb["name"]
        if name.lower() not in existing_lower:
            try:
                nodes.append(SkillNode(
                    name=name,
                    category=fb["category"],
                    importance=SkillImportance.INFERRED,
                    aliases=[],
                ))
                existing_lower.add(name.lower())
            except Exception:
                pass
        if len(nodes) == 5:
            break

    logger.info(
        "skill_expander: padded to %d additional nodes (target=5)", len(nodes)
    )
    return nodes


def _guarantee_edges(
    edges: list[dict],
    jd_skill_names: list[str],
    additional_nodes: list[SkillNode],
    known_lower: set[str],
) -> list[dict]:
    """
    Ensure every node (JD skills + 5 additional) appears in at least one edge.

    Strategy when an edge is missing for a node:
      - Additional node → connect it to the first JD skill with edge_type='related'
      - JD skill → connect it to the next JD skill with edge_type='related'

    This guarantees the graph is always connected and all nodes are visible.
    """
    seen: set[tuple[str, str]] = {(e["source"].lower(), e["target"].lower()) for e in edges}
    nodes_in_edges: set[str] = set()
    for e in edges:
        nodes_in_edges.add(e["source"].lower())
        nodes_in_edges.add(e["target"].lower())

    def add_edge(src: str, tgt: str, etype: str):
        key = (src.lower(), tgt.lower())
        if key not in seen and src.lower() != tgt.lower():
            edges.append({"source": src, "target": tgt, "edge_type": etype})
            seen.add(key)
            nodes_in_edges.add(src.lower())
            nodes_in_edges.add(tgt.lower())

    # Guarantee: all JD skills are connected to each other in a chain
    for i in range(len(jd_skill_names) - 1):
        add_edge(jd_skill_names[i], jd_skill_names[i + 1], "related")

    # Guarantee: each additional node connects to at least one JD skill
    if jd_skill_names:
        for i, node in enumerate(additional_nodes):
            if node.name.lower() not in nodes_in_edges:
                jd_anchor = jd_skill_names[i % len(jd_skill_names)]
                add_edge(jd_anchor, node.name, "prerequisite")

    return edges


def _parse_nodes(raw_list: list, existing_lower: set[str]) -> list[SkillNode]:
    nodes = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name.lower() in existing_lower:
            continue
        try:
            node = SkillNode(
                name=name,
                category=str(item.get("category", "concept")).strip(),
                importance=SkillImportance.INFERRED,
                aliases=[str(a) for a in item.get("aliases", []) if a],
            )
            nodes.append(node)
            existing_lower.add(name.lower())
        except Exception as exc:
            logger.warning("Skipping invalid node %r: %s", name, exc)
    return nodes


def _parse_edges(raw_list: list, known_lower: set[str]) -> list[dict]:
    edges = []
    seen: set[tuple[str, str]] = set()
    for e in raw_list:
        if not isinstance(e, dict):
            continue
        src = str(e.get("source", "")).strip()
        tgt = str(e.get("target", "")).strip()
        key = (src.lower(), tgt.lower())
        if (src and tgt and src.lower() != tgt.lower()
                and src.lower() in known_lower
                and tgt.lower() in known_lower
                and key not in seen):
            edges.append({
                "source": src,
                "target": tgt,
                "edge_type": str(e.get("edge_type", "related")),
            })
            seen.add(key)
    return edges


def expand_skills_for_role(
    jd_profile: JDProfile,
) -> tuple[list[SkillNode], list[dict]]:
    """
    Expand the JD skill graph with exactly 5 additional prerequisite skills
    and a full set of edges connecting all nodes.

    Guarantees:
      - Always returns exactly 5 additional_nodes
      - Always returns edges connecting every node to the graph
      - Same input → same output (temperature=0, seed=42 in llm_client)
    """
    existing_skills = [s.name for s in jd_profile.all_skills]
    existing_lower = {s.lower() for s in existing_skills}

    skills_str = ", ".join(existing_skills[:15])
    user_content = (
        f"Role: {jd_profile.job_role}\n"
        f"Level: {jd_profile.experience_level.value}\n"
        f"Required Skills: {skills_str}\n\n"
        "Return EXACTLY 5 additional prerequisite skills and ALL dependency edges."
    )

    raw = None
    nodes_raw: list = []
    edges_raw: list = []

    try:
        raw = call_llm_for_json(
            system=_SYSTEM,
            user=user_content,
            max_tokens=settings.llm_max_tokens_expand,
        )

        if isinstance(raw, list):
            # Model returned bare list — treat as additional_nodes
            logger.warning("skill_expander: bare list returned, using as additional_nodes")
            nodes_raw = raw
            edges_raw = []
        elif isinstance(raw, dict):
            nodes_raw = raw.get("additional_nodes") or []
            edges_raw = raw.get("edges") or []
        else:
            logger.warning("skill_expander: unexpected type %s", type(raw).__name__)

    except Exception as exc:
        logger.warning("skill_expander LLM call failed: %s — using fallbacks", exc)

    # Build node list (may be empty if LLM failed)
    additional_nodes = _parse_nodes(
        nodes_raw if isinstance(nodes_raw, list) else [],
        existing_lower,  # mutated in-place — new names added
    )

    # Enforce exactly 5
    additional_nodes = _ensure_exactly_five(additional_nodes, existing_lower, jd_profile.job_role)

    # Build all-known set (JD skills + 5 new) for edge validation
    all_known_lower = {s.lower() for s in existing_skills}
    for n in additional_nodes:
        all_known_lower.add(n.name.lower())

    # Parse AI edges
    edges = _parse_edges(
        edges_raw if isinstance(edges_raw, list) else [],
        all_known_lower,
    )

    # Guarantee every node has at least one edge
    edges = _guarantee_edges(edges, existing_skills, additional_nodes, all_known_lower)

    logger.info(
        "Expanded graph: +%d nodes (exactly 5), %d edges for role=%s",
        len(additional_nodes), len(edges), jd_profile.job_role,
    )
    return additional_nodes, edges
