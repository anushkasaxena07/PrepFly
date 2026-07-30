import React, { useState, useEffect, useRef } from 'react';
import { getAdminAnnouncements } from '../../services/adminAPI';

export default function Navbar({ activeTab, setActiveTab, admin = {}, organization = {} }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, title: "AI Interview Completed", desc: "Ananya Patel completed SDE Mock Interview (Score: 9.2/10)", time: "10 min ago", unread: true },
    { id: 2, title: "Subscription Status", desc: "Your organization is currently on a 10-Day Free Trial", time: "1 hour ago", unread: true },
    { id: 3, title: "Coding Submission", desc: "Aarav Sharma submitted DSA & Algorithms Challenge", time: "3 hours ago", unread: true },
    { id: 4, title: "Announcement Published", desc: "Placement readiness drive broadcasted to Computer Science dept", time: "1 day ago", unread: false }
  ]);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const fetchLiveNotifs = async () => {
      try {
        const liveData = await getAdminAnnouncements();
        const list = Array.isArray(liveData) ? liveData : (liveData?.announcements || liveData?.data || []);
        if (list && list.length > 0) {
          const mapped = list.map((item, idx) => ({
            id: item.id || idx + 10,
            title: item.title,
            desc: item.message,
            time: item.created_at || "Recently",
            unread: true
          }));
          setNotifications(prev => [...mapped, ...prev]);
        }
      } catch (e) {
        /* silent */
      }
    };
    fetchLiveNotifs();
  }, []);

  const titles = {
    dashboard: 'Dashboard Overview',
    students: 'Student Roster & Directory',
    interviews: 'AI Technical Interview Management',
    coding: 'Coding Tests & Assessments',
    qbank: 'Central Question Bank',
    reports: 'Executive Reports & Downloads',
    analytics: 'Institutional Performance Analytics',
    announcements: 'Announcements & Notifications',
    organization: 'Organization Profile',
    subscription: 'Subscription & Billing',
    settings: 'Admin Account Settings'
  };

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

  const handleLogout = () => {
    localStorage.removeItem("admin_access_token");
    localStorage.removeItem("admin_org_id");
    localStorage.removeItem("admin_user");
    window.location.href = "/admin/login";
  };

  return (
    <header style={{
      height: "64px",
      background: "rgba(12,18,32,0.85)",
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
      {/* LEFT: SECTION BREADCRUMB */}
      <div>
        <div style={{ fontSize: "11px", color: "var(--text2)", textTransform: "uppercase", fontWeight: 700, letterSpacing: "1px" }}>
          {organization?.name || "Organization"} / Admin
        </div>
        <h1 style={{ fontSize: "18px", fontWeight: 900, margin: 0, color: "#fff" }}>
          {titles[activeTab] || 'Admin Console'}
        </h1>
      </div>

      {/* RIGHT: METRICS BADGES & PROFILE */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        
        {/* MULTI-TENANT BADGE */}
        <div style={{
          background: "rgba(0,240,200,0.1)",
          border: "1px solid rgba(0,240,200,0.25)",
          color: "#00f0c8",
          fontSize: "11px",
          fontWeight: 800,
          padding: "4px 10px",
          borderRadius: "20px",
          display: "flex",
          alignItems: "center",
          gap: "6px"
        }}>
          <span>🔒</span> Multi-Tenant Encrypted
        </div>

        {/* NOTIFICATION BELL WITH DROPDOWN */}
        <div ref={dropdownRef} style={{ position: "relative" }}>
          <div 
            onClick={() => setShowNotifications(!showNotifications)}
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "50%",
              background: showNotifications ? "rgba(0,196,167,0.2)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${showNotifications ? "#00c4a7" : "rgba(255,255,255,0.1)"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              cursor: "pointer",
              position: "relative",
              transition: "all 0.2s ease"
            }}
          >
            🔔
            {unreadCount > 0 && (
              <span style={{
                position: "absolute",
                top: "-2px",
                right: "-2px",
                background: "#ef4444",
                color: "#fff",
                borderRadius: "50%",
                width: "16px",
                height: "16px",
                fontSize: "10px",
                fontWeight: 900,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "2px solid #0c1220"
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
                  <span>🔔</span> Admin Notifications ({unreadCount})
                </h4>
                {unreadCount > 0 && (
                  <button 
                    onClick={markAllRead}
                    style={{ background: "none", border: "none", color: "var(--cyan)", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
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
                      if (setActiveTab) setActiveTab('announcements');
                    }}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "10px",
                      background: n.unread ? "rgba(124, 79, 224, 0.12)" : "rgba(255,255,255,0.03)",
                      border: `1px solid ${n.unread ? "rgba(124, 79, 224, 0.3)" : "rgba(255,255,255,0.05)"}`,
                      cursor: "pointer",
                      transition: "transform 0.15s ease"
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
                    if (setActiveTab) setActiveTab('announcements');
                  }}
                  style={{
                    background: "rgba(0,240,200,0.1)",
                    border: "1px solid rgba(0,240,200,0.3)",
                    color: "#00f0c8",
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
                  📢 Open Announcements & Notifications Page →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ADMIN USER PILL */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          padding: "4px 12px 4px 6px",
          borderRadius: "24px"
        }}>
          <div style={{
            width: "30px",
            height: "30px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
            color: "#fff",
            fontWeight: 800,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "13px"
          }}>
            {admin?.name ? admin.name[0] : "A"}
          </div>
          <div>
            <div style={{ fontSize: "12px", fontWeight: 800, color: "#fff", lineHeight: "1.2" }}>
              {admin?.name || "Admin User"}
            </div>
            <div style={{ fontSize: "10px", color: "var(--text2)" }}>
              {admin?.email || "admin@org.com"}
            </div>
          </div>
        </div>

        {/* HEADER LOGOUT BUTTON */}
        <button
          onClick={handleLogout}
          style={{
            background: "rgba(255, 84, 114, 0.12)",
            border: "1px solid rgba(255, 84, 114, 0.3)",
            color: "#ff5472",
            fontSize: "12px",
            fontWeight: 800,
            padding: "6px 14px",
            borderRadius: "20px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            cursor: "pointer",
            transition: "all 0.2s ease"
          }}
          title="Sign out of Admin Console"
        >
          <span>🚪</span> Logout
        </button>

      </div>
    </header>
  );
}
