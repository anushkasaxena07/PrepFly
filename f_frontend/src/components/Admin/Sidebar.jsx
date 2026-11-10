import React, { useState, useEffect } from 'react';
import { getSupportUnreadCount } from '../../services/supportAPI';
import { usePrepFlyTheme } from '../ui/ThemeContext';

export default function Sidebar({ activeTab, setActiveTab, isCollapsed, setIsCollapsed, organization = {}, isExpired = false }) {
  const { isSunrise } = usePrepFlyTheme();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnread = async () => {
    const cnt = await getSupportUnreadCount(false);
    setUnreadCount(cnt);
  };

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'students', label: 'Students', icon: '🎓' },
    { id: 'interviews', label: 'AI Interviews', icon: '🎤' },
    { id: 'coding', label: 'Coding Tests', icon: '💻' },
    { id: 'qbank', label: 'Question Bank', icon: '📚' },
    { id: 'reports', label: 'Reports', icon: '📄' },
    { id: 'analytics', label: 'Analytics', icon: '📈' },
    { id: 'announcements', label: 'Announcements', icon: '📢' },
    { id: 'support', label: 'Support Chat', icon: '💬', badge: unreadCount },
    { id: 'organization', label: 'Organization Profile', icon: '🏢' },
    { id: 'subscription', label: 'Subscription', icon: '👑' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  const handleLogout = () => {
    localStorage.removeItem("admin_access_token");
    localStorage.removeItem("admin_org_id");
    localStorage.removeItem("admin_user");
    window.location.href = "/admin/login";
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
      transition: "width 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
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
            <div style={{
              width: "32px",
              height: "32px",
              borderRadius: "10px",
              background: isSunrise ? "linear-gradient(135deg, #ea580c, #fb923c)" : "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "15px",
              fontWeight: 800,
              color: "#fff",
              boxShadow: isSunrise ? "0 4px 14px rgba(200,80,29,0.28)" : "0 4px 14px rgba(109,40,217,0.35)"
            }}>
              🏛
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: "14px", color: isSunrise ? "#1f1916" : "#fff", lineHeight: "1.2", maxWidth: "145px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {organization?.name || "PrepFly Admin"}
              </div>
              <div style={{ fontSize: "10px", color: isExpired ? "#dc2626" : (isSunrise ? "#c8501d" : "#a78bfa"), fontWeight: 700, textTransform: "uppercase" }}>
                {isExpired ? "TRIAL EXPIRED" : `${organization?.type || "College"} Portal`}
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
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? "▶" : "◀"}
        </button>
      </div>

      {/* NAVIGATION ITEMS */}
      <div style={{ flex: 1, padding: "12px 8px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
        {menuItems.map((item) => {
          const isActive = activeTab === item.id;
          const isDisabled = isExpired && item.id !== 'subscription';

          return (
            <button
              key={item.id}
              onClick={() => !isDisabled && setActiveTab(item.id)}
              disabled={isDisabled}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                width: "100%",
                padding: isCollapsed ? "10px 0" : "10px 14px",
                justifyContent: isCollapsed ? "center" : "flex-start",
                borderRadius: "10px",
                background: isActive
                  ? (isSunrise ? "#fce3d4" : "linear-gradient(90deg, rgba(109,40,217,0.44) 0%, rgba(79,70,229,0.20) 100%)")
                  : "transparent",
                border: isActive
                  ? (isSunrise ? "1px solid #f5cbb2" : "1px solid rgba(167,139,250,0.34)")
                  : "1px solid transparent",
                color: isDisabled
                  ? (isSunrise ? "#c4b5a9" : "rgba(255,255,255,0.25)")
                  : isActive
                    ? (isSunrise ? "#b84718" : "#ffffff")
                    : (isSunrise ? "#4c3f37" : "#94a3b8"),
                fontWeight: isActive ? 700 : 600,
                fontSize: "13px",
                cursor: isDisabled ? "not-allowed" : "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
                opacity: isDisabled ? 0.45 : 1
              }}
              title={isDisabled ? "Subscription Expired - Locked" : isCollapsed ? item.label : ""}
            >
              <span style={{ fontSize: "16px" }}>{item.icon}</span>
              {!isCollapsed && <span>{item.label}</span>}
              {!isCollapsed && item.badge > 0 && (
                <span style={{ marginLeft: 'auto', background: '#ec4899', color: '#fff', fontSize: '10px', fontWeight: 900, borderRadius: '10px', padding: '2px 6px' }}>
                  {item.badge}
                </span>
              )}
              {!isCollapsed && isDisabled && <span style={{ fontSize: "10px", marginLeft: "auto" }}>🔒</span>}
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
          title={isCollapsed ? "Logout" : ""}
        >
          <span style={{ fontSize: "16px" }}>🚪</span>
          {!isCollapsed && <span>Logout Admin</span>}
        </button>
      </div>
    </aside>
  );
}
