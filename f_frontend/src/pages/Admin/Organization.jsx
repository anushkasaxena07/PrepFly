import React, { useState, useEffect } from 'react';
import { getAdminOrganization, updateAdminOrganization } from '../../services/adminAPI';

import StudentFeedbackForm from '../../components/StudentFeedbackForm';

export default function Organization() {
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetchOrg();
  }, []);

  const fetchOrg = async () => {
    try {
      const data = await getAdminOrganization();
      setOrg(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await updateAdminOrganization(org);
      setIsEditing(false);
      setToast("Organization profile updated!");
      setTimeout(() => setToast(""), 4000);
    } catch (e) {
      alert("Failed to update organization");
    }
  };

  const [saCategory, setSaCategory] = useState("Platform Feature Request");
  const [saRating, setSaRating] = useState(5);
  const [saFeedbackText, setSaFeedbackText] = useState("");
  const [saFeedbackMsg, setSaFeedbackMsg] = useState("");

  const handleSendSaFeedback = async () => {
    if (!saFeedbackText.trim()) return;
    try {
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
      const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
      const res = await fetch(`${BACKEND_URL}/api/admin/feedback-to-superadmin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          admin_name: org?.name ? `${org.name} Admin` : "Organization Admin",
          category: saCategory,
          rating: saRating,
          feedback_text: saFeedbackText
        })
      });
      if (res.ok) {
        setSaFeedbackMsg("🎉 Feedback delivered successfully to Platform Super Admin!");
        setSaFeedbackText("");
      } else {
        setSaFeedbackMsg("❌ Failed to deliver feedback.");
      }
    } catch (err) {
      setSaFeedbackMsg("❌ Error sending feedback.");
    }
  };

  if (loading) {
    return <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading organization profile...</div>;
  }

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000 }}>
          {toast}
        </div>
      )}

      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>🏢 Organization Profile</h2>
            <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Institutional credentials, contact details, and subscription tier.</p>
          </div>

          <button className="btn btn-ghost" onClick={() => setIsEditing(!isEditing)}>
            {isEditing ? "Cancel" : "✏️ Edit Details"}
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "13px" }}>
          <div style={{ gridColumn: "1 / -1", display: "flex", alignItems: "center", gap: "16px", background: "rgba(255,255,255,0.03)", padding: "16px", borderRadius: "12px" }}>
            <div style={{ width: "64px", height: "64px", borderRadius: "14px", background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px", color: "#fff", fontWeight: 900 }}>
              🏛
            </div>
            <div>
              <div style={{ fontSize: "18px", fontWeight: 900, color: "#fff" }}>{org?.name || "Stanford Tech Institute"}</div>
              <div style={{ fontSize: "12px", color: "var(--cyan)", fontWeight: 700 }}>
                {org?.type || "College"} • {org?.subscription_plan || "ENTERPRISE"} TIER
              </div>
            </div>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>ORGANIZATION NAME</label>
            <input type="text" disabled={!isEditing} value={org?.name || ''} onChange={e => setOrg({ ...org, name: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>ORGANIZATION TYPE</label>
            <select disabled={!isEditing} value={org?.type || 'College'} onChange={e => setOrg({ ...org, type: e.target.value })} style={{ width: "100%", background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px" }}>
              <option value="College">College / University</option>
              <option value="Company">Company / Enterprise</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>OFFICIAL EMAIL</label>
            <input type="email" disabled={!isEditing} value={org?.email || ''} onChange={e => setOrg({ ...org, email: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>PHONE NUMBER</label>
            <input type="text" disabled={!isEditing} value={org?.phone || ''} onChange={e => setOrg({ ...org, phone: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>WEBSITE URL</label>
            <input type="text" disabled={!isEditing} value={org?.website || ''} onChange={e => setOrg({ ...org, website: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          <div>
            <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>PHYSICAL ADDRESS</label>
            <input type="text" disabled={!isEditing} value={org?.address || ''} onChange={e => setOrg({ ...org, address: e.target.value })} style={{ width: "100%", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff" }} />
          </div>

          {isEditing && (
            <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "flex-end", marginTop: "12px" }}>
              <button className="btn btn-primary" onClick={handleSave}>Save Organization Profile</button>
            </div>
          )}
        </div>

        {/* FEEDBACK TO SUPER ADMIN SECTION */}
        <div style={{ marginTop: "32px", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "24px" }}>
          <StudentFeedbackForm role="Organization Admin" />
        </div>
      </div>
    </div>
  );
}
