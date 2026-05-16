/**
 * GraphCanvas.jsx
 * React Flow canvas — renders the dynamic skill dependency graph.
 *
 * Fix applied:
 *   - BUG: React Flow v11 logs a "NodeTypes object changed" performance warning
 *     when nodeTypes is defined inline or not passed at all, because React Flow
 *     internally re-registers node renderers on every render. Defining nodeTypes
 *     as a stable constant outside the component avoids this.
 *   - The default node type fully supports JSX labels so no custom renderer is
 *     needed — we just declare it explicitly to silence the warning.
 */

import React, { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { transformGraphData } from "../utils/graphTransform";
import { Legend } from "./Legend";

const S = {
  wrap: {
    marginTop: "8px",
  },
  canvas: {
    width: "100%",
    height: "600px",
    borderRadius: "12px",
    border: "1px solid #1e293b",
    overflow: "hidden",
    background: "#0f1117",
  },
};

// FIX: Define nodeTypes as a module-level constant (not inside the component).
// React Flow compares nodeTypes by reference each render; if it's a new object
// every render it logs a performance warning and re-registers all node types.
// Using a stable reference outside the component eliminates this entirely.
const NODE_TYPES = {};

export function GraphCanvas({ graphData }) {
  const { nodes, edges } = useMemo(
    () => transformGraphData(graphData),
    [graphData]
  );

  return (
    <div style={S.wrap}>
      <Legend />
      <div style={S.canvas}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.3}
          maxZoom={2}
          attributionPosition="bottom-left"
        >
          <Background
            variant={BackgroundVariant.Dots}
            color="#1e293b"
            gap={20}
            size={1}
          />
          <Controls style={{ background: "#1a1d27", border: "1px solid #334155" }} />
          <MiniMap
            style={{ background: "#1a1d27", border: "1px solid #334155" }}
            nodeColor={(n) => {
              const status = graphData.nodes.find((x) => x.id === n.id)?.status;
              return status === "matched"
                ? "#22c55e"
                : status === "inferred"
                ? "#f59e0b"
                : status === "missing"
                ? "#ef4444"
                : "#334155";
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
