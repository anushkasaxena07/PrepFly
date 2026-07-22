import React, { useState, useEffect } from 'react';
import AnalyticsChart from '../../components/Admin/AnalyticsChart';
import { getAdminAnalytics } from '../../services/adminAPI';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDept, setSelectedDept] = useState('All');

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await getAdminAnalytics();
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center", fontSize: "14px", fontWeight: 700 }}>⚡ Loading institutional analytics engine...</div>;
  }

  const deptOptions = ["All", ...(data?.departments?.map(d => d.name) || [])];

  const filteredDepts = (data?.departments || []).filter(d => 
    selectedDept === "All" || d.name === selectedDept
  );

  const filteredTopStudents = (data?.top_students || []).filter(s => 
    selectedDept === "All" || s.dept === selectedDept || (selectedDept === "Computer Science" && s.dept.includes("CS"))
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      
      {/* PAGE HEADER & DYNAMIC DEPT FILTER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>📈 Institutional Analytics & Department Trends</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Comparative department performance, placement readiness metrics, and student tiering.</p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "12px", color: "var(--text2)", fontWeight: 700 }}>Filter Dept:</span>
          <select 
            value={selectedDept}
            onChange={e => setSelectedDept(e.target.value)}
            style={{ 
              background: "#141d30", 
              border: "1px solid rgba(255,255,255,0.15)", 
              borderRadius: "8px", 
              padding: "6px 12px", 
              color: "#fff", 
              fontSize: "12px", 
              fontWeight: 700,
              cursor: "pointer"
            }}
          >
            {deptOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
      </div>

      {/* TOP KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--cyan)", fontWeight: 800 }}>PLACEMENT READINESS RATE</div>
          <div style={{ fontSize: "28px", fontWeight: 900, color: "#fff", marginTop: "4px" }}>{data?.placement_readiness ?? 0}%</div>
        </div>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(124,58,237,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#a855f7", fontWeight: 800 }}>INTERVIEW SUCCESS RATE</div>
          <div style={{ fontSize: "28px", fontWeight: 900, color: "#fff", marginTop: "4px" }}>{data?.interview_success_rate ?? 0}%</div>
        </div>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,184,0,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#ffb800", fontWeight: 800 }}>CODING PASS RATE</div>
          <div style={{ fontSize: "28px", fontWeight: 900, color: "#fff", marginTop: "4px" }}>{data?.coding_pass_rate ?? 0}%</div>
        </div>
      </div>

      {/* CHARTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        <AnalyticsChart type="line" title="Monthly Readiness Growth" data={data?.monthly_readiness} />
        <AnalyticsChart type="bar" title="Department Average Scores" data={data?.department_chart_data} />
      </div>


      {/* DEPARTMENT TABLE & TOP STUDENTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        
        {/* DEPARTMENT BREAKDOWN */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: 0 }}>Department Performance Breakdown</h3>
            <span style={{ fontSize: "11px", color: "var(--cyan)", fontWeight: 700 }}>{filteredDepts.length} Depts</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {filteredDepts.map(d => (
              <div key={d.name} style={{ background: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <div>
                    <div style={{ fontWeight: 800, color: "#fff", fontSize: "13px" }}>{d.name}</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)" }}>Avg Interview: <strong style={{ color: "#00c4a7" }}>{d.avg_interview} / 10</strong> | Coding: <strong style={{ color: "#a855f7" }}>{d.avg_coding}%</strong></div>
                  </div>
                  <span className="pill pill-cyan" style={{ fontWeight: 800, fontSize: "11px" }}>{d.readiness}% Ready</span>
                </div>
                <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{ width: `${d.readiness}%`, height: "100%", background: "linear-gradient(90deg, #00c4a7, #7c3aed)" }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* TOP PERFORMING STUDENTS */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: 0 }}>🏆 Top Candidate Performers</h3>
            <span style={{ fontSize: "11px", color: "var(--purple)", fontWeight: 700 }}>Ranked List</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {filteredTopStudents.map((s, idx) => (
              <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", padding: "12px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: idx === 0 ? "rgba(255,184,0,0.2)" : idx === 1 ? "rgba(190,190,190,0.2)" : "rgba(255,255,255,0.08)", color: idx === 0 ? "#ffb800" : idx === 1 ? "#e2e8f0" : "var(--text2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 900 }}>
                    #{idx + 1}
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: "#fff", fontSize: "13px" }}>{s.name}</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)" }}>{s.dept}</div>
                  </div>
                </div>
                <span style={{ fontWeight: 900, color: "#00c4a7", fontSize: "15px" }}>{s.score} / 10</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

