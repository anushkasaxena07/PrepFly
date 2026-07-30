import React, { useState, useEffect, useRef } from 'react';

export default function Navbar({ activeTab, setActiveTab, superAdmin = {} }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, title: "New Organization Onboarded", desc: "IIT Bombay registered with 500 Candidate seats", time: "15 min ago", unread: true },
    { id: 2, title: "SaaS Plan Upgrade", desc: "Stanford University upgraded to Enterprise Plan", time: "2 hours ago", unread: true },
    { id: 3, title: "System Audit Alert", desc: "All 12 AI Voice synthesis nodes operating smoothly", time: "5 hours ago", unread: false }
  ]);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter(n => n.unread).length;

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
  };

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

        {/* NOTIFICATION BELL WITH DROPDOWN */}
        <div ref={dropdownRef} style={{ position: "relative" }}>
          <div 
            onClick={() => setShowNotifications(!showNotifications)}
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "50%",
              background: showNotifications ? "rgba(236,72,153,0.2)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${showNotifications ? "#ec4899" : "rgba(255,255,255,0.1)"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              cursor: "pointer",
              position: "relative",
              transition: "all 0.2s ease"
            }}
            title="System Broadcasts & Notifications"
          >
            🔔
            {unreadCount > 0 && (
              <span style={{
                position: "absolute",
                top: "-2px",
                right: "-2px",
                background: "#ec4899",
                color: "#fff",
                borderRadius: "50%",
                width: "16px",
                height: "16px",
                fontSize: "10px",
                fontWeight: 900,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "2px solid #0a0e1a"
              }}>
                {unreadCount}
              </span>
            )}
          </div>

          {/* DROPDOWN POPOVER PANEL */}
          {showNotifications && (
            <div style={{
              position: "absolute",
              top: "48px",
              right: 0,
              width: "340px",
              background: "#0c1220",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "16px",
              boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
              padding: "16px",
              zIndex: 1000
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "10px" }}>
                <h4 style={{ margin: 0, color: "#fff", fontSize: "14px", fontWeight: 800, display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>📢</span> Platform Notifications ({unreadCount})
                </h4>
                {unreadCount > 0 && (
                  <button 
                    onClick={markAllRead}
                    style={{ background: "none", border: "none", color: "#ec4899", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "280px", overflowY: "auto" }}>
                {notifications.map(n => (
                  <div 
                    key={n.id} 
                    onClick={() => {
                      setShowNotifications(false);
                      if (setActiveTab) setActiveTab('notifications');
                    }}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "10px",
                      background: n.unread ? "rgba(236, 72, 153, 0.12)" : "rgba(255,255,255,0.03)",
                      border: `1px solid ${n.unread ? "rgba(236, 72, 153, 0.3)" : "rgba(255,255,255,0.05)"}`,
                      cursor: "pointer"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ color: "#fff", fontWeight: 800, fontSize: "12px" }}>{n.title}</div>
                      <div style={{ color: "var(--text2)", fontSize: "10px" }}>{n.time}</div>
                    </div>
                    <div style={{ color: "var(--text2)", fontSize: "11px", marginTop: "4px" }}>
                      {n.desc}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid rgba(255,255,255,0.08)", textAlign: "center" }}>
                <button
                  onClick={() => {
                    setShowNotifications(false);
                    if (setActiveTab) setActiveTab('notifications');
                  }}
                  style={{
                    background: "rgba(236,72,153,0.15)",
                    border: "1px solid rgba(236,72,153,0.4)",
                    color: "#ec4899",
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "6px 12px",
                    borderRadius: "8px",
                    cursor: "pointer",
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px"
                  }}
                >
                  📢 Open System Notifications & Broadcast Center →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* OWNER AVATAR */}
        <div 
          onClick={() => setActiveTab && setActiveTab('profile')}
          style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }}
        >
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
