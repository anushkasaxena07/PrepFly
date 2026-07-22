import React, { useState } from 'react';

export default function AnnouncementModal({ isOpen, onClose, onSend }) {
  const [form, setForm] = useState({
    title: '',
    message: '',
    target_dept: 'All Departments',
    target_sem: 'All Semesters',
    send_email: true,
    send_notif: true
  });

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSend(form);
    onClose();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
      <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "500px", width: "100%", color: "#fff", boxShadow: "0 24px 64px rgba(0,0,0,0.7)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>📢 Dispatch Announcement</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "18px", cursor: "pointer" }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Announcement Title</label>
            <input 
              type="text" 
              required
              value={form.title} 
              onChange={e => setForm({ ...form, title: e.target.value })} 
              placeholder="e.g. Mandatory Placement Assessment Drive"
              style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
            />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Message Content</label>
            <textarea 
              rows="4"
              required
              value={form.message} 
              onChange={e => setForm({ ...form, message: e.target.value })} 
              placeholder="Enter announcement details..."
              style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Target Department</label>
              <select 
                value={form.target_dept} 
                onChange={e => setForm({ ...form, target_dept: e.target.value })}
                style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
              >
                <option value="All Departments">All Departments</option>
                <option value="Computer Science">Computer Science</option>
                <option value="Information Tech">Information Tech</option>
                <option value="Electronics">Electronics</option>
                <option value="Mechanical">Mechanical</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Target Semester</label>
              <select 
                value={form.target_sem} 
                onChange={e => setForm({ ...form, target_sem: e.target.value })}
                style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
              >
                <option value="All Semesters">All Semesters</option>
                <option value="Sem 2">Sem 2</option>
                <option value="Sem 4">Sem 4</option>
                <option value="Sem 6">Sem 6</option>
                <option value="Sem 8">Sem 8</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", gap: "16px", marginTop: "4px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
              <input type="checkbox" checked={form.send_email} onChange={e => setForm({ ...form, send_email: e.target.checked })} />
              <span>📧 Send Email Notification</span>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
              <input type="checkbox" checked={form.send_notif} onChange={e => setForm({ ...form, send_notif: e.target.checked })} />
              <span>🔔 Send Push Notification</span>
            </label>
          </div>

          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "16px" }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Publish Announcement</button>
          </div>
        </form>
      </div>
    </div>
  );
}
