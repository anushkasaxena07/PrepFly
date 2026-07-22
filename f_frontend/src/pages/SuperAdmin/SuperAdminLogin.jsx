import React, { useState } from 'react';
import { superAdminLogin } from '../../services/superAdminAPI';

export default function SuperAdminLogin() {
  const [email, setEmail] = useState("saxenaanushka9645@gmail.com");
  const [password, setPassword] = useState("superadmin123");
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
      background: "#050811",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      position: "relative",
      overflow: "hidden"
    }}>
      <div style={{
        position: "absolute",
        width: "700px",
        height: "700px",
        background: "radial-gradient(circle, rgba(236,72,153,0.18) 0%, transparent 70%)",
        top: "-200px",
        left: "-200px",
        borderRadius: "50%",
        pointerEvents: "none"
      }} />

      <div style={{
        background: "rgba(12,18,32,0.92)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(236,72,153,0.3)",
        borderRadius: "20px",
        padding: "36px",
        maxWidth: "420px",
        width: "100%",
        boxShadow: "0 24px 64px rgba(0,0,0,0.7)",
        zIndex: 10
      }}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{
            width: "52px",
            height: "52px",
            borderRadius: "14px",
            background: "linear-gradient(135deg, #ec4899, #8b5cf6)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "26px",
            marginBottom: "12px",
            boxShadow: "0 8px 24px rgba(236,72,153,0.4)"
          }}>
            👑
          </div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0 }}>Super Admin Portal</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>
            Platform Owner & System Master Console
          </p>
        </div>

        {error && (
          <div style={{ background: "rgba(255,84,114,0.15)", border: "1px solid rgba(255,84,114,0.3)", color: "#ff5472", padding: "10px 14px", borderRadius: "10px", fontSize: "12px", marginBottom: "16px", textAlign: "center" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "#ec4899", marginBottom: "6px", letterSpacing: "1px" }}>
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
                background: "#0c1220",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#fff",
                fontSize: "14px"
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "#ec4899", marginBottom: "6px", letterSpacing: "1px" }}>
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
                background: "#0c1220",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#fff",
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
              fontWeight: 900,
              background: "linear-gradient(135deg, #ec4899, #8b5cf6)",
              border: "none",
              marginTop: "8px"
            }}
          >
            {loading ? "⚡ Authenticating Owner..." : "Sign In to Super Admin Console →"}
          </button>
        </form>

        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: "11px", color: "var(--text2)", textAlign: "center" }}>
          👑 Restricted Access • Super Admin Master Authentication Only
        </div>
      </div>
    </div>
  );
}
