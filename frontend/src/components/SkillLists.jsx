/**
 * SkillLists.jsx — Three animated columns with glow tags.
 */
import React, { useState } from "react";

const COLS = [
  { key: "matched",  title: "Matched",  icon: "✦", color: "#00ffa3", desc: "Directly on your resume" },
  { key: "inferred", title: "Inferred", icon: "◈", color: "#fbbf24", desc: "Implied by related skills" },
  { key: "missing",  title: "Missing",  icon: "✕", color: "#ff4d6d",  desc: "Required, not found" },
];

function SkillTag({ name, coverage, color, index }) {
  const [hovered, setHovered] = useState(false);
  const pct = coverage !== undefined ? Math.round(coverage * 100) : null;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 12px",
        borderRadius: "8px",
        background: hovered ? `${color}12` : `${color}06`,
        border: `1px solid ${hovered ? color + "40" : color + "18"}`,
        cursor: "default",
        transition: "all 0.2s ease",
        animation: `slideIn 0.3s ease ${index * 0.04}s both`,
        boxShadow: hovered ? `0 0 12px ${color}20` : "none",
      }}
    >
      <span style={{ fontSize: "12px", color: "#c8d8ef", fontWeight: 500 }}>{name}</span>
      {pct !== null && (
        <span style={{
          fontSize: "10px", fontWeight: 700,
          color, background: `${color}15`,
          padding: "1px 7px", borderRadius: "999px",
        }}>
          {pct}%
        </span>
      )}
    </div>
  );
}

export function SkillLists({ readiness }) {
  const data = {
    matched: readiness.matched_skills.map(s => ({ name: s })),
    inferred: readiness.inferred_skills.map(s => ({ name: s.skill, coverage: s.coverage })),
    missing: readiness.missing_skills.map(s => ({ name: s })),
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", marginBottom: "28px" }}>
      {COLS.map(({ key, title, icon, color, desc }) => (
        <div key={key} style={{
          background: "linear-gradient(160deg, #0d1321, #090d18)",
          border: `1px solid ${color}22`,
          borderRadius: "16px",
          padding: "20px",
          boxShadow: `inset 0 1px 0 ${color}18`,
        }}>
          {/* Header */}
          <div style={{ marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span style={{
                fontSize: "16px", color,
                textShadow: `0 0 10px ${color}`,
              }}>{icon}</span>
              <span style={{
                fontFamily: "'Syne', sans-serif",
                fontSize: "14px", fontWeight: 700, color,
              }}>{title}</span>
              <span style={{
                marginLeft: "auto",
                background: `${color}18`, color,
                border: `1px solid ${color}30`,
                borderRadius: "999px", padding: "1px 8px",
                fontSize: "11px", fontWeight: 700,
              }}>{data[key].length}</span>
            </div>
            <div style={{ fontSize: "10px", color: "#3d5073", letterSpacing: "0.04em" }}>{desc}</div>
          </div>

          {/* Skills */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {data[key].length === 0 ? (
              <div style={{
                fontSize: "11px", color: "#2a3a52",
                padding: "12px", textAlign: "center",
                border: "1px dashed #1c2a45", borderRadius: "8px",
              }}>
                None
              </div>
            ) : (
              data[key].map((item, i) => (
                <SkillTag key={i} name={item.name} coverage={item.coverage} color={color} index={i} />
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
