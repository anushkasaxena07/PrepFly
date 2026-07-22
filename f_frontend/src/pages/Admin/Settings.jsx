import React, { useState, useEffect } from 'react';
import { getAdminSettings, saveAdminSettings } from '../../services/adminAPI';

export default function Settings() {
  const [settings, setSettings] = useState({
    two_factor_enabled: true,
    email_notifications: true,
    language: 'English'
  });
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetchSettings();
    document.documentElement.setAttribute("data-theme", "dark");
    document.body.classList.remove("light-mode");
    localStorage.removeItem("theme");
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getAdminSettings();
      setSettings(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    try {
      await saveAdminSettings(settings);
      setToast("Settings saved successfully!");
      setTimeout(() => setToast(""), 4000);
    } catch (e) {
      alert("Failed to save settings");
    }
  };

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000 }}>
          {toast}
        </div>
      )}

      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>⚙️ Admin Security & System Settings</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "24px" }}>Manage authentication security, notification channels, and portal preferences.</p>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px", fontSize: "13px" }}>
          
          {/* TWO FACTOR AUTH */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.03)", padding: "14px 18px", borderRadius: "12px" }}>
            <div>
              <div style={{ fontWeight: 800, color: "#fff" }}>Enable Two-Factor Authentication (2FA)</div>
              <div style={{ fontSize: "11px", color: "var(--text2)" }}>Require TOTP / Authenticator code on admin sign in.</div>
            </div>
            <input 
              type="checkbox" 
              checked={settings.two_factor_enabled} 
              onChange={e => setSettings({ ...settings, two_factor_enabled: e.target.checked })} 
              style={{ width: "18px", height: "18px", accentColor: "#00c4a7" }}
            />
          </div>

          {/* EMAIL NOTIFICATIONS */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.03)", padding: "14px 18px", borderRadius: "12px" }}>
            <div>
              <div style={{ fontWeight: 800, color: "#fff" }}>Email Activity Digests</div>
              <div style={{ fontSize: "11px", color: "var(--text2)" }}>Receive weekly institutional candidate performance summaries.</div>
            </div>
            <input 
              type="checkbox" 
              checked={settings.email_notifications} 
              onChange={e => setSettings({ ...settings, email_notifications: e.target.checked })} 
              style={{ width: "18px", height: "18px", accentColor: "#00c4a7" }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "12px" }}>
            <button className="btn btn-primary" onClick={handleSave} style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
              Save Settings
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
