import React, { useState } from "react";
import axios from "axios";
import "./Login.css";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ name: "", email: "", password: "" });
  const [message, setMessage] = useState({ text: "", type: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({ name: "", email: "", password: "" });
    setMessage({ text: "", type: "" });
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.email || !formData.password) {
      setMessage({ text: "All fields are required.", type: "error" });
      return;
    }

    setIsLoading(true);
    try {
      if (isLogin) {
        // ── Login ──────────────────────────────────────────────
        const response = await axios.post("http://localhost:5000/login", formData);
        setMessage({ text: response.data.message, type: "success" });

        // Store user info in localStorage for use across pages
        localStorage.setItem("email",   response.data.email);
        localStorage.setItem("user_id", response.data.user_id);
        localStorage.setItem("user", JSON.stringify({
          email:  response.data.email,
          name:   response.data.name   || "",
          role:   response.data.role   || "",
          phone:  response.data.phone  || "",
          avatar: response.data.avatar || "",
          _id:    response.data.user_id,
        }));

        navigate("/dashboard");

      } else {
        // ── Register ───────────────────────────────────────────
        const response = await axios.post("http://localhost:5000/register", formData);
        // 201 = created successfully
        setMessage({
          text: response.data.message || "Account created! Please check your email to verify.",
          type: "success",
        });
        // Switch to login mode after successful registration
        setTimeout(() => {
          setIsLogin(true);
          setFormData({ name: "", email: formData.email, password: "" });
        }, 2000);
      }
    } catch (error) {
      setMessage({
        text: error.response?.data?.error || "Something went wrong. Please try again.",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Redirect to your backend Google OAuth route
    window.location.href = "http://localhost:5000/auth/google";
  };

  return (
    <div className="auth-root">
      {/* Animated background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="auth-card">
        {/* Logo / Brand */}
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
          <h1 className="auth-title">
            {isLogin ? "Welcome back" : "Create account"}
          </h1>
          <p className="auth-subtitle">
            {isLogin
              ? "Sign in to continue your journey"
              : "Start building something great today"}
          </p>
        </div>

        {/* Google Button */}
        <button className="google-btn" onClick={handleGoogleLogin} type="button">
          <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
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
                <input
                  type="text"
                  name="name"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={handleChange}
                  className="field-input"
                  autoComplete="name"
                />
              </div>
            </div>
          )}

          <div className="field-group">
            <label className="field-label">Email Address</label>
            <div className="field-wrap">
              <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
              </svg>
              <input
                type="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                className="field-input"
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="field-group">
            <div className="field-label-row">
              <label className="field-label">Password</label>
              {isLogin && (
                <button type="button" className="forgot-link">Forgot password?</button>
              )}
            </div>
            <div className="field-wrap">
              <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                className="field-input"
                required
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
              <button
                type="button"
                className="eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label="Toggle password visibility"
              >
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>
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
            {isLoading ? (
              <span className="spinner" />
            ) : (
              isLogin ? "Sign In" : "Create Account"
            )}
          </button>
        </form>

        {/* Toggle */}
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