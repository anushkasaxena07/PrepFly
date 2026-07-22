import React from 'react';

export default function Navbar({ activeTab, superAdmin = {} }) {
  const titles = {
    dashboard: 'Platform Executive Overview',
    organizations: 'Global Organizations Directory',
    createorg: 'Create Organization & Admin',
    admins: 'Global Organization Admins',
    students: 'Global Candidate Directory',
    subscriptions: 'SaaS Plan Tiers & Limits',
    payments: 'Global Payments & Revenue',
    qbank: 'Global AI Question Bank',
    aiconfig: 'LLM & Speech AI Configuration',
    analytics: 'SaaS Platform & Growth Analytics',
    activitylogs: 'Platform Security Audit Logs',
    notifications: 'Targeted System Broadcasts',
    support: 'Enterprise Support Queue',
    settings: 'Platform Settings & Governance',
    profile: 'Super Admin Account'
  };

  return (
    <header style={{
      height: "64px",
      background: "rgba(10,14,26,0.85)",
      backdropFilter: "blur(16px)",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      position: "sticky",
      top: 0,
      zIndex: 90
    }}>
      {/* BREADCRUMB */}
      <div>
        <div style={{ fontSize: "11px", color: "#ec4899", textTransform: "uppercase", fontWeight: 800, letterSpacing: "1px" }}>
          Super Admin Console / Platform Owner
        </div>
        <h1 style={{ fontSize: "18px", fontWeight: 900, margin: 0, color: "#fff" }}>
          {titles[activeTab] || 'Platform Owner Console'}
        </h1>
      </div>

      {/* RIGHT HEALTH BADGES */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        
        <div style={{
          background: "rgba(0,240,200,0.1)",
          border: "1px solid rgba(0,240,200,0.25)",
          color: "#00f0c8",
          fontSize: "11px",
          fontWeight: 800,
          padding: "4px 12px",
          borderRadius: "20px",
          display: "flex",
          alignItems: "center",
          gap: "6px"
        }}>
          <span>🟢</span> System Operational (99.99%)
        </div>

        <div style={{
          background: "rgba(236,72,153,0.15)",
          border: "1px solid rgba(236,72,153,0.3)",
          color: "#ec4899",
          fontSize: "11px",
          fontWeight: 900,
          padding: "4px 10px",
          borderRadius: "6px"
        }}>
          SUPER_ADMIN
        </div>

        {/* OWNER AVATAR */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "34px",
            height: "34px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #ec4899, #8b5cf6)",
            color: "#fff",
            fontWeight: 900,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "14px"
          }}>
            {superAdmin?.name ? superAdmin.name[0] : "S"}
          </div>
          <div>
            <div style={{ fontSize: "12px", fontWeight: 800, color: "#fff", lineHeight: "1.2" }}>
              {superAdmin?.name || "Alex Vance"}
            </div>
            <div style={{ fontSize: "10px", color: "var(--text2)" }}>
              {superAdmin?.email || "superadmin@prepfly.io"}
            </div>
          </div>
        </div>

      </div>
    </header>
  );
}
