import React from 'react';
import { usePrepFlyTheme } from '../ui/ThemeContext';

export default function Sidebar({ activeTab, setActiveTab, isCollapsed, setIsCollapsed }) {
  const { isSunrise } = usePrepFlyTheme();
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⚡' },
    { id: 'organizations', label: 'Organizations', icon: '🏢' },
    { id: 'admins', label: 'Admins', icon: '👔' },
    { id: 'students', label: 'Students', icon: '🎓' },
    { id: 'subscriptions', label: 'Subscriptions', icon: '👑' },
    { id: 'payments', label: 'Payments', icon: '💳' },
    { id: 'qbank', label: 'Question Bank', icon: '📚' },
    { id: 'aiconfig', label: 'AI Configuration', icon: '🤖' },
    { id: 'analytics', label: 'Analytics', icon: '📈' },
    { id: 'activitylogs', label: 'Activity Logs', icon: '📜' },
    { id: 'notifications', label: 'Notifications', icon: '📢' },
    { id: 'feedback', label: 'Feedback', icon: '💬' },
    { id: 'support', label: 'Support Tickets', icon: '🎧' },
    { id: 'settings', label: 'Platform Settings', icon: '⚙️' },
    { id: 'profile', label: 'Profile', icon: '👤' }
  ];

  const handleLogout = () => {
    localStorage.removeItem("superadmin_access_token");
    localStorage.removeItem("superadmin_user");
    window.location.href = "/superadmin/login";
  };

  return (
    <aside className="pf-portal-sidebar" style={{
      width: isCollapsed ? "74px" : "248px",
      minHeight: "100vh",
      background: isSunrise
        ? "linear-gradient(180deg, #fdf9f6 0%, #faf4ee 100%)"
        : "linear-gradient(180deg, #0b0e1a 0%, #0e1222 100%)",
      borderRight: isSunrise ? "1px solid #efe3da" : "1px solid rgba(255,255,255,0.07)",
      display: "flex",
      flexDirection: "column",
      transition: "width 0.2s ease",
      position: "sticky",
      top: 0,
      zIndex: 100,
      userSelect: "none",
      color: isSunrise ? "#3d322c" : "#e2e8f0"
    }}>
      {/* BRAND & TOGGLE HEADER */}
      <div style={{
        height: "68px",
        padding: "0 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: isCollapsed ? "center" : "space-between",
        borderBottom: isSunrise ? "1px solid #efe3da" : "1px solid rgba(255,255,255,0.06)"
      }}>
        {!isCollapsed && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <img src="/prepfly-logo.png" alt="PrepFly Logo" style={{ width: "32px", height: "32px", borderRadius: "10px", objectFit: "cover", boxShadow: isSunrise ? "0 4px 14px rgba(200,80,29,0.28)" : "0 4px 14px rgba(109,40,217,0.4)" }} />
            <div>
              <div style={{ fontWeight: 800, fontSize: "14px", color: isSunrise ? "#1f1916" : "#fff", lineHeight: "1.2" }}>
                PrepFly Console
              </div>
              <div style={{ fontSize: "10px", color: isSunrise ? "#c8501d" : "#a78bfa", fontWeight: 700, textTransform: "uppercase" }}>
                Super Admin
              </div>
            </div>
          </div>
        )}

        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: isSunrise ? "#ffffff" : "rgba(255,255,255,0.05)",
            border: isSunrise ? "1px solid #e4d2c4" : "1px solid rgba(255,255,255,0.1)",
            borderRadius: "6px",
            color: isSunrise ? "#5d4e45" : "var(--text2)",
            padding: "4px 8px",
            cursor: "pointer",
            fontSize: "12px"
          }}
        >
          {isCollapsed ? "▶" : "◀"}
        </button>
      </div>

      {/* NAVIGATION ITEMS */}
      <div style={{ flex: 1, padding: "12px 8px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
        {menuItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                width: "100%",
                padding: isCollapsed ? "10px 0" : "9px 14px",
                justifyContent: isCollapsed ? "center" : "flex-start",
                borderRadius: "10px",
                background: isActive
                  ? (isSunrise ? "#fce3d4" : "linear-gradient(90deg, rgba(109,40,217,0.44) 0%, rgba(79,70,229,0.20) 100%)")
                  : "transparent",
                border: isActive
                  ? (isSunrise ? "1px solid #f5cbb2" : "1px solid rgba(167,139,250,0.34)")
                  : "1px solid transparent",
                color: isActive ? (isSunrise ? "#b84718" : "#ffffff") : (isSunrise ? "#4c3f37" : "#94a3b8"),
                fontWeight: isActive ? 700 : 600,
                fontSize: "13px",
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "left"
              }}
              title={isCollapsed ? item.label : ""}
            >
              <span style={{ fontSize: "15px" }}>{item.icon}</span>
              {!isCollapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </div>

      {/* LOGOUT FOOTER */}
      <div style={{ padding: "12px 8px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <button
          onClick={handleLogout}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            width: "100%",
            padding: isCollapsed ? "10px 0" : "10px 14px",
            justifyContent: isCollapsed ? "center" : "flex-start",
            borderRadius: "10px",
            background: "rgba(255,84,114,0.08)",
            border: "1px solid rgba(255,84,114,0.2)",
            color: "#ff5472",
            fontWeight: 800,
            fontSize: "13px",
            cursor: "pointer"
          }}
        >
          <span style={{ fontSize: "16px" }}>🚪</span>
          {!isCollapsed && <span>Exit Owner Portal</span>}
        </button>
      </div>
    </aside>
  );
}
