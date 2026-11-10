import React from 'react';

export default function StatsCard({ title, value, subtext, icon, trend, color = "#6d28d9" }) {
  return (
    <div style={{
      background: "#ffffff",
      border: "1px solid #e5e8f2",
      borderRadius: "16px",
      padding: "20px",
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 2px 12px rgba(15, 23, 42, 0.04)"
    }}>
      <div style={{
        position: "absolute",
        top: "-24px",
        right: "-24px",
        width: "96px",
        height: "96px",
        background: `radial-gradient(circle, ${color}14 0%, transparent 70%)`,
        borderRadius: "50%",
        pointerEvents: "none"
      }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {title}
        </div>
        <div style={{
          width: "34px",
          height: "34px",
          borderRadius: "8px",
          background: `${color}14`,
          border: `1px solid ${color}30`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "16px"
        }}>
          {icon}
        </div>
      </div>

      <div style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a", marginBottom: "4px" }}>
        {value}
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11.5px" }}>
        <span style={{ color: "#64748b" }}>{subtext}</span>
        {trend && (
          <span style={{ fontWeight: 700, color: trend.startsWith('-') ? "#dc2626" : "#059669" }}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
