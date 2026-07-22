import React from 'react';

export default function StatsCard({ title, value, subtext, icon, trend, color = "#ec4899" }) {
  return (
    <div style={{
      background: "linear-gradient(145deg, rgba(12,18,32,0.95), rgba(24,18,40,0.95))",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: "16px",
      padding: "20px",
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 8px 24px rgba(0,0,0,0.4)"
    }}>
      <div style={{
        position: "absolute",
        top: "-20px",
        right: "-20px",
        width: "100px",
        height: "100px",
        background: `radial-gradient(circle, ${color}25 0%, transparent 70%)`,
        borderRadius: "50%",
        pointerEvents: "none"
      }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
        <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text2)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {title}
        </div>
        <div style={{
          width: "34px",
          height: "34px",
          borderRadius: "8px",
          background: `${color}18`,
          border: `1px solid ${color}35`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "16px"
        }}>
          {icon}
        </div>
      </div>

      <div style={{ fontSize: "26px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>
        {value}
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px" }}>
        <span style={{ color: "var(--text2)" }}>{subtext}</span>
        {trend && (
          <span style={{ fontWeight: 800, color: trend.startsWith('+') ? "#00f0c8" : "#ff5472" }}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
