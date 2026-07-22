import React, { useState, useEffect } from 'react';

export default function StudentModal({ student, isOpen, onClose, onSave }) {
  const [form, setForm] = useState({
    name: '',
    roll_number: '',
    email: '',
    phone: '',
    department: 'Computer Science',
    semester: 'Sem 6',
    year: '3rd',
    gender: 'Male',
    subscription: 'FREE',
    status: 'Active'
  });

  useEffect(() => {
    if (student) {
      setForm({ ...student });
    }
  }, [student]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
      <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "540px", width: "100%", color: "#fff", boxShadow: "0 24px 64px rgba(0,0,0,0.7)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>
            {student?.id ? "✏️ Edit Student Record" : "🎓 Add New Student"}
          </h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text2)", fontSize: "18px", cursor: "pointer" }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "13px" }}>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Full Name</label>
            <input 
              type="text" 
              required
              value={form.name} 
              onChange={e => setForm({ ...form, name: e.target.value })} 
              style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
            />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Roll Number</label>
            <input 
              type="text" 
              required
              value={form.roll_number} 
              onChange={e => setForm({ ...form, roll_number: e.target.value })} 
              style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
            />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Email</label>
            <input 
              type="email" 
              required
              value={form.email} 
              onChange={e => setForm({ ...form, email: e.target.value })} 
              style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
            />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Department</label>
            <select 
              value={form.department} 
              onChange={e => setForm({ ...form, department: e.target.value })} 
              style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
            >
              <option value="Computer Science">Computer Science</option>
              <option value="Information Tech">Information Tech</option>
              <option value="Electronics">Electronics</option>
              <option value="Mechanical">Mechanical</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Semester</label>
            <select 
              value={form.semester} 
              onChange={e => setForm({ ...form, semester: e.target.value })} 
              style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
            >
              <option value="Sem 2">Sem 2</option>
              <option value="Sem 4">Sem 4</option>
              <option value="Sem 6">Sem 6</option>
              <option value="Sem 8">Sem 8</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Subscription</label>
            <select 
              value={form.subscription} 
              onChange={e => setForm({ ...form, subscription: e.target.value })} 
              style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
            >
              <option value="FREE">FREE</option>
              <option value="PREMIUM">PREMIUM</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Status</label>
            <select 
              value={form.status} 
              onChange={e => setForm({ ...form, status: e.target.value })} 
              style={{ width: "100%", background: "#141d30", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}
            >
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>

          <div style={{ gridColumn: "1 / -1", display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "16px" }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Save Student</button>
          </div>
        </form>
      </div>
    </div>
  );
}
