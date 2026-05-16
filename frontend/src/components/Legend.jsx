/**
 * Legend.jsx — Updated to reflect the new 3-tier visual hierarchy.
 */
import React from "react";

const NODES = [
  { color: "#00ffa3", label: "JD Required — Matched",  size: 14 },
  { color: "#fbbf24", label: "JD Required — Inferred", size: 14 },
  { color: "#ff4d6d", label: "JD Required — Missing",  size: 14 },
  { color: "#3d5073", label: "AI Prerequisite (extra)", size: 10 },
];

const EDGES = [
  { color: "#8b5cf6", label: "prerequisite", animated: true  },
  { color: "#00e5ff", label: "enables",      animated: true  },
  { color: "#f97316", label: "hierarchical", animated: false },
  { color: "#1e3a5f", label: "related",      animated: false },
];

export function Legend() {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap",
      padding: "10px 16px",
      background: "#090d18",
      border: "1px solid #1c2a45",
      borderRadius: "10px",
      marginBottom: "12px",
      fontSize: "10px",
      letterSpacing: "0.05em",
    }}>
      <span style={{ color: "#2a3a52", fontWeight: 700, textTransform: "uppercase", flexShrink: 0 }}>
        Nodes
      </span>
      {NODES.map(n => (
        <div key={n.label} style={{ display: "flex", alignItems: "center", gap: "5px", color: "#4d6080" }}>
          <div style={{
            width: `${n.size}px`, height: `${n.size}px`,
            borderRadius: "3px",
            background: n.color + "22",
            border: `1.5px solid ${n.color}`,
            boxShadow: n.size > 10 ? `0 0 5px ${n.color}66` : "none",
            flexShrink: 0,
          }} />
          {n.label}
        </div>
      ))}
      <div style={{ width: "1px", height: "18px", background: "#1c2a45", flexShrink: 0 }} />
      <span style={{ color: "#2a3a52", fontWeight: 700, textTransform: "uppercase", flexShrink: 0 }}>
        Edges
      </span>
      {EDGES.map(e => (
        <div key={e.label} style={{ display: "flex", alignItems: "center", gap: "5px", color: "#4d6080" }}>
          <svg width="22" height="6" style={{ flexShrink: 0 }}>
            <line x1="0" y1="3" x2="22" y2="3"
              stroke={e.color} strokeWidth="2"
              strokeDasharray={e.animated ? "5,3" : "none"}
            />
          </svg>
          {e.label}
        </div>
      ))}
    </div>
  );
}
