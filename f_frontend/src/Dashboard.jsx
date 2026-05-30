import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

const interviewRoles = [
  { name: "Software Developer",   desc: "Core CS fundamentals, algorithms, system design, and problem solving.",       badge: "teal",   label: "General",    time: "45 min" },
  { name: "Full Stack Developer", desc: "End-to-end covering REST APIs, databases, React, and Node.",                   badge: "blue",   label: "Full Stack", time: "60 min" },
  { name: "Mobile App Developer", desc: "iOS & Android concepts, lifecycle, state management, and performance.",         badge: "purple", label: "Mobile",     time: "40 min" },
  { name: "SSB Interview",        desc: "Personality, GTO tasks, situational judgement, and leadership focus.",         badge: "pink",   label: "Defence",    time: "90 min" },
  { name: "Frontend Developer",   desc: "HTML, CSS, JavaScript, accessibility, performance, and frameworks.",            badge: "teal",   label: "Frontend",   time: "45 min" },
  { name: "Backend Developer",    desc: "Server architecture, databases, caching, APIs, and scalability.",              badge: "blue",   label: "Backend",    time: "50 min" },
  { name: "DevOps Engineer",      desc: "CI/CD pipelines, containerization, cloud infrastructure, and monitoring.",     badge: "purple", label: "DevOps",     time: "55 min" },
  { name: "Data Scientist",       desc: "Statistics, ML fundamentals, model evaluation, and case studies.",             badge: "pink",   label: "Data",       time: "60 min" },
];

// ── Mini helpers ────────────────────────────────────────────────────────────
const gradeColor = (g) => ({ S:"#ffd700", A:"#00e5c3", B:"#00b8ff", C:"#f59e0b", D:"#f97316", F:"#ff4f6a" }[g] || "#7a8ba8");

const ScorePill = ({ score, max = 10 }) => {
  const pct = Math.max(0, Math.min(1, score / max));
  const color = pct >= 0.8 ? "#00e5c3" : pct >= 0.6 ? "#00b8ff" : pct >= 0.4 ? "#f59e0b" : "#ff4f6a";
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      background:`${color}14`, border:`1px solid ${color}44`,
      borderRadius:20, padding:"3px 10px", fontSize:12, fontWeight:700, color,
    }}>
      {score}/{max}
    </span>
  );
};

const GradeBadge = ({ grade, size = 36 }) => {
  const c = gradeColor(grade);
  return (
    <div style={{
      width:size, height:size, borderRadius:"50%",
      border:`2px solid ${c}`, background:`${c}18`,
      display:"flex", alignItems:"center", justifyContent:"center",
      fontSize:size*0.38, fontWeight:800, color:c,
      flexShrink:0,
    }}>{grade}</div>
  );
};

// ── Custom SVG Charts for Performance Analytics ─────────────────────────────
const ScoreTrendChart = ({ sessions }) => {
  if (!sessions || sessions.length === 0) return null;
  
  const sorted = [...sessions].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  
  const width = 500;
  const height = 220;
  const paddingX = 40;
  const paddingY = 30;
  
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;
  
  const data = sorted.map((s, idx) => {
    const sc = s.scores || [];
    const avg = s.final_score ?? (sc.length ? sc.reduce((a,b)=>a+b,0)/sc.length : 0);
    return {
      label: `I${idx + 1}`,
      score: parseFloat(avg) || 0,
      date: new Date(s.created_at).toLocaleDateString()
    };
  });
  
  const points = data.map((d, i) => {
    const x = data.length > 1
      ? paddingX + (i / (data.length - 1)) * chartWidth
      : paddingX + chartWidth / 2;
    const y = paddingY + chartHeight - (d.score / 10) * chartHeight;
    return { x, y, score: d.score, label: d.label, date: d.date };
  });
  
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = points.length > 0
    ? `${linePath} L ${points[points.length - 1].x} ${paddingY + chartHeight} L ${points[0].x} ${paddingY + chartHeight} Z`
    : '';

  return (
    <div style={{ width: "100%", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h4 style={{ fontSize: 13, fontWeight: 700, color: "#e8edf8" }}>Overall Score Trend</h4>
        <span style={{ fontSize: 11, color: "#7a8ba8" }}>{data.length} interviews</span>
      </div>
      <div style={{ position: "relative", width: "100%" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#00e5c3" />
              <stop offset="100%" stopColor="#00b8ff" />
            </linearGradient>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00e5c3" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#00e5c3" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {[0, 2.5, 5, 7.5, 10].map((val, idx) => {
            const y = paddingY + chartHeight - (val / 10) * chartHeight;
            return (
              <g key={idx} opacity="0.3">
                <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="rgba(255,255,255,0.15)" strokeDasharray="3,3" />
                <text x={paddingX - 10} y={y + 4} fill="#7a8ba8" fontSize="10" textAnchor="end" fontWeight="500">{val}</text>
              </g>
            );
          })}
          
          {points.length > 0 && (
            <path d={areaPath} fill="url(#areaGrad)" />
          )}
          
          {points.length > 0 && (
            <path d={linePath} fill="none" stroke="url(#lineGrad)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          )}
          
          {points.map((p, idx) => (
            <g key={idx} style={{ cursor: "pointer" }}>
              <circle cx={p.x} cy={p.y} r="5" fill="#080c14" stroke="#00e5c3" strokeWidth="3" />
              <title>{`Interview ${idx+1}\nScore: ${p.score}/10\nDate: ${p.date}`}</title>
            </g>
          ))}
          
          {points.map((p, idx) => (
            <text key={idx} x={p.x} y={height - 8} fill="#7a8ba8" fontSize="9" textAnchor="middle" fontWeight="600">
              {p.label}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
};

const QuestionBarChart = ({ sessions }) => {
  if (!sessions || sessions.length === 0) return null;
  
  const qSums = [0, 0, 0, 0, 0];
  const qCounts = [0, 0, 0, 0, 0];
  
  sessions.forEach(s => {
    const sc = s.scores || [];
    sc.forEach((score, idx) => {
      if (idx < 5) {
        qSums[idx] += score;
        qCounts[idx] += 1;
      }
    });
  });
  
  const qAverages = qSums.map((sum, idx) => {
    const count = qCounts[idx];
    return count > 0 ? parseFloat((sum / count).toFixed(1)) : 0;
  });
  
  const width = 500;
  const height = 220;
  const paddingX = 40;
  const paddingY = 30;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;
  const barWidth = 32;
  
  return (
    <div style={{ width: "100%", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 16, padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h4 style={{ fontSize: 13, fontWeight: 700, color: "#e8edf8" }}>Confidence Progression</h4>
        <span style={{ fontSize: 11, color: "#7a8ba8" }}>Average by Question</span>
      </div>
      <div style={{ position: "relative", width: "100%" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
          {[0, 2.5, 5, 7.5, 10].map((val, idx) => {
            const y = paddingY + chartHeight - (val / 10) * chartHeight;
            return (
              <g key={idx} opacity="0.3">
                <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="rgba(255,255,255,0.15)" strokeDasharray="3,3" />
                <text x={paddingX - 10} y={y + 4} fill="#7a8ba8" fontSize="10" textAnchor="end" fontWeight="500">{val}</text>
              </g>
            );
          })}
          
          {qAverages.map((avg, idx) => {
            const x = paddingX + (idx / 4) * (chartWidth - barWidth);
            const barHeight = (avg / 10) * chartHeight;
            const y = paddingY + chartHeight - barHeight;
            const isZero = avg === 0;
            const color = avg >= 8 ? "#00e5c3" : avg >= 6 ? "#00b8ff" : avg >= 4 ? "#f59e0b" : "#ff4f6a";
            
            return (
              <g key={idx}>
                {!isZero && (
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill={color}
                    opacity="0.8"
                    rx="4"
                    ry="4"
                    style={{ transition: "all 0.3s ease" }}
                  />
                )}
                <text x={x + barWidth / 2} y={y - 8} fill={color} fontSize="11" fontWeight="700" textAnchor="middle">
                  {avg > 0 ? avg : "—"}
                </text>
                <text x={x + barWidth / 2} y={height - 8} fill="#7a8ba8" fontSize="10" textAnchor="middle" fontWeight="600">
                  {`Q${idx + 1}`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

const GradePieChart = ({ sessions }) => {
  if (!sessions || sessions.length === 0) return null;
  
  const counts = { S: 0, A: 0, B: 0, C: 0, D: 0, F: 0 };
  let total = 0;
  
  sessions.forEach(s => {
    if (s.final_grade && counts[s.final_grade] !== undefined) {
      counts[s.final_grade]++;
      total++;
    }
  });
  
  if (total === 0) {
    sessions.forEach(s => {
      const sc = s.scores || [];
      const avg = s.final_score ?? (sc.length ? sc.reduce((a,b)=>a+b,0)/sc.length : 0);
      let g = "F";
      if (avg >= 9.0) g = "S";
      else if (avg >= 8.0) g = "A";
      else if (avg >= 7.0) g = "B";
      else if (avg >= 5.0) g = "C";
      else if (avg >= 4.0) g = "D";
      counts[g]++;
      total++;
    });
  }
  
  const grades = [
    { name: "S", label: "Expert (S)", color: "#ffd700", count: counts.S },
    { name: "A", label: "Advanced (A)", color: "#00e5c3", count: counts.A },
    { name: "B", label: "Proficient (B)", color: "#00b8ff", count: counts.B },
    { name: "C", label: "Intermediate (C)", color: "#f59e0b", count: counts.C },
    { name: "D", label: "Novice (D)", color: "#f97316", count: counts.D },
    { name: "F", label: "Beginner (F)", color: "#ff4f6a", count: counts.F },
  ].filter(g => g.count > 0);
  
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  let accumulatedPercent = 0;
  
  return (
    <div style={{ width: "100%", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 16, padding: 18, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: "#e8edf8" }}>Grade Distribution</h4>
          <span style={{ fontSize: 11, color: "#7a8ba8" }}>Overall standing</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", justifyContent: "center", marginTop: 10 }}>
          <div style={{ position: "relative", width: 110, height: 110, flexShrink: 0 }}>
            <svg width="100%" height="100%" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="12" />
              {grades.map((g, idx) => {
                const percent = g.count / total;
                const strokeLength = percent * circumference;
                const strokeOffset = circumference - (accumulatedPercent * circumference);
                accumulatedPercent += percent;
                
                return (
                  <circle
                    key={idx}
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    stroke={g.color}
                    strokeWidth="12"
                    strokeDasharray={`${strokeLength} ${circumference}`}
                    strokeDashoffset={strokeOffset}
                    transform="rotate(-90 60 60)"
                    strokeLinecap="round"
                    style={{ transition: "stroke-dashoffset 0.5s ease" }}
                  />
                );
              })}
            </svg>
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 16, fontWeight: 800, color: "#e8edf8", lineHeight: 1.1 }}>{total}</span>
              <span style={{ fontSize: 8, color: "#7a8ba8", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total</span>
            </div>
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 110 }}>
            {grades.map((g, idx) => (
              <div key={idx} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: g.color, flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: "#b8c8d8", flex: 1, whiteSpace: "nowrap" }}>{g.name}-Grade</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: "#e8edf8" }}>
                  {g.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── PDF Generator (pure client-side, no library needed) ────────────────────
const generatePDF = (session) => {
  const { questions = [], responses = [], feedbacks = [], scores = [],
          final_score, final_grade, final_report, created_at } = session;

  const date = created_at ? new Date(created_at).toLocaleDateString() : "N/A";
  const avg  = final_score ?? (scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : "N/A");

  // Build HTML for the printable report
  const html = `<!DOCTYPE html><html><head>
  <meta charset="UTF-8"/>
  <title>Interview Report</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&display=swap');
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:'Sora',sans-serif; background:#0a0f1e; color:#e8edf8; padding:40px; }
    .header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:32px; padding-bottom:20px; border-bottom:1px solid rgba(255,255,255,0.1); }
    .brand { font-size:22px; font-weight:800; background:linear-gradient(135deg,#00e5c3,#00b8ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .meta { font-size:12px; color:#7a8ba8; text-align:right; line-height:1.8; }
    .hero { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:24px; margin-bottom:24px; display:flex; align-items:center; gap:24px; }
    .grade-ring { width:72px; height:72px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:28px; font-weight:800; }
    .score-label { font-size:13px; color:#7a8ba8; margin-bottom:4px; }
    .score-val { font-size:32px; font-weight:800; color:#00e5c3; }
    .report-text { font-size:13px; color:#b8c8d8; line-height:1.8; margin-top:8px; }
    .section-title { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#00e5c3; margin-bottom:14px; margin-top:28px; }
    .qa-card { background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:18px; margin-bottom:12px; }
    .q-label { font-size:11px; color:#a78bfa; font-weight:600; margin-bottom:6px; }
    .q-text { font-size:14px; color:#e8edf8; font-weight:600; margin-bottom:12px; line-height:1.5; }
    .a-label { font-size:11px; color:#7a8ba8; font-weight:600; margin-bottom:4px; }
    .a-text { font-size:13px; color:#b8c8d8; margin-bottom:12px; font-style:italic; line-height:1.6; }
    .f-label { font-size:11px; color:#00e5c3; font-weight:600; margin-bottom:4px; }
    .f-text { font-size:13px; color:#9ab0c8; line-height:1.7; white-space:pre-wrap; }
    .score-chip { display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; margin-bottom:10px; }
    .footer { margin-top:40px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.08); font-size:11px; color:#3a4a68; text-align:center; }
  </style>
  </head><body>
  <div class="header">
    <div class="brand">⚡ InterviewAI Report</div>
    <div class="meta">Date: ${date}<br/>Questions: ${questions.length}<br/>Session Report</div>
  </div>
  <div class="hero">
    <div class="grade-ring" style="border:3px solid ${gradeColor(final_grade)};background:${gradeColor(final_grade)}18;color:${gradeColor(final_grade)}">${final_grade || "—"}</div>
    <div>
      <div class="score-label">Overall Score</div>
      <div class="score-val">${avg}/10</div>
      ${final_report ? `<div class="report-text">${final_report}</div>` : ""}
    </div>
  </div>
  <div class="section-title">Question-by-Question Breakdown</div>
  ${questions.map((q, i) => {
    const feedbackText = feedbacks[i]
      ? (typeof feedbacks[i] === "object" ? feedbacks[i].feedback : feedbacks[i])
      : "—";
    return `
    <div class="qa-card">
      <div class="q-label">Question ${i+1}</div>
      <div class="q-text">${q}</div>
      ${scores[i] !== undefined ? `<span class="score-chip" style="background:${gradeColor('A')}18;color:${gradeColor('A')};border:1px solid ${gradeColor('A')}44">Score: ${scores[i]}/10</span>` : ""}
      <div class="a-label">Your Answer</div>
      <div class="a-text">"${responses[i] || "No answer recorded"}"</div>
      <div class="f-label">Feedback</div>
      <div class="f-text">${feedbackText}</div>
    </div>
    `;
  }).join("")}
  <div class="footer">Generated by InterviewAI · ${new Date().toLocaleString()}</div>
  </body></html>`;

  const win = window.open("", "_blank");
  win.document.write(html);
  win.document.close();
  setTimeout(() => win.print(), 600);
};

// ── Modal wrapper ───────────────────────────────────────────────────────────
const Modal = ({ onClose, children }) => (
  <div onClick={e => { if (e.target === e.currentTarget) onClose(); }} style={{
    position:"fixed", inset:0, background:"rgba(0,0,0,0.75)", backdropFilter:"blur(8px)",
    zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:20,
  }}>
    <div style={{
      background:"#0d1525", border:"1px solid rgba(255,255,255,0.1)",
      borderRadius:24, maxWidth:780, width:"100%", maxHeight:"85vh",
      overflowY:"auto", position:"relative",
    }}>
      <button onClick={onClose} style={{
        position:"sticky", top:16, float:"right", marginRight:16,
        background:"rgba(255,255,255,0.07)", border:"1px solid rgba(255,255,255,0.1)",
        borderRadius:"50%", width:32, height:32, color:"#e8edf8",
        cursor:"pointer", fontSize:16, display:"flex", alignItems:"center", justifyContent:"center",
        zIndex:10,
      }}>✕</button>
      {children}
    </div>
  </div>
);

// ── Session Detail Modal ────────────────────────────────────────────────────
const SessionModal = ({ session, onClose }) => {
  const { questions=[], responses=[], feedbacks=[], scores=[], final_score, final_grade, final_report, created_at } = session;
  const avg = final_score ?? (scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : null);

  return (
    <Modal onClose={onClose}>
      <div style={{ padding:"28px 28px 32px" }}>
        {/* Header */}
        <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:24 }}>
          {final_grade && <GradeBadge grade={final_grade} size={52} />}
          <div>
            <div style={{ fontSize:18, fontWeight:800, color:"#e8edf8" }}>Session Report</div>
            <div style={{ fontSize:12, color:"#7a8ba8", marginTop:3 }}>
              {created_at ? new Date(created_at).toLocaleString() : ""}
              {avg ? ` · Score ${avg}/10` : ""}
              {` · ${questions.length} questions`}
            </div>
          </div>
          <div style={{ marginLeft:"auto", display:"flex", gap:10 }}>
            {session.recording_path && (
              <a href={`${BACKEND_URL}/recording/${session.session_id}`} download style={{
                textDecoration:"none", background:"rgba(124,58,237,0.15)",
                border:"1px solid rgba(124,58,237,0.4)", borderRadius:10, padding:"9px 18px", color:"#a78bfa",
                fontWeight:700, fontSize:13, cursor:"pointer", display:"flex", alignItems:"center", gap:7,
              }}>
                <span>🎬</span> Video
              </a>
            )}
            <button onClick={() => generatePDF(session)} style={{
              background:"linear-gradient(135deg,#00e5c3,#00b8ff)",
              border:"none", borderRadius:10, padding:"9px 18px", color:"#050d14",
              fontWeight:700, fontSize:13, cursor:"pointer", display:"flex", alignItems:"center", gap:7,
            }}>
              <span>↓</span> PDF Report
            </button>
          </div>
        </div>

        {/* Final report */}
        {final_report && (
          <div style={{ background:"rgba(0,229,195,0.05)", border:"1px solid rgba(0,229,195,0.18)", borderRadius:14, padding:"14px 18px", marginBottom:20, fontSize:13, color:"#b8c8d8", lineHeight:1.8 }}>
            <div style={{ fontSize:10, fontWeight:700, color:"#00e5c3", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:6 }}>Overall Assessment</div>
            {final_report}
          </div>
        )}

        {/* Score bars */}
        {scores.length > 0 && (
          <div style={{ marginBottom:20 }}>
            <div style={{ fontSize:11, fontWeight:700, color:"#7a8ba8", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:10 }}>Score Breakdown</div>
            <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
              {scores.map((s,i) => {
                const c = s>=8?"#00e5c3":s>=6?"#00b8ff":s>=4?"#f59e0b":"#ff4f6a";
                return (
                  <div key={i} style={{ background:`${c}12`, border:`1px solid ${c}33`, borderRadius:10, padding:"6px 12px", textAlign:"center", minWidth:52 }}>
                    <div style={{ fontSize:10, color:"#7a8ba8" }}>Q{i+1}</div>
                    <div style={{ fontSize:15, fontWeight:800, color:c }}>{s}</div>
                  </div>
                );
              })}
              {avg && (
                <div style={{ background:"rgba(124,58,237,0.12)", border:"1px solid rgba(124,58,237,0.3)", borderRadius:10, padding:"6px 12px", textAlign:"center", minWidth:52 }}>
                  <div style={{ fontSize:10, color:"#7a8ba8" }}>Avg</div>
                  <div style={{ fontSize:15, fontWeight:800, color:"#a78bfa" }}>{avg}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Q&A */}
        <div style={{ fontSize:11, fontWeight:700, color:"#7a8ba8", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:12 }}>Questions & Answers</div>
        {questions.map((q, i) => (
          <div key={i} style={{ background:"rgba(255,255,255,0.02)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:14, padding:"16px 18px", marginBottom:10 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
              <span style={{ fontSize:11, fontWeight:700, color:"#a78bfa", textTransform:"uppercase" }}>Q{i+1}</span>
              {scores[i] !== undefined && <ScorePill score={scores[i]} />}
            </div>
            <div style={{ fontSize:14, fontWeight:600, color:"#e8edf8", marginBottom:10, lineHeight:1.6 }}>{q}</div>
            {responses[i] && (
              <>
                <div style={{ fontSize:10, fontWeight:700, color:"#7a8ba8", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4 }}>Your Answer</div>
                <div style={{ fontSize:13, color:"#7a8ba8", marginBottom:10, fontStyle:"italic", lineHeight:1.6 }}>"{responses[i]}"</div>
              </>
            )}
            {feedbacks[i] && (
              <>
                <div style={{ fontSize:10, fontWeight:700, color:"#00e5c3", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4 }}>Feedback</div>
                <div style={{ fontSize:13, color:"#9ab0c8", lineHeight:1.8, whiteSpace:"pre-wrap" }}>
                  {typeof feedbacks[i] === "object" ? feedbacks[i].feedback : feedbacks[i]}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </Modal>
  );
};

// ════════════════════════════════════════════════════════════════════════════
//  MAIN DASHBOARD
// ════════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const navigate = useNavigate();

  // ── State ────────────────────────────────────────────────────────────────
  const [menuOpen, setMenuOpen]             = useState(false);
  const [resumeUploaded, setResumeUploaded] = useState(false);
  const [resumeFile, setResumeFile]         = useState(null);
  const [formSubmitted, setFormSubmitted]   = useState(false);
  const [skipResume, setSkipResume]         = useState(false);
  const [sessionId, setSessionId]           = useState(null);
  const [jobDetails, setJobDetails]         = useState({ role:"", tools:"", experience:"" });
  const [user, setUser]                     = useState({ name:"", email:"", avatar:"", _id:"" });

  // History
  const [history, setHistory]               = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeTab, setActiveTab]           = useState("setup"); // "setup" | "history"
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectMode, setSelectMode]         = useState(false);
  const [selectedSessionIds, setSelectedSessionIds] = useState([]);

  // ── Init ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        setUser(JSON.parse(stored));
      } else {
        const email   = localStorage.getItem("email")   || "";
        const user_id = localStorage.getItem("user_id") || "";
        setUser({ name:"", email, avatar:"", _id:user_id });
      }
    } catch { /* silent */ }

    const sid = crypto.randomUUID();
    setSessionId(sid);
    localStorage.removeItem("session_id");
  }, []);

  useEffect(() => {
    const handler = (e) => { if (!e.target.closest(".nav-right")) setMenuOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Load history on mount or when user id is available
  useEffect(() => {
    if (user._id) loadHistory();
  }, [user._id]);

  useEffect(() => {
    setSelectMode(false);
    setSelectedSessionIds([]);
  }, [activeTab]);

  const loadHistory = async () => {
    if (!user._id) return;
    setHistoryLoading(true);
    setSelectMode(false);
    setSelectedSessionIds([]);
    try {
      const res  = await fetch(`${BACKEND_URL}/history/${user._id}`);
      const data = await res.json();
      setHistory(Array.isArray(data) ? data : []);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleLogout = () => { localStorage.clear(); navigate("/"); };

  const handleDeleteSession = async (sessId) => {
    if (!window.confirm("Are you sure you want to permanently delete this interview session? This cannot be undone.")) return;
    try {
      const res = await fetch(`${BACKEND_URL}/session/${sessId}`, { method: "DELETE" });
      if (res.ok) {
        setHistory(prev => prev.filter(s => s.session_id !== sessId));
      } else {
        alert("Failed to delete session.");
      }
    } catch {
      alert("Error deleting session.");
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Are you sure you want to permanently delete all your interview history? This cannot be undone.")) return;
    try {
      const res = await fetch(`${BACKEND_URL}/history/${user._id}`, { method: "DELETE" });
      if (res.ok) {
        setHistory([]);
        alert("All interview history has been cleared!");
      } else {
        alert("Failed to clear history.");
      }
    } catch {
      alert("Error clearing history.");
    }
  };

  const handleToggleSelectSession = (sessId) => {
    setSelectedSessionIds(prev => 
      prev.includes(sessId) ? prev.filter(id => id !== sessId) : [...prev, sessId]
    );
  };

  const handleSelectAllSessions = () => {
    if (selectedSessionIds.length === history.length) {
      setSelectedSessionIds([]);
    } else {
      setSelectedSessionIds(history.map(s => s.session_id));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedSessionIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to permanently delete the ${selectedSessionIds.length} selected session(s)? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/session/bulk-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_ids: selectedSessionIds })
      });
      if (res.ok) {
        setHistory(prev => prev.filter(s => !selectedSessionIds.includes(s.session_id)));
        setSelectedSessionIds([]);
        setSelectMode(false);
      } else {
        alert("Failed to delete selected sessions.");
      }
    } catch {
      alert("Error deleting selected sessions.");
    }
  };

  const handleFileChange = (e) => { const f = e.target.files?.[0]; if (f) setResumeFile(f); };

  const uploadResume = async () => {
    if (!resumeFile) { alert("Please select a file."); return; }
    const fd = new FormData();
    fd.append("resume",     resumeFile);
    fd.append("session_id", sessionId);
    if (user._id) fd.append("user_id", user._id);
    try {
      const res = await fetch(`${BACKEND_URL}/upload`, { method:"POST", body:fd });
      if (!res.ok) { const d = await res.json(); alert(d.error || "Upload failed"); return; }
      const data = await res.json();
      if (data.session_id) { setSessionId(data.session_id); localStorage.setItem("session_id", data.session_id); }
      setResumeUploaded(true);
    } catch { alert("Failed to upload. Please try again."); }
  };

  const submitJobDetails = () => {
    const { role, tools, experience } = jobDetails;
    if (role && tools && experience) setFormSubmitted(true);
    else alert("Please fill out all job details.");
  };

  const handleBeginInterview = async () => {
    if (skipResume && !resumeUploaded) {
      try {
        const res = await fetch(`${BACKEND_URL}/create-session-no-resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user._id,
            role: jobDetails.role,
            tools: jobDetails.tools,
            experience: jobDetails.experience
          })
        });
        if (!res.ok) {
          const errData = await res.json();
          alert(errData.error || "Failed to create session.");
          return;
        }
        const data = await res.json();
        if (data.session_id) {
          localStorage.setItem("session_id", data.session_id);
          navigate("/interview");
        }
      } catch {
        alert("Error connecting to server. Please try again.");
      }
    } else {
      navigate("/interview");
    }
  };

  const displayName = user.name ? user.name.split(" ")[0] : user.email ? user.email.split("@")[0] : "Candidate";
  const initials    = user.name ? user.name.split(" ").map(n=>n[0]).join("").toUpperCase().slice(0,2) : (user.email?.[0]||"U").toUpperCase();
  const isReady     = (resumeUploaded || skipResume) && formSubmitted;

  // ── History stats ─────────────────────────────────────────────────────────
  const completedSessions = history.filter(s => !s.active);
  const avgOverall = completedSessions.length
    ? (completedSessions.reduce((sum, s) => {
        const sc = s.scores || [];
        return sum + (sc.length ? sc.reduce((a,b)=>a+b,0)/sc.length : (s.final_score || 0));
      }, 0) / completedSessions.length).toFixed(1)
    : null;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&display=swap');
        *, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
        body { font-family:'Sora',sans-serif; background:#080c14; color:#e8edf8; }

        .db-root { min-height:100vh; background:radial-gradient(ellipse at 15% 40%,rgba(124,58,237,.07) 0%,transparent 55%), radial-gradient(ellipse at 85% 15%,rgba(0,229,195,.05) 0%,transparent 50%), #080c14; }

        /* ── Navbar ── */
        .db-nav { display:flex; justify-content:space-between; align-items:center; height:64px; padding:0 28px; background:rgba(8,12,20,.94); backdrop-filter:blur(16px); border-bottom:1px solid rgba(255,255,255,.07); position:sticky; top:0; z-index:200; }
        .db-brand { display:flex; align-items:center; gap:10px; font-size:17px; font-weight:700; color:#e8edf8; text-decoration:none; }
        .db-brand-icon { width:34px; height:34px; background:linear-gradient(135deg,#00e5c3,#00b8ff); border-radius:9px; display:flex; align-items:center; justify-content:center; color:#080c14; }
        .nav-right { display:flex; align-items:center; gap:12px; position:relative; }
        .nav-pill { display:flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(0,229,195,.08); border:1px solid rgba(0,229,195,.2); border-radius:20px; font-size:12px; font-weight:600; color:#00e5c3; }
        .avatar-btn { width:36px; height:36px; border-radius:50%; background:rgba(0,229,195,.15); border:1.5px solid rgba(0,229,195,.35); display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#00e5c3; cursor:pointer; overflow:hidden; }
        .dropdown { position:absolute; top:48px; right:0; background:#0d1525; border:1px solid rgba(255,255,255,.1); border-radius:14px; padding:6px; min-width:180px; box-shadow:0 16px 40px rgba(0,0,0,.5); }
        .dropdown-header { padding:10px 14px 8px; border-bottom:1px solid rgba(255,255,255,.07); }
        .dropdown-header .dn { font-size:13px; font-weight:600; color:#e8edf8; }
        .dropdown-header .de { font-size:11px; color:#7a8ba8; margin-top:2px; }
        .dropdown ul { list-style:none; padding:4px 0; }
        .dropdown li { display:flex; align-items:center; gap:9px; padding:9px 14px; font-size:13px; color:#e8edf8; border-radius:8px; cursor:pointer; transition:background .15s; }
        .dropdown li:hover { background:rgba(255,255,255,.07); }
        .dropdown li.danger { color:#ff4f6a; }

        /* ── Layout ── */
        .db-body { max-width:1100px; margin:0 auto; padding:32px 20px 60px; }

        /* ── Welcome ── */
        .db-welcome { margin-bottom:28px; }
        .db-welcome h1 { font-size:26px; font-weight:800; color:#e8edf8; margin-bottom:4px; }
        .db-welcome p { font-size:14px; color:#7a8ba8; }

        /* ── Stat cards ── */
        .stat-row { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px; }
        @media(max-width:700px){ .stat-row { grid-template-columns:repeat(2,1fr); } }
        .stat-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.07); border-radius:16px; padding:18px 20px; }
        .stat-card .label { font-size:11px; color:#7a8ba8; font-weight:600; text-transform:uppercase; letter-spacing:.06em; margin-bottom:8px; }
        .stat-card .value { font-size:26px; font-weight:800; color:#e8edf8; }
        .stat-card .sub { font-size:11px; color:#7a8ba8; margin-top:3px; }

        /* ── Tabs ── */
        .tab-bar { display:flex; gap:6px; background:rgba(255,255,255,.04); border-radius:12px; padding:4px; margin-bottom:24px; width:fit-content; }
        .tab-btn { padding:8px 20px; border-radius:9px; border:none; font-family:'Sora',sans-serif; font-size:13px; font-weight:600; cursor:pointer; transition:all .2s; }
        .tab-active { background:rgba(0,229,195,.15); color:#00e5c3; border:1px solid rgba(0,229,195,.3); }
        .tab-inactive { background:transparent; color:#7a8ba8; border:1px solid transparent; }
        .tab-inactive:hover { color:#b8c8d8; }

        /* ── Setup grid ── */
        .setup-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
        @media(max-width:680px){ .setup-grid { grid-template-columns:1fr; } }

        /* ── Glass cards ── */
        .glass { background:rgba(12,18,35,.8); border:1px solid rgba(255,255,255,.07); border-radius:20px; padding:24px; }
        .glass.pulse { animation:cardPulse 2s ease-in-out infinite; }
        @keyframes cardPulse { 0%,100%{border-color:rgba(0,229,195,.15)} 50%{border-color:rgba(0,229,195,.4)} }
        .card-title { display:flex; align-items:center; gap:10px; font-size:14px; font-weight:700; color:#e8edf8; margin-bottom:18px; }
        .card-title-icon { width:30px; height:30px; background:rgba(0,229,195,.1); border:1px solid rgba(0,229,195,.2); border-radius:9px; display:flex; align-items:center; justify-content:center; color:#00e5c3; flex-shrink:0; }

        /* ── Upload area ── */
        .upload-area { border:1.5px dashed rgba(255,255,255,.1); border-radius:14px; padding:24px; text-align:center; cursor:pointer; transition:border-color .2s; position:relative; margin-bottom:14px; }
        .upload-area:hover { border-color:rgba(0,229,195,.35); }
        .upload-area input[type=file] { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; }
        .upload-area .ua-icon { width:40px; height:40px; background:rgba(0,229,195,.08); border-radius:12px; display:flex; align-items:center; justify-content:center; margin:0 auto 10px; color:#00e5c3; }
        .upload-area h4 { font-size:14px; font-weight:600; color:#e8edf8; margin-bottom:4px; }
        .upload-area p { font-size:12px; color:#7a8ba8; }
        .upload-badge { display:flex; align-items:center; gap:8px; background:rgba(0,214,143,.07); border:1px solid rgba(0,214,143,.2); border-radius:12px; padding:10px 14px; font-size:13px; color:#00d68f; margin-bottom:14px; font-weight:500; }

        /* ── Fields ── */
        .field-stack { display:flex; flex-direction:column; gap:12px; margin-bottom:16px; }
        .field-label { font-size:12px; font-weight:600; color:#7a8ba8; margin-bottom:5px; display:block; }
        .field-wrap { position:relative; }
        .field-icon { position:absolute; left:12px; top:50%; transform:translateY(-50%); color:#3a4a68; pointer-events:none; }
        .field-input { width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:10px 12px 10px 36px; color:#e8edf8; font-family:'Sora',sans-serif; font-size:13px; outline:none; transition:border-color .2s; }
        .field-input:focus { border-color:rgba(0,229,195,.4); }
        .field-input::placeholder { color:#3a4a68; }
        .field-input:disabled { opacity:.5; cursor:not-allowed; }

        /* ── Buttons ── */
        .btn-primary { width:100%; padding:11px; border-radius:12px; border:none; background:linear-gradient(135deg,#00e5c3,#00b8ff); color:#050d14; font-family:'Sora',sans-serif; font-size:14px; font-weight:700; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:7px; }
        .btn-primary:hover:not(:disabled) { opacity:.9; transform:translateY(-1px); }
        .btn-primary:disabled { opacity:.4; cursor:not-allowed; transform:none; }
        .btn-ghost { width:100%; padding:10px; border-radius:12px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.04); color:#b8c8d8; font-family:'Sora',sans-serif; font-size:13px; font-weight:600; cursor:pointer; transition:all .2s; margin-top:8px; }
        .btn-ghost:hover { background:rgba(255,255,255,.08); }

        /* ── CTA ── */
        .cta-card { background:linear-gradient(135deg,rgba(124,58,237,.12),rgba(0,229,195,.06)); border:1px solid rgba(124,58,237,.25); border-radius:20px; padding:24px 28px; display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:32px; flex-wrap:wrap; }
        .cta-card h3 { font-size:18px; font-weight:800; color:#e8edf8; margin-bottom:4px; }
        .cta-card p { font-size:13px; color:#7a8ba8; margin-bottom:10px; }
        .status-row { display:flex; align-items:center; gap:8px; }
        .status-dot { width:8px; height:8px; border-radius:50%; background:#3a4a68; transition:background .3s; }
        .status-dot.ready { background:#00d68f; box-shadow:0 0 8px rgba(0,214,143,.5); }
        .status-text { font-size:13px; color:#7a8ba8; }
        .start-btn { padding:13px 30px; background:linear-gradient(135deg,#7c3aed,#00b8ff); border:none; border-radius:14px; color:#fff; font-family:'Sora',sans-serif; font-size:14px; font-weight:700; cursor:pointer; transition:all .2s; white-space:nowrap; display:flex; align-items:center; gap:8px; }
        .start-btn:hover:not(:disabled) { opacity:.9; transform:translateY(-2px); box-shadow:0 8px 28px rgba(124,58,237,.4); }
        .start-btn:disabled { opacity:.35; cursor:not-allowed; transform:none; }

        /* ── Tracks ── */
        .section-hdr { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
        .section-hdr h3 { font-size:16px; font-weight:700; color:#e8edf8; }
        .section-hdr span { font-size:12px; color:#7a8ba8; }
        .tracks-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px; margin-bottom:32px; }
        .track-card { background:rgba(12,18,35,.7); border:1px solid rgba(255,255,255,.07); border-radius:16px; padding:18px; transition:all .2s; cursor:pointer; }
        .track-card:hover { border-color:rgba(0,229,195,.25); transform:translateY(-2px); }
        .track-badge { display:inline-block; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; padding:3px 9px; border-radius:20px; margin-bottom:10px; }
        .badge-teal   { background:rgba(0,229,195,.1);  color:#00e5c3; border:1px solid rgba(0,229,195,.25); }
        .badge-blue   { background:rgba(0,184,255,.1);  color:#00b8ff; border:1px solid rgba(0,184,255,.25); }
        .badge-purple { background:rgba(124,58,237,.12);color:#a78bfa; border:1px solid rgba(124,58,237,.3); }
        .badge-pink   { background:rgba(236,72,153,.1); color:#f472b6; border:1px solid rgba(236,72,153,.25); }
        .track-card h3 { font-size:14px; font-weight:700; color:#e8edf8; margin-bottom:6px; }
        .track-card p { font-size:12px; color:#7a8ba8; line-height:1.6; margin-bottom:12px; }
        .track-footer { display:flex; align-items:center; justify-content:space-between; }
        .track-meta { font-size:11px; color:#3a4a68; }
        .track-btn { display:flex; align-items:center; gap:5px; font-size:12px; font-weight:700; color:#00e5c3; background:rgba(0,229,195,.08); border:1px solid rgba(0,229,195,.2); border-radius:8px; padding:5px 10px; cursor:pointer; }

        /* ── History ── */
        .hist-empty { text-align:center; padding:60px 20px; color:#3a4a68; }
        .hist-empty .icon { font-size:48px; margin-bottom:12px; }
        .hist-summary { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:24px; }
        @media(max-width:600px){ .hist-summary { grid-template-columns:1fr 1fr; } }
        .hs-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.07); border-radius:14px; padding:16px 18px; }
        .hs-card .lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#7a8ba8; margin-bottom:6px; }
        .hs-card .val { font-size:22px; font-weight:800; color:#e8edf8; }
        .session-list { display:flex; flex-direction:column; gap:12px; }
        .sess-card { background:rgba(12,18,35,.8); border:1px solid rgba(255,255,255,.07); border-radius:16px; padding:18px 20px; transition:border-color .2s; }
        .sess-card:hover { border-color:rgba(0,229,195,.2); }
        .sess-top { display:flex; align-items:center; gap:14px; margin-bottom:12px; }
        .sess-info { flex:1; }
        .sess-date { font-size:12px; color:#7a8ba8; margin-bottom:3px; }
        .sess-meta { font-size:13px; font-weight:600; color:#e8edf8; }
        .sess-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
        .act-btn { display:flex; align-items:center; gap:6px; padding:7px 14px; border-radius:9px; font-family:'Sora',sans-serif; font-size:12px; font-weight:600; cursor:pointer; transition:all .2s; border:none; }
        .act-view   { background:rgba(0,229,195,.1);  color:#00e5c3; border:1px solid rgba(0,229,195,.25); }
        .act-pdf    { background:rgba(0,184,255,.1);  color:#00b8ff; border:1px solid rgba(0,184,255,.25); }
        .act-view:hover { background:rgba(0,229,195,.18); }
        .act-pdf:hover  { background:rgba(0,184,255,.18); }
        .score-bar-wrap { display:flex; align-items:center; gap:10px; }
        .score-bar-bg { flex:1; height:5px; border-radius:3px; background:rgba(255,255,255,.07); overflow:hidden; }
        .score-bar-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#00e5c3,#00b8ff); transition:width 1s ease; }
        .active-badge { display:inline-flex; align-items:center; gap:5px; font-size:11px; font-weight:600; color:#f59e0b; background:rgba(245,158,11,.1); border:1px solid rgba(245,158,11,.25); border-radius:20px; padding:3px 9px; }
        .active-dot { width:5px; height:5px; border-radius:50%; background:#f59e0b; animation:pulse 1.5s ease-in-out infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
        .loading-spin { width:20px; height:20px; border:2px solid rgba(0,229,195,.2); border-top-color:#00e5c3; border-radius:50%; animation:spin 0.8s linear infinite; margin:40px auto; }
        @keyframes spin { to{transform:rotate(360deg)} }

        /* ── Performance Dashboard ── */
        .perf-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px; }
        .perf-grid-3 { display:grid; grid-template-columns:1.5fr 1fr 1fr; gap:20px; margin-bottom:24px; }
        @media(max-width:1024px){ .perf-grid-3 { grid-template-columns:1fr 1fr; } }
        @media(max-width:768px){ .perf-grid-3 { grid-template-columns:1fr; } }
        .perf-insight-card { background:rgba(12,18,35,.8); border:1px solid rgba(255,255,255,.07); border-radius:20px; padding:20px; }
        .perf-insight-title { font-size:14px; font-weight:700; color:#e8edf8; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
        .perf-insight-icon { color:#00e5c3; }
        .perf-list { list-style:none; display:flex; flex-direction:column; gap:10px; }
        .perf-list-item { display:flex; gap:10px; align-items:flex-start; font-size:13px; color:#b8c8d8; line-height:1.5; }
        .perf-bullet-check { color:#00e5c3; flex-shrink:0; font-weight:bold; }
        .perf-bullet-warn { color:#ff4f6a; flex-shrink:0; font-weight:bold; }
        .perf-bullet-tip { color:#00b8ff; flex-shrink:0; font-weight:bold; }
        
        .perf-advice-card { background:linear-gradient(135deg,rgba(0,229,195,.08),rgba(0,184,255,.04)); border:1px solid rgba(0,229,195,.2); border-radius:20px; padding:22px; margin-bottom:24px; display:flex; gap:18px; align-items:center; }
        @media(max-width:600px){ .perf-advice-card { flex-direction:column; text-align:center; align-items:center; } }
        .perf-advice-avatar { width:64px; height:64px; border-radius:50%; background:rgba(0,229,195,.15); border:2px solid rgba(0,229,195,.4); display:flex; align-items:center; justify-content:center; font-size:28px; flex-shrink:0; }
        .perf-advice-text h4 { font-size:14px; font-weight:800; color:#00e5c3; margin-bottom:6px; }
        .perf-advice-text p { font-size:13px; color:#b8c8d8; line-height:1.7; }
        
        .perf-empty-state { text-align:center; padding:48px 24px; border:1px dashed rgba(255,255,255,0.1); border-radius:24px; background:rgba(255,255,255,0.01); }
        .perf-empty-state .icon { font-size:40px; margin-bottom:12px; }
      `}</style>

      <div className="db-root">
        {/* ── Navbar ── */}
        <nav className="db-nav">
          <div className="db-brand">
            <div className="db-brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
                <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            InterviewAI
          </div>
          <div className="nav-right">
            <div className="nav-pill">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              Dashboard
            </div>
            <div className="avatar-btn" onClick={() => setMenuOpen(!menuOpen)}>
              {user.avatar ? <img src={user.avatar} alt="av" style={{width:"100%",height:"100%",objectFit:"cover"}} /> : initials}
            </div>
            {menuOpen && (
              <div className="dropdown">
                <div className="dropdown-header">
                  <div className="dn">{user.name || displayName}</div>
                  <div className="de">{user.email}</div>
                </div>
                <ul>
                  <li onClick={() => navigate("/profile")}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    My Profile
                  </li>
                  <li onClick={() => { setActiveTab("history"); setMenuOpen(false); }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    Interview History
                  </li>
                  <li className="danger" onClick={handleLogout}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                    Logout
                  </li>
                </ul>
              </div>
            )}
          </div>
        </nav>

        <div className="db-body">
          {/* Welcome */}
          <div className="db-welcome">
            <h1>Welcome back, {displayName} 👋</h1>
            <p>Practice interviews, track your progress, and get better every session.</p>
          </div>

          {/* Stats */}
          <div className="stat-row">
            <div className="stat-card">
              <div className="label">Total Sessions</div>
              <div className="value">{history.length || "—"}</div>
              <div className="sub">interviews done</div>
            </div>
            <div className="stat-card">
              <div className="label">Completed</div>
              <div className="value">{completedSessions.length || "—"}</div>
              <div className="sub">fully scored</div>
            </div>
            <div className="stat-card">
              <div className="label">Avg Score</div>
              <div className="value" style={{color:"#00e5c3"}}>{avgOverall ?? "—"}</div>
              <div className="sub">out of 10</div>
            </div>
            <div className="stat-card">
              <div className="label">Best Grade</div>
              <div className="value" style={{color: gradeColor(
                completedSessions.map(s=>s.final_grade).sort((a,b)=>["S","A","B","C","D","F"].indexOf(a)-["S","A","B","C","D","F"].indexOf(b))[0]
              )}}>
                {completedSessions.map(s=>s.final_grade).sort((a,b)=>["S","A","B","C","D","F"].indexOf(a)-["S","A","B","C","D","F"].indexOf(b))[0] || "—"}
              </div>
              <div className="sub">highest grade</div>
            </div>
          </div>

          {/* Tabs */}
          <div className="tab-bar">
            <button className={`tab-btn ${activeTab==="setup"?"tab-active":"tab-inactive"}`} onClick={()=>setActiveTab("setup")}>
              🎯 New Interview
            </button>
            <button className={`tab-btn ${activeTab==="history"?"tab-active":"tab-inactive"}`} onClick={()=>setActiveTab("history")}>
              📊 History {history.length > 0 && `(${history.length})`}
            </button>
          </div>

          {/* ══ SETUP TAB ══ */}
          {activeTab === "setup" && (
            <>
              {/* CTA */}
              <div className="cta-card">
                <div>
                  <h3>Ready to start your interview?</h3>
                  <p>Your AI interviewer Hana will ask questions based on your resume or job details.</p>
                  <div className="status-row">
                    <div className={`status-dot ${isReady?"ready":""}`} />
                    <span className="status-text">
                      {!resumeUploaded && !skipResume && !formSubmitted && "Upload resume (or select Job Details mode) & fill job details to unlock"}
                      {(resumeUploaded || skipResume) && !formSubmitted && "Now fill in your job details"}
                      {!(resumeUploaded || skipResume) && formSubmitted && "Now upload your resume or select 'Job Details only' below"}
                      {isReady && "All set — you're ready to go! 🎌"}
                    </span>
                  </div>
                </div>
                <button className="start-btn" onClick={handleBeginInterview} disabled={!isReady}>
                  Begin Interview
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
              </div>

              {/* Setup grid */}
              <div className="setup-grid">
                {/* Resume upload */}
                <div className={`glass ${resumeUploaded || skipResume ? "" : " pulse"}`}>
                  <div className="card-title">
                    <div className="card-title-icon">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    Upload Resume
                    <span style={{ marginLeft: "auto", fontSize: 11, color: "#7a8ba8", fontWeight: 500, background: "rgba(255,255,255,0.04)", padding: "2px 8px", borderRadius: 10 }}>Optional</span>
                  </div>
                  {resumeUploaded ? (
                    <div className="upload-badge">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                      {resumeFile?.name || "Resume uploaded"}
                    </div>
                  ) : skipResume ? (
                    <div className="upload-badge" style={{ background: "rgba(0,184,255,0.08)", borderColor: "rgba(0,184,255,0.25)", color: "#00b8ff" }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
                      Job Details Mode (No Resume)
                    </div>
                  ) : (
                    <div className="upload-area">
                      <input type="file" accept=".pdf,.doc,.docx" onChange={handleFileChange} />
                      <div className="ua-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
                      </div>
                      <h4>{resumeFile ? resumeFile.name : "Drop your resume here"}</h4>
                      <p>{resumeFile ? "Ready to upload" : "PDF, DOC, or DOCX · max 10 MB"}</p>
                    </div>
                  )}
                  {!resumeUploaded && !skipResume && (
                    <button className="btn-primary" onClick={uploadResume} disabled={!resumeFile}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
                      Upload Resume
                    </button>
                  )}
                  {resumeUploaded && (
                    <button className="btn-ghost" onClick={()=>{setResumeUploaded(false);setResumeFile(null);}}>Replace File</button>
                  )}
                  
                  <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", gap: 8 }}>
                    <input 
                      type="checkbox" 
                      id="skipResume" 
                      checked={skipResume}
                      disabled={resumeUploaded}
                      onChange={(e) => {
                        setSkipResume(e.target.checked);
                        if (e.target.checked) {
                          setResumeFile(null);
                        }
                      }}
                      style={{ width: 16, height: 16, accentColor: "#00e5c3", cursor: "pointer" }}
                    />
                    <label htmlFor="skipResume" style={{ fontSize: 12, color: "#b8c8d8", cursor: "pointer", fontWeight: 500, userSelect: "none" }}>
                      Interview using Job Details only (no resume)
                    </label>
                  </div>
                </div>

                {/* Job details */}
                <div className={`glass ${resumeUploaded && !formSubmitted ? "pulse" : ""}`}>
                  <div className="card-title">
                    <div className="card-title-icon">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                    </div>
                    Job Details
                    {formSubmitted && <span style={{marginLeft:"auto",fontSize:12,color:"#00d68f",fontWeight:600}}>✓ Saved</span>}
                  </div>
                  <div className="field-stack">
                    {[
                      {key:"role", label:"Job Role", icon:"M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 7 a4 4 0 1 0 0-8 4 4 0 0 0 0 8", ph:"e.g. Software Engineer"},
                      {key:"tools", label:"Tools & Technologies", icon:"M16 18 22 12 16 6 M8 6 2 12 8 18", ph:"e.g. React, Node.js, AWS"},
                      {key:"experience", label:"Years of Experience", icon:"M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 6v6l4 2", ph:"e.g. 2 years"},
                    ].map(({key,label,ph}) => (
                      <div key={key}>
                        <label className="field-label">{label}</label>
                        <div className="field-wrap">
                          <svg className="field-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="2"/></svg>
                          <input type="text" className="field-input" placeholder={ph}
                            value={jobDetails[key]} disabled={formSubmitted}
                            onChange={e=>setJobDetails({...jobDetails,[key]:e.target.value})} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <button className="btn-primary" onClick={submitJobDetails} disabled={formSubmitted}>
                    {formSubmitted ? <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg> Details Saved</> : "Save Details"}
                  </button>
                  {formSubmitted && <button className="btn-ghost" onClick={()=>setFormSubmitted(false)}>Edit Details</button>}
                </div>
              </div>

              {/* Performance Analytics Dashboard */}
              <div className="section-hdr" style={{ marginTop: 28, marginBottom: 16 }}>
                <h3>Performance Analytics</h3>
                <span>Detailed Insights</span>
              </div>

              {completedSessions.length === 0 ? (
                <div className="perf-empty-state">
                  <div className="icon">📈</div>
                  <h4 style={{ fontSize: 16, fontWeight: 700, color: "#e8edf8", marginBottom: 6 }}>Analytics Pending</h4>
                  <p style={{ fontSize: 13, color: "#7a8ba8", maxWidth: 440, margin: "0 auto 18px", lineHeight: 1.6 }}>
                    Complete your first AI-driven interview session to unlock trend tracking, question-by-question metrics, strengths assessment, and custom advice.
                  </p>
                  <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
                    <div style={{ fontSize: 12, color: "#00e5c3", background: "rgba(0,229,195,0.07)", border: "1px solid rgba(0,229,195,0.2)", borderRadius: 20, padding: "6px 14px" }}>
                      🎯 Personalised questions
                    </div>
                    <div style={{ fontSize: 12, color: "#00b8ff", background: "rgba(0,184,255,0.07)", border: "1px solid rgba(0,184,255,0.2)", borderRadius: 20, padding: "6px 14px" }}>
                      🎥 Webcam/Voice optional
                    </div>
                    <div style={{ fontSize: 12, color: "#a78bfa", background: "rgba(124,58,237,0.07)", border: "1px solid rgba(124,58,237,0.2)", borderRadius: 20, padding: "6px 14px" }}>
                      🎌 Interactive feedback
                    </div>
                  </div>
                </div>
              ) : (() => {
                const strengthsList = [];
                const improvementsList = [];
                const tipsList = [];
                
                completedSessions.forEach(s => {
                  const feeds = s.feedbacks || [];
                  feeds.forEach(f => {
                    if (typeof f === 'object' && f !== null) {
                      if (f.strength) strengthsList.push(f.strength);
                      if (f.improvement) improvementsList.push(f.improvement);
                      if (f.tip) tipsList.push(f.tip);
                    } else if (typeof f === 'string') {
                      const lines = f.split('\n');
                      lines.forEach(l => {
                        if (l.toLowerCase().includes("strength:")) {
                          strengthsList.push(l.replace(/^(✅\s*)?Strength:\s*/i, '').trim());
                        } else if (l.toLowerCase().includes("improve:") || l.toLowerCase().includes("improvement:")) {
                          improvementsList.push(l.replace(/^(⚠️\s*)?Improve:\s*/i, '').trim());
                        } else if (l.toLowerCase().includes("tip:")) {
                          tipsList.push(l.replace(/^(💡\s*)?Tip:\s*/i, '').trim());
                        }
                      });
                    }
                  });
                });
                
                const finalStrengths = [...new Set(strengthsList)].reverse().slice(0, 3);
                const finalImprovements = [...new Set(improvementsList)].reverse().slice(0, 3);
                const finalTips = [...new Set(tipsList)].reverse().slice(0, 3);
                
                const displayStrengths = finalStrengths.length > 0 ? finalStrengths : [
                  "Exhibits a good initial attempt to explain candidate background.",
                  "Willingness to detail project context and toolsets used.",
                  "Displays structured technical communication when describing experiences."
                ];
                
                const displayImprovements = finalImprovements.length > 0 ? finalImprovements : [
                  "Focus on structure: use the STAR method to describe actions and metrics.",
                  "Remember to specify time and space complexity for algorithmic solutions.",
                  "Provide more precise technical tradeoffs when selecting database tools."
                ];
                
                const displayTips = finalTips.length > 0 ? finalTips : [
                  "Explain the 'why' behind architectural decisions, not just the 'what'.",
                  "Keep your answers concise; try to finish within 1.5 to 2 minutes.",
                  "Ask clarifying questions to ensure your solution targets the root problem."
                ];

                let adviceTitle = "Hana's Preparing Your Strategy";
                let adviceBody = "Complete an interview to receive custom actionable advice from your interviewer Hana.";
                if (avgOverall !== null) {
                  const scoreVal = parseFloat(avgOverall);
                  if (scoreVal >= 8.5) {
                    adviceTitle = "Hana's Evaluation: Elite Performance! 🌸";
                    adviceBody = "Hana is highly impressed! Your technical depth and overall answers are outstanding. To achieve absolute perfection, focus on polishing delivery speed and explaining complex architectural edge cases.";
                  } else if (scoreVal >= 7.0) {
                    adviceTitle = "Hana's Evaluation: Strong Foundation! 🎌";
                    adviceBody = "You are doing great! Your answers are clear and detailed, but there is room for improvement. Consistently apply the STAR framework (Situation, Task, Action, Result) and state clear quantitative metrics.";
                  } else {
                    adviceTitle = "Hana's Evaluation: Let's Level Up! ⚡";
                    adviceBody = "Keep practicing! Focus on explaining time/space complexities and organizing your thoughts before speaking. Try writing down 2-3 key talking points on paper before answering Hana.";
                  }
                }

                return (
                  <>
                    <div className="perf-grid-3">
                      <ScoreTrendChart sessions={completedSessions} />
                      <QuestionBarChart sessions={completedSessions} />
                      <GradePieChart sessions={completedSessions} />
                    </div>

                    <div className="perf-advice-card">
                      <div className="perf-advice-avatar">🎌</div>
                      <div className="perf-advice-text">
                        <h4>{adviceTitle}</h4>
                        <p>{adviceBody}</p>
                      </div>
                    </div>

                    <div className="perf-grid">
                      <div className="perf-insight-card">
                        <div className="perf-insight-title">
                          <span className="perf-insight-icon">✅</span>
                          Key Strengths
                        </div>
                        <ul className="perf-list">
                          {displayStrengths.map((str, idx) => (
                            <li className="perf-list-item" key={idx}>
                              <span className="perf-bullet-check">✓</span>
                              <span>{str}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="perf-insight-card">
                        <div className="perf-insight-title">
                          <span className="perf-insight-icon" style={{ color: "#ff4f6a" }}>⚠️</span>
                          Focus Areas & Tips
                        </div>
                        <ul className="perf-list">
                          {displayImprovements.map((imp, idx) => (
                            <li className="perf-list-item" key={idx}>
                              <span className="perf-bullet-warn">!</span>
                              <span>{imp}</span>
                            </li>
                          ))}
                          {displayTips.slice(0, 1).map((tipText, idx) => (
                            <li className="perf-list-item" key={idx + 3}>
                              <span className="perf-bullet-tip">💡</span>
                              <span>{tipText}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </>
                );
              })()}
            </>
          )}

          {/* ══ HISTORY TAB ══ */}
          {activeTab === "history" && (
            <>
              {historyLoading ? (
                <div className="loading-spin" />
              ) : history.length === 0 ? (
                <div className="hist-empty">
                  <div className="icon">🎌</div>
                  <div style={{fontSize:16,fontWeight:600,color:"#7a8ba8",marginBottom:6}}>No interviews yet</div>
                  <div style={{fontSize:13,color:"#3a4a68"}}>Complete your first interview to see your history here.</div>
                  <button className="btn-primary" style={{width:"auto",marginTop:20,padding:"10px 24px"}} onClick={()=>setActiveTab("setup")}>
                    Start First Interview
                  </button>
                </div>
              ) : (
                <>
                  {/* Summary stats */}
                  <div className="hist-summary">
                    <div className="hs-card">
                      <div className="lbl">Total Sessions</div>
                      <div className="val">{history.length}</div>
                    </div>
                    <div className="hs-card">
                      <div className="lbl">Avg Score</div>
                      <div className="val" style={{color:"#00e5c3"}}>{avgOverall ?? "—"}</div>
                    </div>
                    <div className="hs-card">
                      <div className="lbl">Questions Asked</div>
                      <div className="val">{history.reduce((s,h)=>(s+(h.questions?.length||0)),0)}</div>
                    </div>
                  </div>

                  {/* Session list */}
                  <div className="section-hdr" style={{marginBottom:14}}>
                    <h3>All Sessions</h3>
                    <div style={{ display:"flex", gap:15, alignItems:"center" }}>
                      {!selectMode ? (
                        <>
                          <button onClick={() => setSelectMode(true)} style={{fontSize:12,color:"#00e5c3",background:"none",border:"none",cursor:"pointer",fontWeight:600}}>☑ Select</button>
                          <button onClick={loadHistory} style={{fontSize:12,color:"#7a8ba8",background:"none",border:"none",cursor:"pointer"}}>↻ Refresh</button>
                          <button onClick={handleDeleteAll} style={{fontSize:12,color:"#ff4f6a",background:"none",border:"none",cursor:"pointer",fontWeight:600}}>🗑 Clear History</button>
                        </>
                      ) : (
                        <>
                          <button onClick={handleSelectAllSessions} style={{fontSize:12,color:"#00b8ff",background:"none",border:"none",cursor:"pointer",fontWeight:600}}>
                            {selectedSessionIds.length === history.length ? "☐ Deselect All" : "☑ Select All"}
                          </button>
                          <button onClick={handleDeleteSelected} disabled={selectedSessionIds.length === 0} style={{fontSize:12,color:selectedSessionIds.length === 0 ? "#4a5a72" : "#ff4f6a",background:"none",border:"none",cursor:selectedSessionIds.length === 0 ? "not-allowed" : "pointer",fontWeight:600}}>
                            🗑 Delete Selected ({selectedSessionIds.length})
                          </button>
                          <button onClick={() => { setSelectMode(false); setSelectedSessionIds([]); }} style={{fontSize:12,color:"#7a8ba8",background:"none",border:"none",cursor:"pointer"}}>Cancel</button>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="session-list">
                    {history.map((s, i) => {
                      const sc = s.scores || [];
                      const avg = s.final_score ?? (sc.length ? (sc.reduce((a,b)=>a+b,0)/sc.length).toFixed(1) : null);
                      const pct = avg ? (avg/10)*100 : 0;
                      const barColor = pct>=80?"#00e5c3":pct>=60?"#00b8ff":pct>=40?"#f59e0b":"#ff4f6a";
                      const isChecked = selectedSessionIds.includes(s.session_id);
                      return (
                        <div 
                          className="sess-card" 
                          key={s.session_id || i}
                          style={{
                            display: "flex",
                            gap: 16,
                            alignItems: "stretch",
                            borderColor: isChecked ? "rgba(0, 229, 195, 0.4)" : "rgba(255, 255, 255, 0.07)",
                            background: isChecked ? "rgba(0, 229, 195, 0.03)" : "rgba(12, 18, 35, 0.8)",
                            cursor: selectMode ? "pointer" : "default"
                          }}
                          onClick={() => {
                            if (selectMode) {
                              handleToggleSelectSession(s.session_id);
                            }
                          }}
                        >
                          {selectMode && (
                            <div style={{ display: "flex", alignItems: "center", paddingRight: 4, userSelect: "none" }} onClick={(e) => e.stopPropagation()}>
                              <input 
                                type="checkbox" 
                                checked={isChecked}
                                onChange={() => handleToggleSelectSession(s.session_id)}
                                style={{
                                  width: 18,
                                  height: 18,
                                  accentColor: "#00e5c3",
                                  cursor: "pointer"
                                }}
                              />
                            </div>
                          )}
                          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
                            <div className="sess-top">
                              {s.final_grade && <GradeBadge grade={s.final_grade} />}
                              <div className="sess-info">
                                <div className="sess-date">{s.created_at ? new Date(s.created_at).toLocaleString() : "Unknown date"}</div>
                                <div className="sess-meta">
                                  {s.questions?.length || 0} questions
                                  {avg ? ` · Score ${avg}/10` : ""}
                                </div>
                              </div>
                              {s.active
                                ? <span className="active-badge"><span className="active-dot"/>In Progress</span>
                                : avg && <ScorePill score={parseFloat(avg)} />
                              }
                            </div>

                            {/* Score bar */}
                            {avg && (
                              <div className="score-bar-wrap" style={{marginBottom:12}}>
                                <div style={{fontSize:11,color:"#7a8ba8",minWidth:28}}>0</div>
                                <div className="score-bar-bg">
                                  <div className="score-bar-fill" style={{width:`${pct}%`,background:`linear-gradient(90deg,${barColor},${barColor}99)`}} />
                                </div>
                                <div style={{fontSize:11,color:"#7a8ba8",minWidth:20}}>10</div>
                              </div>
                            )}

                            {/* Per-question mini scores */}
                            {sc.length > 0 && (
                              <div style={{display:"flex",gap:5,flexWrap:"wrap",marginBottom:12}}>
                                {sc.map((score,qi) => {
                                  const c = score>=8?"#00e5c3":score>=6?"#00b8ff":score>=4?"#f59e0b":"#ff4f6a";
                                  return (
                                    <span key={qi} style={{fontSize:11,fontWeight:700,background:`${c}14`,border:`1px solid ${c}33`,borderRadius:8,padding:"2px 8px",color:c}}>
                                      Q{qi+1}: {score}
                                    </span>
                                  );
                                })}
                              </div>
                            )}

                            {/* Action buttons */}
                            {!selectMode && (
                              <div className="sess-actions">
                                <button className="act-btn act-view" onClick={()=>setSelectedSession(s)}>
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                  View Report
                                </button>
                                {!s.active && (
                                  <button className="act-btn act-pdf" onClick={()=>generatePDF(s)}>
                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                                    Download PDF
                                  </button>
                                )}
                                {s.recording_path && (
                                  <a className="act-btn act-pdf" href={`${BACKEND_URL}/recording/${s.session_id}`} download style={{ textDecoration:"none", background:"rgba(124,58,237,0.12)", color:"#a78bfa", border:"1px solid rgba(124,58,237,0.25)" }}>
                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                                    Download Video
                                  </a>
                                )}
                                {s.active && (
                                  <button className="act-btn" style={{background:"rgba(245,158,11,.1)",color:"#f59e0b",border:"1px solid rgba(245,158,11,.25)"}}
                                    onClick={()=>{localStorage.setItem("session_id",s.session_id);navigate("/interview");}}>
                                    ▶ Resume
                                  </button>
                                )}
                                <button className="act-btn" style={{ background:"rgba(255,79,106,0.1)", color:"#ff4f6a", border:"1px solid rgba(255,79,106,0.22)", marginLeft:"auto" }}
                                  onClick={() => handleDeleteSession(s.session_id)}>
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                                  Delete
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Session detail modal */}
      {selectedSession && <SessionModal session={selectedSession} onClose={()=>setSelectedSession(null)} />}
    </>
  );
}
