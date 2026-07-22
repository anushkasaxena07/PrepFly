import React from 'react';

export default function Sidebar({ activeTab, setActiveTab, isCollapsed, setIsCollapsed }) {
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
    <aside style={{
      width: isCollapsed ? "72px" : "260px",
      minHeight: "100vh",
      background: "#050811",
      borderRight: "1px solid rgba(255,255,255,0.08)",
      display: "flex",
      flexDirection: "column",
      transition: "width 0.2s ease",
      position: "sticky",
      top: 0,
      zIndex: 100,
      userSelect: "none"
    }}>
      {/* BRAND & TOGGLE HEADER */}
      <div style={{
        height: "64px",
        padding: "0 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: isCollapsed ? "center" : "space-between",
        borderBottom: "1px solid rgba(255,255,255,0.06)"
      }}>
        {!isCollapsed && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <img src="/prepfly-logo.png" alt="PrepFly Logo" style={{ width: "32px", height: "32px", borderRadius: "50%", objectFit: "cover", boxShadow: "0 0 10px rgba(236,72,153,0.5)" }} />
            <div>
              <div style={{ fontWeight: 900, fontSize: "14px", color: "#fff", lineHeight: "1.2" }}>
                PrepFly Console
              </div>
              <div style={{ fontSize: "10px", color: "#ec4899", fontWeight: 800, textTransform: "uppercase" }}>
                Super Admin
              </div>
            </div>
          </div>
        )}

        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "6px",
            color: "var(--text2)",
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
                background: isActive ? "linear-gradient(135deg, rgba(236,72,153,0.25), rgba(139,92,246,0.2))" : "transparent",
                border: isActive ? "1px solid rgba(236,72,153,0.4)" : "1px solid transparent",
                color: isActive ? "#fff" : "var(--text2)",
                fontWeight: isActive ? 800 : 600,
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
