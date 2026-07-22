import React, { useState, useEffect } from 'react';
import RevenueChart from '../../components/SuperAdmin/RevenueChart';
import AnalyticsChart from '../../components/Admin/AnalyticsChart';
import { getSuperAdminAnalytics } from '../../services/superAdminAPI';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await getSuperAdminAnalytics();
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ color: "#ec4899", padding: "40px", textAlign: "center" }}>⚡ Loading platform analytics...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>📈 Platform SaaS Analytics & AI Call Metrics</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Institutional growth, revenue expansion, LLM API call consumption, and peak hours.</p>
      </div>

      {/* TOP KPI CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 700 }}>PLATFORM GROWTH</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "var(--cyan)", marginTop: "4px" }}>{data?.platform_growth || "+34% YoY"}</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 700 }}>REVENUE GROWTH</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>{data?.revenue_growth || "+42% YoY"}</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#a78bfa", fontWeight: 700 }}>GEMINI API CALLS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>{data?.ai_api_usage?.gemini_calls ?? 330}</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(56,189,248,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700 }}>OPENAI API CALLS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#38bdf8", marginTop: "4px" }}>{data?.ai_api_usage?.openai_calls ?? 120}</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700 }}>LLM TOKENS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>{data?.ai_api_usage?.total_tokens_millions ?? 4.85}M</div>
        </div>
      </div>

      {/* CHARTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        <RevenueChart title="Platform Revenue Trend" data={data?.revenue_trend} />
        <AnalyticsChart type="line" title="Active Students & DAU Growth" data={data?.activity_trend} />
      </div>

      {/* TOP ORGANIZATIONS BREAKDOWN TABLE */}
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
          <span>🏆</span> Top Active Client Organizations
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", color: "#f0f4fd" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "#94a3b8", textAlign: "left" }}>
                <th style={{ padding: "10px" }}>Organization Name</th>
                <th style={{ padding: "10px" }}>Active Candidates</th>
                <th style={{ padding: "10px" }}>AI Mock Sessions</th>
                <th style={{ padding: "10px" }}>Placement Status</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_organizations || []).map((org, i) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>{org.name}</td>
                  <td style={{ padding: "12px 10px", color: "var(--cyan)", fontWeight: 700 }}>{org.students} Candidates</td>
                  <td style={{ padding: "12px 10px", color: "#a78bfa", fontWeight: 700 }}>{org.interviews} Sessions</td>
                  <td style={{ padding: "12px 10px" }}>
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: "rgba(16,185,129,0.15)", color: "#10b981", fontWeight: 800 }}>
                      ● Active Enterprise
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
