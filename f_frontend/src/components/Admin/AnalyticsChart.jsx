import React from 'react';

export default function AnalyticsChart({ type = "line", title, data = {} }) {
  let labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
  let values1 = [45, 60, 75, 82, 88, 91, 94];
  let values2 = [50, 65, 78, 85, 90, 93, 96];
  let label1 = null;
  let label2 = null;

  if (Array.isArray(data) && data.length > 0) {
    labels = data.map(d => d.month || d.label || d.name || "");
    values1 = data.map(d => Number(d.interviews ?? d.value1 ?? d.college ?? d.score ?? 0));
    values2 = data.map(d => Number(d.coding ?? d.value2 ?? d.company ?? 0));
  } else if (data && typeof data === 'object') {
    if (Array.isArray(data.labels) && data.labels.length > 0) labels = data.labels;
    if (Array.isArray(data.interviews) && data.interviews.length > 0) values1 = data.interviews.map(Number);
    if (Array.isArray(data.coding) && data.coding.length > 0) values2 = data.coding.map(Number);
    if (data.label1) label1 = data.label1;
    if (data.label2) label2 = data.label2;
  }

  const calculatedMax = Math.max(...values1, ...values2, 1);
  const maxVal = calculatedMax > 100 ? calculatedMax : 100;

  const formatShortLabel = (str) => {
    if (!str) return "";
    if (str.length <= 10) return str;
    const map = {
      "Computer Science": "Comp Sci",
      "Electronics": "Electronics",
      "Information Tech": "Info Tech",
      "Mechanical": "Mech Eng"
    };
    return map[str] || str.substring(0, 8) + "..";
  };

  if (type === "line") {
    const points1 = values1.map((val, idx) => {
      const x = (idx / Math.max(1, labels.length - 1)) * 300 + 30;
      const y = 130 - (val / maxVal) * 100;
      return `${x},${y}`;
    }).join(" ");

    const points2 = values2.map((val, idx) => {
      const x = (idx / Math.max(1, labels.length - 1)) * 300 + 30;
      const y = 130 - (val / maxVal) * 100;
      return `${x},${y}`;
    }).join(" ");

    return (
      <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a", margin: 0 }}>📈 {title || "Monthly Activity Trend"}</h3>
          <div style={{ display: "flex", gap: "12px", fontSize: "11px" }}>
            <span style={{ color: "#6d28d9", fontWeight: 700 }}>● {label1 || "AI Mock Practice"}</span>
            <span style={{ color: "#7c3aed", fontWeight: 700 }}>● {label2 || "Coding Readiness"}</span>
          </div>
        </div>

        <svg viewBox="0 0 360 160" style={{ width: "100%", height: "auto" }}>
          {/* Grid lines */}
          <line x1="20" y1="30" x2="340" y2="30" stroke="#f1f5f9" strokeDasharray="4" />
          <line x1="20" y1="80" x2="340" y2="80" stroke="#f1f5f9" strokeDasharray="4" />
          <line x1="20" y1="130" x2="340" y2="130" stroke="rgba(255,255,255,0.12)" />

          {/* Polyline 1 */}
          <polyline fill="none" stroke="#6d28d9" strokeWidth="3" points={points1} strokeLinecap="round" />
          {/* Polyline 2 */}
          <polyline fill="none" stroke="#7c3aed" strokeWidth="3" points={points2} strokeLinecap="round" />

          {/* Data Points */}
          {values1.map((val, idx) => {
            const x = (idx / Math.max(1, labels.length - 1)) * 300 + 30;
            const y = 130 - (val / maxVal) * 100;
            return <circle key={`p1-${idx}`} cx={x} cy={y} r="3.5" fill="#6d28d9" stroke="#ffffff" strokeWidth="1.5" />;
          })}

          {/* X Axis Labels */}
          {labels.map((lbl, idx) => {
            const x = (idx / Math.max(1, labels.length - 1)) * 300 + 30;
            return (
              <text key={idx} x={x} y="150" fill="var(--text2)" fontSize="10" fontWeight="600" textAnchor="middle">
                {lbl}
              </text>
            );
          })}
        </svg>
      </div>
    );
  }

  if (type === "bar") {
    const numBars = labels.length;
    const step = 300 / Math.max(1, numBars);

    return (
      <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a", margin: 0 }}>📊 {title || "Department Average Scores"}</h3>
          <div style={{ display: "flex", gap: "12px", fontSize: "11px" }}>
            <span style={{ color: "#6d28d9", fontWeight: 700 }}>● {label1 || "Interview Avg"}</span>
            <span style={{ color: "#7c3aed", fontWeight: 700 }}>● {label2 || "Coding Avg"}</span>
          </div>
        </div>

        <svg viewBox="0 0 360 160" style={{ width: "100%", height: "auto" }}>
          <line x1="20" y1="30" x2="340" y2="30" stroke="#f1f5f9" strokeDasharray="4" />
          <line x1="20" y1="80" x2="340" y2="80" stroke="#f1f5f9" strokeDasharray="4" />
          <line x1="20" y1="130" x2="340" y2="130" stroke="rgba(255,255,255,0.12)" />

          {labels.map((lbl, idx) => {
            const val1 = values1[idx] || 0;
            const val2 = values2[idx] || 0;
            const h1 = (val1 / maxVal) * 95;
            const h2 = (val2 / maxVal) * 95;

            const groupX = idx * step + 30 + (step - 32) / 2;

            return (
              <g key={idx}>
                <rect x={groupX} y={130 - h1} width="14" height={h1} rx="4" fill="#6d28d9" />
                <rect x={groupX + 16} y={130 - h2} width="14" height={h2} rx="4" fill="#7c3aed" />
                <text x={groupX + 15} y="148" fill="var(--text2)" fontSize="10" fontWeight="700" textAnchor="middle">
                  {formatShortLabel(lbl)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    );
  }

  return null;
}
