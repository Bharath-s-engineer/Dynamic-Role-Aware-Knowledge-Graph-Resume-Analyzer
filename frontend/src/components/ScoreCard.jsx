/**
 * ScoreCard.jsx — Animated SVG ring + glowing score + meta chips.
 */
import React, { useEffect, useState } from "react";

function scoreColor(s) {
  if (s >= 75) return "#00ffa3";
  if (s >= 50) return "#fbbf24";
  return "#ff4d6d";
}

const LEVEL_COLORS = {
  intern: "#a78bfa", junior: "#60a5fa", mid: "#34d399",
  senior: "#fbbf24", lead: "#f97316", principal: "#ff4d6d",
};

const RADIUS = 70;
const CIRC = 2 * Math.PI * RADIUS;

export function ScoreCard({ result }) {
  const score = result.readiness.readiness_score;
  const color = scoreColor(score);
  const [displayed, setDisplayed] = useState(0);

  // Animate score number counting up
  useEffect(() => {
    let start = 0;
    const step = score / 40;
    const timer = setInterval(() => {
      start += step;
      if (start >= score) { setDisplayed(score); clearInterval(timer); }
      else setDisplayed(Math.round(start));
    }, 20);
    return () => clearInterval(timer);
  }, [score]);

  const dashOffset = CIRC - (score / 100) * CIRC;
  const levelColor = LEVEL_COLORS[result.experience_level] || "#4d6080";

  const statChips = [
    { label: "Matched",  value: result.readiness.matched_skills.length,  color: "#00ffa3" },
    { label: "Inferred", value: result.readiness.inferred_skills.length,  color: "#fbbf24" },
    { label: "Missing",  value: result.readiness.missing_skills.length,   color: "#ff4d6d" },
    { label: "JD Skills",value: result.jd_required_skills.length + result.jd_preferred_skills.length, color: "#00e5ff" },
  ];

  return (
    <div style={{
      background: "linear-gradient(135deg, #0d1321 0%, #0a1020 100%)",
      border: "1px solid #1c2a45",
      borderRadius: "20px",
      padding: "28px 32px",
      marginBottom: "28px",
      display: "flex",
      alignItems: "center",
      gap: "36px",
      boxShadow: `0 0 60px ${color}12`,
      animation: "fadeUp 0.5s ease both",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Background glow */}
      <div style={{
        position: "absolute", top: "-40px", left: "-40px",
        width: "200px", height: "200px", borderRadius: "50%",
        background: `radial-gradient(circle, ${color}10, transparent 70%)`,
        pointerEvents: "none",
      }} />

      {/* SVG Ring */}
      <div style={{ flexShrink: 0, position: "relative" }}>
        <svg width="160" height="160" viewBox="0 0 160 160" style={{ transform: "rotate(-90deg)" }}>
          {/* track */}
          <circle cx="80" cy="80" r={RADIUS} fill="none" stroke="#1c2a45" strokeWidth="8" />
          {/* progress */}
          <circle cx="80" cy="80" r={RADIUS} fill="none"
            stroke={color} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={dashOffset}
            style={{
              filter: `drop-shadow(0 0 8px ${color})`,
              transition: "stroke-dashoffset 1.2s cubic-bezier(0.22,1,0.36,1)",
            }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
        }}>
          <span style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: "38px", fontWeight: 800,
            color, lineHeight: 1,
            textShadow: `0 0 20px ${color}88`,
          }}>
            {displayed}
          </span>
          <span style={{ fontSize: "10px", color: "#4d6080", letterSpacing: "0.1em", marginTop: "2px" }}>
            READINESS
          </span>
        </div>
      </div>

      {/* Meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: "'Syne', sans-serif",
          fontSize: "22px", fontWeight: 800,
          color: "#e2eaf7", marginBottom: "4px",
          lineHeight: 1.2,
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
        }}>
          {result.job_title}
        </div>
        <div style={{ fontSize: "12px", color: "#4d6080", marginBottom: "16px", letterSpacing: "0.04em" }}>
          {result.job_role}
        </div>

        {/* Level pill */}
        <span style={{
          display: "inline-flex", alignItems: "center", gap: "5px",
          padding: "3px 12px", borderRadius: "999px",
          background: `${levelColor}18`, color: levelColor,
          border: `1px solid ${levelColor}44`,
          fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em",
          textTransform: "uppercase", marginBottom: "18px",
        }}>
          ◆ {result.experience_level}
        </span>

        {/* Stats row */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          {statChips.map(({ label, value, color: c }) => (
            <div key={label} style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              background: `${c}0d`, border: `1px solid ${c}25`,
              borderRadius: "10px", padding: "8px 14px", minWidth: "64px",
            }}>
              <span style={{
                fontFamily: "'Syne', sans-serif",
                fontSize: "22px", fontWeight: 800, color: c, lineHeight: 1,
              }}>{value}</span>
              <span style={{ fontSize: "9px", color: "#4d6080", marginTop: "2px", letterSpacing: "0.06em" }}>
                {label.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
