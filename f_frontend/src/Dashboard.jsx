import React, { useState, useEffect } from "react";
import "./Dashboard.css";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = "http://localhost:5000";

const interviewRoles = [
  { name: "Software Developer",   desc: "Core CS fundamentals, algorithms, system design, and problem solving.",        badge: "badge-teal",   label: "General",    time: "45 min" },
  { name: "Full Stack Developer", desc: "End-to-end interview covering REST APIs, databases, React, and Node.",          badge: "badge-blue",   label: "Full Stack", time: "60 min" },
  { name: "Mobile App Developer", desc: "iOS & Android concepts, lifecycle, state management, and performance.",          badge: "badge-purple", label: "Mobile",     time: "40 min" },
  { name: "SSB Interview",        desc: "Personality, GTO tasks, situational judgement, and leadership focus.",          badge: "badge-pink",   label: "Defence",    time: "90 min" },
  { name: "Frontend Developer",   desc: "HTML, CSS, JavaScript, accessibility, performance, and frameworks.",             badge: "badge-teal",   label: "Frontend",   time: "45 min" },
  { name: "Backend Developer",    desc: "Server architecture, databases, caching, APIs, and scalability.",               badge: "badge-blue",   label: "Backend",    time: "50 min" },
  { name: "DevOps Engineer",      desc: "CI/CD pipelines, containerization, cloud infrastructure, and monitoring.",       badge: "badge-purple", label: "DevOps",     time: "55 min" },
  { name: "Data Scientist",       desc: "Statistics, ML fundamentals, model evaluation, and case studies.",              badge: "badge-pink",   label: "Data",       time: "60 min" },
];

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const ArrowIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <path d="M5 12h14M12 5l7 7-7 7"/>
  </svg>
);

export default function Dashboard() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen]             = useState(false);
  const [resumeUploaded, setResumeUploaded] = useState(false);
  const [resumeFile, setResumeFile]         = useState(null);
  const [formSubmitted, setFormSubmitted]   = useState(false);
  const [sessionId, setSessionId]           = useState(null);
  const [jobDetails, setJobDetails]         = useState({ role: "", tools: "", experience: "" });
  const [user, setUser]                     = useState({ name: "", email: "", avatar: "", _id: "" });

  useEffect(() => {
    // ── Load user from localStorage (set during login) ──────────
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        setUser(JSON.parse(stored));
      } else {
        const email   = localStorage.getItem("email")   || "";
        const user_id = localStorage.getItem("user_id") || "";
        setUser({ name: "", email, avatar: "", _id: user_id });
      }
    } catch { /* silent */ }

    // Always generate a fresh session_id on mount — never reuse stale one (causes duplicate key error)
    const sid = crypto.randomUUID();
    setSessionId(sid);
    localStorage.removeItem("session_id");
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!e.target.closest(".nav-right")) setMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) setResumeFile(file);
  };

  const uploadResume = async () => {
    if (!resumeFile) { alert("Please select a file."); return; }
    const formData = new FormData();
    formData.append("resume",     resumeFile);
    formData.append("session_id", sessionId);
    // Pass user_id so the session is linked to the logged-in user
    if (user._id) formData.append("user_id", user._id);

    try {
      const res = await fetch(`${BACKEND_URL}/upload`, { method: "POST", body: formData });
      if (!res.ok) { const d = await res.json(); alert(d.error || "Upload failed"); return; }
      const data = await res.json();
      // Save the returned session_id (may differ if server generated one)
      if (data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem("session_id", data.session_id);
      }
      setResumeUploaded(true);
    } catch {
      alert("Failed to upload. Please try again.");
    }
  };

  const submitJobDetails = () => {
    const { role, tools, experience } = jobDetails;
    if (role && tools && experience) {
      setFormSubmitted(true);
    } else {
      alert("Please fill out all job details.");
    }
  };

  // Derive display name: prefer name, fall back to email prefix
  const displayName = user.name
    ? user.name.split(" ")[0]          // first name only
    : user.email
      ? user.email.split("@")[0]
      : "Candidate";

  // Derive initials for avatar fallback
  const initials = user.name
    ? user.name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : (user.email?.[0] || "U").toUpperCase();

  const isReady = resumeUploaded && formSubmitted;

  return (
    <div className="dashboard-container">
      {/* Background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* ── Navbar ───────────────────────────────────────────── */}
      <nav className="navbar">
        <div className="nav-brand">
          <div className="nav-brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
              <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="nav-brand-name">InterviewAI</span>
        </div>

        <div className="nav-right">
          <div className="nav-pill">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            Dashboard
          </div>

          {/* Avatar button — shows photo or initials */}
          <div className="profile-icon-btn" onClick={() => setMenuOpen(!menuOpen)}
            style={{ overflow: "hidden", background: user.avatar ? "transparent" : undefined }}>
            {user.avatar
              ? <img src={user.avatar} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              : initials
            }
          </div>

          {menuOpen && (
            <div className="dropdown-menu">
              {/* User info header */}
              <div style={{ padding: "12px 14px 8px", borderBottom: "1px solid var(--border)" }}>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                  {user.name || displayName}
                </div>
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)", marginTop: 2 }}>
                  {user.email}
                </div>
              </div>
              <ul>
                <li onClick={() => navigate("/profile")}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  </svg>
                  My Profile
                </li>
                <li>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                  </svg>
                  Settings
                </li>
                <div className="dropdown-divider" />
                <li onClick={handleLogout} style={{ color: "var(--danger)" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                    <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                  </svg>
                  Logout
                </li>
              </ul>
            </div>
          )}
        </div>
      </nav>

      {/* ── Page Body ─────────────────────────────────────────── */}
      <div className="page-body">

        {/* Welcome — shows real user name */}
        <div className="welcome-banner">
          <h2>Good to have you back, <span className="accent-text">{displayName}</span> 👋</h2>
          <p>Set up your profile below and pick an interview track to begin.</p>
        </div>

        {/* Setup cards */}
        <div className="setup-section">

          {/* Resume Upload */}
          <div className="glass-card">
            <div className="card-title">
              <div className="card-title-icon">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              Upload Resume
            </div>

            {resumeUploaded ? (
              <div className="upload-badge"><CheckIcon /> {resumeFile?.name || "Resume uploaded"}</div>
            ) : (
              <div className="upload-area">
                <input type="file" accept=".pdf,.doc,.docx" onChange={handleFileChange} />
                <div className="upload-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
                    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
                  </svg>
                </div>
                <h4>{resumeFile ? resumeFile.name : "Drop your resume here"}</h4>
                <p>{resumeFile ? "Ready to upload" : "PDF, DOC, or DOCX · max 10 MB"}</p>
              </div>
            )}

            {!resumeUploaded && (
              <button className="btn-primary" onClick={uploadResume} disabled={!resumeFile}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
                  <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
                </svg>
                Upload Resume
              </button>
            )}
            {resumeUploaded && (
              <button className="btn-ghost" onClick={() => { setResumeUploaded(false); setResumeFile(null); }}>
                Replace File
              </button>
            )}
          </div>

          {/* Job Details */}
          <div className={"glass-card" + (resumeUploaded && !formSubmitted ? " card-pulse" : "")}>
            <div className="card-title">
              <div className="card-title-icon">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
                </svg>
              </div>
              Job Details
              {formSubmitted && (
                <span style={{ marginLeft: "auto", fontSize: "12px", color: "#00d68f", fontWeight: 600 }}>
                  ✓ Saved
                </span>
              )}
            </div>

            <div className="field-stack">
              <div className="field-group">
                <label className="field-label">Job Role</label>
                <div className="field-wrap">
                  <svg className="field-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  </svg>
                  <input
                    type="text"
                    className="field-input"
                    placeholder="e.g. Software Engineer"
                    value={jobDetails.role}
                    onChange={(e) => setJobDetails({ ...jobDetails, role: e.target.value })}
                    disabled={formSubmitted}
                  />
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">Tools & Technologies</label>
                <div className="field-wrap">
                  <svg className="field-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                  </svg>
                  <input
                    type="text"
                    className="field-input"
                    placeholder="e.g. React, Node.js, AWS"
                    value={jobDetails.tools}
                    onChange={(e) => setJobDetails({ ...jobDetails, tools: e.target.value })}
                    disabled={formSubmitted}
                  />
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">Years of Experience</label>
                <div className="field-wrap">
                  <svg className="field-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                  </svg>
                  <input
                    type="text"
                    className="field-input"
                    placeholder="e.g. 2 years"
                    value={jobDetails.experience}
                    onChange={(e) => setJobDetails({ ...jobDetails, experience: e.target.value })}
                    disabled={formSubmitted}
                  />
                </div>
              </div>
            </div>

            <button
              className="btn-primary"
              style={{ marginTop: "8px" }}
              onClick={submitJobDetails}
              disabled={formSubmitted}
            >
              {formSubmitted ? <><CheckIcon /> Details Saved</> : "Save Details"}
            </button>
            {formSubmitted && (
              <button className="btn-ghost" style={{ marginTop: "8px" }}
                onClick={() => setFormSubmitted(false)}>
                Edit Details
              </button>
            )}
          </div>
        </div>

        {/* Start Interview CTA */}
        <div className="cta-section">
          <div className="cta-card">
            <div className="cta-text">
              <h3>Ready to start your interview?</h3>
              <p>Your AI interviewer will ask questions tailored to your resume and role.</p>
              <div className="cta-status">
                <div className={`status-dot ${resumeUploaded ? "ready" : ""}`} />
                <span className="status-label">
                  {!resumeUploaded && !formSubmitted && "Upload resume & fill job details to unlock"}
                  {resumeUploaded && !formSubmitted && "Now fill in your job details"}
                  {!resumeUploaded && formSubmitted && "Now upload your resume"}
                  {isReady && "All set — you're ready to go!"}
                </span>
              </div>
            </div>
            <button className="start-btn" onClick={() => navigate("/interview")} disabled={!isReady}>
              Begin Interview <ArrowIcon />
            </button>
          </div>
        </div>

        {/* Interview Tracks */}
        <div className="section-header">
          <h3>Interview Tracks</h3>
          <span>{interviewRoles.length} tracks available</span>
        </div>

        <div className="interview-cards">
          {interviewRoles.map((item, i) => (
            <div className="interview-card" key={i}>
              <div className={`card-badge ${item.badge}`}>{item.label}</div>
              <h3>{item.name}</h3>
              <p>{item.desc}</p>
              <div className="card-footer">
                <span className="card-meta">~{item.time}</span>
                <button className="card-btn" onClick={() => navigate("/interview")}>
                  Start <ArrowIcon />
                </button>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}