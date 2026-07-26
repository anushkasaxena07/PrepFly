import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./Login.css";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// ─── screens the user can be on ───────────────────────────────────────────────
// "login"           → email + password form
// "signup"          → name + email + password form
// "login-otp"       → OTP entry after password verified
// "signup-otp"      → OTP entry after signup submitted
// "forgot-email"    → enter email to request reset OTP
// "forgot-otp"      → enter reset OTP
// "reset-password"  → enter new password
// "otp-login"       → passwordless OTP login (email entry)
// "otp-login-verify"→ passwordless OTP verify

export default function Login() {
  const [screen, setScreen]           = useState("login");
  const [formData, setFormData]       = useState({ name: "", email: "", password: "" });
  const [otpEmail, setOtpEmail]       = useState("");
  const [otp, setOtp]                 = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [resetToken, setResetToken]   = useState("");
  const [message, setMessage]         = useState({ text: "", type: "" });
  const [isLoading, setIsLoading]     = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [showPassword, setShowPassword]   = useState(false);
  const [showNewPass, setShowNewPass]     = useState(false);
  const [otpCountdown, setOtpCountdown]   = useState(0);
  const navigate = useNavigate();
  const googleInitRef = useRef(false);  // prevent re-initializing Google SDK on every click

  /* ── Animated star canvas ── */
  useEffect(() => {
    const container = document.querySelector('.auth-root');
    if (!container) return;
    const stars = Array.from({ length: 55 }, (_, i) => {
      const s = document.createElement('span');
      s.style.cssText = [
        'position:absolute',
        `left:${Math.random() * 100}%`,
        `top:${Math.random() * 100}%`,
        `width:${Math.random() < 0.2 ? 2.5 : 1.5}px`,
        `height:${Math.random() < 0.2 ? 2.5 : 1.5}px`,
        'border-radius:50%',
        `background:rgba(255,255,255,${(Math.random() * 0.35 + 0.1).toFixed(2)})`,
        'pointer-events:none',
        'z-index:0',
        `animation:twinkle ${(Math.random() * 4 + 3).toFixed(1)}s ease-in-out ${(Math.random() * 5).toFixed(1)}s infinite alternate`
      ].join(';');
      return s;
    });
    // inject keyframes once
    if (!document.getElementById('pf-twinkle-kf')) {
      const st = document.createElement('style');
      st.id = 'pf-twinkle-kf';
      st.textContent = '@keyframes twinkle{0%{opacity:.15}100%{opacity:.8}}';
      document.head.appendChild(st);
    }
    stars.forEach(s => container.appendChild(s));
    return () => stars.forEach(s => s.remove());
  }, []);

  /* ── OTP countdown ── */
  useEffect(() => {
    if (otpCountdown <= 0) return;
    const t = setTimeout(() => setOtpCountdown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [otpCountdown]);

  const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  /* ── Google SDK ── */
  useEffect(() => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true; s.defer = true;
    document.body.appendChild(s);
    return () => document.body.removeChild(s);
  }, []);

  /* ── helpers ── */
  const msg  = (text, type = "error") => setMessage({ text, type });
  const ok   = (text) => msg(text, "success");
  const err  = (e, fallback = "Something went wrong.") =>
    msg(e?.response?.data?.error || fallback);
  const saveUser = (data) => {
    const isSuperAdmin = data.role === "SUPER_ADMIN" || data.email === "saxenaanushka9645@gmail.com";
    const isAdmin = data.role === "ADMIN" || data.role === "admin" || data.role === "Organization Admin" || data.email === "aditya20522113@gmail.com";
    const userRole = isSuperAdmin ? "SUPER_ADMIN" : isAdmin ? "ADMIN" : (data.role || "candidate");
    
    localStorage.setItem("email", data.email);
    localStorage.setItem("user_id", data.user_id || data.id || "user_default");
    if (data.access_token) {
      localStorage.setItem("access_token", data.access_token);
      if (isSuperAdmin) {
        localStorage.setItem("superadmin_access_token", data.access_token);
      }
      if (isAdmin) {
        localStorage.setItem("admin_access_token", data.access_token);
      }
    }
    const userObj = {
      email: data.email,
      name: data.name || (isAdmin ? "Aditya" : ""),
      role: userRole,
      phone: data.phone || "",
      avatar: data.avatar || "",
      _id: data.user_id || data.id || "user_default",
      organization_id: data.organization_id || "d258e381-6a6e-4376-8bf2-2865731b1939"
    };
    localStorage.setItem("user", JSON.stringify(userObj));
    if (isSuperAdmin) {
      localStorage.setItem("superadmin_user", JSON.stringify(userObj));
    }
    if (isAdmin) {
      localStorage.setItem("admin_user", JSON.stringify(userObj));
    }
    return isSuperAdmin;
  };

  const handleRoleRedirect = (data) => {
    const isSuperAdmin = data.role === "SUPER_ADMIN" || data.email === "saxenaanushka9645@gmail.com";
    const isAdmin = data.role === "ADMIN" || data.role === "admin" || data.role === "Organization Admin" || data.email === "aditya20522113@gmail.com";
    if (isSuperAdmin) {
      navigate("/superadmin/dashboard");
    } else if (isAdmin) {
      navigate("/admin/dashboard");
    } else {
      navigate("/dashboard");
    }
  };
  const goTo = (s) => { setScreen(s); setMessage({ text: "", type: "" }); setOtp(""); };

  /* ── Google Login ── */
  const handleGoogleCallback = async (gRes) => {
    setGoogleLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/google/verify`,
        { credential: gRes.credential }, { withCredentials: true });
      saveUser(data);
      ok("Signed in with Google! Redirecting…");
      setTimeout(() => handleRoleRedirect(data), 800);
    } catch (e) { err(e, "Google sign-in failed."); }
    finally { setGoogleLoading(false); }
  };

  const handleGoogleLogin = () => {
    if (!window.google) { msg("Google SDK not loaded yet."); return; }
    if (!GOOGLE_CLIENT_ID) { msg("Google Client ID not configured."); return; }
    // Only initialize once — re-initializing on every click causes the GSI_LOGGER warning
    if (!googleInitRef.current) {
      window.google.accounts.id.initialize({ client_id: GOOGLE_CLIENT_ID, callback: handleGoogleCallback, ux_mode: "popup" });
      googleInitRef.current = true;
    }
    const c = document.getElementById("google-btn-hidden");
    if (c) {
      c.innerHTML = "";
      window.google.accounts.id.renderButton(c, { type: "standard", size: "large" });
      c.querySelector("div[role=button]")?.click();
    }
  };

  /* ══════════════════════════════════════════════════════════════════
   *  SIGNUP FLOW: submit form → get OTP → verify OTP → account created
   * ══════════════════════════════════════════════════════════════════ */
  const handleSignup = async (e) => {
    e.preventDefault();
    const { name, email, password } = formData;
    if (!name || !email || !password) { msg("All fields are required."); return; }
    if (password.length < 6) { msg("Password must be at least 6 characters."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/register`, { name, email, password });
      ok(data.message);
      setOtpEmail(email);
      setOtpCountdown(300);
      goTo("signup-otp");
    } catch (e) { err(e, "Registration failed."); }
    finally { setIsLoading(false); }
  };

  const handleVerifySignupOtp = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) { msg("Enter the 6-digit OTP."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/verify-signup-otp`,
        { email: otpEmail, otp });
      saveUser(data);
      ok("Account created! Redirecting…");
      setTimeout(() => handleRoleRedirect(data), 800);
    } catch (e) { err(e, "Invalid or expired OTP."); }
    finally { setIsLoading(false); }
  };

  /* ══════════════════════════════════════════════════════════════════
   *  LOGIN FLOW: password → OTP → dashboard
   * ══════════════════════════════════════════════════════════════════ */
  const handleLogin = async (e) => {
    e.preventDefault();
    const { email, password } = formData;
    if (!email || !password) { msg("Email and password are required."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/login`, { email, password }, { withCredentials: true });
      ok(data.message);
      setOtpEmail(email);
      setOtpCountdown(300);
      goTo("login-otp");
    } catch (e) { err(e, "Invalid credentials."); }
    finally { setIsLoading(false); }
  };

  const handleVerifyLoginOtp = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) { msg("Enter the 6-digit OTP."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/verify-login-otp`, { email: otpEmail, otp });
      saveUser(data);
      ok("Login successful! Redirecting…");
      setTimeout(() => handleRoleRedirect(data), 800);
    } catch (e) { err(e, "Invalid or expired OTP."); }
    finally { setIsLoading(false); }
  };

  /* ══════════════════════════════════════════════════════════════════
   *  PASSWORDLESS OTP LOGIN
   * ══════════════════════════════════════════════════════════════════ */
  const handleRequestOtpLogin = async (e) => {
    e.preventDefault();
    if (!otpEmail) { msg("Email is required."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      await axios.post(`${API}/auth/email/request-otp`, { email: otpEmail.trim().toLowerCase() });
      ok("OTP sent! Check your inbox.");
      setOtpCountdown(300);
      goTo("otp-login-verify");
    } catch (e) { err(e, "Failed to send OTP."); }
    finally { setIsLoading(false); }
  };

  const handleVerifyOtpLogin = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) { msg("Enter the 6-digit OTP."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/email/verify-otp`,
        { email: otpEmail.trim().toLowerCase(), otp });
      saveUser(data);
      ok("Login successful!");
      setTimeout(() => handleRoleRedirect(data), 800);
      setTimeout(() => navigate("/dashboard"), 800);
    } catch (e) { err(e, "Invalid or expired OTP."); }
    finally { setIsLoading(false); }
  };

  /* ══════════════════════════════════════════════════════════════════
   *  FORGOT PASSWORD FLOW
   * ══════════════════════════════════════════════════════════════════ */
  const handleForgotRequest = async (e) => {
    e.preventDefault();
    if (!otpEmail) { msg("Email is required."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/forgot-password`,
        { email: otpEmail.trim().toLowerCase() });
      ok(data.message);
      setOtpCountdown(300);
      goTo("forgot-otp");
    } catch (e) { err(e, "Failed to send reset code."); }
    finally { setIsLoading(false); }
  };

  const handleVerifyResetOtp = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) { msg("Enter the 6-digit OTP."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/verify-reset-otp`,
        { email: otpEmail.trim().toLowerCase(), otp });
      setResetToken(data.reset_token);
      ok("OTP verified. Set your new password.");
      goTo("reset-password");
    } catch (e) { err(e, "Invalid or expired OTP."); }
    finally { setIsLoading(false); }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 6) { msg("Password must be at least 6 characters."); return; }
    if (newPassword !== confirmPass) { msg("Passwords do not match."); return; }
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(`${API}/auth/reset-password`, {
        email: otpEmail.trim().toLowerCase(),
        reset_token: resetToken,
        new_password: newPassword,
      });
      ok(data.message);
      setTimeout(() => { goTo("login"); setFormData({ name: "", email: otpEmail, password: "" }); }, 1500);
    } catch (e) { err(e, "Failed to reset password."); }
    finally { setIsLoading(false); }
  };

  /* ── Resend OTP helper ── */
  const handleResend = async (purpose) => {
    setIsLoading(true); setMessage({ text: "", type: "" });
    try {
      if (purpose === "login") {
        await axios.post(`${API}/login`,
          { email: otpEmail, password: formData.password }, { withCredentials: true });
      } else if (purpose === "signup") {
        await axios.post(`${API}/register`,
          { name: formData.name, email: otpEmail, password: formData.password });
      } else if (purpose === "reset") {
        await axios.post(`${API}/auth/forgot-password`, { email: otpEmail });
      } else {
        await axios.post(`${API}/auth/email/request-otp`, { email: otpEmail });
      }
      ok("New OTP sent!"); setOtpCountdown(300);
    } catch (e) { err(e, "Failed to resend OTP."); }
    finally { setIsLoading(false); }
  };

  /* ── Shared UI helpers ── */
  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const EmailIcon = () => (
    <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  );
  const LockIcon = () => (
    <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
  const UserIcon = () => (
    <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
  const EyeIcon = ({ open }) => open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );

  const OtpCountdownBadge = () => otpCountdown > 0 ? (
    <div style={{textAlign:"center",padding:"12px",background:"rgba(255,79,106,.12)",
      border:"1px solid rgba(255,79,106,.2)",borderRadius:"10px",
      color:"var(--danger)",fontSize:"13px",marginBottom:"16px"}}>
      ⏱️ Expires in: <strong style={{fontSize:"15px"}}>{fmt(otpCountdown)}</strong>
    </div>
  ) : null;

  const OtpInput = () => (
    <div className="field-group">
      <label className="field-label">6-Digit Code</label>
      <input
        type="text" value={otp}
        onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
        placeholder="000000" className="field-input" maxLength={6} required autoFocus
        style={{fontSize:"28px",fontWeight:"700",letterSpacing:"10px",
          textAlign:"center",fontFamily:"'JetBrains Mono', monospace",paddingLeft:"14px"}}
      />
    </div>
  );

  const EmailSentBadge = ({ onBack }) => (
    <div style={{textAlign:"center",padding:"16px",background:"var(--accent-dim)",
      borderRadius:"12px",marginBottom:"20px",border:"1px solid rgba(0,229,195,.2)"}}>
      <p style={{color:"var(--text-secondary)",fontSize:"13px",margin:"0 0 4px"}}>Code sent to:</p>
      <strong style={{color:"var(--text-primary)",fontSize:"14px"}}>{otpEmail}</strong>
      {onBack && (
        <button type="button" onClick={onBack}
          style={{display:"block",margin:"8px auto 0",background:"none",border:"none",
            color:"var(--accent)",fontSize:"12px",cursor:"pointer",textDecoration:"underline"}}>
          Change email
        </button>
      )}
    </div>
  );

  const ResendBtn = ({ purpose }) => (
    <button type="button" onClick={() => handleResend(purpose)} disabled={isLoading || otpCountdown > 0}
      style={{width:"100%",padding:"12px",background:"rgba(255,255,255,.05)",
        border:"1px solid var(--border)",borderRadius:"var(--radius-btn)",
        color: otpCountdown > 0 ? "var(--text-muted)" : "var(--text-secondary)",
        fontSize:"14px",fontWeight:"500",cursor: otpCountdown > 0 ? "not-allowed" : "pointer",marginTop:"10px"}}>
      {otpCountdown > 0 ? `Resend in ${fmt(otpCountdown)}` : "🔄 Resend Code"}
    </button>
  );

  /* ── screen meta ── */
  const screenMeta = {
    login:            { title: "Welcome back",           sub: "Sign in to continue your growth" },
    signup:           { title: "Create account",         sub: "Start building something great today" },
    "login-otp":      { title: "Check your email",       sub: "Enter the code we just sent you" },
    "signup-otp":     { title: "Verify your email",      sub: "One last step to activate your account" },
    "otp-login":      { title: "Sign in with OTP",       sub: "We'll email you a one-time code" },
    "otp-login-verify":{ title:"Enter your code",        sub: "Check your email for the verification code" },
    "forgot-email":   { title: "Forgot password?",       sub: "Enter your email to receive a reset code" },
    "forgot-otp":     { title: "Enter reset code",       sub: "Check your email for the reset code" },
    "reset-password": { title: "Set new password",       sub: "Choose a strong password" },
  };
  const { title, sub } = screenMeta[screen] || screenMeta.login;

  return (
    <div className="auth-root">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="auth-card">
        {/* Brand Header with Glowing Circle Logo */}
        <div className="brand-header">
          <div className="logo-circle-glow">
            <img 
              src="/prepfly-logo.jpg" 
              alt="PrepFly Logo" 
              className="logo-circle-img"
              onError={(e) => { e.target.src = "/prepfly-logo.png"; }}
            />
          </div>
          <h1 className="brand-title">
            Prep<span className="brand-highlight">Fly</span>
          </h1>
          <p className="brand-tagline">
            P R A C T I C E &nbsp;.&nbsp; P R E P A R E &nbsp;.&nbsp; <span style={{ color: '#35c7f0' }}>F L Y</span>
          </p>
        </div>

        {/* Header */}
        <div className="auth-header">
          <h2 className="auth-title">{title}</h2>
          <p className="auth-subtitle">
            {screen === 'login' ? (
              <>Sign in to continue your <span style={{ color: '#35c7f0', fontWeight: 600 }}>growth</span></>
            ) : screen === 'signup' ? (
              <>Start your journey to tech <span style={{ color: '#35c7f0', fontWeight: 600 }}>mastery</span></>
            ) : sub}
          </p>
        </div>


        {/* Google btn – only on login / signup screens */}
        {(screen === "login" || screen === "signup") && (
          <>
            <div id="google-btn-hidden" style={{ display: "none" }} />
            <button className="google-btn" onClick={handleGoogleLogin} type="button" disabled={googleLoading}>
              {googleLoading ? (
                <span className="spinner" style={{borderColor:"rgba(255,255,255,.3)",borderTopColor:"#fff"}} />
              ) : (
                <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              )}
              {googleLoading ? "Signing in…" : "Continue with Google"}
            </button>
            <div className="divider">
              <span className="divider-line"/><span className="divider-text">or</span><span className="divider-line"/>
            </div>
          </>
        )}

        {/* Message box */}
        {message.text && (
          <div className={`message-box message-${message.type}`}>
            {message.type === "error" ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            )}
            {message.text}
          </div>
        )}

        {/* ══ LOGIN ══════════════════════════════════════════════════════ */}
        {screen === "login" && (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="field-group">
              <label className="field-label">Email Address</label>
              <div className="field-wrap">
                <EmailIcon />
                <input type="email" name="email" placeholder="you@example.com"
                  value={formData.email} onChange={handleChange}
                  className="field-input" required autoComplete="email" />
              </div>
            </div>

            <div className="field-group">
              <div className="field-label-row">
                <label className="field-label">Password</label>
                <button type="button" className="forgot-link"
                  onClick={() => { setOtpEmail(formData.email); goTo("forgot-email"); }}>
                  Forgot password?
                </button>
              </div>
              <div className="field-wrap">
                <LockIcon />
                <input type={showPassword ? "text" : "password"} name="password"
                  placeholder="••••••••" value={formData.password} onChange={handleChange}
                  className="field-input" required autoComplete="current-password" />
                <button type="button" className="eye-btn" onClick={() => setShowPassword(p => !p)}>
                  <EyeIcon open={showPassword} />
                </button>
              </div>
            </div>

            <button type="submit" className="submit-btn" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : (
                <>Sign in <span style={{ fontSize: "16px", marginLeft: "4px" }}>→</span></>
              )}
            </button>

            <p style={{textAlign:"center",fontSize:"13px",color:"var(--text-secondary)",marginTop:"4px"}}>
              Prefer no password?{" "}
              <button type="button" className="toggle-btn"
                onClick={() => { setOtpEmail(formData.email); goTo("otp-login"); }}>
                Login with OTP
              </button>
            </p>

            <p className="toggle-text">
              Don't have an account?
              <button type="button" onClick={() => goTo("signup")} className="toggle-btn"> Sign up</button>
            </p>
          </form>
        )}

        {/* ══ LOGIN OTP VERIFY ═══════════════════════════════════════════ */}
        {screen === "login-otp" && (
          <form onSubmit={handleVerifyLoginOtp} className="auth-form">
            <EmailSentBadge onBack={() => goTo("login")} />
            <OtpInput />
            <OtpCountdownBadge />
            <button type="submit" className="submit-btn" disabled={isLoading || otp.length !== 6}>
              {isLoading ? <span className="spinner" /> : "Verify & Sign In"}
            </button>
            <ResendBtn purpose="login" />
          </form>
        )}

        {/* ══ SIGNUP ═════════════════════════════════════════════════════ */}
        {screen === "signup" && (
          <form onSubmit={handleSignup} className="auth-form">
            <div className="field-group">
              <label className="field-label">Full Name</label>
              <div className="field-wrap">
                <UserIcon />
                <input type="text" name="name" placeholder="John Doe"
                  value={formData.name} onChange={handleChange}
                  className="field-input" autoComplete="name" required />
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Email Address</label>
              <div className="field-wrap">
                <EmailIcon />
                <input type="email" name="email" placeholder="you@example.com"
                  value={formData.email} onChange={handleChange}
                  className="field-input" required autoComplete="email" />
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Password</label>
              <div className="field-wrap">
                <LockIcon />
                <input type={showPassword ? "text" : "password"} name="password"
                  placeholder="Min. 6 characters" value={formData.password} onChange={handleChange}
                  className="field-input" required autoComplete="new-password" />
                <button type="button" className="eye-btn" onClick={() => setShowPassword(p => !p)}>
                  <EyeIcon open={showPassword} />
                </button>
              </div>
            </div>

            <button type="submit" className="submit-btn" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : "Create Account"}
            </button>

            <p className="toggle-text">
              Already have an account?
              <button type="button" onClick={() => goTo("login")} className="toggle-btn"> Sign in</button>
            </p>
          </form>
        )}

        {/* ══ SIGNUP OTP VERIFY ══════════════════════════════════════════ */}
        {screen === "signup-otp" && (
          <form onSubmit={handleVerifySignupOtp} className="auth-form">
            <EmailSentBadge onBack={() => goTo("signup")} />
            <OtpInput />
            <OtpCountdownBadge />
            <button type="submit" className="submit-btn" disabled={isLoading || otp.length !== 6}>
              {isLoading ? <span className="spinner" /> : "Verify & Create Account"}
            </button>
            <ResendBtn purpose="signup" />
          </form>
        )}

        {/* ══ PASSWORDLESS OTP LOGIN ═════════════════════════════════════ */}
        {screen === "otp-login" && (
          <form onSubmit={handleRequestOtpLogin} className="auth-form">
            <div className="field-group">
              <label className="field-label">Email Address</label>
              <div className="field-wrap">
                <EmailIcon />
                <input type="email" value={otpEmail} onChange={e => setOtpEmail(e.target.value)}
                  placeholder="you@example.com" className="field-input" required autoFocus />
              </div>
            </div>
            <button type="submit" className="submit-btn" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : "Send OTP"}
            </button>
            <p className="toggle-text">
              Have a password?
              <button type="button" onClick={() => goTo("login")} className="toggle-btn"> Sign in with password</button>
            </p>
          </form>
        )}

        {/* ══ PASSWORDLESS OTP VERIFY ════════════════════════════════════ */}
        {screen === "otp-login-verify" && (
          <form onSubmit={handleVerifyOtpLogin} className="auth-form">
            <EmailSentBadge onBack={() => goTo("otp-login")} />
            <OtpInput />
            <OtpCountdownBadge />
            <button type="submit" className="submit-btn" disabled={isLoading || otp.length !== 6}>
              {isLoading ? <span className="spinner" /> : "Verify & Login"}
            </button>
            <ResendBtn purpose="otp" />
          </form>
        )}

        {/* ══ FORGOT PASSWORD – EMAIL ════════════════════════════════════ */}
        {screen === "forgot-email" && (
          <form onSubmit={handleForgotRequest} className="auth-form">
            <div className="field-group">
              <label className="field-label">Your Email Address</label>
              <div className="field-wrap">
                <EmailIcon />
                <input type="email" value={otpEmail} onChange={e => setOtpEmail(e.target.value)}
                  placeholder="you@example.com" className="field-input" required autoFocus />
              </div>
            </div>
            <button type="submit" className="submit-btn" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : "Send Reset Code"}
            </button>
            <p className="toggle-text">
              Remember it?
              <button type="button" onClick={() => goTo("login")} className="toggle-btn"> Back to login</button>
            </p>
          </form>
        )}

        {/* ══ FORGOT PASSWORD – OTP ══════════════════════════════════════ */}
        {screen === "forgot-otp" && (
          <form onSubmit={handleVerifyResetOtp} className="auth-form">
            <EmailSentBadge onBack={() => goTo("forgot-email")} />
            <OtpInput />
            <OtpCountdownBadge />
            <button type="submit" className="submit-btn" disabled={isLoading || otp.length !== 6}>
              {isLoading ? <span className="spinner" /> : "Verify Code"}
            </button>
            <ResendBtn purpose="reset" />
          </form>
        )}

        {/* ══ RESET PASSWORD ═════════════════════════════════════════════ */}
        {screen === "reset-password" && (
          <form onSubmit={handleResetPassword} className="auth-form">
            <div className="field-group">
              <label className="field-label">New Password</label>
              <div className="field-wrap">
                <LockIcon />
                <input type={showNewPass ? "text" : "password"} value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="Min. 6 characters" className="field-input" required autoFocus />
                <button type="button" className="eye-btn" onClick={() => setShowNewPass(p => !p)}>
                  <EyeIcon open={showNewPass} />
                </button>
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Confirm New Password</label>
              <div className="field-wrap">
                <LockIcon />
                <input type={showNewPass ? "text" : "password"} value={confirmPass}
                  onChange={e => setConfirmPass(e.target.value)}
                  placeholder="Re-enter password" className="field-input" required />
              </div>
            </div>

            {newPassword && confirmPass && newPassword !== confirmPass && (
              <p style={{fontSize:"12px",color:"var(--danger)",marginTop:"-8px"}}>
                ⚠️ Passwords don't match
              </p>
            )}

            <button type="submit" className="submit-btn"
              disabled={isLoading || newPassword !== confirmPass || newPassword.length < 6}>
              {isLoading ? <span className="spinner" /> : "Reset Password"}
            </button>
          </form>
        )}

        {/* Terms */}
        {(screen === "login" || screen === "signup") && (
          <p className="terms-text">
            By continuing, you agree to our{" "}
            <a href="#" className="terms-link">Terms</a> &amp;{" "}
            <a href="#" className="terms-link">Privacy Policy</a>
          </p>
        )}
      </div>
    </div>
  );
}