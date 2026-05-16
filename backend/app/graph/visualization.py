"""
app/graph/visualization.py
Convert NetworkX graph + coverage → React Flow-compatible GraphData.

Visual hierarchy (JD skills dominate):
  JD required + matched  → bright green  (large node)
  JD required + inferred → amber         (large node)
  JD required + missing  → bright red    (large node)
  JD preferred + matched → teal          (medium node)
  JD preferred + missing → orange        (medium node)
  AI-inferred (extra)    → dim slate     (small node, clearly secondary)

Node size is encoded in the `weight` field (3/2/1) so the frontend
can scale node dimensions accordingly.
"""

import networkx as nx
from app.models.graph_models import GraphData, GraphNode, GraphEdge, NodeStatus
from app.core.config import settings


def build_graph_visualization(
    G: nx.DiGraph,
    coverage: dict[str, float],
    jd_required_skills: list[str],
    jd_preferred_skills: list[str],
) -> GraphData:
    """
    Build a React Flow-compatible graph payload.

    JD skills are always the primary visual focus.
    AI-added nodes appear as supporting context (smaller, dimmer).
    """
    jd_required_lower = {s.lower() for s in jd_required_skills}
    jd_preferred_lower = {s.lower() for s in jd_preferred_skills}
    jd_all_lower = jd_required_lower | jd_preferred_lower

    match_t = settings.match_threshold
    infer_t = settings.infer_threshold

    nodes: list[GraphNode] = []
    for node_name, data in G.nodes(data=True):
        cov = coverage.get(node_name, 0.0)
        node_lower = node_name.lower()
        is_jd = node_lower in jd_all_lower
        weight = data.get("weight", 1)   # 3=required, 2=preferred, 1=inferred

        # ── Determine status ────────────────────────────────────────────────
        if is_jd:
            if cov >= match_t:
                status = NodeStatus.MATCHED
            elif cov >= infer_t:
                status = NodeStatus.INFERRED
            else:
                status = NodeStatus.MISSING
        else:
            # AI-inferred extra nodes: show coverage if propagated, else EXTRA
            status = NodeStatus.INFERRED if cov >= infer_t else NodeStatus.EXTRA

        nodes.append(GraphNode(
            id=node_name,
            label=node_name,
            status=status,
            coverage=round(min(cov, 1.0), 3),
            category=data.get("category", ""),
            importance=data.get("importance", "inferred"),
            is_jd_skill=is_jd,
            weight=weight,
            # weight drives node size in the frontend (3=large, 2=medium, 1=small)
        ))

    # Sort: JD required first, then preferred, then AI-inferred
    # This helps React Flow layout algorithms prioritise JD nodes
    importance_order = {"required": 0, "preferred": 1, "inferred": 2}
    nodes.sort(key=lambda n: importance_order.get(n.importance, 2))

    edges: list[GraphEdge] = []
    for i, (src, tgt, edata) in enumerate(G.edges(data=True)):
        edges.append(GraphEdge(
            id=f"e{i}",
            source=src,
            target=tgt,
            edge_type=edata.get("edge_type", "related"),
        ))

    return GraphData(nodes=nodes, edges=edges)
