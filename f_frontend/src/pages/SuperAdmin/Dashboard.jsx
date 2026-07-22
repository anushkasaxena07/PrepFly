import React, { useState, useEffect } from 'react';
import StatsCard from '../../components/SuperAdmin/StatsCard';
import RevenueChart from '../../components/SuperAdmin/RevenueChart';
import AnalyticsChart from '../../components/Admin/AnalyticsChart';
import { getSuperAdminDashboardStats } from '../../services/superAdminAPI';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const data = await getSuperAdminDashboardStats();
      setStats(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ color: "#ec4899", padding: "40px", textAlign: "center" }}>👑 Loading Super Admin Executive Metrics...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      
      {/* SECTION 1: STATS CARDS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
        <StatsCard title="Total Organizations" value={stats?.total_organizations ?? 0} subtext="Colleges & Companies" icon="🏢" trend="+12%" color="#ec4899" />
        <StatsCard title="Total Colleges" value={stats?.total_colleges ?? 0} subtext="Academic Institutions" icon="🏛" trend="+8%" color="#8b5cf6" />
        <StatsCard title="Total Companies" value={stats?.total_companies ?? 0} subtext="Corporate Recruiters" icon="💼" trend="+20%" color="#3b82f6" />
        <StatsCard title="Total Admins" value={stats?.total_admins ?? 0} subtext="Org Administrators" icon="👔" trend="+15%" color="#00c4a7" />
        <StatsCard title="Total Students" value={stats?.total_students ?? 0} subtext="Global Candidates" icon="🎓" trend="+24%" color="#00f0c8" />
        <StatsCard title="Active Students" value={stats?.active_students ?? 0} subtext="DAU/MAU Active" icon="⚡" trend="90% Active" color="#ffb800" />
        <StatsCard title="Premium Users" value={stats?.premium_users ?? 0} subtext="Paid Subscribers" icon="👑" trend="34% Convert" color="#f59e0b" />
        <StatsCard title="Today's Revenue" value={stats?.today_revenue ?? "$0.00"} subtext="Live Gross Revenue" icon="💵" trend="+32%" color="#10b981" />
        <StatsCard title="Monthly Revenue" value={stats?.monthly_revenue ?? "$0.00"} subtext="MRR Growth" icon="📈" trend="+42% YoY" color="#ec4899" />
        <StatsCard title="Yearly Revenue" value={stats?.yearly_revenue ?? "$0.00"} subtext="ARR Projected" icon="🏆" trend="ARR Milestone" color="#8b5cf6" />
        <StatsCard title="AI Interviews" value={stats?.total_interviews ?? 0} subtext="Conducted Platform-wide" icon="🎤" trend="+30%" color="#3b82f6" />
        <StatsCard title="Coding Tests" value={stats?.total_coding_tests ?? 0} subtext="Submissions Evaluated" icon="💻" trend="+28%" color="#a855f7" />
        <StatsCard title="AI API Calls" value={stats?.total_ai_api_calls ?? 0} subtext="Gemini & Whisper Calls" icon="🤖" trend="0 Calls" color="#00c4a7" />
        <StatsCard title="Storage Used" value={stats?.storage_used_gb ?? "1 GB"} subtext="PostgreSQL & Cloud Storage" icon="💾" trend="Dynamic" color="#64748b" />

      </div>

      {/* SECTION 2: REVENUE & GROWTH CHARTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        <RevenueChart title="Platform Monthly Revenue Growth ($)" data={stats?.revenue_trend} />
        <AnalyticsChart type="bar" title="Colleges vs Companies Performance" data={stats?.colleges_companies_trend || stats?.revenue_trend} />
      </div>

      {/* SECTION 3: SYSTEM HEALTH & RECENT ORGANIZATIONS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
        
        {/* RECENT ORGANIZATIONS */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🏢</span> Latest Organization Onboardings
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {stats?.recent_organizations?.map(org => (
              <div key={org.id} style={{ background: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 800, color: "#fff" }}>{org.name}</div>
                  <div style={{ fontSize: "11px", color: "var(--text2)" }}>{org.email} • {org.type}</div>
                </div>
                <span className="pill pill-purple" style={{ fontSize: "10px" }}>{org.subscription_plan || "ENTERPRISE"}</span>
              </div>
            ))}
          </div>
        </div>

        {/* PLATFORM HEALTH & AI STATUS */}
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>⚡</span> Real-time Platform Health & AI Services
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "10px", padding: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#00f0c8" }}>Flask Backend & Server</div>
                <div style={{ fontSize: "11px", color: "var(--text2)" }}>{stats?.system_health?.server_status}</div>
              </div>
              <span style={{ fontSize: "18px" }}>🟢</span>
            </div>

            <div style={{ background: "rgba(139,92,246,0.08)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: "10px", padding: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#a855f7" }}>Database Connection</div>
                <div style={{ fontSize: "11px", color: "var(--text2)" }}>{stats?.system_health?.database_status}</div>
              </div>
              <span style={{ fontSize: "18px" }}>🟢</span>
            </div>

            <div style={{ background: "rgba(236,72,153,0.08)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "10px", padding: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#ec4899" }}>AI API Connection</div>
                <div style={{ fontSize: "11px", color: "var(--text2)" }}>{stats?.system_health?.api_status}</div>
              </div>
              <span style={{ fontSize: "18px" }}>🟢</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
