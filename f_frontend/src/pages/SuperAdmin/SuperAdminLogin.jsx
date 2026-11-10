import React, { useState } from 'react';
import { superAdminLogin } from '../../services/superAdminAPI';
import { ThemeToggleButton, usePrepFlyTheme } from '../../components/ui/ThemeContext';

export default function SuperAdminLogin() {
  const { isSunrise } = usePrepFlyTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await superAdminLogin(email, password);
      localStorage.setItem("superadmin_access_token", data.access_token);
      localStorage.setItem("superadmin_user", JSON.stringify(data.superadmin));
      
      window.location.href = "/superadmin/dashboard";
    } catch (err) {
      setError(err.message || "Failed to authenticate Super Admin credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: isSunrise
        ? "linear-gradient(160deg, #fdf7f3 0%, #faece1 60%, #fcf8f4 100%)"
        : "linear-gradient(160deg, #090c1a 0%, #121633 60%, #0b0e1a 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      position: "relative",
      overflow: "hidden"
    }}>
      <div style={{ position: "fixed", top: "20px", right: "24px", zIndex: 50 }}>
        <ThemeToggleButton />
      </div>
      <div style={{
        position: "absolute",
        width: "700px",
        height: "700px",
        background: isSunrise
          ? "radial-gradient(circle, rgba(234,88,12,0.16) 0%, transparent 70%)"
          : "radial-gradient(circle, rgba(124,58,237,0.28) 0%, transparent 70%)",
        top: "-200px",
        left: "-200px",
        borderRadius: "50%",
        pointerEvents: "none"
      }} />

      <div style={{
        background: "#ffffff",
        border: "1px solid #e5e8f2",
        borderRadius: "22px",
        padding: "36px",
        maxWidth: "420px",
        width: "100%",
        boxShadow: "0 24px 64px rgba(0,0,0,0.48)",
        zIndex: 10,
        color: "#0f172a"
      }}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{
            width: "52px",
            height: "52px",
            borderRadius: "14px",
            background: "linear-gradient(135deg, #6d28d9, #8b5cf6)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
            color: "#ffffff",
            marginBottom: "12px",
            boxShadow: "0 8px 24px rgba(109,40,217,0.35)"
          }}>
            👑
          </div>
          <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", margin: 0 }}>Super Admin Portal</h2>
          <p style={{ fontSize: "12.5px", color: "#64748b", marginTop: "4px" }}>
            Platform Owner &amp; System Master Console
          </p>
        </div>

        {error && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#dc2626", padding: "10px 14px", borderRadius: "10px", fontSize: "12px", marginBottom: "16px", textAlign: "center" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "#6d28d9", marginBottom: "6px", letterSpacing: "1px" }}>
              SUPER ADMIN EMAIL
            </label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="superadmin@prepfly.io"
              style={{
                width: "100%",
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#0f172a",
                fontSize: "14px"
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "#6d28d9", marginBottom: "6px", letterSpacing: "1px" }}>
              MASTER PASSWORD
            </label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: "100%",
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#0f172a",
                fontSize: "14px"
              }}
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="btn btn-primary"
            style={{
              width: "100%",
              justifyContent: "center",
              padding: "12px",
              fontSize: "14px",
              fontWeight: 800,
              background: "linear-gradient(135deg, #6d28d9, #7c3aed)",
              border: "none",
              marginTop: "8px"
            }}
          >
            {loading ? "Authenticating Owner..." : "Sign In to Super Admin Console →"}
          </button>
        </form>

        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid #e5e8f2", fontSize: "11px", color: "#64748b", textAlign: "center" }}>
          Restricted Access · Super Admin Master Authentication Only
        </div>
      </div>
    </div>
  );
}
