import React, { useState } from 'react';
import { adminLogin } from '../../services/adminAPI';

export default function AdminLogin() {
  const [email, setEmail] = useState("admin@stanford.edu");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await adminLogin(email, password);
      localStorage.setItem("admin_access_token", data.access_token);
      localStorage.setItem("admin_org_id", data.admin.organization_id);
      localStorage.setItem("admin_user", JSON.stringify(data.admin));
      localStorage.setItem("admin_organization", JSON.stringify(data.organization));
      
      window.location.href = "/admin/dashboard";
    } catch (err) {
      setError(err.message || "Failed to authenticate admin credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#070b14",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      position: "relative",
      overflow: "hidden"
    }}>
      <div style={{
        position: "absolute",
        width: "600px",
        height: "600px",
        background: "radial-gradient(circle, rgba(124,79,224,0.15) 0%, transparent 70%)",
        top: "-150px",
        left: "-150px",
        borderRadius: "50%",
        pointerEvents: "none"
      }} />

      <div style={{
        background: "rgba(12,18,32,0.9)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: "20px",
        padding: "36px",
        maxWidth: "420px",
        width: "100%",
        boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
        zIndex: 10
      }}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{
            width: "48px",
            height: "48px",
            borderRadius: "12px",
            background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
            marginBottom: "12px",
            boxShadow: "0 8px 24px rgba(124,79,224,0.3)"
          }}>
            🏛
          </div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0 }}>Organization Admin Login</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>
            College & Recruiter Administrative Portal
          </p>
        </div>

        {error && (
          <div style={{ background: "rgba(255,84,114,0.15)", border: "1px solid rgba(255,84,114,0.3)", color: "#ff5472", padding: "10px 14px", borderRadius: "10px", fontSize: "12px", marginBottom: "16px", textAlign: "center" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--text2)", marginBottom: "6px" }}>
              ADMIN EMAIL
            </label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@stanford.edu"
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
            <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--text2)", marginBottom: "6px" }}>
              PASSWORD
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
              fontWeight: 800,
              background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
              border: "none",
              marginTop: "8px"
            }}
          >
            {loading ? "🔐 Authenticating..." : "Sign In to Admin Dashboard →"}
          </button>
        </form>

        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: "11px", color: "var(--text2)", textAlign: "center" }}>
          🔒 Multi-Tenant Encrypted Isolation • Access Restricted to Authorized Institution Admins
        </div>
      </div>
    </div>
  );
}
