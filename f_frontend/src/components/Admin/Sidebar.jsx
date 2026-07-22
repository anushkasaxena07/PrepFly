import React, { useState, useEffect } from 'react';
import { getSupportUnreadCount } from '../../services/supportAPI';

export default function Sidebar({ activeTab, setActiveTab, isCollapsed, setIsCollapsed, organization = {}, isExpired = false }) {
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
    <aside style={{
      width: isCollapsed ? "72px" : "260px",
      minHeight: "100vh",
      background: "#070b14",
      borderRight: "1px solid rgba(255,255,255,0.08)",
      display: "flex",
      flexDirection: "column",
      transition: "width 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
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
            <div style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "16px",
              fontWeight: 900,
              color: "#fff"
            }}>
              🏛
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: "14px", color: "#fff", lineHeight: "1.2", maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {organization?.name || "Organization Admin"}
              </div>
              <div style={{ fontSize: "10px", color: isExpired ? "#f87171" : "var(--cyan)", fontWeight: 700, textTransform: "uppercase" }}>
                {isExpired ? "🔴 TRIAL EXPIRED" : `${organization?.type || "College"} Admin`}
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
                background: isActive ? "linear-gradient(135deg, rgba(124,79,224,0.25), rgba(0,196,167,0.15))" : "transparent",
                border: isActive ? "1px solid rgba(0,240,200,0.3)" : "1px solid transparent",
                color: isDisabled ? "rgba(255,255,255,0.2)" : isActive ? "#fff" : "var(--text2)",
                fontWeight: isActive ? 800 : 600,
                fontSize: "13px",
                cursor: isDisabled ? "not-allowed" : "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
                opacity: isDisabled ? 0.4 : 1
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
