import React, { useState, useEffect } from 'react';
import { submitFeedback, uploadFeedbackScreenshot, getMyFeedback, updateMyFeedback } from '../services/feedbackAPI';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function StudentFeedbackForm({ role = "Student" }) {
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("General Feedback");
  const [rating, setRating] = useState(5);
  const [message, setMessage] = useState("");
  const [screenshotFile, setScreenshotFile] = useState(null);
  const [screenshotPreview, setScreenshotPreview] = useState("");
  
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccessMsg, setFeedbackSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // History list
  const [myFeedbacks, setMyFeedbacks] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editSubject, setEditSubject] = useState("");
  const [editCategory, setEditCategory] = useState("General Feedback");
  const [editRating, setEditRating] = useState(5);
  const [editMessage, setEditMessage] = useState("");

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const records = await getMyFeedback();
      let list = [];
      if (Array.isArray(records)) {
        list = records;
      } else if (records && typeof records === 'object') {
        list = records.feedback || records.feedbacks || records.data || records.records || [];
        if (!Array.isArray(list)) list = [];
      }
      setMyFeedbacks(list);
    } catch (e) {
      console.error("Fetch history notice:", e);
      setMyFeedbacks([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleScreenshotChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setScreenshotFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setScreenshotPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setSubmitting(true);
    setFeedbackSuccessMsg("");
    setErrorMsg("");

    try {
      let screenshot_url = null;
      if (screenshotFile) {
        const uploadRes = await uploadFeedbackScreenshot(screenshotFile);
        screenshot_url = uploadRes.url;
      }

      await submitFeedback({
        subject: subject.trim() || "Feedback Submission",
        category,
        rating,
        message: message.trim(),
        screenshot_url,
        submitted_by_role: role
      });

      setFeedbackSuccessMsg("Thank you for your feedback. Your response has been submitted successfully.");
      setSubject("");
      setMessage("");
      setScreenshotFile(null);
      setScreenshotPreview("");
      setRating(5);
      setCategory("General Feedback");
      fetchHistory();
    } catch (err) {
      setErrorMsg(err.message || "Failed to submit feedback. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const startEdit = (fb) => {
    setEditingId(fb.id);
    setEditSubject(fb.subject || "");
    setEditCategory(fb.category || "General Feedback");
    setEditRating(fb.rating || 5);
    setEditMessage(fb.message || "");
  };

  const handleSaveEdit = async (id) => {
    try {
      await updateMyFeedback(id, {
        subject: editSubject,
        category: editCategory,
        rating: editRating,
        message: editMessage
      });
      setEditingId(null);
      fetchHistory();
    } catch (err) {
      alert("Failed to update feedback: " + err.message);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px", maxWidth: "750px" }}>
      
      {/* SUBMISSION FORM CARD */}
      <div className="pr-glass-card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h3 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "6px" }}>
          💬 Share Your Feedback & Bug Reports
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text2, #94a3b8)", marginBottom: "20px" }}>
          Your feedback goes directly to our platform administrators to help improve your interview preparation experience.
        </p>

        {feedbackSuccessMsg && (
          <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(0,196,167,0.15)", border: "1px solid #00c4a7", color: "#fff", fontWeight: 700, marginBottom: "20px", fontSize: "13px" }}>
            🎉 {feedbackSuccessMsg}
          </div>
        )}

        {errorMsg && (
          <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444", color: "#f87171", fontWeight: 700, marginBottom: "20px", fontSize: "13px" }}>
            ⚠️ {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          
          {/* SUBJECT */}
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "var(--text2, #94a3b8)", marginBottom: "6px", textTransform: "uppercase" }}>SUBJECT / TITLE</label>
            <input
              type="text"
              required
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="e.g. Issue during DSA live coding round..."
              style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px" }}
            />
          </div>

          {/* CATEGORY & RATING GRID */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "var(--text2, #94a3b8)", marginBottom: "6px", textTransform: "uppercase" }}>CATEGORY</label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px" }}
              >
                <option value="General Feedback">General Feedback</option>
                <option value="Bug Report">Bug Report</option>
                <option value="Feature Request">Feature Request</option>
                <option value="Payment Issue">Payment Issue</option>
                <option value="AI Interview">AI Interview</option>
                <option value="Coding Round">Coding Round</option>
                <option value="Dashboard">Dashboard</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "var(--text2, #94a3b8)", marginBottom: "6px", textTransform: "uppercase" }}>RATING (1–5 STARS)</label>
              <div style={{ display: "flex", gap: "8px", fontSize: "22px", cursor: "pointer", paddingTop: "4px" }}>
                {[1, 2, 3, 4, 5].map(star => (
                  <span key={star} onClick={() => setRating(star)} style={{ opacity: star <= rating ? 1 : 0.25, transition: "opacity 0.2s ease" }}>
                    ⭐
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* FEEDBACK MESSAGE */}
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "var(--text2, #94a3b8)", marginBottom: "6px", textTransform: "uppercase" }}>FEEDBACK MESSAGE</label>
            <textarea
              rows={4}
              required
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Provide detailed suggestions, bug details, or feedback..."
              style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px", resize: "vertical" }}
            />
          </div>

          {/* SCREENSHOT UPLOAD */}
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 800, color: "var(--text2, #94a3b8)", marginBottom: "6px", textTransform: "uppercase" }}>OPTIONAL SCREENSHOT</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleScreenshotChange}
              style={{ fontSize: "12px", color: "#94a3b8" }}
            />
            {screenshotPreview && (
              <div style={{ marginTop: "10px" }}>
                <img src={screenshotPreview} alt="Preview" style={{ maxHeight: "120px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.15)" }} />
              </div>
            )}
          </div>

          {/* SUBMIT BUTTON */}
          <button
            type="submit"
            disabled={submitting}
            className="btn btn-primary"
            style={{
              background: "linear-gradient(135deg, #00c4a7, #7c4fe0)",
              border: "none",
              padding: "12px 24px",
              borderRadius: "12px",
              fontWeight: 800,
              fontSize: "14px",
              color: "#fff",
              cursor: "pointer",
              alignSelf: "flex-start",
              marginTop: "8px"
            }}
          >
            {submitting ? "Submitting..." : "📤 Submit Feedback"}
          </button>
        </form>
      </div>

      {/* MY SUBMITTED FEEDBACK HISTORY */}
      <div className="pr-glass-card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "28px" }}>
        <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", marginBottom: "16px" }}>
          📜 My Submitted Feedback & Status
        </h3>

        {(() => {
          const safeFeedbacks = Array.isArray(myFeedbacks) ? myFeedbacks : [];

          if (loadingHistory) {
            return <div style={{ color: "#00c4a7", fontSize: "13px", fontWeight: 700 }}>Loading feedback history...</div>;
          }

          if (safeFeedbacks.length === 0) {
            return <div style={{ color: "#94a3b8", fontSize: "13px" }}>You haven't submitted any feedback yet.</div>;
          }

          return (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {safeFeedbacks.map(fb => (
                <div key={fb.id} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "16px" }}>
                
                {editingId === fb.id ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <input type="text" value={editSubject} onChange={e => setEditSubject(e.target.value)} style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "8px 12px", color: "#fff", fontSize: "13px" }} />
                    <textarea rows={3} value={editMessage} onChange={e => setEditMessage(e.target.value)} style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "8px 12px", color: "#fff", fontSize: "13px" }} />
                    <div style={{ display: "flex", gap: "10px" }}>
                      <button onClick={() => handleSaveEdit(fb.id)} style={{ background: "#00c4a7", border: "none", color: "#fff", borderRadius: "6px", padding: "6px 12px", fontWeight: 700, fontSize: "12px" }}>Save</button>
                      <button onClick={() => setEditingId(null)} style={{ background: "transparent", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", borderRadius: "6px", padding: "6px 12px", fontSize: "12px" }}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <div>
                        <span style={{ fontSize: "11px", color: "#a78bfa", fontWeight: 800 }}>{fb.category}</span>
                        <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "2px 0 0 0" }}>{fb.subject}</h4>
                      </div>

                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span style={{ fontSize: "11px", padding: "3px 10px", borderRadius: "20px", fontWeight: 800, background: fb.status === "Resolved" ? "rgba(16,185,129,0.15)" : "rgba(56,189,248,0.15)", color: fb.status === "Resolved" ? "#10b981" : "#38bdf8" }}>
                          {fb.status}
                        </span>

                        {!["Resolved", "Closed"].includes(fb.status) && (
                          <button onClick={() => startEdit(fb)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", borderRadius: "6px", padding: "4px 8px", fontSize: "11px", cursor: "pointer" }}>
                            ✏️ Edit
                          </button>
                        )}
                      </div>
                    </div>

                    <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5, margin: "0 0 8px 0" }}>{fb.message}</p>
                    
                    {fb.screenshot_url && (
                      <div style={{ marginTop: "8px" }}>
                        <img src={fb.screenshot_url.startsWith('/') ? `${BACKEND_URL}${fb.screenshot_url}` : fb.screenshot_url} alt="Attachment" style={{ maxHeight: "80px", borderRadius: "6px" }} />
                      </div>
                    )}

                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "8px" }}>
                      Submitted on: {fb.created_at} {fb.rating ? `· Rating: ${fb.rating} ⭐` : ""}
                    </div>
                  </>
                )}

              </div>
            ))}
          </div>
        );
      })()}
      </div>

    </div>
  );
}
