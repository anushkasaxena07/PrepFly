import React, { useState, useEffect } from 'react';
import { getAdminReports, generateCustomReport, openStudentDossierPDF } from '../../services/adminAPI';

export default function Reports() {
  const [reportsData, setReportsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Selected reports state for custom report generator
  const [selectedModules, setSelectedModules] = useState([
    'rep_readiness',
    'rep_weak_skills',
    'rep_coding',
    'rep_ai_interview',
    'rep_resume',
    'rep_company',
    'rep_top_performers'
  ]);

  const [exportingFormat, setExportingFormat] = useState(null);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const data = await getAdminReports();
      setReportsData(data);
    } catch (e) {
      console.error("Fetch reports error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleModule = (modId) => {
    if (selectedModules.includes(modId)) {
      setSelectedModules(selectedModules.filter(id => id !== modId));
    } else {
      setSelectedModules([...selectedModules, modId]);
    }
  };

  const handleGenerate = async (format) => {
    if (selectedModules.length === 0) {
      alert("Please select at least one report module to generate.");
      return;
    }
    setExportingFormat(format);
    try {
      if (format === "email") {
        const res = await generateCustomReport(selectedModules, "email");
        alert(res.message || "Executive report emailed successfully!");
      } else {
        await generateCustomReport(selectedModules, format);
      }
    } catch (e) {
      alert("Failed to generate report");
    } finally {
      setExportingFormat(null);
    }
  };

  const filteredStudents = (reportsData?.students || []).filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.roll_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      
      {/* PAGE HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0 }}>📊 Executive Reports & Placement Intelligence</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Actionable candidate performance metrics, skill gap analysis, company target readiness, and multi-format report exports for CS Department.</p>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "50px", textAlign: "center", fontSize: "14px", fontWeight: 700 }}>⚡ Generating institutional placement intelligence...</div>
      ) : (
        <>
          {/* AI ACTIONABLE INSIGHTS BANNER */}
          <div className="card" style={{ background: "linear-gradient(135deg, rgba(12,18,32,0.95), rgba(24,18,48,0.95))", border: "1px solid rgba(124,58,237,0.35)", borderRadius: "16px", padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <span style={{ fontSize: "20px" }}>💡</span>
              <h3 style={{ fontSize: "15px", fontWeight: 900, color: "var(--cyan)", margin: 0, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                AI Placement Intelligence & Actionable Insights
              </h3>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
              {(reportsData?.ai_insights || []).map((insight, idx) => (
                <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", padding: "12px 14px", borderRadius: "10px", fontSize: "12px", color: "#e2e8f0", lineHeight: "1.5" }}>
                  📌 {insight}
                </div>
              ))}
            </div>
          </div>

          {/* KEY PLACEMENT KPI CARDS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            
            {/* OVERALL READINESS */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.25)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--cyan)", textTransform: "uppercase" }}>BATCH PLACEMENT READINESS</div>
              <div style={{ fontSize: "32px", fontWeight: 900, color: "#fff", marginTop: "4px" }}>
                {reportsData?.placement_readiness_pct || 84}%
              </div>
              <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "4px" }}>Cohort Average Placement Index</div>
            </div>

            {/* PLACEMENT PREDICTION */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--purple)", textTransform: "uppercase" }}>PLACEMENT PREDICTION</div>
              <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                <div><span style={{ fontSize: "18px", fontWeight: 900, color: "#00c4a7" }}>{reportsData?.tier_distribution?.ready || 124}</span> <span style={{ fontSize: "10px", color: "var(--text2)" }}>Ready</span></div>
                <div><span style={{ fontSize: "18px", fontWeight: 900, color: "#ffb800" }}>{reportsData?.tier_distribution?.needs_improvement || 65}</span> <span style={{ fontSize: "10px", color: "var(--text2)" }}>Improve</span></div>
                <div><span style={{ fontSize: "18px", fontWeight: 900, color: "#ff4d4f" }}>{reportsData?.tier_distribution?.high_risk || 18}</span> <span style={{ fontSize: "10px", color: "var(--text2)" }}>At Risk</span></div>
              </div>
            </div>

            {/* COMPANY READINESS */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "#ffb800", textTransform: "uppercase" }}>TARGET COMPANY ALIGNMENT</div>
              <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                <div><span style={{ fontSize: "18px", fontWeight: 900, color: "#a855f7" }}>{reportsData?.company_readiness?.maang_product_ready || 32}</span> <span style={{ fontSize: "10px", color: "var(--text2)" }}>MAANG</span></div>
                <div><span style={{ fontSize: "18px", fontWeight: 900, color: "#00c4a7" }}>{reportsData?.company_readiness?.tcs_infosys_service_ready || 410}</span> <span style={{ fontSize: "10px", color: "var(--text2)" }}>Tech Enterprise</span></div>
              </div>
            </div>

            {/* RESUME QUALITY */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "#a855f7", textTransform: "uppercase" }}>RESUME QUALITY DIST.</div>
              <div style={{ display: "flex", gap: "10px", marginTop: "8px", fontSize: "11px" }}>

                <span style={{ color: "#00c4a7", fontWeight: 800 }}>{reportsData?.resume_distribution?.excellent || 60} Exc</span>
                <span style={{ color: "#ffb800", fontWeight: 800 }}>{reportsData?.resume_distribution?.good || 180} Good</span>
                <span style={{ color: "#ff4d4f", fontWeight: 800 }}>{reportsData?.resume_distribution?.needs_improvement || 260} Imp</span>
              </div>
            </div>

          </div>

          {/* WEAK SKILLS & DETAILED SUB-METRICS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
            
            {/* WEAK SUBJECT AREAS */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "14px" }}>⚠️ Primary Concept & Skill Bottlenecks</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {(reportsData?.weak_skills || []).map((sk, idx) => (
                  <div key={idx} style={{ background: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "10px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "6px" }}>
                      <strong style={{ color: "#fff" }}>{sk.subject}</strong>
                      <span style={{ color: sk.fail_rate > 40 ? "#ff4d4f" : "#ffb800", fontWeight: 800 }}>{sk.fail_rate}% Fail Rate ({sk.avg_score}% Avg)</span>
                    </div>
                    <div style={{ height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ width: `${sk.avg_score}%`, height: "100%", background: sk.avg_score < 50 ? "#ff4d4f" : sk.avg_score < 70 ? "#ffb800" : "#00c4a7" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI INTERVIEW & CODING BREAKDOWN */}
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "14px" }}>🎤 AI Interview & Coding Sub-Metrics</h3>
              
              <div style={{ fontSize: "12px", color: "var(--cyan)", fontWeight: 700, marginBottom: "8px" }}>AI INTERVIEW SCORECARD</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.25)", padding: "12px", borderRadius: "10px", fontSize: "11px", marginBottom: "14px" }}>
                <div>Tech: <strong style={{ color: "#00c4a7" }}>{reportsData?.interview_breakdown?.technical}%</strong></div>
                <div>Comm: <strong style={{ color: "#a855f7" }}>{reportsData?.interview_breakdown?.communication}%</strong></div>
                <div>Conf: <strong style={{ color: "#ffb800" }}>{reportsData?.interview_breakdown?.confidence}%</strong></div>
                <div>Grammar: <span style={{ color: "#fff" }}>{reportsData?.interview_breakdown?.grammar}%</span></div>
                <div>Eye Contact: <span style={{ color: "#fff" }}>{reportsData?.interview_breakdown?.eye_contact}%</span></div>
                <div>Voice Clarity: <span style={{ color: "#fff" }}>{reportsData?.interview_breakdown?.voice_clarity}%</span></div>
              </div>

              <div style={{ fontSize: "12px", color: "#ffb800", fontWeight: 700, marginBottom: "8px" }}>CODING DIFFICULTY BREAKDOWN</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.25)", padding: "12px", borderRadius: "10px", fontSize: "11px" }}>
                <div>Easy: <strong style={{ color: "#00c4a7" }}>{reportsData?.coding_breakdown?.easy_pass}%</strong></div>
                <div>Medium: <strong style={{ color: "#ffb800" }}>{reportsData?.coding_breakdown?.medium_pass}%</strong></div>
                <div>Hard: <strong style={{ color: "#ff4d4f" }}>{reportsData?.coding_breakdown?.hard_pass}%</strong></div>
              </div>
            </div>

          </div>

          {/* CANDIDATE PLACEMENT READINESS SCORE MATRIX TABLE */}
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", margin: 0 }}>📋 Student Placement Readiness Score Matrix</h3>
                <p style={{ fontSize: "11px", color: "var(--text2)", margin: "2px 0 0 0" }}>Multi-dimensional candidate ratings across Resume, DSA, Technical, HR, and Coding assessments.</p>
              </div>

              <input 
                type="text" 
                placeholder="🔍 Search student name or roll..." 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "6px 12px", color: "#fff", fontSize: "12px", width: "240px" }}
              />
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--text2)", fontSize: "10px", textTransform: "uppercase" }}>
                    <th style={{ padding: "10px 8px" }}>Candidate</th>
                    <th style={{ padding: "10px 8px" }}>Roll No</th>
                    <th style={{ padding: "10px 8px" }}>Resume</th>
                    <th style={{ padding: "10px 8px" }}>DSA</th>
                    <th style={{ padding: "10px 8px" }}>Technical</th>
                    <th style={{ padding: "10px 8px" }}>HR</th>
                    <th style={{ padding: "10px 8px" }}>Coding</th>
                    <th style={{ padding: "10px 8px" }}>Overall</th>
                    <th style={{ padding: "10px 8px" }}>Status</th>
                    <th style={{ padding: "10px 8px", textAlign: "right" }}>Dossier Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map(st => (
                    <tr key={st.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "10px 8px", fontWeight: 800, color: "#fff" }}>{st.name}</td>
                      <td style={{ padding: "10px 8px", color: "var(--text2)" }}>{st.roll_number}</td>
                      <td style={{ padding: "10px 8px" }}>{st.resume}%</td>
                      <td style={{ padding: "10px 8px" }}>{st.dsa}%</td>
                      <td style={{ padding: "10px 8px" }}>{st.technical}%</td>
                      <td style={{ padding: "10px 8px" }}>{st.hr}%</td>
                      <td style={{ padding: "10px 8px", color: "var(--cyan)", fontWeight: 700 }}>{st.coding}%</td>
                      <td style={{ padding: "10px 8px", fontWeight: 900, color: st.overall >= 78 ? "#00c4a7" : st.overall >= 60 ? "#ffb800" : "#ff4d4f" }}>{st.overall}%</td>
                      <td style={{ padding: "10px 8px" }}>
                        <span className={`pill ${st.status === "Ready" ? "pill-cyan" : st.status === "Needs Improvement" ? "pill-purple" : "pill-pink"}`} style={{ fontSize: "9px" }}>
                          ● {st.status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 8px", textAlign: "right" }}>
                        <button className="btn btn-ghost btn-xs" onClick={() => openStudentDossierPDF(st.id)}>
                          📄 25-Pg Dossier PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* CUSTOM EXECUTIVE REPORT GENERATOR SUITE */}
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "16px", padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "17px", fontWeight: 900, color: "#fff", margin: 0 }}>⚙️ Custom Executive Report Generator Suite</h3>
                <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Select specific analytical modules and export as PDF, Excel, CSV, or direct email to HOD & faculty.</p>
              </div>

              <div style={{ display: "flex", gap: "8px" }}>
                <button 
                  className="btn btn-ghost btn-xs" 
                  onClick={() => setSelectedModules((reportsData?.available_reports || []).map(r => r.id))}
                >
                  Select All
                </button>
                <button 
                  className="btn btn-ghost btn-xs" 
                  onClick={() => setSelectedModules([])}
                >
                  Deselect All
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px", marginBottom: "20px" }}>
              {(reportsData?.available_reports || []).map(rep => {
                const isChecked = selectedModules.includes(rep.id);
                return (
                  <div 
                    key={rep.id} 
                    onClick={() => handleToggleModule(rep.id)}
                    style={{ 
                      background: isChecked ? "rgba(124,58,237,0.15)" : "rgba(255,255,255,0.02)", 
                      border: isChecked ? "1px solid #7c3aed" : "1px solid rgba(255,255,255,0.06)", 
                      borderRadius: "12px", 
                      padding: "14px", 
                      cursor: "pointer",
                      transition: "all 0.2s ease" 
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                      <input 
                        type="checkbox" 
                        checked={isChecked} 
                        onChange={() => {}} 
                        style={{ cursor: "pointer", accentColor: "#7c3aed" }} 
                      />
                      <span style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>{rep.name}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text2)", paddingLeft: "24px", lineHeight: "1.4" }}>
                      {rep.description}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* EXPORT ACTION BUTTONS */}
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end", flexWrap: "wrap", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "16px" }}>
              <button 
                className="btn btn-ghost" 
                onClick={() => handleGenerate("pdf")}
                disabled={exportingFormat === "pdf"}
                style={{ fontWeight: 800 }}
              >
                📄 Generate PDF Audit Report
              </button>

              <button 
                className="btn btn-ghost" 
                onClick={() => handleGenerate("excel")}
                disabled={exportingFormat === "excel"}
                style={{ color: "var(--cyan)", fontWeight: 800 }}
              >
                📊 Generate Excel Report (.xlsx)
              </button>

              <button 
                className="btn btn-primary" 
                onClick={() => handleGenerate("csv")}
                disabled={exportingFormat === "csv"}
                style={{ background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", border: "none", fontWeight: 800 }}
              >
                📈 Download CSV Dataset
              </button>

              <button 
                className="btn btn-ghost" 
                onClick={() => handleGenerate("email")}
                disabled={exportingFormat === "email"}
                style={{ color: "#a855f7", fontWeight: 800 }}
              >
                📧 Email Report to HOD
              </button>
            </div>

          </div>

        </>
      )}
    </div>
  );
}

