import React from 'react';

export default function UsageCard({ usage }) {
  const isUnlimited = (val) => val === "Unlimited";

  const calcPercent = (used, limit) => {
    if (isUnlimited(limit)) return 100;
    const num = Number(limit) || 1;
    return Math.min(100, Math.round((used / num) * 100));
  };

  const usageItems = [
    {
      label: "AI Interviews Used",
      used: usage?.ai_interviews_used ?? 6,
      limit: usage?.ai_interviews_limit ?? "Unlimited",
      unit: "interviews",
      icon: "🎤",
      color: "#00c4a7"
    },
    {
      label: "Coding Tests",
      used: usage?.coding_tests_used ?? 15,
      limit: usage?.coding_tests_limit ?? "Unlimited",
      unit: "tests",
      icon: "💻",
      color: "#7c4fe0"
    },
    {
      label: "Resume Analysis",
      used: usage?.resume_analysis_used ?? 3,
      limit: usage?.resume_analysis_limit ?? 5,
      unit: "scans",
      icon: "📄",
      color: "#ffb800"
    },
    {
      label: "Reports Generated",
      used: usage?.reports_generated ?? 25,
      limit: "Unlimited",
      unit: "reports",
      icon: "📊",
      color: "#3b82f6"
    },
    {
      label: "Storage Used",
      used: `${usage?.storage_used_mb ?? 220} MB`,
      limit: `${(usage?.storage_limit_mb ?? 1024) / 1024} GB`,
      unit: "storage",
      pct: Math.round(((usage?.storage_used_mb ?? 220) / (usage?.storage_limit_mb ?? 1024)) * 100),
      icon: "💾",
      color: "#ec4899"
    }
  ];

  return (
    <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
      <div style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
        <span>📊</span> Usage Statistics & Consumption
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        {usageItems.map((item, idx) => {
          const pct = item.pct !== undefined ? item.pct : calcPercent(item.used, item.limit);
          return (
            <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px", padding: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text1)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{item.icon}</span> {item.label}
                </span>
                <span style={{ fontSize: "11px", fontWeight: 800, color: item.color }}>
                  {pct}%
                </span>
              </div>

              <div style={{ fontSize: "16px", fontWeight: 900, color: "#fff", marginBottom: "8px" }}>
                {item.used} <span style={{ fontSize: "12px", color: "var(--text2)", fontWeight: 600 }}>/ {item.limit}</span>
              </div>

              <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                <div 
                  style={{ 
                    height: "100%", 
                    width: `${pct}%`, 
                    background: item.color, 
                    borderRadius: "3px", 
                    transition: "width 0.4s ease" 
                  }} 
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
