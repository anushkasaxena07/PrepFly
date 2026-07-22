import React, { useState } from 'react';
import { createSuperAdminOrganization } from '../../services/superAdminAPI';

export default function CreateOrganization({ onDone }) {
  const [form, setForm] = useState({
    name: '',
    type: 'College',
    email: '',
    phone: '',
    website: '',
    address: '',
    subscription_plan: 'ENTERPRISE',
    admin_name: '',
    admin_email: '',
    temp_password: 'admin123'
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSuccess("");

    try {
      await createSuperAdminOrganization(form);
      setSuccess("🎉 Organization, Admin Account & Enterprise Subscription created atomically!");
      setTimeout(() => {
        if (onDone) onDone();
      }, 1500);
    } catch (err) {
      alert(err.message || "Failed to create organization");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto" }}>
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.3)", borderRadius: "16px", padding: "28px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>🏢 Create New Organization & Admin</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "20px" }}>Atomically registers the Organization, provisions the primary Admin account, and assigns a SaaS subscription tier.</p>

        {success && (
          <div style={{ background: "rgba(0,196,167,0.15)", border: "1px solid rgba(0,196,167,0.3)", color: "var(--cyan)", padding: "12px", borderRadius: "10px", marginBottom: "16px", fontWeight: 800, fontSize: "13px" }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "13px" }}>
          
          <div style={{ gridColumn: "1 / -1", fontSize: "13px", fontWeight: 900, color: "#ec4899", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "6px" }}>
            1. ORGANIZATION DETAILS
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>ORGANIZATION NAME *</label>
            <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Harvard Tech Institute" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>ORGANIZATION TYPE</label>
            <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} style={{ width: "100%", background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px" }}>
              <option value="College">College / University</option>
              <option value="Company">Company / Recruiter</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>OFFICIAL EMAIL *</label>
            <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="admin@harvard.edu" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>SUBSCRIPTION PLAN TIER</label>
            <select value={form.subscription_plan} onChange={e => setForm({ ...form, subscription_plan: e.target.value })} style={{ width: "100%", background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px" }}>
              <option value="ENTERPRISE">ENTERPRISE (Unlimited)</option>
              <option value="BUSINESS">BUSINESS (Starter)</option>
              <option value="FREE_TRIAL">FREE TRIAL (14 Days)</option>
            </select>
          </div>

          <div style={{ gridColumn: "1 / -1", fontSize: "13px", fontWeight: 900, color: "#8b5cf6", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "6px", marginTop: "12px" }}>
            2. PRIMARY ADMIN ACCOUNT CREATION
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>ADMIN FULL NAME *</label>
            <input type="text" required value={form.admin_name} onChange={e => setForm({ ...form, admin_name: e.target.value })} placeholder="Dr. Alan Turing" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>ADMIN LOGIN EMAIL *</label>
            <input type="email" required value={form.admin_email} onChange={e => setForm({ ...form, admin_email: e.target.value })} placeholder="turing@harvard.edu" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>TEMPORARY ADMIN PASSWORD</label>
            <input type="password" value={form.temp_password} onChange={e => setForm({ ...form, temp_password: e.target.value })} placeholder="Default: admin123" style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div style={{ gridColumn: "1 / -1", marginTop: "16px" }}>
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", fontSize: "14px", fontWeight: 900, background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none" }}>
              {loading ? "⚡ Provisioning Infrastructure..." : "Save & Provision Organization →"}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
