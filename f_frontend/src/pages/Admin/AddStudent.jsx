import React, { useState } from 'react';
import { createAdminStudent } from '../../services/adminAPI';

export default function AddStudent() {
  const [form, setForm] = useState({
    name: '',
    roll_number: '',
    email: '',
    password: '',
    phone: '',
    department: 'Computer Science',
    semester: 'Sem 6',
    year: '3rd',
    gender: 'Male',
    subscription: 'FREE'
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSuccess("");
    try {
      await createAdminStudent(form);
      setSuccess("🎉 Student onboarded successfully into your organization!");
      setForm({
        name: '',
        roll_number: '',
        email: '',
        password: '',
        phone: '',
        department: 'Computer Science',
        semester: 'Sem 6',
        year: '3rd',
        gender: 'Male',
        subscription: 'FREE'
      });
    } catch (e) {
      alert(e.message || "Failed to create student");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto" }}>
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>➕ Student Onboarding Form</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "20px" }}>Create a new candidate record assigned strictly to your organization.</p>

        {success && (
          <div style={{ background: "rgba(0,196,167,0.15)", border: "1px solid rgba(0,196,167,0.3)", color: "var(--cyan)", padding: "12px", borderRadius: "10px", marginBottom: "16px", fontWeight: 800, fontSize: "13px" }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "13px" }}>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>STUDENT FULL NAME *</label>
            <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Aarav Sharma" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>ROLL NUMBER *</label>
            <input type="text" required value={form.roll_number} onChange={e => setForm({ ...form, roll_number: e.target.value })} placeholder="CS2026101" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>EMAIL ADDRESS *</label>
            <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="student@org.edu" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>INITIAL PASSWORD</label>
            <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="Default: Student@123" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>PHONE NUMBER</label>
            <input type="text" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+91 9876543210" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>DEPARTMENT</label>
            <select value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} style={{ width: "100%", background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 14px" }}>
              <option value="Computer Science">Computer Science</option>
              <option value="Information Tech">Information Tech</option>
              <option value="Electronics">Electronics</option>
              <option value="Mechanical">Mechanical</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>SEMESTER & YEAR</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <select value={form.semester} onChange={e => setForm({ ...form, semester: e.target.value })} style={{ flex: 1, background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 8px" }}>
                <option value="Sem 2">Sem 2</option>
                <option value="Sem 4">Sem 4</option>
                <option value="Sem 6">Sem 6</option>
                <option value="Sem 8">Sem 8</option>
              </select>
              <select value={form.year} onChange={e => setForm({ ...form, year: e.target.value })} style={{ flex: 1, background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px 8px" }}>
                <option value="1st">1st Year</option>
                <option value="2nd">2nd Year</option>
                <option value="3rd">3rd Year</option>
                <option value="4th">4th Year</option>
              </select>
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", marginTop: "12px" }}>
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", fontSize: "14px", fontWeight: 800, background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none" }}>
              {loading ? "⌛ Registering Student..." : "Register & Onboard Student →"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
