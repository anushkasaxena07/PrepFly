import React, { useState, useEffect, useRef } from 'react';
import { ThemeToggleButton, usePrepFlyTheme } from '../ui/ThemeContext';

export default function Navbar({ activeTab, setActiveTab, superAdmin = {} }) {
  const { isSunrise } = usePrepFlyTheme();
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
    <header className="pf-portal-header" style={{
      height: "82px",
      background: isSunrise
        ? "linear-gradient(135deg, #fdf7f3 0%, #faf0e8 100%)"
        : "linear-gradient(135deg, #090c1a 0%, #121633 100%)",
      borderBottom: isSunrise ? "1px solid #efe3da" : "1px solid rgba(255,255,255,0.08)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 28px 14px",
      position: "sticky",
      top: 0,
      zIndex: 90,
      color: isSunrise ? "#1f1916" : "#ffffff"
    }}>
      {/* BREADCRUMB */}
      <div>
        <div className="pf-portal-header-sub" style={{ fontSize: "11px", color: isSunrise ? "#c8501d" : "#a78bfa", textTransform: "uppercase", fontWeight: 800, letterSpacing: "1px" }}>
          Super Admin Console / Platform Owner
        </div>
        <h1 style={{ fontSize: "20px", fontWeight: 800, margin: 0, color: isSunrise ? "#1f1916" : "#fff", fontFamily: isSunrise ? "'Playfair Display', Georgia, serif" : "inherit" }}>
          {titles[activeTab] || 'Platform Owner Console'}
        </h1>
      </div>

      {/* RIGHT HEALTH BADGES */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <ThemeToggleButton />

        <div style={{
          background: isSunrise ? "#ecfdf5" : "rgba(16,185,129,0.16)",
          border: isSunrise ? "1px solid #a7f3d0" : "1px solid rgba(52,211,153,0.35)",
          color: isSunrise ? "#047857" : "#34d399",
          fontSize: "11px",
          fontWeight: 800,
          padding: "5px 12px",
          borderRadius: "20px",
          display: "flex",
          alignItems: "center",
          gap: "6px"
        }}>
          <span>System Operational (99.99%)</span>
        </div>

        <div style={{
          background: isSunrise ? "#fdf0e7" : "rgba(124,58,237,0.22)",
          border: isSunrise ? "1px solid #f5cbb2" : "1px solid rgba(167,139,250,0.4)",
          color: isSunrise ? "#b84718" : "#c4b5fd",
          fontSize: "11px",
          fontWeight: 800,
          padding: "5px 10px",
          borderRadius: "8px"
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
