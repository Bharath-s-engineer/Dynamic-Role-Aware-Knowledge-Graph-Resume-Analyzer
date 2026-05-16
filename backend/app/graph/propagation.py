"""
app/graph/propagation.py
BFS confidence propagation through the skill dependency graph.

Logic:
  - Resume skills start with coverage = 1.0
  - Each outgoing edge propagates coverage * DECAY_FACTOR
  - We keep the maximum coverage seen at each node
  - Propagation stops at MAX_DEPTH hops

Fix applied:
  - BUG: The original BFS re-queued a node whenever its coverage was improved,
    even if the same node was already in the queue with a higher score. In graphs
    with many paths this caused O(n²) redundant processing.
    Fix: only enqueue a node if the new propagated score actually improves on the
    ALREADY-QUEUED best score. Track `queued_best` separately from `coverage`
    so we don't re-queue the same node with a score that will be dominated.
"""

import logging
from collections import deque
import networkx as nx
from app.core.config import settings

logger = logging.getLogger(__name__)


def propagate_skills(
    G: nx.DiGraph,
    resume_skills: list[str],
) -> dict[str, float]:
    """
    Propagate resume skill coverage through the dependency graph.

    Args:
        G:             The JD-specific skill graph.
        resume_skills: List of canonical skill names from the resume.

    Returns:
        Dict mapping every graph node name → coverage score [0.0, 1.0].
        1.0 = directly on resume; 0 < x < 1.0 = inferred; 0.0 = not reachable.
    """
    decay = settings.propagation_decay
    max_depth = settings.propagation_max_depth

    coverage: dict[str, float] = {node: 0.0 for node in G.nodes()}

    # FIX: Track the best score we have already queued for each node.
    # This prevents re-queuing a node when an incoming path offers a score
    # that is ≤ what is already scheduled to be processed.
    queued_best: dict[str, float] = {node: 0.0 for node in G.nodes()}

    # Build case-insensitive lookup for matching resume skills to graph nodes
    node_lookup: dict[str, str] = {n.lower(): n for n in G.nodes()}

    # Also check node aliases
    alias_lookup: dict[str, str] = {}
    for node, data in G.nodes(data=True):
        for alias in data.get("aliases", []):
            alias_lookup[alias.lower()] = node

    queue: deque[tuple[str, float, int]] = deque()

    for skill in resume_skills:
        skill_lower = skill.lower()
        matched_node = node_lookup.get(skill_lower)
        if not matched_node:
            matched_node = alias_lookup.get(skill_lower)

        if matched_node:
            coverage[matched_node] = 1.0
            queued_best[matched_node] = 1.0
            queue.append((matched_node, 1.0, 0))
        else:
            logger.debug("Resume skill '%s' not in graph — skipped.", skill)

    # BFS propagation
    while queue:
        node, score, depth = queue.popleft()

        # FIX: Skip stale entries — a better score for this node was processed later.
        # Without this check the queue can accumulate many dominated entries.
        if score < coverage[node]:
            continue

        if depth >= max_depth:
            continue

        for neighbor in G.successors(node):
            propagated = score * decay
            if propagated > coverage[neighbor]:
                coverage[neighbor] = propagated
                # FIX: Only enqueue if this improves on what's already queued,
                # avoiding duplicate entries for the same node.
                if propagated > queued_best[neighbor]:
                    queued_best[neighbor] = propagated
                    queue.append((neighbor, propagated, depth + 1))

    active = {k: v for k, v in coverage.items() if v > 0}
    logger.info(
        "Propagation complete: %d/%d nodes activated",
        len(active),
        len(coverage),
    )
    return coverage
