import React, { useState, useEffect } from "react";
import axios from "axios";
import "./Login.css";
import { useNavigate } from "react-router-dom";

// Debug logging
console.log("=== ENV DEBUG ===");
console.log("ALL ENV:", import.meta.env);
console.log("VITE_GOOGLE_CLIENT_ID:", import.meta.env.VITE_GOOGLE_CLIENT_ID);
console.log("MODE:", import.meta.env.MODE);
console.log("================");

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;// set in your .env
console.log("Google Client ID loaded:", GOOGLE_CLIENT_ID); // Add this debug line
export default function Login() {
  const [isLogin, setIsLogin]       = useState(true);
  const [formData, setFormData]     = useState({ name: "", email: "", password: "" });
  const [message, setMessage]       = useState({ text: "", type: "" });
  const [isLoading, setIsLoading]   = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [showPassword, setShowPassword]   = useState(false);
  const navigate = useNavigate();

  /* ── Load Google Identity Services script once ── */
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, []);

  /* ── Google callback — called after user picks account ── */
  const handleGoogleCallback = async (googleResponse) => {
    setGoogleLoading(true);
    setMessage({ text: "", type: "" });
    try {
      const { data } = await axios.post(
        "http://localhost:5000/auth/google/verify",
        { credential: googleResponse.credential },
        { withCredentials: true }
      );

      localStorage.setItem("email",   data.email);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("user", JSON.stringify({
        email:  data.email,
        name:   data.name   || "",
        role:   data.role   || "",
        phone:  data.phone  || "",
        avatar: data.avatar || "",
        _id:    data.user_id,
      }));

      setMessage({ text: "Signed in with Google!", type: "success" });
      setTimeout(() => navigate("/dashboard"), 800);
    } catch (err) {
      setMessage({
        text: err.response?.data?.error || "Google sign-in failed. Please try again.",
        type: "error",
      });
    } finally {
      setGoogleLoading(false);
    }
  };

  /* ── Open Google account picker popup reliably ── */
  const handleGoogleLogin = () => {
    if (!window.google) {
      setMessage({ text: "Google SDK not loaded yet, please wait a moment.", type: "error" });
      return;
    }
    if (!GOOGLE_CLIENT_ID) {
      setMessage({ text: "Google Client ID is not configured. Check your .env file.", type: "error" });
      return;
    }

    // Use oauth2 token client — opens a real popup window, never suppressed
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: GOOGLE_CLIENT_ID,
      scope: "openid email profile",
      callback: "", // handled via id flow below
    });

    // Initialize id flow for the credential (JWT) we actually need
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback:  handleGoogleCallback,
      ux_mode:   "popup",
    });

    // Render an invisible button and programmatically click it
    // This is the officially supported way to trigger popup on button click
    const container = document.getElementById("google-btn-hidden");
    if (container) {
      container.innerHTML = "";
      window.google.accounts.id.renderButton(container, {
        type: "standard",
        size: "large",
      });
      const btn = container.querySelector("div[role=button]");
      if (btn) btn.click();
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({ name: "", email: "", password: "" });
    setMessage({ text: "", type: "" });
  };

  const handleChange = (e) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.email || !formData.password) {
      setMessage({ text: "All fields are required.", type: "error" });
      return;
    }
    setIsLoading(true);
    try {
      if (isLogin) {
        const { data } = await axios.post("http://localhost:5000/login", formData, {
          withCredentials: true,
        });
        setMessage({ text: data.message, type: "success" });
        localStorage.setItem("email",   data.email);
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user", JSON.stringify({
          email:  data.email,
          name:   data.name   || "",
          role:   data.role   || "",
          phone:  data.phone  || "",
          avatar: data.avatar || "",
          _id:    data.user_id,
        }));
        navigate("/dashboard");
      } else {
        const { data } = await axios.post("http://localhost:5000/register", formData);
        setMessage({
          text: data.message || "Account created! Please check your email to verify.",
          type: "success",
        });
        setTimeout(() => {
          setIsLogin(true);
          setFormData({ name: "", email: formData.email, password: "" });
        }, 2000);
      }
    } catch (err) {
      setMessage({
        text: err.response?.data?.error || "Something went wrong. Please try again.",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-root">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="auth-card">
        {/* Brand */}
        <div className="brand">
          <div className="brand-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
              <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="brand-name">Luminary</span>
        </div>

        {/* Heading */}
        <div className="auth-header">
          <h1 className="auth-title">{isLogin ? "Welcome back" : "Create account"}</h1>
          <p className="auth-subtitle">
            {isLogin ? "Sign in to continue your journey" : "Start building something great today"}
          </p>
        </div>

        {/* Hidden container for Google's renderButton — triggers real popup */}
        <div id="google-btn-hidden" style={{ display: "none" }} />

        {/* Google Button */}
        <button
          className="google-btn"
          onClick={handleGoogleLogin}
          type="button"
          disabled={googleLoading}
        >
          {googleLoading ? (
            <span className="spinner" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "#fff" }} />
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

        {/* Divider */}
        <div className="divider">
          <span className="divider-line" />
          <span className="divider-text">or</span>
          <span className="divider-line" />
        </div>

        {/* Message */}
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

        {/* Form */}
        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <div className="field-group">
              <label className="field-label">Full Name</label>
              <div className="field-wrap">
                <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
                <input type="text" name="name" placeholder="John Doe" value={formData.name}
                  onChange={handleChange} className="field-input" autoComplete="name" />
              </div>
            </div>
          )}

          <div className="field-group">
            <label className="field-label">Email Address</label>
            <div className="field-wrap">
              <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
              </svg>
              <input type="email" name="email" placeholder="you@example.com" value={formData.email}
                onChange={handleChange} className="field-input" required autoComplete="email" />
            </div>
          </div>

          <div className="field-group">
            <div className="field-label-row">
              <label className="field-label">Password</label>
              {isLogin && <button type="button" className="forgot-link">Forgot password?</button>}
            </div>
            <div className="field-wrap">
              <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input type={showPassword ? "text" : "password"} name="password" placeholder="••••••••"
                value={formData.password} onChange={handleChange} className="field-input" required
                autoComplete={isLogin ? "current-password" : "new-password"} />
              <button type="button" className="eye-btn" onClick={() => setShowPassword(!showPassword)}
                aria-label="Toggle password visibility">
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button type="submit" className={`submit-btn ${isLoading ? "loading" : ""}`} disabled={isLoading}>
            {isLoading ? <span className="spinner" /> : isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>

        <p className="toggle-text">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button type="button" onClick={toggleMode} className="toggle-btn">
            {isLogin ? " Sign up" : " Sign in"}
          </button>
        </p>

        <p className="terms-text">
          By continuing, you agree to our{" "}
          <a href="#" className="terms-link">Terms</a> &amp;{" "}
          <a href="#" className="terms-link">Privacy Policy</a>
        </p>
      </div>
    </div>
  );
}