/**
 * App.jsx — Neural Terminal aesthetic orchestrator.
 *
 * Fixes applied:
 *   - BUG: `key: stage` was placed inside the `style` object of the stage text
 *     div. Keys must be props on the React element, not CSS style properties.
 *     Inside a style object, `key` is silently ignored, so React never unmounts
 *     and remounts the element when stage changes — meaning the `fadeUp`
 *     animation never re-triggers. Fixed by moving `key={stage}` to the div.
 */
import React, { useState } from "react";
import { UploadPanel } from "./components/UploadPanel";
import { ScoreCard } from "./components/ScoreCard";
import { SkillLists } from "./components/SkillLists";
import { GraphCanvas } from "./components/GraphCanvas";
import { useAnalysis } from "./hooks/useAnalysis";

// ── Shared style tokens ────────────────────────────────────────────────────
const T = {
  surface: {
    background: "linear-gradient(135deg, #0d1321, #090d18)",
    border: "1px solid #1c2a45",
    borderRadius: "16px",
    padding: "20px 24px",
  },
};

// ── Loading screen ─────────────────────────────────────────────────────────
const STAGES = [
  "Extracting text from PDFs…",
  "Parsing job description with AI…",
  "Parsing resume with AI…",
  "Expanding skill graph for this role…",
  "Building dependency graph…",
  "Propagating skills through graph…",
  "Computing weighted readiness score…",
];

function LoadingScreen() {
  const [stage, setStage] = React.useState(0);
  React.useEffect(() => {
    const t = setInterval(() => setStage(s => Math.min(s + 1, STAGES.length - 1)), 2800);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "70px 0", gap: "28px",
    }}>
      {/* Spinning hex */}
      <div style={{ position: "relative", width: "80px", height: "80px" }}>
        <svg viewBox="0 0 80 80" style={{ animation: "spin 2s linear infinite", position: "absolute", inset: 0 }}>
          <polygon points="40,4 74,22 74,58 40,76 6,58 6,22"
            fill="none" stroke="#00e5ff" strokeWidth="1.5"
            strokeDasharray="8 4"
            style={{ filter: "drop-shadow(0 0 6px #00e5ff)" }} />
        </svg>
        <svg viewBox="0 0 80 80" style={{ animation: "spin 3s linear infinite reverse", position: "absolute", inset: 0 }}>
          <polygon points="40,12 66,26 66,54 40,68 14,54 14,26"
            fill="none" stroke="#8b5cf6" strokeWidth="1" opacity="0.6" />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "22px",
        }}>🧠</div>
      </div>

      {/*
        FIX: `key` was incorrectly placed inside the style object as `key: stage`.
        CSS style objects do not have a `key` property — it was silently ignored,
        meaning React kept the same DOM node across stage changes and the fadeUp
        animation never re-played.
        The key must be a prop on the React element itself so React unmounts and
        remounts the element (resetting the animation) when the stage changes.
      */}
      <div
        key={stage}
        style={{
          fontFamily: "'Syne', sans-serif",
          fontSize: "15px", fontWeight: 700, color: "#00e5ff",
          textAlign: "center", maxWidth: "320px",
          textShadow: "0 0 16px #00e5ff88",
          minHeight: "24px",
          animation: "fadeUp 0.4s ease both",
        }}
      >
        {STAGES[stage]}
      </div>

      {/* Progress dots */}
      <div style={{ display: "flex", gap: "8px" }}>
        {STAGES.map((_, i) => (
          <div key={i} style={{
            width: i === stage ? "24px" : "6px",
            height: "6px",
            borderRadius: "3px",
            background: i <= stage ? "#00e5ff" : "#1c2a45",
            boxShadow: i === stage ? "0 0 8px #00e5ff" : "none",
            transition: "all 0.4s ease",
          }} />
        ))}
      </div>

      <div style={{ fontSize: "11px", color: "#3d5073", letterSpacing: "0.06em" }}>
        BUILDING YOUR KNOWLEDGE GRAPH — ~15-20s
      </div>
    </div>
  );
}

// ── Tab bar ────────────────────────────────────────────────────────────────
const TABS = [
  { id: "skills", label: "Skills",          icon: "◈" },
  { id: "graph",  label: "Graph",           icon: "⬡" },
  { id: "recs",   label: "Recommendations", icon: "▸" },
];

function TabBar({ active, onChange }) {
  return (
    <div style={{
      display: "flex", gap: "4px",
      marginBottom: "24px",
      background: "#090d18",
      border: "1px solid #1c2a45",
      borderRadius: "12px",
      padding: "4px",
    }}>
      {TABS.map(t => {
        const isActive = t.id === active;
        return (
          <button key={t.id} onClick={() => onChange(t.id)} style={{
            flex: 1,
            padding: "10px 16px",
            border: "none",
            borderRadius: "9px",
            background: isActive
              ? "linear-gradient(135deg, #00e5ff15, #8b5cf615)"
              : "transparent",
            color: isActive ? "#00e5ff" : "#3d5073",
            fontFamily: "'Syne', sans-serif",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
            letterSpacing: "0.04em",
            boxShadow: isActive ? "inset 0 0 0 1px #00e5ff30" : "none",
            transition: "all 0.2s ease",
            display: "flex", alignItems: "center", justifyContent: "center", gap: "7px",
          }}>
            <span style={{ color: isActive ? "#00e5ff" : "#3d5073" }}>{t.icon}</span>
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

// ── Recommendations ────────────────────────────────────────────────────────
function RecommendationsList({ items }) {
  const [expanded, setExpanded] = useState(null);
  const icons = items.map((r) =>
    r.toLowerCase().includes("learn") ? "📚"
    : r.toLowerCase().includes("strengthen") ? "💪"
    : r.toLowerCase().includes("strong") ? "🏆"
    : r.toLowerCase().includes("consider") ? "💡"
    : "→"
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {items.map((rec, i) => (
        <div key={i}
          onClick={() => setExpanded(expanded === i ? null : i)}
          style={{
            background: expanded === i
              ? "linear-gradient(135deg, #0d1321, #0e1526)"
              : "#090d18",
            border: `1px solid ${expanded === i ? "#00e5ff30" : "#1c2a45"}`,
            borderRadius: "12px",
            padding: "14px 18px",
            cursor: "pointer",
            transition: "all 0.25s ease",
            animation: `slideIn 0.3s ease ${i * 0.06}s both`,
            boxShadow: expanded === i ? "0 0 20px #00e5ff10" : "none",
          }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
            <span style={{
              fontSize: "18px", flexShrink: 0,
              filter: expanded === i ? "none" : "grayscale(0.4)",
            }}>{icons[i]}</span>
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: "13px",
                color: expanded === i ? "#c8d8ef" : "#7a90b0",
                lineHeight: 1.6,
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {expanded === i ? rec : rec.slice(0, 80) + (rec.length > 80 ? "…" : "")}
              </div>
            </div>
            <span style={{
              color: "#2a3a52", fontSize: "12px", flexShrink: 0,
              transform: expanded === i ? "rotate(180deg)" : "none",
              transition: "transform 0.2s",
            }}>▾</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────
export default function App() {
  const { resume, setResume, jd, setJd, result, loading, error, analyze, reset } = useAnalysis();
  const [activeTab, setActiveTab] = useState("skills");
  const canAnalyze = !!resume && !!jd && !loading;

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "36px 24px" }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: "36px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "8px" }}>
          <div style={{
            width: "36px", height: "36px",
            background: "linear-gradient(135deg, #00e5ff20, #8b5cf620)",
            border: "1px solid #00e5ff40",
            borderRadius: "10px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "18px",
          }}>🧠</div>
          <div>
            <h1 style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "24px", fontWeight: 800,
              background: "linear-gradient(90deg, #00e5ff, #8b5cf6)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              letterSpacing: "-0.01em",
            }}>
              Knowledge Graph Resume Analyzer
            </h1>
          </div>
        </div>
        <div style={{
          fontSize: "11px", color: "#3d5073",
          letterSpacing: "0.12em", textTransform: "uppercase",
          paddingLeft: "50px",
        }}>
          Dynamic Role-Aware Skill Graph · JD Alignment · Readiness Scoring · Groq AI
        </div>
        <div style={{ height: "1px", background: "linear-gradient(90deg, #00e5ff20, #8b5cf620, transparent)", marginTop: "20px" }} />
      </div>

      {/* ── Upload ── */}
      <UploadPanel resume={resume} setResume={setResume} jd={jd} setJd={setJd} />

      {/* ── Analyze Button ── */}
      <button
        onClick={analyze}
        disabled={!canAnalyze}
        style={{
          width: "100%",
          padding: "15px",
          border: "none",
          borderRadius: "12px",
          background: canAnalyze
            ? "linear-gradient(135deg, #00e5ff18, #8b5cf618)"
            : "transparent",
          boxShadow: canAnalyze
            ? "inset 0 0 0 1.5px #00e5ff50, 0 0 30px #00e5ff15"
            : "inset 0 0 0 1px #1c2a45",
          color: canAnalyze ? "#00e5ff" : "#2a3a52",
          fontFamily: "'Syne', sans-serif",
          fontWeight: 800,
          fontSize: "14px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          cursor: canAnalyze ? "pointer" : "not-allowed",
          marginBottom: "28px",
          transition: "all 0.3s ease",
        }}
      >
        {loading ? "Analyzing…" : "⬡  Analyze Match"}
      </button>

      {/* ── Error ── */}
      {error && (
        <div style={{
          background: "#ff4d6d0d",
          border: "1px solid #ff4d6d40",
          borderRadius: "12px",
          padding: "14px 18px",
          marginBottom: "24px",
          fontSize: "12px",
          color: "#ff4d6d",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          ⚠ {error}
        </div>
      )}

      {/* ── Loading ── */}
      {loading && <LoadingScreen />}

      {/* ── Results ── */}
      {result && !loading && (
        <div style={{ animation: "fadeUp 0.5s ease both" }}>
          <ScoreCard result={result} />
          <TabBar active={activeTab} onChange={setActiveTab} />

          {activeTab === "skills" && <SkillLists readiness={result.readiness} />}

          {activeTab === "graph" && (
            <div>
              <div style={{
                fontFamily: "'Syne', sans-serif",
                fontSize: "13px", fontWeight: 700,
                color: "#3d5073", letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: "12px",
                display: "flex", alignItems: "center", gap: "8px",
              }}>
                <span style={{ color: "#00e5ff" }}>⬡</span> Dependency Knowledge Graph
              </div>
              <GraphCanvas graphData={result.graph_data} />
            </div>
          )}

          {activeTab === "recs" && (
            <div>
              <div style={{
                fontFamily: "'Syne', sans-serif",
                fontSize: "13px", fontWeight: 700,
                color: "#3d5073", letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: "16px",
                display: "flex", alignItems: "center", gap: "8px",
              }}>
                <span style={{ color: "#8b5cf6" }}>▸</span> Action Plan
              </div>
              <RecommendationsList items={result.recommendations} />
            </div>
          )}

          {/* Reset */}
          <button onClick={reset} style={{
            marginTop: "32px",
            padding: "10px 24px",
            border: "1px solid #1c2a45",
            borderRadius: "10px",
            background: "transparent",
            color: "#3d5073",
            fontFamily: "'Syne', sans-serif",
            fontWeight: 700,
            fontSize: "12px",
            letterSpacing: "0.08em",
            cursor: "pointer",
            transition: "all 0.2s",
          }}>
            ↩ NEW ANALYSIS
          </button>
        </div>
      )}
    </div>
  );
}
