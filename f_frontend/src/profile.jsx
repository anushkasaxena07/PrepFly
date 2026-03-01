import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

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

/* ─── Main Component ─────────────────────────────────────────── */
const Profile = () => {
  const navigate = useNavigate();
  const [user, setUser]         = useState({ name: "", email: "", phone: "", role: "", avatar: "" });
  const [preview, setPreview]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [saved, setSaved]       = useState(false);
  const [error, setError]       = useState(null);
  const [isEditing, setIsEditing] = useState(true);
  const [dragOver, setDragOver] = useState(false);

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
      const res = await axios.put("http://localhost:5000/update-profile", {
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
        <div className="pr-brand">
          <div className="pr-brand-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
              <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="pr-brand-name">InterviewAI</span>
        </div>
        <button className="pr-back-btn" onClick={() => navigate("/dashboard")}>
          <BackIcon /> Back to Dashboard
        </button>
      </nav>

      {/* ── Page ───────────────────────────────────────────────── */}
      <div className="pr-page">

        {/* Page title */}
        <div className="pr-page-header">
          <h2 className="pr-page-title">My Profile</h2>
          <p className="pr-page-sub">Manage your personal information and preferences.</p>
        </div>

        <div className="pr-layout">

          {/* ── Left: Avatar card ──────────────────────────────── */}
          <div className="pr-side">
            <div className="pr-glass-card pr-avatar-card">
              {/* Drop zone */}
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

            {/* Quick stats */}
            <div className="pr-glass-card pr-stats-card">
              <div className="pr-stat">
                <div className="pr-stat-value">0</div>
                <div className="pr-stat-label">Interviews</div>
              </div>
              <div className="pr-stat-divider" />
              <div className="pr-stat">
                <div className="pr-stat-value">—</div>
                <div className="pr-stat-label">Avg Score</div>
              </div>
              <div className="pr-stat-divider" />
              <div className="pr-stat">
                <div className="pr-stat-value">0</div>
                <div className="pr-stat-label">Sessions</div>
              </div>
            </div>
          </div>

          {/* ── Right: Form card ───────────────────────────────── */}
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
    position: fixed; top: 0; left: 0; right: 0; height: 70px;
    background: rgba(8,12,20,0.88); backdrop-filter: blur(20px) saturate(160%);
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 36px; z-index: 1000;
  }
  .pr-brand { display: flex; align-items: center; gap: 10px; }
  .pr-brand-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #00e5c3, #00b8ff);
    border-radius: 9px; display: flex; align-items: center; justify-content: center;
    color: #080c14; box-shadow: 0 4px 16px rgba(0,229,195,0.3);
  }
  .pr-brand-name { font-size: 17px; font-weight: 700; color: #e8edf8; letter-spacing: -0.3px; }
  .pr-back-btn {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 16px; background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
    color: #7a8ba8; font-size: 13px; font-weight: 500;
    cursor: pointer; transition: all 0.22s ease;
    font-family: 'Sora', sans-serif;
  }
  .pr-back-btn:hover { border-color: rgba(0,229,195,0.3); color: #00e5c3; background: rgba(0,229,195,0.06); transform: none; }

  /* ── Page ─────────────────────────────────────────────────── */
  .pr-page {
    position: relative; z-index: 1;
    max-width: 1000px; margin: 0 auto;
    padding: 106px 36px 80px;
    animation: prFadeUp 0.5s ease both;
  }
  @keyframes prFadeUp { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }

  .pr-page-header { margin-bottom: 32px; }
  .pr-page-title { font-size: 26px; font-weight: 700; letter-spacing: -0.6px; color: #e8edf8; margin-bottom: 4px; }
  .pr-page-sub { font-size: 14px; color: #7a8ba8; }

  /* ── Layout ───────────────────────────────────────────────── */
  .pr-layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 20px;
    align-items: start;
  }

  /* ── Glass card ───────────────────────────────────────────── */
  .pr-glass-card {
    background: rgba(13,18,32,0.85);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px; padding: 28px;
    backdrop-filter: blur(24px) saturate(160%);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.04), 0 20px 60px rgba(0,0,0,0.4);
    position: relative; overflow: hidden;
  }
  .pr-glass-card::before {
    content: ''; position: absolute; inset: 0; border-radius: 20px; padding: 1px;
    background: linear-gradient(135deg, rgba(0,229,195,0.18) 0%, transparent 50%, rgba(99,40,255,0.08) 100%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none;
  }

  /* ── Avatar card ──────────────────────────────────────────── */
  .pr-avatar-card { display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }

  .pr-avatar-zone {
    position: relative; width: 120px; height: 120px; border-radius: 50%;
    overflow: hidden; cursor: pointer; flex-shrink: 0;
    border: 2px solid rgba(0,229,195,0.25);
    box-shadow: 0 0 0 4px rgba(0,229,195,0.08);
    transition: border-color 0.22s ease;
  }
  .pr-avatar-zone--over { border-color: rgba(0,229,195,0.6); }
  .pr-avatar-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .pr-avatar-placeholder {
    width: 100%; height: 100%;
    background: linear-gradient(135deg, #00e5c3, #00b8ff);
    display: flex; align-items: center; justify-content: center;
    font-size: 36px; font-weight: 700; color: #050d14; letter-spacing: -1px;
  }
  .pr-avatar-overlay {
    position: absolute; inset: 0; border-radius: 50%;
    background: rgba(8,12,20,0.7); display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 4px;
    color: #00e5c3; font-size: 11px; font-weight: 600;
    opacity: 0; cursor: pointer; transition: opacity 0.22s ease;
  }
  .pr-avatar-zone:hover .pr-avatar-overlay { opacity: 1; }
  .pr-avatar-hint { font-size: 11.5px; color: #4a5a72; margin-top: -8px; }
  .pr-avatar-name { font-size: 16px; font-weight: 700; color: #e8edf8; letter-spacing: -0.3px; }
  .pr-avatar-role { font-size: 13px; color: #4a5a72; margin-top: 2px; }

  .pr-status-badge {
    display: flex; align-items: center; gap: 7px; padding: 6px 14px;
    background: rgba(0,214,143,0.1); border: 1px solid rgba(0,214,143,0.2);
    border-radius: 50px; font-size: 12px; font-weight: 600; color: #00d68f;
  }
  .pr-status-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #00d68f; box-shadow: 0 0 6px rgba(0,214,143,0.7);
    animation: prPulse 1.6s ease-in-out infinite;
  }
  @keyframes prPulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

  /* ── Stats card ───────────────────────────────────────────── */
  .pr-stats-card { display: flex; align-items: center; justify-content: space-around; padding: 20px 16px; margin-top: 16px; }
  .pr-stat { text-align: center; }
  .pr-stat-value { font-size: 22px; font-weight: 700; color: #00e5c3; letter-spacing: -0.5px; }
  .pr-stat-label { font-size: 11px; color: #4a5a72; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 3px; }
  .pr-stat-divider { width: 1px; height: 36px; background: rgba(255,255,255,0.07); }

  /* ── Form card ────────────────────────────────────────────── */
  .pr-main { display: flex; flex-direction: column; gap: 16px; }
  .pr-form-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
  .pr-form-title { font-size: 16px; font-weight: 700; color: #e8edf8; letter-spacing: -0.3px; }
  .pr-form-sub { font-size: 13px; color: #4a5a72; margin-top: 3px; }

  .pr-message {
    display: flex; align-items: center; gap: 9px;
    padding: 11px 15px; border-radius: 10px; font-size: 13px; font-weight: 500;
    margin-bottom: 18px; animation: prMsgIn 0.25s ease both;
  }
  @keyframes prMsgIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
  .pr-message--error { background: rgba(255,79,106,0.1); border: 1px solid rgba(255,79,106,0.22); color: #ff4f6a; }
  .pr-message--success { background: rgba(0,214,143,0.1); border: 1px solid rgba(0,214,143,0.22); color: #00d68f; }

  .pr-fields { display: flex; flex-direction: column; gap: 18px; }
  .pr-field-group { display: flex; flex-direction: column; gap: 7px; }
  .pr-field-label { font-size: 12px; font-weight: 500; color: #4a5a72; text-transform: uppercase; letter-spacing: 0.06em; }
  .pr-field-wrap { position: relative; display: flex; align-items: center; }
  .pr-field-icon { position: absolute; left: 13px; color: #4a5a72; pointer-events: none; transition: color 0.22s; }
  .pr-field-input {
    width: 100%; padding: 12px 14px 12px 42px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; color: #e8edf8; font-family: 'Sora', sans-serif;
    font-size: 14px; outline: none; transition: all 0.22s ease;
  }
  .pr-field-input::placeholder { color: #4a5a72; }
  .pr-field-input:focus { border-color: rgba(0,229,195,0.45); background: rgba(255,255,255,0.06); box-shadow: 0 0 0 3px rgba(0,229,195,0.1); }
  .pr-field-input:-webkit-autofill, .pr-field-input:-webkit-autofill:focus {
    -webkit-box-shadow: 0 0 0 1000px #0d1220 inset; -webkit-text-fill-color: #e8edf8;
  }
  .pr-field-wrap:focus-within .pr-field-icon { color: #00e5c3; }

  .pr-field-view {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 16px; background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;
  }
  .pr-field-icon--view { position: static; }
  .pr-field-value { font-size: 14px; color: #e8edf8; }
  .pr-field-empty { color: #4a5a72; font-style: italic; }

  .pr-form-actions { display: flex; gap: 12px; margin-top: 28px; justify-content: flex-end; }

  /* ── Buttons ──────────────────────────────────────────────── */
  .pr-btn {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 11px 20px; border-radius: 12px; border: none;
    font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: all 0.22s ease;
  }
  .pr-btn--primary {
    background: linear-gradient(135deg, #00e5c3, #00b8ff); color: #050d14;
    box-shadow: 0 4px 18px rgba(0,229,195,0.25); min-width: 140px; justify-content: center;
  }
  .pr-btn--primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(0,229,195,0.38); }
  .pr-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .pr-btn--ghost {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); color: #7a8ba8;
  }
  .pr-btn--ghost:hover { border-color: rgba(0,229,195,0.3); color: #00e5c3; background: rgba(0,229,195,0.06); transform: none; }
  .pr-btn--sm { padding: 8px 14px; font-size: 13px; }
  .pr-btn--danger {
    background: rgba(255,79,106,0.1); border: 1px solid rgba(255,79,106,0.25); color: #ff4f6a;
    padding: 9px 18px; font-size: 13px;
  }
  .pr-btn--danger:hover { background: rgba(255,79,106,0.18); box-shadow: 0 4px 18px rgba(255,79,106,0.2); transform: none; }

  /* ── Spinner ──────────────────────────────────────────────── */
  .pr-spinner {
    width: 16px; height: 16px; border-radius: 50%;
    border: 2.5px solid rgba(5,13,20,0.3); border-top-color: #050d14;
    animation: prSpin 0.7s linear infinite;
  }
  @keyframes prSpin { to{transform:rotate(360deg)} }

  /* ── Danger zone ──────────────────────────────────────────── */
  .pr-danger-zone { border-color: rgba(255,79,106,0.1); }
  .pr-danger-zone::before { background: linear-gradient(135deg, rgba(255,79,106,0.1) 0%, transparent 50%); }
  .pr-danger-title { font-size: 14px; font-weight: 700; color: #ff4f6a; margin-bottom: 16px; }
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
