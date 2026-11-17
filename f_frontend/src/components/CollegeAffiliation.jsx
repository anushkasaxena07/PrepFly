import React, { useState, useEffect } from "react";
import { BACKEND_URL } from "../config/apiConfig";

export default function CollegeAffiliation() {
  const [loading, setLoading] = useState(true);
  const [college, setCollege] = useState(null);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");

  // Join modal state
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [department, setDepartment] = useState("");
  const [consent, setConsent] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [joining, setJoining] = useState(false);

  // Leave confirmation state
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [leaving, setLeaving] = useState(false);

  const getToken = () => {
    return (
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      localStorage.getItem("admin_access_token") ||
      localStorage.getItem("superadmin_token")
    );
  };

  const showNotification = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 4500);
  };

  useEffect(() => {
    fetchMyCollege();
  }, []);

  const fetchMyCollege = async () => {
    setLoading(true);
    setError("");
    try {
      const token = getToken();
      const res = await fetch(`${BACKEND_URL}/api/student/my-college`, {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        const data = await res.json();
        setCollege(data.college || null);
      } else {
        setCollege(null);
      }
    } catch (e) {
      console.error("Fetch my college error:", e);
      setCollege(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLookupCode = async (codeToLookup) => {
    const code = (codeToLookup || joinCode).trim().toUpperCase();
    if (!code) return;
    setPreviewLoading(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_URL}/api/student/college-preview?code=${encodeURIComponent(code)}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
      } else {
        const err = await res.json().catch(() => ({}));
        setPreviewData(null);
        setError(err.error || "Invalid institutional join code. Please check with your campus coordinator.");
      }
    } catch (e) {
      setError("Failed to verify join code.");
      setPreviewData(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleJoinCollege = async (e) => {
    e.preventDefault();
    if (!consent) {
      setError("You must provide consent to link your account to your educational institution.");
      return;
    }
    setJoining(true);
    setError("");
    try {
      const token = getToken();
      const res = await fetch(`${BACKEND_URL}/api/student/join-college`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          join_code: joinCode.trim().toUpperCase(),
          consent: true,
          roll_number: rollNumber.trim(),
          department: department.trim()
        })
      });

      const data = await res.json();
      if (res.ok) {
        showNotification(`🎉 Successfully linked to ${data.organization?.name || "your college"}!`);
        setShowJoinModal(false);
        setJoinCode("");
        setRollNumber("");
        setDepartment("");
        setConsent(false);
        setPreviewData(null);
        fetchMyCollege();
      } else {
        setError(data.error || "Failed to link account to college");
      }
    } catch (e) {
      setError("An unexpected error occurred while linking to college.");
    } finally {
      setJoining(false);
    }
  };

  const handleLeaveCollege = async () => {
    setLeaving(true);
    try {
      const token = getToken();
      const res = await fetch(`${BACKEND_URL}/api/student/leave-college`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        showNotification("Account unlinked from college. Your profile has reverted to independent candidate status.");
        setShowLeaveConfirm(false);
        fetchMyCollege();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.error || "Failed to leave college");
      }
    } catch (e) {
      alert("Failed to un-link from college");
    } finally {
      setLeaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "40px", color: "var(--cyan)" }}>
        ⚡ Verifying institutional affiliation...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {toast && (
        <div style={{
          position: "fixed",
          top: "24px",
          right: "24px",
          background: "linear-gradient(135deg, #10b981, #059669)",
          color: "#fff",
          padding: "14px 22px",
          borderRadius: "12px",
          fontWeight: 800,
          zIndex: 3000,
          boxShadow: "0 12px 30px rgba(16,185,129,0.3)"
        }}>
          {toast}
        </div>
      )}

      {/* ── CASE 1: LINKED TO A COLLEGE ────────────────────────── */}
      {college ? (
        <>
          {/* AFFILIATION BANNER */}
          <div style={{
            background: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "18px",
            padding: "26px",
            boxShadow: "0 4px 16px rgba(0,0,0,0.03)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
              <div style={{ display: "flex", gap: "18px", alignItems: "center" }}>
                <div style={{
                  width: "56px",
                  height: "56px",
                  borderRadius: "14px",
                  background: "linear-gradient(135deg, #f5f3ff, #ede9fe)",
                  border: "1px solid #ddd6fe",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "28px"
                }}>
                  🏛️
                </div>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                      {college.name}
                    </h3>
                    <span style={{
                      background: "#ecfdf5",
                      color: "#059669",
                      border: "1px solid #a7f3d0",
                      fontSize: "11px",
                      fontWeight: 800,
                      padding: "3px 10px",
                      borderRadius: "20px"
                    }}>
                      ● Active Institutional Enrollee
                    </span>
                  </div>
                  <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
                    Department: <strong>{college.department || "General"}</strong> &bull; Roll Number: <strong>{college.roll_number || "Not assigned"}</strong>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowLeaveConfirm(true)}
                  style={{
                    background: "#fff",
                    border: "1px solid #fecaca",
                    color: "#dc2626",
                    padding: "8px 16px",
                    borderRadius: "10px",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                    transition: "all 0.2s ease"
                  }}
                >
                  Unlink / Leave College
                </button>
              </div>
            </div>
          </div>

          {/* TRANSPARENCY & DATA DISCLOSURE MATRIX */}
          <div style={{
            background: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "18px",
            padding: "26px",
            boxShadow: "0 4px 16px rgba(0,0,0,0.03)"
          }}>
            <h4 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: "0 0 6px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>🛡️</span> Data Privacy &amp; Institutional Visibility Disclosure
            </h4>
            <p style={{ fontSize: "12.5px", color: "#64748b", margin: "0 0 20px 0" }}>
              PrepFly enforces cryptographic and logical tenant isolation. Here is exactly what your institution administrators can and cannot access:
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
              
              {/* CAN SEE */}
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "14px", padding: "18px" }}>
                <div style={{ fontSize: "13px", fontWeight: 800, color: "#166534", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>✅</span> What {college.name} Administrators CAN See
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", color: "#15803d" }}>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Scores, evaluation rubrics, and feedback on <strong>college-assigned mock interviews</strong>.</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Test-case pass rate, execution speed, and ranking on <strong>college coding assessments</strong>.</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Aggregated cohort placement readiness scores and department analytics.</span>
                  </div>
                </div>
              </div>

              {/* CANNOT SEE */}
              <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "14px", padding: "18px" }}>
                <div style={{ fontSize: "13px", fontWeight: 800, color: "#6b21a8", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>🔒</span> What Remains STRICTLY PRIVATE to You
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", color: "#7e22ce" }}>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Your independent, self-initiated mock interviews and personal speech drills.</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Personal coding sandbox experiments and non-institutional problem solutions.</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Private mentor conversations, personalized study notes, and resume revisions.</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span>&bull;</span>
                    <span>Personal payment, subscription, billing, and invoice information.</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </>
      ) : (
        /* ── CASE 2: INDEPENDENT CANDIDATE ────────────────────────── */
        <div style={{
          background: "#ffffff",
          border: "1px solid #e2e8f0",
          borderRadius: "18px",
          padding: "36px 28px",
          textAlign: "center",
          boxShadow: "0 4px 16px rgba(0,0,0,0.03)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "14px"
        }}>
          <div style={{
            width: "68px",
            height: "68px",
            borderRadius: "18px",
            background: "linear-gradient(135deg, #f5f3ff, #ede9fe)",
            border: "1px solid #ddd6fe",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "32px"
          }}>
            🎓
          </div>
          <div style={{ maxWidth: "520px" }}>
            <h3 style={{ fontSize: "19px", fontWeight: 800, color: "#0f172a", margin: "0 0 6px 0" }}>
              Independent Candidate Account
            </h3>
            <p style={{ fontSize: "13px", color: "#64748b", margin: 0, lineHeight: 1.5 }}>
              You are currently registered as an independent candidate. All your interview practices, speech assessments, and coding solutions are <strong>completely private</strong>.
            </p>
            <p style={{ fontSize: "13px", color: "#64748b", marginTop: "8px", lineHeight: 1.5 }}>
              If your college or university has enrolled with PrepFly, you can link your account using their campus <strong>Join Code</strong> to unlock college-assigned mock interviews and campus placement challenges.
            </p>
          </div>

          <button
            type="button"
            onClick={() => { setShowJoinModal(true); setError(""); setPreviewData(null); }}
            style={{
              background: "linear-gradient(135deg, #7c3aed, #6d28d9)",
              color: "#fff",
              border: "none",
              padding: "12px 24px",
              borderRadius: "12px",
              fontSize: "13.5px",
              fontWeight: 800,
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(124,58,237,0.25)",
              marginTop: "10px"
            }}
          >
            🏛️ Join College or University
          </button>
        </div>
      )}

      {/* ── JOIN COLLEGE MODAL ────────────────────────────────────── */}
      {showJoinModal && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.7)",
          backdropFilter: "blur(6px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 3000,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            border: "1px solid #cbd5e1",
            borderRadius: "18px",
            padding: "26px",
            maxWidth: "520px",
            width: "100%",
            maxHeight: "90vh",
            overflowY: "auto",
            color: "#0f172a"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>🏛️ Link Account to College</h3>
                <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>Enter your institution's registration join code.</p>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-xs"
                onClick={() => setShowJoinModal(false)}
              >
                ✕ Close
              </button>
            </div>

            {error && (
              <div style={{
                background: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#b91c1c",
                padding: "10px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                marginBottom: "14px"
              }}>
                ⚠️ {error}
              </div>
            )}

            <form onSubmit={handleJoinCollege} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "6px" }}>
                  Campus Join Code *
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    required
                    value={joinCode}
                    onChange={(e) => {
                      const v = e.target.value.toUpperCase();
                      setJoinCode(v);
                      if (v.length >= 4) {
                        handleLookupCode(v);
                      }
                    }}
                    placeholder="e.g. SUN2026"
                    style={{
                      flex: 1,
                      fontFamily: "monospace",
                      fontWeight: 800,
                      fontSize: "14px",
                      letterSpacing: "1px",
                      padding: "8px 12px",
                      background: "#f8fafc",
                      border: "1px solid #cbd5e1",
                      borderRadius: "8px"
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleLookupCode()}
                    disabled={previewLoading || !joinCode.trim()}
                    style={{
                      background: "#f1f5f9",
                      border: "1px solid #cbd5e1",
                      borderRadius: "8px",
                      padding: "8px 14px",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    {previewLoading ? "Verifying..." : "Verify Code"}
                  </button>
                </div>
              </div>

              {/* LIVE COLLEGE PREVIEW CARD */}
              {previewData && (
                <div style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  padding: "14px"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a" }}>
                      🏛️ {previewData.college_name}
                    </div>
                    <span style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      color: previewData.seats_available ? "#16a34a" : "#dc2626",
                      background: previewData.seats_available ? "#dcfce7" : "#fee2e2",
                      padding: "2px 8px",
                      borderRadius: "12px"
                    }}>
                      {previewData.seats_available ? "Seats Available" : "Capacity Full"}
                    </span>
                  </div>
                  <div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "6px", lineHeight: 1.4 }}>
                    {previewData.consent_notice}
                  </div>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Roll Number
                  </label>
                  <input
                    type="text"
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value)}
                    placeholder="e.g. CS-2026-042"
                    style={{ width: "100%", padding: "8px 10px", fontSize: "12px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "4px" }}>
                    Department
                  </label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder="e.g. Computer Science"
                    style={{ width: "100%", padding: "8px 10px", fontSize: "12px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px" }}
                  />
                </div>
              </div>

              {/* MANDATORY CONSENT CHECKBOX */}
              <div style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "10px",
                padding: "12px",
                display: "flex",
                gap: "10px",
                alignItems: "flex-start"
              }}>
                <input
                  type="checkbox"
                  id="consent-check"
                  required
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  style={{ marginTop: "3px", width: "16px", height: "16px", cursor: "pointer" }}
                />
                <label htmlFor="consent-check" style={{ fontSize: "11.5px", color: "#166534", lineHeight: 1.4, cursor: "pointer" }}>
                  I explicitly consent to link my account to this institution. I understand college administrators will be able to assign mock interviews and coding assessments to me and view my scores for assigned tests. My independent practice remains private.
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => setShowJoinModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={joining || !joinCode.trim() || !consent || (previewData && !previewData.seats_available)}
                  style={{
                    background: "linear-gradient(135deg, #7c3aed, #6d28d9)",
                    color: "#fff",
                    border: "none",
                    padding: "10px 18px",
                    borderRadius: "10px",
                    fontSize: "12.5px",
                    fontWeight: 800,
                    cursor: "pointer",
                    opacity: (joining || !joinCode.trim() || !consent || (previewData && !previewData.seats_available)) ? 0.6 : 1
                  }}
                >
                  {joining ? "Linking..." : "Confirm & Join College"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── LEAVE CONFIRMATION MODAL ──────────────────────────────── */}
      {showLeaveConfirm && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.7)",
          backdropFilter: "blur(6px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 3000,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            border: "1px solid #cbd5e1",
            borderRadius: "18px",
            padding: "24px",
            maxWidth: "460px",
            width: "100%",
            color: "#0f172a"
          }}>
            <h3 style={{ fontSize: "17px", fontWeight: 800, margin: "0 0 10px 0", color: "#b91c1c" }}>
              ⚠️ Unlink from {college?.name}?
            </h3>
            <p style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5, margin: 0 }}>
              Are you sure you want to unlink your account from <strong>{college?.name}</strong>?
            </p>
            <p style={{ fontSize: "12px", color: "#64748b", lineHeight: 1.4, marginTop: "8px" }}>
              Your profile will immediately revert to an independent candidate account. You will no longer receive assignments or announcements from this college. Past submissions on college-assigned tests will be preserved on the institution's accreditation records.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "20px" }}>
              <button
                type="button"
                className="btn btn-ghost btn-xs"
                onClick={() => setShowLeaveConfirm(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleLeaveCollege}
                disabled={leaving}
                style={{
                  background: "#dc2626",
                  color: "#fff",
                  border: "none",
                  padding: "8px 16px",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontWeight: 800,
                  cursor: "pointer"
                }}
              >
                {leaving ? "Unlinking..." : "Yes, Unlink My Account"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
