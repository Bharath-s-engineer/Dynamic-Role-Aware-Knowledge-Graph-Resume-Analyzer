/**
 * graphTransform.js
 * Backend GraphData → React Flow nodes + edges.
 *
 * Visual hierarchy driven by node.weight:
 *   weight 3 → JD required  → large (180px), full glow, bright colour
 *   weight 2 → JD preferred → medium (160px), moderate glow
 *   weight 1 → AI-inferred  → small (140px), no glow, dim colour
 *
 * Status → colour:
 *   matched  → #00ffa3  (green)
 *   inferred → #fbbf24  (amber)
 *   missing  → #ff4d6d  (red)
 *   extra    → #3d5073  (slate — AI context nodes)
 */

const STATUS_COLORS = {
  matched:  { bg: "#052e16", border: "#00ffa3", text: "#bbf7d0", glow: "#00ffa3" },
  inferred: { bg: "#2d1a00", border: "#fbbf24", text: "#fde68a", glow: "#fbbf24" },
  missing:  { bg: "#2d0a10", border: "#ff4d6d", text: "#fecaca", glow: "#ff4d6d" },
  extra:    { bg: "#0f172a", border: "#3d5073", text: "#4d6080", glow: null      },
};

// Node dimensions by weight (importance level)
const NODE_SIZE = {
  3: { width: 180, fontSize: "13px", fontWeight: 700, padding: "10px 14px" }, // required
  2: { width: 160, fontSize: "12px", fontWeight: 600, padding: "8px 12px"  }, // preferred
  1: { width: 140, fontSize: "11px", fontWeight: 400, padding: "6px 10px"  }, // inferred
};

/**
 * Layered layout:
 *   Row 0: JD required skills  (weight=3, top row, spread wide)
 *   Row 1: JD preferred skills (weight=2, middle)
 *   Row 2: AI-inferred extras  (weight=1, bottom)
 */
function layoutNodes(backendNodes) {
  const byWeight = { 3: [], 2: [], 1: [] };
  for (const n of backendNodes) {
    const w = n.weight ?? (n.importance === "required" ? 3 : n.importance === "preferred" ? 2 : 1);
    (byWeight[w] || byWeight[1]).push(n);
  }

  const positions = {};
  const X_GAP = [210, 190, 170]; // wider gap for heavier nodes
  const Y_ROWS = [0, 150, 280];
  const rows = [byWeight[3], byWeight[2], byWeight[1]];

  rows.forEach((group, rowIdx) => {
    const xGap = X_GAP[rowIdx];
    const totalW = (group.length - 1) * xGap;
    const startX = Math.max(20, 600 - totalW / 2); // centre each row
    group.forEach((node, i) => {
      positions[node.id] = {
        x: startX + i * xGap,
        y: Y_ROWS[rowIdx],
      };
    });
  });

  return positions;
}

export function transformGraphData(graphData) {
  if (!graphData?.nodes?.length) return { nodes: [], edges: [] };

  const positions = layoutNodes(graphData.nodes);

  const nodes = graphData.nodes.map((n) => {
    const colors = STATUS_COLORS[n.status] || STATUS_COLORS.extra;
    const pos = positions[n.id] || { x: 0, y: 0 };
    const w = n.weight ?? 1;
    const size = NODE_SIZE[w] || NODE_SIZE[1];
    const isJd = n.is_jd_skill;

    return {
      id: n.id,
      type: "default",
      position: pos,
      data: {
        label: (
          <div style={{ textAlign: "center", lineHeight: 1.4 }}>
            {/* JD badge for required/preferred */}
            {isJd && w === 3 && (
              <div style={{
                fontSize: "8px", letterSpacing: "0.1em",
                color: colors.border, marginBottom: "3px",
                fontFamily: "monospace", fontWeight: 700,
              }}>
                ◆ JD REQUIRED
              </div>
            )}
            {isJd && w === 2 && (
              <div style={{
                fontSize: "8px", letterSpacing: "0.1em",
                color: colors.border, marginBottom: "3px",
                fontFamily: "monospace",
              }}>
                ◇ JD PREFERRED
              </div>
            )}
            {!isJd && (
              <div style={{
                fontSize: "8px", letterSpacing: "0.08em",
                color: "#2a3a52", marginBottom: "3px",
                fontFamily: "monospace",
              }}>
                AI PREREQ
              </div>
            )}
            <div style={{
              fontSize: size.fontSize,
              fontWeight: size.fontWeight,
              color: colors.text,
            }}>
              {n.label}
            </div>
            {/* Coverage badge — only for JD skills */}
            {isJd && (
              <div style={{
                fontSize: "9px",
                color: n.coverage > 0 ? colors.border : "#3d5073",
                marginTop: "3px",
                fontFamily: "monospace",
              }}>
                {n.coverage >= 1.0
                  ? "✓ matched"
                  : n.coverage > 0
                  ? `~${Math.round(n.coverage * 100)}% inferred`
                  : "✕ missing"}
              </div>
            )}
          </div>
        ),
      },
      style: {
        background: colors.bg,
        border: `${isJd ? "2px" : "1px"} solid ${colors.border}`,
        borderRadius: isJd ? "12px" : "8px",
        padding: size.padding,
        width: size.width,
        opacity: isJd ? 1.0 : 0.7,   // AI nodes are visually subdued
        boxShadow: isJd && colors.glow
          ? `0 0 ${w === 3 ? "14px" : "8px"} ${colors.glow}44`
          : "none",
        // JD required nodes get a subtle top accent line
        borderTop: isJd && w === 3
          ? `3px solid ${colors.border}`
          : undefined,
      },
    };
  });

  const edges = graphData.edges.map((e, i) => {
    // Edges involving JD required nodes are more prominent
    const srcNode = graphData.nodes.find((n) => n.id === e.source);
    const tgtNode = graphData.nodes.find((n) => n.id === e.target);
    const isJdEdge = srcNode?.is_jd_skill || tgtNode?.is_jd_skill;

    const edgeColor =
      e.edge_type === "prerequisite" ? "#8b5cf6"
      : e.edge_type === "enables"    ? "#00e5ff"
      : e.edge_type === "hierarchical" ? "#f97316"
      : "#1e3a5f";

    return {
      id: e.id,
      source: e.source,
      target: e.target,
      animated: isJdEdge && (e.edge_type === "prerequisite" || e.edge_type === "enables"),
      style: {
        stroke: edgeColor,
        strokeWidth: isJdEdge ? 2 : 1,
        opacity: isJdEdge ? 0.9 : 0.4,
      },
      markerEnd: {
        type: "arrowclosed",
        color: edgeColor,
        width: isJdEdge ? 16 : 10,
        height: isJdEdge ? 16 : 10,
      },
    };
  });

  return { nodes, edges };
}
