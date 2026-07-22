import React from 'react';

export default function RevenueChart({ title, data = {} }) {
  const labels = data.labels || ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
  const revenue = data.revenue || [18000, 24000, 31000, 29000, 38000, 41000, 42850];
  const maxRev = Math.max(...revenue, 50000);

  const points = revenue.map((val, idx) => {
    const x = (idx / (labels.length - 1)) * 320 + 20;
    const y = 140 - (val / maxRev) * 110;
    return `${x},${y}`;
  }).join(" ");

  const areaPoints = `20,140 ${points} 340,140`;

  return (
    <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#fff", margin: 0 }}>💰 {title || "Monthly Platform Revenue ($)"}</h3>
        <span style={{ fontSize: "12px", color: "#00c4a7", fontWeight: 800 }}>+42% YoY Growth</span>
      </div>

      <svg viewBox="0 0 360 160" style={{ width: "100%", height: "auto" }}>
        <defs>
          <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ec4899" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ec4899" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Grid Lines */}
        <line x1="20" y1="30" x2="340" y2="30" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
        <line x1="20" y1="85" x2="340" y2="85" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
        <line x1="20" y1="140" x2="340" y2="140" stroke="rgba(255,255,255,0.1)" />

        {/* Area */}
        <polygon fill="url(#revGrad)" points={areaPoints} />

        {/* Line */}
        <polyline fill="none" stroke="#ec4899" strokeWidth="3" points={points} strokeLinecap="round" />

        {/* X Labels */}
        {labels.map((lbl, idx) => {
          const x = (idx / (labels.length - 1)) * 320 + 20;
          return (
            <text key={idx} x={x} y="155" fill="var(--text2)" fontSize="10" textAnchor="middle">
              {lbl}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
