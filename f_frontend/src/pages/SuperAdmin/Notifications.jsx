import React, { useState } from 'react';
import { sendSuperAdminNotification } from '../../services/superAdminAPI';

export default function Notifications() {
  const [form, setForm] = useState({
    title: '',
    message: '',
    target: 'All Organizations',
    send_email: true,
    send_push: true
  });
  const [toast, setToast] = useState("");

  const handleSend = async (e) => {
    e.preventDefault();
    try {
      await sendSuperAdminNotification(form);
      setToast("📢 Broadcast notification sent to target group!");
      setTimeout(() => setToast(""), 4000);
      setForm({ title: '', message: '', target: 'All Organizations', send_email: true, send_push: true });
    } catch (e) {
      alert("Failed to send broadcast");
    }
  };

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #ec4899, #8b5cf6)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000 }}>
          {toast}
        </div>
      )}

      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>📢 Targeted Broadcast & Notification Center</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "20px" }}>Dispatch system announcements to all institutions, specific admins, or candidate groups.</p>

        <form onSubmit={handleSend} style={{ display: "flex", flexDirection: "column", gap: "16px", fontSize: "13px" }}>
          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>NOTIFICATION TITLE *</label>
            <input type="text" required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="e.g. Scheduled System Upgrade & Maintenance Window" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>MESSAGE BODY *</label>
            <textarea rows="4" required value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="Enter message details..." style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>TARGET AUDIENCE</label>
            <select value={form.target} onChange={e => setForm({ ...form, target: e.target.value })} style={{ width: "100%", background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px" }}>
              <option value="All Organizations">All Organizations & Colleges</option>
              <option value="Colleges Only">Colleges & Universities Only</option>
              <option value="Companies Only">Recruiter Companies Only</option>
              <option value="All Students">All Platform Candidates</option>
            </select>
          </div>

          <div style={{ display: "flex", gap: "20px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
              <input type="checkbox" checked={form.send_email} onChange={e => setForm({ ...form, send_email: e.target.checked })} style={{ accentColor: "#ec4899" }} />
              <span>📧 Send Email Notification</span>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
              <input type="checkbox" checked={form.send_push} onChange={e => setForm({ ...form, send_push: e.target.checked })} style={{ accentColor: "#ec4899" }} />
              <span>🔔 Send Push Notification</span>
            </label>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", fontSize: "14px", fontWeight: 900, background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", marginTop: "8px" }}>
            Dispatch Global Notification →
          </button>
        </form>
      </div>
    </div>
  );
}
