import React, { useState, useEffect } from 'react';
import DashboardCard from '../../components/Admin/DashboardCard';
import AnalyticsChart from '../../components/Admin/AnalyticsChart';
import { getAdminDashboardStats } from '../../services/adminAPI';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [autoSync, setAutoSync] = useState(true);

  useEffect(() => {
    fetchStats();
    let interval;
    if (autoSync) {
      interval = setInterval(() => {
        fetchStats(true);
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoSync]);

  const fetchStats = async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    else setIsRefreshing(true);
    try {
      const data = await getAdminDashboardStats();
      setStats(data);
    } catch (e) {
      console.error("Fetch admin stats error:", e);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  if (loading) {
    return <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading Organization Dashboard metrics...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      
      {/* HEADER & CONTROLS */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0 }}>
            🏛️ Organization Executive Command Center
          </h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>
            Real-time candidate telemetry, placement assessment stats, and institutional usage analytics.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => setAutoSync(!autoSync)}
            style={{
              background: autoSync ? "rgba(0,196,167,0.15)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${autoSync ? "#00c4a7" : "rgba(255,255,255,0.1)"}`,
              color: autoSync ? "#00c4a7" : "#94a3b8",
              padding: "6px 12px",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: 800,
              cursor: "pointer"
            }}
          >
            {autoSync ? "🟢 Live Sync (5s)" : "⏸️ Sync Paused"}
          </button>

          <button
            onClick={() => fetchStats(false)}
            disabled={isRefreshing}
            style={{
              background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
              border: "none",
              color: "#fff",
              padding: "6px 14px",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: 900,
              cursor: "pointer",
              opacity: isRefreshing ? 0.6 : 1
            }}
          >
            {isRefreshing ? "⚡ Syncing..." : "🔄 Refresh"}
          </button>
        </div>
      </div>

      {/* SECTION 1: STATS CARDS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <DashboardCard title="Total Students" value={stats?.total_students ?? 0} subtext="Enrolled Candidates" icon="🎓" trend="+14% this month" color="#00c4a7" />
        <DashboardCard title="Active Students" value={stats?.active_students ?? 0} subtext="Platform Active" icon="⚡" trend="+8% active" color="#7c4fe0" />
        <DashboardCard title="Premium Students" value={stats?.premium_students ?? 0} subtext="Subscribed Plan" icon="👑" trend="35% conversion" color="#ffb800" />
        <DashboardCard title="AI Interviews" value={stats?.ai_interviews_conducted ?? 0} subtext="Conducted Sessions" icon="🎤" trend="+24% YoY" color="#3b82f6" />
        <DashboardCard title="Coding Tests" value={stats?.coding_tests_completed ?? 0} subtext="Completed Solutions" icon="💻" trend="+18% YoY" color="#ec4899" />
        <DashboardCard title="Avg Interview Score" value={`${stats?.avg_interview_score ?? 0.0} / 10`} subtext="Institutional Average" icon="📊" trend="Grade A" color="#00f0c8" />
        <DashboardCard title="Avg Coding Score" value={`${stats?.avg_coding_score ?? 0.0}%`} subtext="Algorithmic Average" icon="🏆" trend="86th Percentile" color="#a855f7" />
        <DashboardCard title="Reports Generated" value={stats?.total_reports_generated ?? 0} subtext="Executive Digests" icon="📄" trend="100% Dynamic" color="#f59e0b" />

      </div>

      {/* SECTION 2: CHARTS ROW */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        <AnalyticsChart type="line" title="Monthly Interview & Coding Activity" data={stats?.monthly_activity} />
        <AnalyticsChart type="bar" title="Department Placement Assessment Rates" data={stats?.department_chart_data || stats?.monthly_activity} />
      </div>

      {/* SECTION 3: RECENT ACTIVITIES & RECENT STUDENTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
        
        {/* RECENT ACTIVITIES */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🕒</span> Recent Institutional Activities
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {stats?.recent_activities?.map((act) => (
              <div key={act.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.03)", padding: "12px 14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>{act.title}</div>
                  <div style={{ fontSize: "11px", color: "var(--text2)" }}>{act.time}</div>
                </div>
                <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{act.type}</span>
              </div>
            ))}
          </div>
        </div>

        {/* SYSTEM STATUS & STORAGE */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>💾</span> Storage & Organization Status
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "6px" }}>
                <span style={{ color: "var(--text2)" }}>Cloud Storage Used</span>
                <span style={{ color: "#fff", fontWeight: 800 }}>{stats?.storage_used_mb ?? 420} MB / {stats?.storage_total_gb ?? 10} GB</span>
              </div>
              <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.08)", borderRadius: "4px", overflow: "hidden" }}>
                <div style={{ width: `${Math.min(100, Math.max(2, stats?.storage_pct ?? 12))}%`, height: "100%", background: "linear-gradient(90deg, #00c4a7, #7c3aed)", borderRadius: "4px" }} />
              </div>
            </div>

            <div style={{ background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "10px", padding: "12px", fontSize: "12px", color: "#fff" }}>
              <div style={{ fontWeight: 800, color: "var(--cyan)", marginBottom: "2px" }}>Subscription Plan</div>
              <div>{stats?.subscription_status || "Active (ENTERPRISE PLAN)"}</div>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text2)" }}>
              <span>Recent Admin Login: </span>
              <strong style={{ color: "#fff" }}>{stats?.recent_login || "Active Session"}</strong>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
