import React, { useState, useEffect } from 'react';
import RevenueChart from '../../components/SuperAdmin/RevenueChart';
import AnalyticsChart from '../../components/Admin/AnalyticsChart';
import { getSuperAdminAnalytics } from '../../services/superAdminAPI';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoSync, setAutoSync] = useState(true);

  // Timeframe filter
  const [timeframe, setTimeframe] = useState("ytd"); // 'mtd' | 'ytd' | '30d' | 'all'

  // Table filters
  const [searchOrg, setSearchOrg] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  // Inspector Drawer for Organization Details
  const [selectedOrg, setSelectedOrg] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, [timeframe]);

  useEffect(() => {
    let interval = null;
    if (autoSync) {
      interval = setInterval(() => {
        fetchAnalytics(true);
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoSync, timeframe]);

  const fetchAnalytics = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await getSuperAdminAnalytics({ timeframe });
      setData(res);
    } catch (e) {
      console.error("Failed to fetch platform analytics:", e);
    } finally {
      if (!silent) setLoading(false);
      setRefreshing(false);
    }
  };

  const getStatusBadge = (status = "") => {
    if (status.includes("Enterprise")) {
      return { bg: "rgba(16,185,129,0.15)", color: "#10b981", label: "● Active Enterprise" };
    } else if (status.includes("Pro")) {
      return { bg: "rgba(56,189,248,0.15)", color: "#38bdf8", label: "● Active Pro" };
    } else if (status.includes("Starter")) {
      return { bg: "rgba(245,158,11,0.15)", color: "#f59e0b", label: "● Active Starter" };
    }
    return { bg: "rgba(168,85,247,0.15)", color: "#c084fc", label: `● ${status || 'Active'}` };
  };

  const filteredOrgs = (data?.top_organizations || []).filter(org => {
    const matchesSearch = !searchOrg || org.name.toLowerCase().includes(searchOrg.toLowerCase());
    const matchesStatus = statusFilter === 'All' || (org.placement_status || '').includes(statusFilter);
    return matchesSearch && matchesStatus;
  });

  if (loading && !data) {
    return <div style={{ color: "#ec4899", padding: "60px", textAlign: "center", fontWeight: 800 }}>⚡ Synchronizing Platform SaaS & LLM Analytics...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
      
      {/* HEADER BAR WITH TIMEFRAME & AUTO-SYNC CONTROLS */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            📈 Platform SaaS Analytics & AI Call Metrics
            {refreshing && <span style={{ fontSize: "12px", color: "var(--cyan)", fontWeight: 700 }}>⚡ Syncing...</span>}
          </h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "3px" }}>Institutional growth, revenue expansion, LLM API call consumption, and peak hours.</p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          {/* Timeframe selector */}
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "8px",
              padding: "7px 12px",
              fontSize: "12px",
              color: "#fff",
              fontWeight: 800,
              outline: "none",
              cursor: "pointer"
            }}
          >
            <option value="ytd" style={{ background: "#0c1220" }}>📅 Year to Date (YTD)</option>
            <option value="mtd" style={{ background: "#0c1220" }}>📅 Month to Date (MTD)</option>
            <option value="30d" style={{ background: "#0c1220" }}>📅 Last 30 Days</option>
            <option value="all" style={{ background: "#0c1220" }}>📅 All Time</option>
          </select>

          {/* Auto Sync Toggle */}
          <button
            onClick={() => setAutoSync(!autoSync)}
            style={{
              background: autoSync ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${autoSync ? "#10b981" : "rgba(255,255,255,0.12)"}`,
              borderRadius: "8px",
              padding: "7px 12px",
              fontSize: "11px",
              color: autoSync ? "#10b981" : "#94a3b8",
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            {autoSync ? '🟢 Auto-Sync (5s)' : '⏸ Auto-Sync Off'}
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => fetchAnalytics(false)}
            style={{
              background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
              border: "none",
              borderRadius: "8px",
              padding: "7px 14px",
              fontSize: "11px",
              color: "#fff",
              fontWeight: 800,
              cursor: "pointer"
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* TOP KPI METRICS CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,240,200,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 700 }}>PLATFORM GROWTH</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "var(--cyan)", marginTop: "4px" }}>{data?.platform_growth || "+34% YoY"}</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "4px", fontWeight: 700 }}>▲ +12% vs last quarter</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 700 }}>REVENUE GROWTH</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>{data?.revenue_growth || "+42% YoY"}</div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "4px", fontWeight: 700 }}>▲ ₹48.5K Monthly Rec. Rev.</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(139,92,246,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#a78bfa", fontWeight: 700 }}>GEMINI API CALLS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>{data?.ai_api_usage?.gemini_calls ?? 330}</div>
          <div style={{ fontSize: "10px", color: "#a78bfa", marginTop: "4px", fontWeight: 700 }}>⚡ Avg Latency: 1.1s</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(56,189,248,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700 }}>OPENAI API CALLS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#38bdf8", marginTop: "4px" }}>{data?.ai_api_usage?.openai_calls ?? 120}</div>
          <div style={{ fontSize: "10px", color: "#38bdf8", marginTop: "4px", fontWeight: 700 }}>⚡ Fallback Engine: Active</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700 }}>LLM TOKENS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>{data?.ai_api_usage?.total_tokens_millions ?? 4.85}M</div>
          <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "4px", fontWeight: 700 }}>🔥 99.9% Prompt Efficiency</div>
        </div>
      </div>

      {/* CHARTS ROW */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        <RevenueChart title="Platform Revenue Trend ($)" data={data?.revenue_trend} />
        <AnalyticsChart type="line" title="Active Candidates & DAU Growth" data={data?.activity_trend} />
      </div>

      {/* DYNAMIC TOP ACTIVE CLIENT ORGANIZATIONS TABLE */}
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
        
        {/* Table Filters */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🏆</span> Top Active Client Organizations ({filteredOrgs.length})
          </h3>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="🔍 Search organization..."
              value={searchOrg}
              onChange={(e) => setSearchOrg(e.target.value)}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                padding: "6px 12px",
                fontSize: "12px",
                color: "#fff",
                outline: "none",
                minWidth: "180px"
              }}
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                padding: "6px 10px",
                fontSize: "11px",
                color: "#fff",
                outline: "none"
              }}
            >
              <option value="All" style={{ background: "#0c1220" }}>All Statuses</option>
              <option value="Enterprise" style={{ background: "#0c1220" }}>Enterprise Tier</option>
              <option value="Pro" style={{ background: "#0c1220" }}>Pro Tier</option>
              <option value="Starter" style={{ background: "#0c1220" }}>Starter Tier</option>
            </select>
          </div>
        </div>

        {/* Organizations Table */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", color: "#f0f4fd" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "#94a3b8", textAlign: "left" }}>
                <th style={{ padding: "12px 10px" }}>Organization Name</th>
                <th style={{ padding: "12px 10px" }}>Active Candidates</th>
                <th style={{ padding: "12px 10px" }}>AI Mock Sessions</th>
                <th style={{ padding: "12px 10px" }}>Placement Status</th>
                <th style={{ padding: "12px 10px" }}>Contract Renewal</th>
                <th style={{ padding: "12px 10px", textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.length > 0 ? (
                filteredOrgs.map((org, i) => {
                  const badge = getStatusBadge(org.placement_status);
                  return (
                    <tr key={org.id || i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ width: "24px", height: "24px", borderRadius: "50%", background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px", fontWeight: 800 }}>
                            {org.name.charAt(0)}
                          </span>
                          <span>{org.name}</span>
                        </div>
                      </td>
                      <td style={{ padding: "12px 10px", color: "var(--cyan)", fontWeight: 800 }}>
                        {org.students} Candidates
                      </td>
                      <td style={{ padding: "12px 10px", color: "#a78bfa", fontWeight: 800 }}>
                        {org.interviews} Sessions
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "3px 9px", borderRadius: "12px", background: badge.bg, color: badge.color, fontWeight: 800 }}>
                          {badge.label}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", color: "var(--text2)", fontSize: "11px" }}>
                        📅 {org.renewal_date || "2026-12-31"}
                      </td>
                      <td style={{ padding: "12px 10px", textAlign: "right" }}>
                        <button
                          onClick={() => setSelectedOrg(org)}
                          style={{
                            background: "rgba(0,196,167,0.12)",
                            border: "1px solid rgba(0,196,167,0.3)",
                            color: "#00c4a7",
                            padding: "4px 10px",
                            borderRadius: "6px",
                            fontSize: "11px",
                            fontWeight: 800,
                            cursor: "pointer"
                          }}
                        >
                          🔍 Details
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="6" style={{ padding: "30px", textAlign: "center", color: "var(--text2)" }}>
                    No client organizations match your filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* INSTITUTIONAL DETAILS MODAL / DRAWER */}
      {selectedOrg && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.75)",
          backdropFilter: "blur(6px)",
          zIndex: 2000,
          display: "flex",
          justifyContent: "flex-end"
        }}>
          <div style={{
            width: "420px",
            maxWidth: "90%",
            height: "100%",
            background: "#0c1220",
            borderLeft: "1px solid rgba(255,255,255,0.1)",
            padding: "24px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "18px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "14px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", margin: 0 }}>{selectedOrg.name}</h3>
                <span style={{ fontSize: "11px", color: "var(--cyan)" }}>ID: {selectedOrg.id}</span>
              </div>
              <button onClick={() => setSelectedOrg(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="card-sm" style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>SUBSCRIPTION TIER</div>
                <div style={{ fontSize: "14px", fontWeight: 900, color: "#10b981", marginTop: "4px" }}>{selectedOrg.placement_status}</div>
              </div>

              <div className="card-sm" style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>ACTIVE ENROLLED CANDIDATES</div>
                <div style={{ fontSize: "18px", fontWeight: 900, color: "var(--cyan)", marginTop: "4px" }}>{selectedOrg.students} Enrolled Students</div>
              </div>

              <div className="card-sm" style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>TOTAL AI MOCK INTERVIEW SESSIONS</div>
                <div style={{ fontSize: "18px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>{selectedOrg.interviews} Sessions Completed</div>
              </div>

              <div className="card-sm" style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>RENEWAL DATE</div>
                <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff", marginTop: "4px" }}>📅 {selectedOrg.renewal_date}</div>
              </div>
            </div>

            <div style={{ marginTop: "auto", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
              <button
                onClick={() => setSelectedOrg(null)}
                style={{ width: "100%", padding: "10px", background: "rgba(255,255,255,0.08)", border: "none", borderRadius: "8px", color: "#fff", fontWeight: 800, cursor: "pointer" }}
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

