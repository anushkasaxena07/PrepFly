import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import StudentFeedbackForm from "./components/StudentFeedbackForm";

/* ─── Small SVG icons ────────────────────────────────────────── */
const Icon = ({ d, size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const BackIcon  = () => <Icon d="M19 12H5M12 5l-7 7 7 7" />;
const UserIcon  = () => <Icon d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />;
const MailIcon  = () => <Icon d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6" />;
const PhoneIcon = () => <Icon d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.59 1h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9a16 16 0 0 0 6.91 6.91l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />;
const BriefIcon = () => <Icon d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 2 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />;
const EditIcon  = () => <Icon d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />;
const SaveIcon  = () => <Icon d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2zM17 21v-8H7v8M7 3v5h8" />;
const CamIcon   = () => <Icon d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />;

const fields = [
  { key: "name",  label: "Full Name",    icon: <UserIcon />,  type: "text",  placeholder: "John Doe" },
  { key: "email", label: "Email Address",icon: <MailIcon />,  type: "email", placeholder: "you@example.com" },
  { key: "phone", label: "Phone Number", icon: <PhoneIcon />, type: "tel",   placeholder: "+91 00000 00000" },
  { key: "role",  label: "Job Role",     icon: <BriefIcon />, type: "text",  placeholder: "Software Engineer" },
];

import SubscriptionPage from "./components/subscription/SubscriptionPage";

const Profile = ({ onBackToDashboard, setActiveTab, apiFetch, initialSubTab = "info" }) => {
  const navigate = useNavigate();
  const [profileSubTab, setProfileSubTab] = useState(initialSubTab);

  useEffect(() => {
    if (initialSubTab) {
      setProfileSubTab(initialSubTab);
    }
  }, [initialSubTab]);

  const handleBack = () => {
    if (typeof onBackToDashboard === 'function') {
      onBackToDashboard();
    } else if (typeof setActiveTab === 'function') {
      setActiveTab("dashboard");
    } else {
      navigate("/dashboard");
    }
  };
  const [user, setUser]         = useState({ name: "", email: "", phone: "", role: "", avatar: "" });
  const [preview, setPreview]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [saved, setSaved]       = useState(false);
  const [error, setError]       = useState(null);
  const [isEditing, setIsEditing] = useState(true);
  const [dragOver, setDragOver] = useState(false);

  const [stats, setStats] = useState({ interviews: 0, avgScore: "—", sessions: 0 });

  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const parsed = JSON.parse(stored);
        setUser(parsed);
        setPreview(parsed?.avatar || "");
      } else {
        // Try email fallback
        const email = localStorage.getItem("email");
        if (email) setUser(u => ({ ...u, email }));
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    const userId = user?._id || user?.id || user?.user_id;
    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      localStorage.getItem("admin_access_token") ||
      localStorage.getItem("superadmin_token");
    if (userId && token) {
      const fetchStats = async () => {
        try {
          let data = null;
          if (typeof apiFetch === "function") {
            const res = await apiFetch(`/user-stats/me`);
            if (res && res.ok) {
              data = await res.json();
            }
          } else {
            const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
            const res = await axios.get(`${BACKEND_URL}/user-stats/me`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 200) {
              data = res.data;
            }
          }
          if (data) {
            const totalSessions = (data.interviews?.total || 0) + (data.coding?.total || 0) + (data.speech?.total || 0) + (data.resume?.total || 0);
            setStats({
              interviews: data.interviews?.total || 0,
              avgScore: data.interviews?.avg_score ? data.interviews.avg_score.toFixed(1) : "—",
              sessions: totalSessions
            });
          }
        } catch (e) {
          console.error("Failed to fetch user stats in profile:", e);
        }
      };
      fetchStats();
    }
  }, [user?._id, user?.id, user?.user_id, apiFetch]);

  const processImage = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result);
      setUser(u => ({ ...u, avatar: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const handleImageChange = (e) => processImage(e.target.files[0]);
  const handleDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    processImage(e.dataTransfer.files[0]);
  };

  const handleChange = (e) => {
    setUser(u => ({ ...u, [e.target.name]: e.target.value }));
    setSaved(false);
  };

  const handleSave = async () => {
    setLoading(true); setError(null);
    try {
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
      const res = await axios.put(`${BACKEND_URL}/update-profile`, {
        user_id: user._id, ...user,
      });
      localStorage.setItem("user", JSON.stringify(user));
      setSaved(true);
      setIsEditing(false);
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const initials = user.name
    ? user.name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : (user.email?.[0] || "U").toUpperCase();

  return (
    <>
      <style>{css}</style>

      {/* Orbs */}
      <div className="pr-orb pr-orb-1" />
      <div className="pr-orb pr-orb-2" />

      {/* ── Navbar ─────────────────────────────────────────────── */}
      <nav className="pr-navbar">
        <div className="pr-brand" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span className="pr-brand-name" style={{ fontSize: "18px", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.4px" }}>Prep<span style={{ color: "#c4b5fd" }}>Fly</span></span>
        </div>
        <button className="pr-back-btn" onClick={handleBack}>
          <BackIcon /> Back to Dashboard
        </button>
      </nav>

      {/* ── Page ───────────────────────────────────────────────── */}
      <div className="pr-page">

        {/* Page title */}
        <div className="pr-page-header">
          <h2 className="pr-page-title">My Profile &amp; Membership</h2>
          <p className="pr-page-sub">Manage your personal information, preferences, and SaaS subscription.</p>
        </div>

        {/* Profile Sub Tabs */}
        <div style={{ display: "flex", gap: "10px", marginBottom: "24px", borderBottom: "1px solid #e5e8f2", paddingBottom: "12px", position: "relative", zIndex: 10 }}>
          <button 
            type="button"
            className={`pf-filter-pill ${profileSubTab === "info" ? "active" : ""}`} 
            onClick={() => setProfileSubTab("info")}
          >
            Personal Details
          </button>
          <button 
            type="button"
            className={`pf-filter-pill ${profileSubTab === "subscription" ? "active" : ""}`} 
            onClick={() => setProfileSubTab("subscription")}
          >
            Subscription
          </button>
          <button 
            type="button"
            className={`pf-filter-pill ${profileSubTab === "feedback" ? "active" : ""}`} 
            onClick={() => setProfileSubTab("feedback")}
          >
            Send Feedback
          </button>
        </div>

        {profileSubTab === "subscription" && (
          <SubscriptionPage apiFetch={apiFetch} user={user} />
        )}

        {profileSubTab === "feedback" && (
          <StudentFeedbackForm role="Student" />
        )}

        {(profileSubTab === "info" || (!["subscription", "feedback"].includes(profileSubTab))) && (
          <div className="pr-layout">

          <div className="pr-side">
            <div className="pr-glass-card pr-avatar-card">
              <div
                className={`pr-avatar-zone ${dragOver ? "pr-avatar-zone--over" : ""}`}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                {preview ? (
                  <img src={preview} alt="Avatar" className="pr-avatar-img" />
                ) : (
                  <div className="pr-avatar-placeholder">{initials}</div>
                )}
                {isEditing && (
                  <label className="pr-avatar-overlay" htmlFor="pr-file-input">
                    <CamIcon />
                    <span>Change photo</span>
                    <input
                      id="pr-file-input" type="file" accept="image/*"
                      onChange={handleImageChange} style={{ display: "none" }}
                    />
                  </label>
                )}
              </div>

              {isEditing && (
                <p className="pr-avatar-hint">Drag & drop or click to upload</p>
              )}

              <div className="pr-avatar-meta">
                <div className="pr-avatar-name">{user.name || "Your Name"}</div>
                <div className="pr-avatar-role">{user.role || "Your Role"}</div>
              </div>

              <div className="pr-status-badge">
                <div className="pr-status-dot" />
                Active
              </div>
            </div>

            <div className="pr-glass-card pr-stats-card">
              <div className="pr-stat">
                <div className="pr-stat-value">{stats.interviews}</div>
                <div className="pr-stat-label">Interviews</div>
              </div>
              <div className="pr-stat-divider" />
              <div className="pr-stat">
                <div className="pr-stat-value">{stats.avgScore}</div>
                <div className="pr-stat-label">Avg Score</div>
              </div>
              <div className="pr-stat-divider" />
              <div className="pr-stat">
                <div className="pr-stat-value">{stats.sessions}</div>
                <div className="pr-stat-label">Sessions</div>
              </div>
            </div>
          </div>

          <div className="pr-main">
            <div className="pr-glass-card">

              <div className="pr-form-header">
                <div>
                  <div className="pr-form-title">Personal Information</div>
                  <div className="pr-form-sub">
                    {isEditing ? "Update your details below and save." : "View your saved profile details."}
                  </div>
                </div>
                {!isEditing && (
                  <button className="pr-btn pr-btn--ghost pr-btn--sm" onClick={() => setIsEditing(true)}>
                    <EditIcon /> Edit
                  </button>
                )}
              </div>

              {/* Error */}
              {error && (
                <div className="pr-message pr-message--error">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                  {error}
                </div>
              )}

              {/* Success */}
              {saved && !isEditing && (
                <div className="pr-message pr-message--success">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  Profile saved successfully!
                </div>
              )}

              {/* Fields */}
              <div className="pr-fields">
                {fields.map(({ key, label, icon, type, placeholder }) => (
                  <div className="pr-field-group" key={key}>
                    <label className="pr-field-label">{label}</label>
                    {isEditing ? (
                      <div className="pr-field-wrap">
                        <span className="pr-field-icon">{icon}</span>
                        <input
                          type={type}
                          name={key}
                          value={user[key] || ""}
                          onChange={handleChange}
                          placeholder={placeholder}
                          className="pr-field-input"
                          autoComplete={key === "email" ? "email" : "off"}
                        />
                      </div>
                    ) : (
                      <div className="pr-field-view">
                        <span className="pr-field-icon pr-field-icon--view">{icon}</span>
                        <span className="pr-field-value">{user[key] || <span className="pr-field-empty">Not set</span>}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Actions */}
              {isEditing && (
                <div className="pr-form-actions">
                  <button className="pr-btn pr-btn--ghost" onClick={() => setIsEditing(false)} disabled={loading}>
                    Cancel
                  </button>
                  <button className="pr-btn pr-btn--primary" onClick={handleSave} disabled={loading}>
                    {loading ? (
                      <span className="pr-spinner" />
                    ) : (
                      <><SaveIcon /> Save Changes</>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Danger zone */}
            <div className="pr-glass-card pr-danger-zone">
              <div className="pr-danger-title">Danger Zone</div>
              <div className="pr-danger-row">
                <div>
                  <div className="pr-danger-label">Sign out of your account</div>
                  <div className="pr-danger-sub">You will be redirected to the login page.</div>
                </div>
                <button className="pr-btn pr-btn--danger" onClick={() => { localStorage.clear(); navigate("/"); }}>
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        </div>
        )}
      </div>
    </>
  );
};

/* ─── Scoped CSS ─────────────────────────────────────────────── */
const css = `
  .pr-orb {
    position: fixed; border-radius: 50%; filter: blur(90px);
    pointer-events: none; z-index: 0;
  }
  .pr-orb-1 {
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(0,229,195,0.15), transparent 70%);
    top: -150px; right: -80px; animation: prFloat 12s ease-in-out infinite;
  }
  .pr-orb-2 {
    width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(99,40,255,0.18), transparent 70%);
    bottom: -120px; left: -60px; animation: prFloat 14s ease-in-out infinite reverse;
    animation-delay: -6s;
  }
  @keyframes prFloat { 0%,100%{transform:translateY(0) scale(1)} 50%{transform:translateY(-32px) scale(1.05)} }

  /* ── Navbar ───────────────────────────────────────────────── */
  .pr-navbar {
    position: sticky; top: 0; height: 64px;
    background: #0b0e1a; border-bottom: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 28px; z-index: 50; border-radius: 16px; margin-bottom: 20px;
  }
  .pr-brand { display: flex; align-items: center; gap: 10px; }
  .pr-brand-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 9px; display: flex; align-items: center; justify-content: center;
    color: #ffffff; box-shadow: 0 4px 14px rgba(109,40,217,0.3);
  }
  .pr-brand-name { font-size: 17px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px; }
  .pr-back-btn {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px; background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.14); border-radius: 10px;
    color: #e2e8f0; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.2s ease;
    font-family: inherit;
  }
  .pr-back-btn:hover { border-color: #a78bfa; color: #ffffff; background: rgba(124,58,237,0.25); }

  /* ── Page ─────────────────────────────────────────────────── */
  .pr-page {
    position: relative; z-index: 1;
    max-width: 1060px; margin: 0 auto;
    padding: 8px 0 60px;
    animation: prFadeUp 0.4s ease both;
  }
  @keyframes prFadeUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }

  .pr-page-header { margin-bottom: 24px; }
  .pr-page-title { font-size: 24px; font-weight: 800; letter-spacing: -0.5px; color: #0f172a; margin-bottom: 4px; }
  .pr-page-sub { font-size: 14px; color: #64748b; }

  /* ── Layout ───────────────────────────────────────────────── */
  .pr-layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 20px;
    align-items: start;
  }
  @media (max-width: 820px) { .pr-layout { grid-template-columns: 1fr; } }

  /* ── Light Elevated Card ───────────────────────────────────── */
  .pr-glass-card {
    background: #ffffff;
    border: 1px solid #e5e8f2;
    border-radius: 18px; padding: 26px;
    box-shadow: 0 2px 12px rgba(15,23,42,0.04);
    position: relative; overflow: hidden;
  }

  /* ── Avatar card ──────────────────────────────────────────── */
  .pr-avatar-card { display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }

  .pr-avatar-zone {
    position: relative; width: 112px; height: 112px; border-radius: 50%;
    overflow: hidden; cursor: pointer; flex-shrink: 0;
    border: 3px solid #ddd6fe;
    box-shadow: 0 0 0 4px #f5f3ff;
    transition: border-color 0.2s ease;
  }
  .pr-avatar-zone--over { border-color: #7c3aed; }
  .pr-avatar-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .pr-avatar-placeholder {
    width: 100%; height: 100%;
    background: linear-gradient(135deg, #6d28d9, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 34px; font-weight: 800; color: #ffffff; letter-spacing: -1px;
  }
  .pr-avatar-overlay {
    position: absolute; inset: 0; border-radius: 50%;
    background: rgba(11,14,26,0.72); display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 4px;
    color: #e9d5ff; font-size: 11px; font-weight: 700;
    opacity: 0; cursor: pointer; transition: opacity 0.2s ease;
  }
  .pr-avatar-zone:hover .pr-avatar-overlay { opacity: 1; }
  .pr-avatar-hint { font-size: 11.5px; color: #64748b; margin-top: -8px; }
  .pr-avatar-name { font-size: 16px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px; }
  .pr-avatar-role { font-size: 13px; color: #64748b; margin-top: 2px; }

  .pr-status-badge {
    display: flex; align-items: center; gap: 7px; padding: 6px 14px;
    background: #ecfdf5; border: 1px solid #a7f3d0;
    border-radius: 50px; font-size: 12px; font-weight: 700; color: #059669;
  }
  .pr-status-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #10b981;
  }

  /* ── Stats card ───────────────────────────────────────────── */
  .pr-stats-card { display: flex; align-items: center; justify-content: space-around; padding: 20px 16px; margin-top: 16px; }
  .pr-stat { text-align: center; }
  .pr-stat-value { font-size: 22px; font-weight: 800; color: #6d28d9; letter-spacing: -0.5px; }
  .pr-stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 3px; }
  .pr-stat-divider { width: 1px; height: 36px; background: #e5e8f2; }

  /* ── Form card ────────────────────────────────────────────── */
  .pr-main { display: flex; flex-direction: column; gap: 16px; }
  .pr-form-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
  .pr-form-title { font-size: 16px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px; }
  .pr-form-sub { font-size: 13px; color: #64748b; margin-top: 3px; }

  .pr-message {
    display: flex; align-items: center; gap: 9px;
    padding: 11px 15px; border-radius: 10px; font-size: 13px; font-weight: 600;
    margin-bottom: 18px;
  }
  .pr-message--error { background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; }
  .pr-message--success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #059669; }

  .pr-fields { display: flex; flex-direction: column; gap: 18px; }
  .pr-field-group { display: flex; flex-direction: column; gap: 7px; }
  .pr-field-label { font-size: 11.5px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; }
  .pr-field-wrap { position: relative; display: flex; align-items: center; }
  .pr-field-icon { position: absolute; left: 13px; color: #64748b; pointer-events: none; transition: color 0.2s; }
  .pr-field-input {
    width: 100%; padding: 12px 14px 12px 42px;
    background: #f8fafc; border: 1px solid #cbd5e1;
    border-radius: 12px; color: #0f172a; font-family: inherit;
    font-size: 14px; outline: none; transition: all 0.2s ease;
  }
  .pr-field-input::placeholder { color: #94a3b8; }
  .pr-field-input:focus { border-color: #7c3aed; background: #ffffff; box-shadow: 0 0 0 3px rgba(124,58,237,0.12); }
  .pr-field-wrap:focus-within .pr-field-icon { color: #6d28d9; }

  .pr-field-view {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 16px; background: #f8fafc;
    border: 1px solid #e5e8f2; border-radius: 12px;
  }
  .pr-field-icon--view { position: static; }
  .pr-field-value { font-size: 14px; color: #0f172a; font-weight: 500; }
  .pr-field-empty { color: #94a3b8; font-style: italic; }

  .pr-form-actions { display: flex; gap: 12px; margin-top: 28px; justify-content: flex-end; }

  /* ── Buttons ──────────────────────────────────────────────── */
  .pr-btn {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 11px 20px; border-radius: 12px; border: none;
    font-family: inherit; font-size: 14px; font-weight: 700;
    cursor: pointer; transition: all 0.18s ease;
  }
  .pr-btn--primary {
    background: linear-gradient(135deg, #6d28d9, #7c3aed); color: #ffffff;
    box-shadow: 0 4px 14px rgba(109,40,217,0.25); min-width: 140px; justify-content: center;
  }
  .pr-btn--primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 22px rgba(109,40,217,0.34); }
  .pr-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .pr-btn--ghost {
    background: #ffffff; border: 1px solid #d5dbe9; color: #475569;
  }
  .pr-btn--ghost:hover { border-color: #7c3aed; color: #6d28d9; background: #f5f3ff; }
  .pr-btn--sm { padding: 8px 14px; font-size: 13px; }
  .pr-btn--danger {
    background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;
    padding: 9px 18px; font-size: 13px;
  }
  .pr-btn--danger:hover { background: #fee2e2; }

  /* ── Spinner ──────────────────────────────────────────────── */
  .pr-spinner {
    width: 16px; height: 16px; border-radius: 50%;
    border: 2.5px solid rgba(255,255,255,0.35); border-top-color: #ffffff;
    animation: prSpin 0.7s linear infinite;
  }
  @keyframes prSpin { to{transform:rotate(360deg)} }

  /* ── Danger zone ──────────────────────────────────────────── */
  .pr-danger-zone { border-color: #fecaca; }
  .pr-danger-title { font-size: 14px; font-weight: 700; color: #dc2626; margin-bottom: 16px; }
  .pr-danger-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .pr-danger-label { font-size: 13.5px; font-weight: 500; color: #e8edf8; }
  .pr-danger-sub { font-size: 12px; color: #4a5a72; margin-top: 3px; }

  /* ── Responsive ───────────────────────────────────────────── */
  @media (max-width: 768px) {
    .pr-layout { grid-template-columns: 1fr; }
    .pr-page { padding: 90px 20px 60px; }
    .pr-navbar { padding: 0 20px; }
    .pr-back-btn span { display: none; }
    .pr-form-actions { flex-direction: column-reverse; }
    .pr-btn--primary { width: 100%; }
  }
`;

export default Profile;
