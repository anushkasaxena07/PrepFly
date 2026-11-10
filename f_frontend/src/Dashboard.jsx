import { getGradeInfo } from './utils/gradingSystem';
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSubscriptionStatus } from './components/subscription/subscriptionAPI';
import { PrepFlyMark, NavIcon, CosmicHero } from './components/ui/PrepFlyTheme';
import { ThemeToggleButton, usePrepFlyTheme } from './components/ui/ThemeContext';

import DashboardTab from "./components/DashboardTab";
import CodingTab from "./components/CodingTab";
import SpeechTab from "./components/SpeechTab";
import ResumeTab from "./components/ResumeTab";
import AvaTab from "./components/AvaTab";
import InterviewsTab from "./components/InterviewsTab";
import Profile from "./profile";
import RoadmapTab from "./components/Intelligence/RoadmapTab";
import ProgressDashboard from "./components/Intelligence/ProgressDashboard";
import JobPreparationTab from "./components/Intelligence/JobPreparationTab";
import AchievementsTab from "./components/Intelligence/AchievementsTab";
import "./components/Intelligence/intelligence.css";

const BACKEND_URL = (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"))
  ? "http://localhost:5000"
  : (import.meta.env.VITE_BACKEND_URL || "http://localhost:5000");

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "roadmap", label: "Prep Roadmap", icon: "roadmap" },
  { id: "coding", label: "Coding", icon: "coding" },
  { id: "speech", label: "Speech AI", icon: "speech" },
  { id: "resume", label: "Resume AI", icon: "resume" },
  { id: "ava", label: "AI Interview", icon: "ava" },
  { id: "achievements", label: "Achievements", icon: "achievements" },
  { id: "interviews", label: "Interviews", icon: "interviews" },
  { id: "analytics", label: "Analytics", icon: "analytics" },
  { id: "jobs", label: "Job Prep", icon: "jobs" },
];

const TAB_HERO_META = {
  dashboard: {
    badge: "Preparation Workspace",
    titleWhite: "Welcome back,",
    titleAccentKey: "firstName",
    subtitle: "Review your interview readiness, resume strength, coding momentum, and next high-impact practice steps.",
  },
  roadmap: {
    badge: "Adaptive Curriculum",
    titleWhite: "Prep",
    titleAccent: "Roadmap",
    subtitle: "Personalized daily study blocks and prioritized skill milestones synced directly from your real practice evidence.",
  },
  coding: {
    badge: "Technical Practice",
    titleWhite: "Coding",
    titleAccent: "Playground",
    subtitle: "Solve curated algorithmic challenges with runtime complexity analysis, hints, and automated evaluation.",
  },
  speech: {
    badge: "Delivery Telemetry",
    titleWhite: "Speech",
    titleAccent: "& Pace AI",
    subtitle: "Measure speaking pace (WPM), clarity, filler words, and vocal confidence in real time.",
  },
  resume: {
    badge: "ATS Intelligence",
    titleWhite: "Resume",
    titleAccent: "Scanner & ATS",
    subtitle: "Analyze keyword alignment, section impact, and structured experience evidence against target job roles.",
  },
  ava: {
    badge: "Live Voice & Rubric Engine",
    titleWhite: "AI Mock",
    titleAccent: "Interview",
    subtitle: "Interactive technical & behavioral interviews with verbatim quote verification, live timing telemetry, and deterministic scoring.",
  },
  interviews: {
    badge: "Session Archive",
    titleWhite: "Interview",
    titleAccent: "History & Reports",
    subtitle: "Inspect past mock interview sessions, dimension breakdowns, evidence citations, and downloadable reports.",
  },
  analytics: {
    badge: "Readiness Telemetry",
    titleWhite: "Progress",
    titleAccent: "& Analytics",
    subtitle: "Track longitudinal skill mastery, mock performance trends, and verifiable evidence progression.",
  },
  jobs: {
    badge: "Role Alignment",
    titleWhite: "Job Prep",
    titleAccent: "Intelligence",
    subtitle: "Paste a target job description to extract core requirements, score skill gaps, and launch targeted mock drills.",
  },
  profile: {
    badge: "Account & Plan",
    titleWhite: "Profile",
    titleAccent: "& Settings",
    subtitle: "Manage your candidate details, subscription plan, billing invoices, and workspace preferences.",
  },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { isSunrise } = usePrepFlyTheme();

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

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showQuickSearch, setShowQuickSearch] = useState(false);
  const [quickQuery, setQuickQuery] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("active_tab", activeTab);
    }
  }, [activeTab]);

  const handleTabChange = (targetTab) => {
    setMobileMenuOpen(false);
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

  const [notifications, setNotifications] = useState(() => {
    try {
      const cached = localStorage.getItem("prepfly_cached_notifications");
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      const token = localStorage.getItem("access_token");
      if (stored && token) {
        const parsed = JSON.parse(stored);
        setUser(parsed);
        setSettings(s => ({ ...s, name: parsed.name || "User" }));
      } else {
        navigate("/", { replace: true });
      }
    } catch {
      navigate("/", { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [history, setHistory] = useState(() => {
    try {
      const cached = localStorage.getItem("prepfly_cached_history");
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });

  const [userStats, setUserStats] = useState(() => {
    try {
      const cached = localStorage.getItem("prepfly_cached_stats");
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });

  const [profileInitialSubTab, setProfileInitialSubTab] = useState("info");

  const apiFetch = async (endpoint, options = {}) => {
    const token = localStorage.getItem("access_token");
    const headers = { ...(options.headers || {}) };
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    let urlPath = endpoint;
    if (urlPath.startsWith('/api/')) {
      urlPath = urlPath.replace('/api/', '/');
    }
    return fetch(`${BACKEND_URL}${urlPath}`, { ...options, headers });
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const targetUserId = user?._id || user?.id || localStorage.getItem("user_id") || user?.email;
    const fetchData = async () => {
      try {
        const histRes = await apiFetch(`/history/me`);
        if (histRes.ok) {
          const histData = await histRes.json();
          setHistory(histData || []);
          if (histData && histData.length > 0) {
            localStorage.setItem("prepfly_cached_history", JSON.stringify(histData));
          }
        } else if (targetUserId) {
          const fbRes = await apiFetch(`/history/${targetUserId}`);
          if (fbRes.ok) {
            const fbData = await fbRes.json();
            setHistory(fbData || []);
            if (fbData && fbData.length > 0) {
              localStorage.setItem("prepfly_cached_history", JSON.stringify(fbData));
            }
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
          if (statsData) {
            localStorage.setItem("prepfly_cached_stats", JSON.stringify(statsData));
          }
        } else if (targetUserId) {
          const fbStatsRes = await apiFetch(`/user-stats/${targetUserId}`);
          if (fbStatsRes.ok) {
            const fbStatsData = await fbStatsRes.json();
            setUserStats(fbStatsData);
            if (fbStatsData) {
              localStorage.setItem("prepfly_cached_stats", JSON.stringify(fbStatsData));
            }
          }
        }
      } catch (e) {
        console.error("Failed to fetch user stats:", e);
      }
    };
    fetchData();
  }, [user?._id, user?.email, activeTab]);

  const fetchLiveNotifications = useCallback(async () => {
    if (typeof document !== "undefined" && document.hidden) return;
    try {
      const targetUserId = user?._id || user?.id || localStorage.getItem("user_id") || user?.email;
      const orgId = user?.organization_id || localStorage.getItem("organization_id") || localStorage.getItem("admin_org_id") || "global";
      const notifRes = await apiFetch(`/notifications?user_id=${targetUserId || 'me'}&org_id=${orgId}`);
      if (notifRes.ok) {
        const notifData = await notifRes.json();
        const list = Array.isArray(notifData) ? notifData : (notifData?.notifications || []);
        setNotifications(list);
        localStorage.setItem("prepfly_cached_notifications", JSON.stringify(list));
      }
    } catch (e) {
      console.error("Failed to fetch live notifications:", e);
    }
  }, [user]);

  useEffect(() => {
    fetchLiveNotifications();
    const timer = setInterval(fetchLiveNotifications, 30000);
    const handleVisibility = () => {
      if (!document.hidden) fetchLiveNotifications();
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [fetchLiveNotifications]);

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

  const hasCompletedInterviews = (userStats?.interviews?.total ?? 0) > 0 || history.length > 0;
  const rawAvg = hasCompletedInterviews
    ? (userStats?.interviews?.avg_score ?? (history.length > 0 ? (history.reduce((a, s) => a + (s.final_score || s.overall_score || 7.5), 0) / history.length) : null))
    : null;
  const score100 = rawAvg !== null ? Math.min(100, Math.max(0, Math.round(Number(rawAvg) * 10))) : null;
  const gradeInfo = score100 !== null ? getGradeInfo(score100) : null;
  const userGrade = gradeInfo ? `Grade ${gradeInfo.grade}` : "Starter";
  const displayStreak = userStats?.streak_days ?? userStats?.streak ?? 0;

  const isLoggedIn = () => {
    return !!localStorage.getItem("access_token") || !!user?._id || !!user?.email || !!user?.name;
  };

  const handleLogout = () => {
    localStorage.clear();
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
      const validTabs = ["dashboard", "coding", "speech", "resume", "ava", "interviews", "analytics", "profile", "achievements", "roadmap", "jobs"];
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

  const safeUser = user || {};
  const firstName = (safeUser.name || "Anushka").split(" ")[0];
  const initials = (safeUser.avatar && safeUser.avatar.length <= 3)
    ? safeUser.avatar
    : (safeUser.name ? safeUser.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2) : "AS");

  const heroMeta = TAB_HERO_META[activeTab] || TAB_HERO_META.dashboard;
  const heroTitleAccent = heroMeta.titleAccentKey === "firstName" ? firstName : heroMeta.titleAccent;

  const topRightControls = (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", position: "relative" }}>
      <ThemeToggleButton />

      <button
        type="button"
        className="pf-icon-btn"
        title="Quick Jump"
        aria-label="Quick search navigation"
        onClick={() => { setQuickQuery(""); setShowQuickSearch((prev) => !prev); }}
      >
        <NavIcon name="search" size={16} />
      </button>

      {/* Notifications Dropdown */}
      <div style={{ position: "relative" }} ref={notifRef}>
        <button
          className="pf-icon-btn"
          id="notif-btn"
          aria-label="Notifications"
          title="Notifications"
          onClick={() => {
            setShowNotif((prev) => {
              const next = !prev;
              if (next) fetchLiveNotifications();
              return next;
            });
          }}
        >
          <NavIcon name="announcements" size={16} />
          {unreadCount > 0 && <div className="notif-badge" id="notif-badge">{unreadCount}</div>}
        </button>

        {showNotif && (
          <div
            id="notif-panel"
            style={{
              position: "absolute",
              top: "44px",
              right: 0,
              width: "320px",
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "16px",
              boxShadow: "0 20px 50px rgba(15, 23, 42, 0.22)",
              zIndex: 250,
              overflow: "hidden",
              color: "#0f172a",
            }}
          >
            <div style={{ padding: "14px 16px", borderBottom: "1px solid #e5e8f2", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ fontSize: "13px", fontWeight: 800 }}>Notifications</div>
              <button onClick={markAllRead} style={{ fontSize: "11px", fontWeight: 700, color: "#6d28d9", background: "none", border: "none", cursor: "pointer" }}>
                Mark all read
              </button>
            </div>
            <div style={{ maxHeight: "320px", overflowY: "auto" }}>
              {notifications.length === 0 ? (
                <div style={{ padding: "24px", textAlign: "center", fontSize: "12px", color: "#64748b" }}>No notifications yet.</div>
              ) : notifications.map((n) => {
                const dotColors = { speech: "#dc2626", resume: "#d97706", coding: "#6d28d9" };
                const dotColor = dotColors[n.type] || "#7c3aed";
                return (
                  <div key={n.id} className={`notif-item ${!n.read ? "unread" : ""}`} onClick={() => handleNotifClick(n)}>
                    <div className="notif-dot-item" style={{ background: n.read ? "transparent" : dotColor }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "2px", color: "#0f172a" }}>{n.title}</div>
                      <div style={{ fontSize: "11px", color: "#475569" }}>{n.desc}</div>
                      <div style={{ fontSize: "10px", color: "#64748b", marginTop: "3px" }}>{n.time}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div style={{ padding: "10px 16px", borderTop: "1px solid #e5e8f2", textAlign: "center" }}>
              <button onClick={() => setShowNotif(false)} style={{ fontSize: "11px", color: "#64748b", background: "none", border: "none", cursor: "pointer" }}>
                Close Panel
              </button>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        className="pf-upgrade-pill"
        onClick={() => { setProfileInitialSubTab("subscription"); setActiveTab("profile"); }}
      >
        <NavIcon name="subscription" size={14} color="#fcd34d" />
        <span>Upgrade Pro</span>
      </button>

      {!isLoggedIn() && (
        <button id="login-btn" onClick={() => navigate("/")} className="btn btn-primary btn-sm">
          Sign In
        </button>
      )}
    </div>
  );

  return (
    <div className="pf-shell">
      {/* ── LEFT OBSIDIAN SIDEBAR ── */}
      <aside className={`pf-sidebar ${mobileMenuOpen ? "mobile-open" : ""}`} aria-label="Main navigation">
        <div className="pf-sidebar-head">
          <div
            className="pf-sidebar-brand"
            style={{ cursor: "pointer" }}
            onClick={() => handleTabChange("dashboard")}
          >
            <PrepFlyMark size={32} />
            <span className="pf-brand-text">PrepFly</span>
          </div>
          {mobileMenuOpen && (
            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "18px", cursor: "pointer" }}
            >
              ✕
            </button>
          )}
        </div>

        <nav className="pf-sidebar-nav" role="tablist" aria-label="Workspace sections">
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                disabled={isOrgExpired}
                onClick={() => !isOrgExpired && handleTabChange(item.id)}
                className={`pf-nav-item ${isActive ? "active" : ""}`}
              >
                <NavIcon name={item.icon} size={16} strokeWidth={isActive ? 2.1 : 1.75} color="currentColor" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="pf-sidebar-promo">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
            <div>
              <div className="pf-promo-title">Keep going!</div>
              <div className="pf-promo-sub">
                {displayStreak > 0 ? `${displayStreak}-day streak active` : "You're doing great."}
              </div>
            </div>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="pf-promo-icon" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              <polyline points="17 6 23 6 23 12" />
            </svg>
          </div>
          <button
            type="button"
            className="pf-sidebar-promo-btn"
            onClick={() => handleTabChange("analytics")}
          >
            View Progress →
          </button>
        </div>

        <div className="pf-sidebar-footer" ref={profileRef} style={{ position: "relative" }}>
          <button
            type="button"
            className="pf-user-trigger"
            id="avatar-btn"
            onClick={(e) => { e.stopPropagation(); setShowProfile((prev) => !prev); }}
          >
            <div className="avatar-btn" style={{ width: "32px", height: "32px", flexShrink: 0, overflow: "hidden" }}>
              {typeof safeUser.avatar === "string" && (safeUser.avatar.startsWith("http") || safeUser.avatar.startsWith("data:")) ? (
                <img src={safeUser.avatar} alt="Avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
              ) : (
                initials
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
              <div className="pf-user-name">
                {isSunrise ? (safeUser.name || firstName) : firstName}
              </div>
              <div className="pf-user-sub">{isSunrise && userGrade === "Starter" ? "Free Plan" : userGrade}</div>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="pf-user-chev" strokeWidth="2.2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {showProfile && isLoggedIn() && (
            <div
              id="profile-panel"
              style={{
                position: "absolute",
                bottom: "64px",
                left: "12px",
                right: "12px",
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "14px",
                boxShadow: "0 20px 50px rgba(15, 23, 42, 0.28)",
                zIndex: 250,
                overflow: "hidden",
                color: "#0f172a",
              }}
            >
              <div style={{ padding: "12px 14px", borderBottom: "1px solid #e5e8f2" }}>
                <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>{safeUser.name || "Anushka"}</div>
                <div style={{ fontSize: "11px", color: "#64748b", overflow: "hidden", textOverflow: "ellipsis" }}>{safeUser.email || ""}</div>
              </div>
              <div style={{ padding: "6px" }}>
                <div className="profile-menu-item" onClick={() => { setProfileInitialSubTab("info"); setActiveTab("profile"); setShowProfile(false); }}>My Profile</div>
                <div className="profile-menu-item" onClick={() => { setProfileInitialSubTab("subscription"); setActiveTab("profile"); setShowProfile(false); }}>Subscription</div>
                <div className="profile-menu-item" onClick={() => { setSettings((prev) => ({ ...prev, name: safeUser.name })); setShowSettings(true); setShowProfile(false); }}>Settings</div>
                <div className="profile-menu-item" onClick={() => { setShowLinkedIn(true); setShowProfile(false); }}>Connect LinkedIn</div>
              </div>
              <div style={{ padding: "6px", borderTop: "1px solid #e5e8f2" }}>
                <div className="profile-menu-item" style={{ color: "#dc2626" }} onClick={handleLogout}>Sign Out</div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── MAIN WORKSPACE COLUMN ── */}
      <div className="pf-main-col">
        {/* Top Cosmic Utility Strip */}
        <div className="pf-topbar">
          <button
            type="button"
            className="pf-icon-btn pf-mobile-menu-btn"
            aria-label="Open menu"
            onClick={() => setMobileMenuOpen(true)}
          >
            ☰
          </button>
          <div className="pf-topbar-right">{topRightControls}</div>
        </div>

        {/* Quick Search Palette */}
        {showQuickSearch && (
          <div className="pf-quick-search-wrap">
            <div className="pf-quick-search-box">
              <input
                type="text"
                autoFocus
                placeholder="Jump to a tool (e.g. Interview, Coding, Resume, Achievements)..."
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                className="pf-quick-search-input"
              />
              {quickQuery.trim() && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                  {NAV_ITEMS.filter((n) => n.label.toLowerCase().includes(quickQuery.toLowerCase())).map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => { handleTabChange(n.id); setShowQuickSearch(false); }}
                      className="pf-quick-search-chip"
                    >
                      {n.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Unified Cosmic / Alpine Sunrise Hero + Workspace Body */}
        {isOrgExpired ? (
          <>
            <CosmicHero
              badge="Account Notice"
              titleWhite="Organization"
              titleAccent="Subscription Expired"
              subtitle="Contact your administrator to restore campus practice access."
            />
            <div className="pf-body-surface">
              <div className="pf-body-inner">
                <div className="pf-card" style={{ maxWidth: "580px", margin: "32px auto", textAlign: "center", padding: "36px" }}>
                  <span className="pill pill-red" style={{ marginBottom: "12px" }}>Access Restricted</span>
                  <h2 style={{ fontSize: "22px", fontWeight: 800, marginBottom: "8px", color: "#0f172a" }}>Organization Subscription Expired</h2>
                  <p style={{ fontSize: "14px", color: "#475569", marginBottom: "24px", lineHeight: 1.6 }}>
                    Your organization's trial or annual subscription has expired. AI Interviews, Coding Tests, Reports, and Resume Analysis are currently paused.
                  </p>
                  <button onClick={handleLogout} className="btn btn-primary">Sign Out</button>
                </div>
              </div>
            </div>
          </>
        ) : activeTab === "achievements" ? (
          <AchievementsTab onNavigateTab={(tab) => handleTabChange(tab)} />
        ) : (
          <>
            <CosmicHero
              badge={heroMeta.badge}
              titleWhite={heroMeta.titleWhite}
              titleAccent={heroTitleAccent}
              subtitle={heroMeta.subtitle}
              cornerNote="Dream Bigger"
              sunriseBadge={activeTab === "dashboard" ? "YOUR CAREER PREP COMPANION" : heroMeta.badge}
              sunriseTitleLead={activeTab === "dashboard" ? "Prepare. Practice." : heroMeta.titleWhite}
              sunriseTitleAccent={activeTab === "dashboard" ? "Get Hired." : heroTitleAccent}
              sunriseSubtitle={
                activeTab === "dashboard"
                  ? "An AI-powered platform to sharpen your skills, ace interviews, and build a career you're proud of."
                  : heroMeta.subtitle
              }
              ctaLabel={activeTab === "dashboard" ? "Continue Your Prep →" : null}
              onCtaClick={activeTab === "dashboard" ? () => handleTabChange("ava") : null}
            />
            <main className="pf-body-surface">
              <div className="pf-body-inner">
                {activeTab === "dashboard" && <DashboardTab setActiveTab={handleTabChange} user={user} history={history} userStats={userStats} />}
                {activeTab === "roadmap" && <RoadmapTab onNavigateTab={(tab) => handleTabChange(tab)} />}
                {activeTab === "coding" && <CodingTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
                {activeTab === "speech" && <SpeechTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
                {activeTab === "resume" && <ResumeTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
                {activeTab === "ava" && <AvaTab apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
                {activeTab === "interviews" && <InterviewsTab setActiveTab={handleTabChange} apiFetch={apiFetch} isLoggedIn={isLoggedIn} user={user} />}
                {activeTab === "analytics" && <ProgressDashboard onNavigateTab={(tab) => handleTabChange(tab)} />}
                {activeTab === "jobs" && (
                  <JobPreparationTab
                    user={user}
                    onStartInterview={(sessionData) => {
                      if (sessionData?.session_id) {
                        sessionStorage.setItem("current_session_id", sessionData.session_id);
                      }
                      handleTabChange("ava");
                    }}
                  />
                )}
                {activeTab === "profile" && <Profile onBackToDashboard={() => handleTabChange("dashboard")} setActiveTab={handleTabChange} apiFetch={apiFetch} initialSubTab={profileInitialSubTab} />}
              </div>
            </main>
          </>
        )}
      </div>

      {/* ── MODALS (SETTINGS, LINKEDIN, PRACTICE, ANNOUNCEMENTS) ── */}
      {showSettings && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ padding: "24px", maxWidth: "460px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>Account & AI Settings</h3>
              <button onClick={() => setShowSettings(false)} style={{ background: "none", border: "none", color: "#64748b", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "4px" }}>Display Name</label>
                <input type="text" className="form-input" value={settings.name} onChange={(e) => setSettings({ ...settings, name: e.target.value })} />
              </div>
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "4px" }}>Target Role</label>
                <input type="text" className="form-input" value={settings.targetRole} onChange={(e) => setSettings({ ...settings, targetRole: e.target.value })} />
              </div>
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "4px" }}>AI Voice Output</label>
                <select className="form-select" value={settings.voiceEnabled ? "true" : "false"} onChange={(e) => setSettings({ ...settings, voiceEnabled: e.target.value === "true" })}>
                  <option value="true">Enabled (Audio Feedback Active)</option>
                  <option value="false">Disabled (Text Only)</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "4px" }}>AI Feedback Depth</label>
                <select className="form-select" value={settings.detailLevel} onChange={(e) => setSettings({ ...settings, detailLevel: e.target.value })}>
                  <option value="High">Comprehensive Analysis (Detailed)</option>
                  <option value="Medium">Standard Feedback (Balanced)</option>
                  <option value="Low">Summary Only (Quick)</option>
                </select>
              </div>
            </div>
            <div style={{ display: "flex", gap: "10px", marginTop: "24px", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowSettings(false)}>Cancel</button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  const updatedName = settings.name.trim() || user.name;
                  setUser((prev) => ({
                    ...prev,
                    name: updatedName,
                    avatar: updatedName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2),
                  }));
                  localStorage.setItem("full_name", updatedName);
                  setShowSettings(false);
                  alert("Settings updated successfully!");
                }}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {showLinkedIn && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ padding: "24px", maxWidth: "460px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>Connect LinkedIn Profile</h3>
              <button onClick={() => { setShowLinkedIn(false); setLinkedInSuccess(false); }} style={{ background: "none", border: "none", color: "#64748b", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>
            {!linkedInSuccess ? (
              <>
                <p style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5, marginBottom: "16px" }}>
                  Connect your LinkedIn account to import candidate experience, auto-generate interview practice scenarios, and sync ATS ratings.
                </p>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", display: "block", marginBottom: "4px" }}>LinkedIn Profile URL</label>
                  <input type="url" className="form-input" placeholder="https://linkedin.com/in/yourname" value={linkedInUrl} onChange={(e) => setLinkedInUrl(e.target.value)} />
                </div>
                <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowLinkedIn(false)}>Cancel</button>
                  <button className="btn btn-primary btn-sm" disabled={!linkedInUrl.trim()} onClick={() => { setLinkedInSuccess(true); localStorage.setItem("linkedin_url", linkedInUrl); }}>
                    Sync & Connect
                  </button>
                </div>
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "#059669", marginBottom: "4px" }}>LinkedIn Account Connected!</div>
                <div style={{ fontSize: "12px", color: "#475569", marginBottom: "20px" }}>Profile skills synced for AI practice sessions.</div>
                <button className="btn btn-primary btn-sm" onClick={() => { setShowLinkedIn(false); setLinkedInSuccess(false); }}>Done</button>
              </div>
            )}
          </div>
        </div>
      )}

      {showPracticeModal && practiceQuestion && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ padding: "24px", maxWidth: "600px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <span className="pill pill-purple" style={{ fontSize: "10px", marginRight: "6px" }}>{practiceQuestion.category}</span>
                <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{practiceQuestion.difficulty}</span>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: "6px 0 0 0" }}>Practice: {practiceQuestion.title}</h3>
              </div>
              <button onClick={() => setShowPracticeModal(false)} style={{ background: "none", border: "none", color: "#64748b", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", fontSize: "13px" }}>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "12px 16px", borderRadius: "10px", lineHeight: 1.5 }}>
                <div style={{ fontWeight: 800, marginBottom: "4px", color: "#64748b" }}>Question Prompt</div>
                <div style={{ color: "#0f172a", whiteSpace: "pre-line" }}>{practiceQuestion.description}</div>
              </div>
              {practiceQuestion.constraints && (
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "10px 14px", borderRadius: "8px", fontFamily: "monospace", fontSize: "11px", color: "#475569" }}>
                  <strong>Constraints:</strong> {practiceQuestion.constraints}
                </div>
              )}
              <div>
                <label style={{ display: "block", fontWeight: 700, color: "#475569", marginBottom: "6px" }}>Draft Your Answer</label>
                <textarea rows="5" value={studentAnswer} onChange={(e) => setStudentAnswer(e.target.value)} placeholder="Type your explanation or structured answer here..." className="form-input" />
              </div>
              {!answerFeedback ? (
                <button
                  onClick={() => {
                    if (!studentAnswer.trim()) { alert("Please draft your answer first!"); return; }
                    setAnswerFeedback("Compare your solution guide above with your drafted response. Pay close attention to key definitions, structure, and edge cases.");
                  }}
                  className="btn btn-primary"
                >
                  Submit & Compare with Model Answer
                </button>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", padding: "12px 14px", borderRadius: "8px", color: "#065f46", fontSize: "12px" }}>
                    <strong>Draft Submitted:</strong> {answerFeedback}
                  </div>
                  {practiceQuestion.solution && (
                    <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", padding: "14px", borderRadius: "10px" }}>
                      <div style={{ fontWeight: 800, color: "#5b21b6", marginBottom: "6px" }}>Model Solution / Answer Guide</div>
                      <div style={{ color: "#0f172a", whiteSpace: "pre-line" }}>{practiceQuestion.solution}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeAnnouncement && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ padding: "24px", maxWidth: "500px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #e5e8f2", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, margin: 0 }}>Campus Alert / Announcement</h3>
              <button onClick={() => setActiveAnnouncement(null)} style={{ background: "none", border: "none", color: "#64748b", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ fontSize: "15px", fontWeight: 800, color: "#6d28d9" }}>{activeAnnouncement.title}</div>
              <div style={{ fontSize: "11px", color: "#64748b", display: "flex", justifyContent: "space-between" }}>
                <span>From: {activeAnnouncement.sender || "Platform Admin"}</span>
                <span>Date: {activeAnnouncement.time ? (activeAnnouncement.time.includes("ago") || activeAnnouncement.time.includes("Yesterday") ? activeAnnouncement.time : new Date(activeAnnouncement.time).toLocaleDateString()) : "Recently"}</span>
              </div>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px", fontSize: "13px", lineHeight: 1.6, color: "#0f172a", whiteSpace: "pre-wrap" }}>
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
