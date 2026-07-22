import React, { useState, useEffect } from 'react';
import { getSuperAdminSettings, saveSuperAdminSettings } from '../../services/superAdminAPI';

export default function PlatformSettings() {
  const [settings, setSettings] = useState({
    platform_name: 'PrepFly Enterprise SaaS Platform',
    contact_email: 'support@prepfly.io',
    contact_phone: '+1 (800) 555-0199',
    timezone: 'UTC',
    maintenance_mode: false,
    jwt_expiry_hours: 24,
    rate_limit_rpm: 120
  });
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getSuperAdminSettings();
      setSettings(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    try {
      await saveSuperAdminSettings(settings);
      setToast("Platform Settings saved successfully!");
      setTimeout(() => setToast(""), 4000);
    } catch (e) {
      alert("Failed to save settings");
    }
  };

  return (
    <div style={{ maxWidth: "750px", margin: "0 auto" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #ec4899, #8b5cf6)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000 }}>
          {toast}
        </div>
      )}

      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>⚙️ Global Platform Governance & Security Settings</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "24px" }}>Manage platform branding, maintenance toggles, JWT token expiration, and database backup controls.</p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "13px" }}>
          
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>PLATFORM BRAND NAME</label>
            <input type="text" value={settings.platform_name} onChange={e => setSettings({ ...settings, platform_name: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>SUPPORT CONTACT EMAIL</label>
            <input type="email" value={settings.contact_email} onChange={e => setSettings({ ...settings, contact_email: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>SUPPORT PHONE</label>
            <input type="text" value={settings.contact_phone} onChange={e => setSettings({ ...settings, contact_phone: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>JWT EXPIRATION (HOURS)</label>
            <input type="number" value={settings.jwt_expiry_hours} onChange={e => setSettings({ ...settings, jwt_expiry_hours: Number(e.target.value) })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>API RATE LIMIT (RPM)</label>
            <input type="number" value={settings.rate_limit_rpm} onChange={e => setSettings({ ...settings, rate_limit_rpm: Number(e.target.value) })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div style={{ gridColumn: "1 / -1", background: "rgba(255,84,114,0.08)", border: "1px solid rgba(255,84,114,0.2)", borderRadius: "12px", padding: "14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 800, color: "#ff5472" }}>Maintenance Mode</div>
              <div style={{ fontSize: "11px", color: "var(--text2)" }}>Temporarily block candidate & admin logins during system upgrades.</div>
            </div>
            <input type="checkbox" checked={settings.maintenance_mode} onChange={e => setSettings({ ...settings, maintenance_mode: e.target.checked })} style={{ width: "18px", height: "18px", accentColor: "#ff5472" }} />
          </div>

          <div style={{ gridColumn: "1 / -1", display: "flex", gap: "10px", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
            <button type="button" className="btn btn-ghost" onClick={() => alert("Snapshotting PostgreSQL Database Backup...")}>
              💾 Trigger DB Backup Snapshot
            </button>
            <button className="btn btn-primary" onClick={handleSave} style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", fontWeight: 900 }}>
              Save Governance Settings
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
