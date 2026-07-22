import React, { useState } from 'react';

export default function Profile() {
  const [profile, setProfile] = useState({
    name: 'Alex Vance',
    email: 'superadmin@prepfly.io',
    role: 'SUPER_ADMIN'
  });
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });

  const handlePasswordChange = (e) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
      alert("New password and confirm password do not match!");
      return;
    }
    alert("Super Admin password updated successfully!");
    setPasswords({ current: '', new: '', confirm: '' });
  };

  return (
    <div style={{ maxWidth: "650px", margin: "0 auto" }}>
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ width: "72px", height: "72px", borderRadius: "50%", background: "linear-gradient(135deg, #ec4899, #8b5cf6)", color: "#fff", fontSize: "28px", fontWeight: 900, display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: "10px" }}>
            AV
          </div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>{profile.name}</h2>
          <div style={{ fontSize: "12px", color: "#ec4899", fontWeight: 800, textTransform: "uppercase", marginTop: "2px" }}>Platform Owner ({profile.role})</div>
        </div>

        <form onSubmit={handlePasswordChange} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>SUPER ADMIN EMAIL</label>
            <input type="email" disabled value={profile.email} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "var(--text2)" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>CURRENT PASSWORD</label>
            <input type="password" required value={passwords.current} onChange={e => setPasswords({ ...passwords, current: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>NEW MASTER PASSWORD</label>
            <input type="password" required value={passwords.new} onChange={e => setPasswords({ ...passwords, new: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>CONFIRM NEW MASTER PASSWORD</label>
            <input type="password" required value={passwords.confirm} onChange={e => setPasswords({ ...passwords, confirm: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", fontSize: "14px", fontWeight: 900, background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", marginTop: "8px" }}>
            Update Super Admin Password →
          </button>
        </form>
      </div>
    </div>
  );
}
