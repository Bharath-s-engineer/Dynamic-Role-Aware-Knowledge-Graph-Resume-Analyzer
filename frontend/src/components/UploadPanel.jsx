/**
 * UploadPanel.jsx — Cinematic dual-upload panel with drag hover states.
 */
import React, { useRef, useState } from "react";

function DropZone({ label, icon, sublabel, file, onFile, accentColor }) {
  const ref = useRef();
  const [dragging, setDragging] = useState(false);

  const isActive = !!file || dragging;
  const color = accentColor || "#00e5ff";

  return (
    <div
      onClick={() => ref.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault(); setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f?.type === "application/pdf") onFile(f);
      }}
      style={{
        position: "relative",
        border: `1.5px dashed ${isActive ? color : "#1c2a45"}`,
        borderRadius: "16px",
        padding: "36px 24px",
        textAlign: "center",
        cursor: "pointer",
        background: isActive
          ? `linear-gradient(135deg, ${color}08, ${color}03)`
          : "linear-gradient(135deg, #0d1321, #0a101c)",
        transition: "all 0.3s ease",
        boxShadow: isActive ? `0 0 28px ${color}22, inset 0 0 20px ${color}08` : "none",
        overflow: "hidden",
      }}
    >
      {/* corner accents */}
      {["top:0;left:0", "top:0;right:0", "bottom:0;left:0", "bottom:0;right:0"].map((pos, i) => (
        <div key={i} style={{
          position: "absolute",
          ...Object.fromEntries(pos.split(";").map(p => p.split(":"))),
          width: "12px", height: "12px",
          borderTop: i < 2 ? `2px solid ${color}66` : "none",
          borderBottom: i >= 2 ? `2px solid ${color}66` : "none",
          borderLeft: i % 2 === 0 ? `2px solid ${color}66` : "none",
          borderRight: i % 2 === 1 ? `2px solid ${color}66` : "none",
          opacity: isActive ? 1 : 0,
          transition: "opacity 0.3s",
        }} />
      ))}

      <div style={{ fontSize: "36px", marginBottom: "12px", lineHeight: 1 }}>{icon}</div>

      <div style={{
        fontFamily: "'Syne', sans-serif",
        fontSize: "12px",
        fontWeight: 700,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: isActive ? color : "#4d6080",
        marginBottom: "6px",
        transition: "color 0.3s",
      }}>
        {label}
      </div>

      <div style={{ fontSize: "11px", color: "#3d5073", marginBottom: "8px" }}>
        {sublabel}
      </div>

      {file ? (
        <div style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          background: `${color}15`, border: `1px solid ${color}40`,
          borderRadius: "6px", padding: "4px 12px",
          fontSize: "11px", color: color, fontWeight: 600,
          marginTop: "6px",
        }}>
          <span>✓</span> {file.name.length > 28 ? file.name.slice(0, 25) + "..." : file.name}
        </div>
      ) : (
        <div style={{
          fontSize: "11px", color: "#2a3a52",
          border: "1px solid #1c2a45", borderRadius: "6px",
          padding: "4px 12px", display: "inline-block", marginTop: "6px",
        }}>
          drag & drop or click
        </div>
      )}

      <input ref={ref} type="file" accept=".pdf" style={{ display: "none" }}
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])} />
    </div>
  );
}

export function UploadPanel({ resume, setResume, jd, setJd }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "28px" }}>
      <DropZone label="Resume" icon="📄" sublabel="Candidate PDF" file={resume} onFile={setResume} accentColor="#00e5ff" />
      <DropZone label="Job Description" icon="💼" sublabel="Role requirements PDF" file={jd} onFile={setJd} accentColor="#8b5cf6" />
    </div>
  );
}
