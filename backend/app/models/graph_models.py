"""
app/models/graph_models.py
Pydantic models for graph data — React Flow compatible.

weight field encodes visual priority:
  3 → JD required skill   (large node, always prominent)
  2 → JD preferred skill  (medium node)
  1 → AI-inferred extra   (small node, supporting context)
"""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    MATCHED  = "matched"   # on resume + in JD → green
    INFERRED = "inferred"  # propagated from resume skills → amber
    MISSING  = "missing"   # in JD, not on resume → red
    EXTRA    = "extra"     # AI-added context, not in JD → slate


class GraphNode(BaseModel):
    id: str
    label: str
    status: NodeStatus
    coverage: float = Field(ge=0.0, le=1.0)
    category: str = ""
    importance: str = ""      # "required" | "preferred" | "inferred"
    is_jd_skill: bool = False
    weight: int = Field(default=1, ge=1, le=3)  # 3=required, 2=preferred, 1=extra


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str = "related"


class GraphData(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
