import { getGradeInfo } from './utils/gradingSystem';
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSubscriptionStatus } from './components/subscription/subscriptionAPI';

// Modular tab components
import DashboardTab from "./components/DashboardTab";
import CodingTab from "./components/CodingTab";
import SpeechTab from "./components/SpeechTab";
import ResumeTab from "./components/ResumeTab";
import AvaTab from "./components/AvaTab";
import InterviewsTab from "./components/InterviewsTab";
import AnalyticsTab from "./components/AnalyticsTab";
import Profile from "./profile";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") ? "http://localhost:5000" : "https://prepfly.up.railway.app");


export default function Dashboard() {
  const navigate = useNavigate();

  // Navigation & panels active states
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const roomParam = params.get("room");
      const tabParam = params.get("tab");
      if (roomParam || tabParam === "coding" || sessionStorage.getItem("coding_room_id")) {
        return "coding";
      }
      return tabParam || sessionStorage.getItem("active_tab") || "dashboard";
    }
    return "dashboard";
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("active_tab", activeTab);
    }
  }, [activeTab]);

  const handleTabChange = (targetTab) => {
    if (activeTab === targetTab) return;
    if (activeTab === 'ava' || activeTab === 'interviews') {
      const ok = window.confirm("Are you sure you want to leave the active interview page? Your progress may be lost.");
      if (!ok) return;
    }
    setActiveTab(targetTab);
  };

  const [showNotif, setShowNotif] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showLinkedIn, setShowLinkedIn] = useState(false);
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [settings, setSettings] = useState({ name: "User", targetRole: "Software Engineer", voiceEnabled: true, detailLevel: "High" });
  const [linkedInUrl, setLinkedInUrl] = useState(localStorage.getItem("linkedin_url") || "");
  const [linkedInSuccess, setLinkedInSuccess] = useState(false);
  const [showPracticeModal, setShowPracticeModal] = useState(false);
  const [practiceQuestion, setPracticeQuestion] = useState(null);
  const [studentAnswer, setStudentAnswer] = useState("");
  const [answerFeedback, setAnswerFeedback] = useState("");
  const [activeAnnouncement, setActiveAnnouncement] = useState(null);

  const notifRef = useRef(null);
  const profileRef = useRef(null);

  // Default notifications list
  const [notifications, setNotifications] = useState([
    { id: 1, title: 'Speech session analyzed', desc: 'Your last mock interview scored 8.2 — 3 filler words detected', time: '2 min ago', type: 'speech', read: false },
    { id: 2, title: 'Resume ATS report ready', desc: 'Score: 75/100 · 4 missing keywords found', time: '18 min ago', type: 'resume', read: false },
    { id: 3, title: 'New coding challenge unlocked', desc: 'LRU Cache · Hard · System Design track', time: '1 hour ago', type: 'coding', read: false },
    { id: 4, title: '🔥 7-day streak maintained!', desc: 'Keep going — you\'re on a roll. 3 more days for a badge.', time: 'Yesterday', type: 'dashboard', read: true },
  ]);

  // Load user from localStorage on mount & redirect if unauthenticated
  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      const token = localStorage.getItem("access_token");
      if (stored && token) {
        const parsed = JSON.parse(stored);
        setUser(parsed);
        setSettings(s => ({ ...s, name: parsed.name || "User" }));
      } else {
        // Unauthenticated direct link access — redirect to login landing page
        navigate("/", { replace: true });
      }
    } catch (e) {
      navigate("/", { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const [history, setHistory] = useState([]);
  const [userStats, setUserStats] = useState(null);
  const [profileInitialSubTab, setProfileInitialSubTab] = useState("info");

  useEffect(() => {
    const targetUserId = user?._id || user?.id || localStorage.getItem("user_id") || user?.email;
    const fetchData = async () => {
      try {
        const histRes = await apiFetch(`/history/me`);
        if (histRes.ok) {
          const histData = await histRes.json();
          setHistory(histData || []);
        } else if (targetUserId) {
          const fbRes = await apiFetch(`/history/${targetUserId}`);
          if (fbRes.ok) {
            const fbData = await fbRes.json();
            setHistory(fbData || []);
          }
        }
      } catch (e) {
        console.error("Failed to fetch user history:", e);
      }

      try {
        const statsRes = await apiFetch(`/user-stats/me`);
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setUserStats(statsData);
        } else if (targetUserId) {
          const fbStatsRes = await apiFetch(`/user-stats/${targetUserId}`);
          if (fbStatsRes.ok) {
            const fbStatsData = await fbStatsRes.json();
            setUserStats(fbStatsData);
          }
        }
      } catch (e) {
        console.error("Failed to fetch user stats:", e);
      }

      try {
        const orgId = user?.organization_id || localStorage.getItem("organization_id") || localStorage.getItem("admin_org_id") || "org_stanford_01";
        const notifRes = await apiFetch(`/notifications?user_id=${targetUserId || 'me'}&org_id=${orgId}`);
        if (notifRes.ok) {
          const notifData = await notifRes.json();
          if (notifData && notifData.length > 0) {
            setNotifications(notifData);
          }
        }
      } catch (e) {
        console.error("Failed to fetch live notifications:", e);
      }
    };
    fetchData();
  }, [user?._id, user?.email, activeTab]);


  // Click outside to close panels
  useEffect(() => {
    const handler = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotif(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setShowProfile(false);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  // Compute dynamic user grade
  const rawAvg = userStats?.interviews?.avg_score ?? (history.length > 0 ? (history.reduce((a, s) => a + (s.final_score || s.overall_score || 7.5), 0) / history.length) : null);
  const score100 = rawAvg !== null ? Math.min(100, Math.max(0, Math.round(Number(rawAvg) * 10))) : null;
  const gradeInfo = score100 !== null ? getGradeInfo(score100) : null;
  const userGrade = gradeInfo ? `Grade ${gradeInfo.grade}` : (userStats?.has_data || history.length > 0 ? "Grade B" : "Newbie");
  const displayStreak = userStats?.streak_days ?? userStats?.streak ?? 0;

  const isLoggedIn = () => {
    return !!localStorage.getItem("access_token") || !!user?._id || !!user?.email || !!user?.name;
  };

  // Core API Fetch wrapper
  const apiFetch = async (endpoint, options = {}) => {
    const token = localStorage.getItem("access_token");
    const headers = {
      ...(options.headers || {})
    };
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    // Normalize endpoint path to match app.py routes (Flask app routes do not have '/api' prefix)
    let urlPath = endpoint;
    if (urlPath.startsWith('/api/')) {
      urlPath = urlPath.replace('/api/', '/');
    }
    
    return fetch(`${BACKEND_URL}${urlPath}`, {
      ...options,
      headers
    });
  };

  const handleLogout = () => {
    localStorage.clear();
    setUser({ name: "Anushka", email: "saxenaanushka9645@gmail.com", avatar: "A", _id: "sa_anushka_01", role: "SUPER_ADMIN" });
    navigate("/");
  };

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const handleNotifClick = (notif) => {
    setNotifications(prev => prev.map(n => n.id === notif.id ? { ...n, read: true } : n));
    setShowNotif(false);

    if (notif.type === "practice_question") {
      try {
        const qData = typeof notif.raw_message === "string" ? JSON.parse(notif.raw_message) : notif.raw_message;
        if (qData.category === "Coding") {
          localStorage.setItem("selected_problem_id", qData.question_id);
          handleTabChange("coding");
        } else {
          setPracticeQuestion(qData);
          setStudentAnswer("");
          setAnswerFeedback("");
          setShowPracticeModal(true);
        }
      } catch (e) {
        console.error("Failed to parse question notification:", e);
      }
    } else if (notif.type === "system" || notif.type === "announcement") {
      setActiveAnnouncement(notif);
    } else if (notif.type) {
      const validTabs = ["dashboard", "coding", "speech", "resume", "ava", "interviews", "analytics", "profile"];
      if (validTabs.includes(notif.type)) {
        handleTabChange(notif.type);
      }
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;
  const [isOrgExpired, setIsOrgExpired] = useState(false);

  useEffect(() => {
    if (user?.role === "SUPER_ADMIN") {
      setIsOrgExpired(false);
      return;
    }
    const orgId = user?.organization_id || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";
    fetchSubscriptionStatus(apiFetch, orgId).then((sub) => {
      if (sub && (sub.is_blocked || sub.subscription_status === 'EXPIRED')) {
        setIsOrgExpired(true);
      } else {
        setIsOrgExpired(false);
      }
    }).catch(() => setIsOrgExpired(false));
  }, [user]);

  return (
    <div style={{ background: "var(--bg)", color: "var(--text)", minHeight: "100vh", fontFamily: "'Cabinet Grotesk', sans-serif" }}>
      
      {/* ── NAVBAR ── */}
      <nav className="nav" role="navigation" aria-label="Main navigation">
        <div className="nav-logo" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <img src="/prepfly-logo.png" alt="PrepFly Logo" style={{ width: "34px", height: "34px", borderRadius: "50%", objectFit: "cover", boxShadow: "0 0 12px rgba(0,196,167,0.4)" }} />
          <span className="logo-name" style={{ fontSize: "19px", fontWeight: 900, letterSpacing: "-0.5px" }}>Prep<span style={{ color: "#00c4a7" }}>Fly</span></span>
        </div>

        <div className="nav-center" role="tablist" aria-label="Page navigation">
          <button className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('dashboard')} disabled={isOrgExpired} role="tab">Dashboard</button>
          <button className={`nav-link ${activeTab === 'coding' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('coding')} disabled={isOrgExpired} role="tab">Coding</button>
          <button className={`nav-link ${activeTab === 'speech' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('speech')} disabled={isOrgExpired} role="tab">Speech AI</button>
          <button className={`nav-link ${activeTab === 'resume' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('resume')} disabled={isOrgExpired} role="tab">Resume AI</button>
          <button className={`nav-link ${activeTab === 'ava' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('ava')} disabled={isOrgExpired} role="tab">AI Interview</button>
          <button className={`nav-link ${activeTab === 'interviews' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('interviews')} disabled={isOrgExpired} role="tab">Interviews</button>
          <button className={`nav-link ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => !isOrgExpired && handleTabChange('analytics')} disabled={isOrgExpired} role="tab">Analytics</button>
        </div>

        <div className="nav-right">
          {!isLoggedIn() && (
            <button 
              id="login-btn" 
              onClick={() => navigate("/")} 
              style={{
                display: "block",
                padding: "6px 14px",
                borderRadius: "9px",
                border: "1px solid rgba(155,109,255,0.3)",
                background: "rgba(155,109,255,0.1)",
                color: "#9b6dff",
                fontFamily: "inherit",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              Sign In
            </button>
          )}

          {isLoggedIn() && (
            <button
              onClick={handleLogout}
              style={{
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid rgba(239,68,68,0.3)",
                background: "rgba(239,68,68,0.1)",
                color: "#ef4444",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              🚪 Logout
            </button>
          )}

          {/* NOTIFICATION BELL */}
          <div style={{ position: "relative" }} ref={notifRef}>
            <button 
              className="notif-btn" 
              id="notif-btn" 
              aria-label="Notifications" 
              title="Notifications" 
              onClick={() => setShowNotif(prev => !prev)}
            >
              <span aria-hidden="true" style={{ fontSize: "15px" }}>🔔</span>
              {unreadCount > 0 && <div className="notif-badge" id="notif-badge" aria-hidden="true">{unreadCount}</div>}
            </button>
            
            {showNotif && (
              <div id="notif-panel" style={{ display: "block", position: "absolute", top: "42px", right: 0, width: "320px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "14px", boxShadow: "0 16px 48px rgba(0,0,0,0.5)", zIndex: 200, overflow: "hidden" }}>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ fontSize: "13px", fontWeight: 800 }}>Notifications</div>
                  <button onClick={markAllRead} style={{ fontSize: "11px", fontWeight: 700, color: "var(--cyan)", background: "none", border: "none", cursor: "pointer" }}>Mark all read</button>
                </div>
                <div id="notif-list" style={{ maxHeight: "320px", overflowY: "auto" }}>
                  {notifications.map(n => {
                    const dotColors = { speech: 'var(--red)', resume: 'var(--orange)', coding: 'var(--cyan)' };
                    const dotColor = dotColors[n.type] || 'transparent';
                    return (
                      <div key={n.id} className={`notif-item ${!n.read ? 'unread' : ''}`} onClick={() => handleNotifClick(n)}>
                        <div className="notif-dot-item" style={{ background: n.read ? 'transparent' : dotColor }}></div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "2px" }}>{n.title}</div>
                          <div style={{ fontSize: "11px", color: "var(--text2)" }}>{n.desc}</div>
                          <div style={{ fontSize: "10px", color: "var(--text3)", marginTop: "3px" }}>{n.time}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ padding: "10px 16px", borderTop: "1px solid rgba(255,255,255,0.07)", textAlign: "center" }}>
                  <button onClick={() => setShowNotif(false)} style={{ fontSize: "11px", color: "var(--text2)", background: "none", border: "none", cursor: "pointer" }}>Close Panel</button>
                </div>
              </div>
            )}
          </div>

          {/* AVATAR / PROFILE */}
          {isLoggedIn() && (
            <div style={{ position: "relative" }} ref={profileRef}>
              <div 
                className="avatar-btn" 
                id="avatar-btn" 
                aria-label="User menu" 
                role="button" 
                tabIndex="0" 
                onClick={(e) => { e.stopPropagation(); handleTabChange('profile'); setShowProfile(prev => !prev); }}
                style={{ overflow: "hidden", cursor: "pointer" }}
              >
                {typeof user.avatar === 'string' && (user.avatar.startsWith('http') || user.avatar.startsWith('data:')) ? (
                  <img src={user.avatar} alt="Avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                ) : (
                  (user.avatar && user.avatar.length <= 3) ? user.avatar : (user.name ? user.name.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0, 2) : "AK")
                )}
              </div>
              
              {showProfile && (
                <div id="profile-panel" style={{ display: "block", position: "absolute", top: "42px", right: 0, width: "230px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "14px", boxShadow: "0 16px 48px rgba(0,0,0,0.5)", zIndex: 200, overflow: "hidden" }}>
                  <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "38px", height: "38px", borderRadius: "50%", background: "linear-gradient(135deg,#7c4fe0,#00c4a7)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: 800, color: "#fff", overflow: "hidden" }}>
                        {typeof user.avatar === 'string' && (user.avatar.startsWith('http') || user.avatar.startsWith('data:')) ? (
                          <img src={user.avatar} alt="Avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                        ) : (
                          (user.avatar && user.avatar.length <= 3) ? user.avatar : (user.name ? user.name.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0, 2) : "AK")
                        )}
                      </div>
                      <div>
                        <div style={{ fontSize: "13px", fontWeight: 800 }}>{user.name || "Anushka Kumari"}</div>
                        <div style={{ fontSize: "11px", color: "var(--text2)" }}>{user.email || "anushka@email.com"}</div>
                      </div>
                    </div>
                    <div style={{ marginTop: "10px", padding: "6px 10px", background: "rgba(0,240,200,0.07)", border: "1px solid rgba(0,240,200,0.15)", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "11px", color: "var(--cyan)", fontWeight: 700 }}>🔥 {displayStreak}-day streak</span>
                      <span style={{ fontSize: "11px", color: "var(--text2)" }}>{userGrade}</span>
                    </div>
                  </div>
                  <div style={{ padding: "6px 8px" }}>
                    <div className="profile-menu-item" onClick={() => { setProfileInitialSubTab('info'); setActiveTab('profile'); setShowProfile(false); }}>👤 My Profile</div>
                    <div className="profile-menu-item" onClick={() => { setProfileInitialSubTab('subscription'); setActiveTab('profile'); setShowProfile(false); }}>👑 Subscription</div>
                    <div className="profile-menu-item" onClick={() => { setProfileInitialSubTab('feedback'); setActiveTab('profile'); setShowProfile(false); }}>💬 Send Feedback</div>
                    <div className="profile-menu-item" onClick={() => { setActiveTab('analytics'); setShowProfile(false); }}>📊 My Progress</div>
                    <div className="profile-menu-item" onClick={() => { setActiveTab('resume'); setShowProfile(false); }}>📄 Resume Reports</div>
                    <div className="profile-menu-item" onClick={() => { setActiveTab('interviews'); setShowProfile(false); }}>🎤 Interview History</div>
                    <div className="profile-menu-item" onClick={() => { setSettings(prev => ({ ...prev, name: user.name })); setShowSettings(true); setShowProfile(false); }}>⚙️ Settings</div>
                    <div className="profile-menu-item" onClick={() => { setShowLinkedIn(true); setShowProfile(false); }}>🔗 Connect LinkedIn</div>
                  </div>
                  <div style={{ padding: "8px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="profile-menu-item" style={{ color: "var(--red)" }} onClick={handleLogout}>🚪 Sign Out</div>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </nav>

      <main style={{ padding: "24px 0" }}>
        {isOrgExpired ? (
          <div style={{ maxWidth: "600px", margin: "60px auto", padding: "40px 24px", background: "linear-gradient(145deg, #0c1220, #1a1020)", border: "1px solid rgba(239,68,68,0.4)", borderRadius: "24px", textAlign: "center", color: "#fff" }}>
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>🔒</div>
            <span className="pill pill-red" style={{ fontSize: "11px", marginBottom: "12px" }}>Access Restricted</span>
            <h2 style={{ fontSize: "22px", fontWeight: 900, marginBottom: "8px", color: "#fff" }}>Organization Subscription Expired</h2>
            <p style={{ fontSize: "14px", color: "var(--text2)", marginBottom: "24px", lineHeight: "1.6" }}>
              Your organization's 10-day trial or annual subscription has expired. AI Interviews, Coding Tests, Reports, and Resume Analysis are currently disabled. Please contact your College / Organization Administrator to renew the subscription.
            </p>
            <button onClick={handleLogout} className="btn btn-ghost" style={{ background: "rgba(255,255,255,0.1)", color: "#fff" }}>
              🚪 Sign Out
            </button>
          </div>
        ) : (
          <>
            {activeTab === "dashboard" && <DashboardTab setActiveTab={setActiveTab} user={user} history={history} userStats={userStats} />}
            {activeTab === "coding" && <CodingTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
            {activeTab === "speech" && <SpeechTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
            {activeTab === "resume" && <ResumeTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
            {activeTab === "ava" && <AvaTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
            {activeTab === "interviews" && <InterviewsTab setActiveTab={setActiveTab} apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
            {activeTab === "analytics" && <AnalyticsTab user={user} history={history} userStats={userStats} />}
            {activeTab === "profile" && <Profile onBackToDashboard={() => setActiveTab("dashboard")} setActiveTab={setActiveTab} apiFetch={apiFetch} initialSubTab={profileInitialSubTab} />}
          </>
        )}
      </main>

      {/* ── MODALS FOR SETTINGS & LINKEDIN ── */}
      {showSettings && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "460px", width: "100%", color: "#fff", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>⚙️ Account & AI Settings</h3>
              <button onClick={() => setShowSettings(false)} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", display: "block", marginBottom: "4px" }}>Display Name</label>
                <input type="text" className="lang-select" style={{ width: "100%", padding: "8px 12px" }} value={settings.name} onChange={(e) => setSettings({ ...settings, name: e.target.value })} />
              </div>
              
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", display: "block", marginBottom: "4px" }}>Target Role</label>
                <input type="text" className="lang-select" style={{ width: "100%", padding: "8px 12px" }} value={settings.targetRole} onChange={(e) => setSettings({ ...settings, targetRole: e.target.value })} />
              </div>

              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", display: "block", marginBottom: "4px" }}>AI Voice Output</label>
                <select className="lang-select" style={{ width: "100%", padding: "8px 12px" }} value={settings.voiceEnabled ? "true" : "false"} onChange={(e) => setSettings({ ...settings, voiceEnabled: e.target.value === "true" })}>
                  <option value="true">Enabled (Audio Feedback Active)</option>
                  <option value="false">Disabled (Text Only)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", display: "block", marginBottom: "4px" }}>AI Feedback Depth</label>
                <select className="lang-select" style={{ width: "100%", padding: "8px 12px" }} value={settings.detailLevel} onChange={(e) => setSettings({ ...settings, detailLevel: e.target.value })}>
                  <option value="High">Comprehensive Analysis (Detailed)</option>
                  <option value="Medium">Standard Feedback (Balanced)</option>
                  <option value="Low">Summary Only (Quick)</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "24px", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowSettings(false)}>Cancel</button>
              <button className="btn btn-primary btn-sm" onClick={() => {
                const updatedName = settings.name.trim() || user.name;
                setUser(prev => ({
                  ...prev,
                  name: updatedName,
                  avatar: updatedName.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0, 2)
                }));
                localStorage.setItem("full_name", updatedName);
                setShowSettings(false);
                alert("Settings updated successfully!");
              }}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {showLinkedIn && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "460px", width: "100%", color: "#fff", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#0a66c2", fontSize: "20px" }}>in</span> Connect LinkedIn Profile
              </h3>
              <button onClick={() => { setShowLinkedIn(false); setLinkedInSuccess(false); }} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>

            {!linkedInSuccess ? (
              <>
                <p style={{ fontSize: "13px", color: "var(--text2)", lineHeight: "1.5", marginBottom: "16px" }}>
                  Connect your LinkedIn account to import candidate experience, auto-generate interview practice scenarios, and sync ATS resume ratings.
                </p>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", display: "block", marginBottom: "4px" }}>LinkedIn Profile URL</label>
                  <input 
                    type="url" 
                    className="lang-select" 
                    style={{ width: "100%", padding: "8px 12px" }} 
                    placeholder="https://linkedin.com/in/yourname" 
                    value={linkedInUrl} 
                    onChange={(e) => setLinkedInUrl(e.target.value)} 
                  />
                </div>
                <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowLinkedIn(false)}>Cancel</button>
                  <button 
                    className="btn btn-cyan btn-sm" 
                    disabled={!linkedInUrl.trim()} 
                    onClick={() => {
                      setLinkedInSuccess(true);
                      localStorage.setItem("linkedin_url", linkedInUrl);
                    }}
                  >
                    ⚡ Sync & Connect
                  </button>
                </div>
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <div style={{ fontSize: "36px", marginBottom: "8px" }}>✅</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--cyan)", marginBottom: "4px" }}>LinkedIn Account Connected!</div>
                <div style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "20px" }}>Profile skills and experience synced for AI practice sessions.</div>
                <button className="btn btn-primary btn-sm" onClick={() => { setShowLinkedIn(false); setLinkedInSuccess(false); }}>Done</button>
              </div>
            )}
          </div>
        </div>
      )}
      {showPracticeModal && practiceQuestion && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "600px", width: "100%", color: "#fff", maxHeight: "90vh", overflowY: "auto", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <span className="pill pill-purple" style={{ fontSize: "10px", marginRight: "6px" }}>{practiceQuestion.category}</span>
                <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{practiceQuestion.difficulty}</span>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: "6px 0 0 0" }}>🎯 Practice: {practiceQuestion.title}</h3>
              </div>
              <button onClick={() => setShowPracticeModal(false)} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", fontSize: "13px" }}>
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", padding: "12px 16px", borderRadius: "10px", lineHeight: "1.5" }}>
                <div style={{ fontWeight: 800, marginBottom: "4px", color: "var(--text2)" }}>Question Prompt</div>
                <div style={{ color: "#fff", whiteSpace: "pre-line" }}>{practiceQuestion.description}</div>
              </div>

              {practiceQuestion.constraints && (
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", padding: "10px 14px", borderRadius: "8px", fontFamily: "monospace", fontSize: "11px", color: "var(--text2)" }}>
                  <strong>Constraints:</strong> {practiceQuestion.constraints}
                </div>
              )}

              <div>
                <label style={{ display: "block", fontWeight: 700, color: "var(--text2)", marginBottom: "6px" }}>Draft Your Answer</label>
                <textarea 
                  rows="5" 
                  value={studentAnswer} 
                  onChange={e => setStudentAnswer(e.target.value)} 
                  placeholder="Type your explanation or structured answer here..." 
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff", lineHeight: "1.5", fontSize: "13px" }} 
                />
              </div>

              {!answerFeedback ? (
                <button 
                  onClick={() => {
                    if (!studentAnswer.trim()) {
                      alert("Please draft your answer first!");
                      return;
                    }
                    setAnswerFeedback("Compare your solution guide above with your drafted response. Pay close attention to key definitions, structure, and communication depth.");
                  }} 
                  className="btn btn-primary" 
                  style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800, padding: "10px 0" }}
                >
                  📝 Submit & Compare with Model Answer
                </button>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "4px" }}>
                  <div style={{ background: "rgba(0, 196, 167, 0.08)", border: "1px solid rgba(0, 196, 167, 0.2)", padding: "12px 14px", borderRadius: "8px", color: "#00e1bf", fontSize: "12px", lineHeight: "1.4" }}>
                    <strong>✅ Draft Submitted!</strong>
                    <div>{answerFeedback}</div>
                  </div>

                  {practiceQuestion.solution && (
                    <div style={{ background: "rgba(124, 79, 224, 0.08)", border: "1px solid rgba(124, 79, 224, 0.2)", padding: "14px", borderRadius: "10px", lineHeight: "1.5" }}>
                      <div style={{ fontWeight: 800, color: "#c0a7ff", marginBottom: "6px" }}>💡 Model Solution / Answer Guide</div>
                      <div style={{ color: "#fff", whiteSpace: "pre-line" }}>{practiceQuestion.solution}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeAnnouncement && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "500px", width: "100%", color: "#fff", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <span>📢</span> Campus Alert / Announcement
              </h3>
              <button onClick={() => setActiveAnnouncement(null)} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ fontSize: "15px", fontWeight: 800, color: "var(--cyan)" }}>{activeAnnouncement.title}</div>
              <div style={{ fontSize: "11px", color: "var(--text3)", display: "flex", justifyContent: "space-between" }}>
                <span>From: {activeAnnouncement.sender || "Platform Admin"}</span>
                <span>Date: {activeAnnouncement.time ? (activeAnnouncement.time.includes("ago") || activeAnnouncement.time.includes("Yesterday") ? activeAnnouncement.time : new Date(activeAnnouncement.time).toLocaleDateString()) : "Recently"}</span>
              </div>
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "16px", fontSize: "13px", lineHeight: "1.6", color: "#e2e8f0", whiteSpace: "pre-wrap" }}>
                {activeAnnouncement.desc}
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
              <button className="btn btn-primary btn-sm" onClick={() => setActiveAnnouncement(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
