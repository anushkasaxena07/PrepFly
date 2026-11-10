import React, { useState, useEffect } from 'react';
import AnnouncementModal from '../../components/Admin/AnnouncementModal';
import { getAdminAnnouncements, createAdminAnnouncement } from '../../services/adminAPI';

export default function Announcements() {
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetchAnnouncements();
  }, []);

  const fetchAnnouncements = async () => {
    try {
      const data = await getAdminAnnouncements();
      const list = Array.isArray(data) ? data : (data?.announcements || data?.data || data?.items || []);
      setAnnouncements(list);
    } catch (e) {
      console.error(e);
      setAnnouncements([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (annData) => {
    try {
      await createAdminAnnouncement(annData);
      setToast("📢 Announcement published & dispatched!");
      setTimeout(() => setToast(""), 4000);
      fetchAnnouncements();
    } catch (e) {
      alert("Failed to send announcement");
    }
  };

  const safeAnnouncements = Array.isArray(announcements) ? announcements : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #6d28d9, #7c3aed)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000 }}>
          {toast}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#0f172a", margin: 0 }}>📢 Announcements & Email Notifications</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Dispatch targeted announcements and push notifications to departments or semesters.</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)} style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)", border: "none", fontWeight: 800 }}>
          ➕ New Announcement
        </button>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading announcements...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {safeAnnouncements.map((ann) => (
            <div key={ann.id} className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: 0 }}>{ann.title}</h3>
                <span style={{ fontSize: "11px", color: "var(--text2)" }}>📅 {ann.created_at}</span>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text1)", lineHeight: "1.5", margin: "0 0 12px 0" }}>{ann.message}</p>
              <div style={{ display: "flex", gap: "8px", fontSize: "11px" }}>
                <span className="pill pill-purple">🎯 {ann.target_dept}</span>
                <span className="pill pill-cyan">🎓 {ann.target_sem}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <AnnouncementModal isOpen={showModal} onClose={() => setShowModal(false)} onSend={handleSend} />
    </div>
  );
}
