import React, { useState, useEffect } from 'react';
import RenewButton from './RenewButton';
import PaymentHistory from './PaymentHistory';
import PaymentSuccess from './PaymentSuccess';
import PaymentFailed from './PaymentFailed';
import { fetchSubscriptionStatus, fetchPaymentHistory } from './subscriptionAPI';

export default function Subscription({ apiFetch, orgId, isAdmin = false }) {
  const [statusData, setStatusData] = useState(null);
  const [payments, setPayments] = useState([]);
  const [students, setStudents] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkRenewing, setBulkRenewing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toastMsg, setToastMsg] = useState("");
  const [successData, setSuccessData] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const organizationId = orgId || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";

  useEffect(() => {
    loadData();
  }, [organizationId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const subStatus = await fetchSubscriptionStatus(apiFetch, organizationId);
      const payHist = await fetchPaymentHistory(apiFetch, organizationId);
      setStatusData(subStatus);
      setPayments(payHist || []);

      if (isAdmin) {
        const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const sRes = await fetch(`${import.meta.env.VITE_BACKEND_URL || "http://localhost:5000"}/api/admin/students`, { headers });
        if (sRes.ok) {
          const sData = await sRes.json();
          setStudents(sData.students || []);
        }
      }
    } catch (e) {
      console.error("Error loading subscription data:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(students.map(s => s.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const handleBulkRenew = async () => {
    if (selectedIds.length === 0) return;
    setBulkRenewing(true);
    try {
      const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL || "http://localhost:5000"}/api/admin/students/bulk-renew`, {
        method: "POST",
        headers,
        body: JSON.stringify({ student_ids: selectedIds })
      });
      if (res.ok) {
        setToastMsg(`🎉 Successfully renewed 1-Year subscription for ${selectedIds.length} selected students!`);
        setSelectedIds([]);
        loadData();
      } else {
        const d = await res.json();
        setErrorMsg(d.error || "Bulk renewal failed");
      }
    } catch (e) {
      setErrorMsg("Failed to perform bulk student renewal");
    } finally {
      setBulkRenewing(false);
    }
  };

  const handleSuccess = (res) => {
    setSuccessData(res);
    setToastMsg("🎉 Premium 1-Year Subscription Activated Successfully!");
    loadData();
  };

  const handleError = (err) => {
    setErrorMsg(err || "Payment failed");
  };

  if (loading) {
    return (
      <div style={{ padding: "60px 0", textAlign: "center", color: "var(--cyan)" }}>
        <div style={{ fontSize: "32px", marginBottom: "12px" }}>👑</div>
        <div style={{ fontWeight: 800, fontSize: "16px" }}>Loading Organization Subscription Status...</div>
      </div>
    );
  }

  const subStatus = statusData?.subscription_status || "TRIAL";
  const planName = statusData?.current_plan || (subStatus === "ACTIVE" ? "Premium" : subStatus === "EXPIRED" ? "Expired" : "Trial");
  const isBlocked = statusData?.is_blocked || subStatus === "EXPIRED";
  const daysRemaining = statusData?.days_remaining ?? 0;
  const reminders = statusData?.reminders || [];

  return (
    <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "0 16px" }}>
      
      {/* TOAST NOTIFICATION */}
      {toastMsg && (
        <div style={{
          position: "fixed",
          top: "24px",
          right: "24px",
          background: "linear-gradient(135deg, #00c4a7, #1e293b)",
          color: "#fff",
          padding: "16px 24px",
          borderRadius: "14px",
          boxShadow: "0 12px 32px rgba(0,196,167,0.3)",
          zIndex: 9999,
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          gap: "12px",
          animation: "slideIn 0.3s ease"
        }}>
          {toastMsg}
        </div>
      )}

      {/* MODALS */}
      {successData && <PaymentSuccess data={successData} onClose={() => setSuccessData(null)} />}
      {errorMsg && <PaymentFailed errorMsg={errorMsg} onClose={() => setErrorMsg("")} onRetry={() => { setErrorMsg(""); setTimeout(() => { document.getElementById("renew-sub-btn")?.click(); }, 100); }} />}

      {/* HEADER SECTION */}
      <div style={{ marginBottom: "28px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "nowrap", gap: "20px" }}>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: "28px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span>👑</span> Subscription & Billing
            <span style={{
              fontSize: "12px",
              padding: "4px 10px",
              borderRadius: "20px",
              background: subStatus === 'ACTIVE' ? "rgba(0,196,167,0.2)" : subStatus === 'EXPIRED' ? "rgba(239,68,68,0.2)" : "rgba(124,79,224,0.2)",
              color: subStatus === 'ACTIVE' ? "#00c4a7" : subStatus === 'EXPIRED' ? "#ef4444" : "#a855f7",
              border: `1px solid ${subStatus === 'ACTIVE' ? "#00c4a7" : subStatus === 'EXPIRED' ? "#ef4444" : "#a855f7"}`,
              fontWeight: 800
            }}>
              {subStatus}
            </span>
          </h1>
          <p style={{ color: "var(--text2)", fontSize: "14px", marginTop: "6px", margin: 0 }}>
            Manage your organization's plan, monitor trial duration, and renew subscription for full platform access.
          </p>
        </div>

        <div style={{ flexShrink: 0 }}>
          <RenewButton apiFetch={apiFetch} orgId={organizationId} onSuccess={handleSuccess} onError={handleError} />
        </div>
      </div>

      {/* EXPIRY REMINDER ALERTS */}
      {reminders.map((rem, i) => (
        <div key={i} style={{
          background: rem.level === 'EXPIRED' ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
          border: `1px solid ${rem.level === 'EXPIRED' ? "#ef4444" : "#f59e0b"}`,
          borderRadius: "14px",
          padding: "16px 20px",
          marginBottom: "24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "16px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "20px" }}>{rem.level === 'EXPIRED' ? "🚨" : "⚠️"}</span>
            <span style={{ color: rem.level === 'EXPIRED' ? "#fca5a5" : "#fcd34d", fontWeight: 700, fontSize: "14px" }}>
              {rem.message}
            </span>
          </div>
          <RenewButton apiFetch={apiFetch} orgId={organizationId} onSuccess={handleSuccess} onError={handleError} />
        </div>
      ))}

      {/* SUBSCRIPTION STATUS CARD */}
      <div style={{
        background: "linear-gradient(135deg, rgba(12, 18, 32, 0.9) 0%, rgba(20, 28, 48, 0.8) 100%)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        borderRadius: "20px",
        padding: "28px",
        boxShadow: "0 16px 40px rgba(0, 0, 0, 0.4)",
        position: "relative",
        overflow: "hidden"
      }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "24px"
        }}>
          
          <div>
            <div style={{ fontSize: "12px", color: "var(--text2)", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 700 }}>CURRENT PLAN</div>
            <div style={{ fontSize: "24px", fontWeight: 900, color: "#fff", marginTop: "6px" }}>{planName} Plan</div>
            <div style={{ fontSize: "14px", color: "var(--cyan)", fontWeight: 800, marginTop: "4px" }}>₹500 / 365 Days (1 Year)</div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: "var(--text2)", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 700 }}>STATUS & DAYS REMAINING</div>
            <div style={{
              fontSize: "24px",
              fontWeight: 900,
              color: isBlocked ? "#ef4444" : daysRemaining <= 3 ? "#f59e0b" : "#00c4a7",
              marginTop: "6px"
            }}>
              {isBlocked ? "Expired Access" : `${daysRemaining} Days Left`}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>
              {subStatus === 'TRIAL' ? "10 Days Free Trial Active" : subStatus === 'ACTIVE' ? "Annual Subscription Active" : "Trial Period Ended"}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: "var(--text2)", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 700 }}>DATES</div>
            <div style={{ fontSize: "13px", color: "#fff", marginTop: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
              <div><strong>Started:</strong> {statusData?.trial_start ? statusData.trial_start.split("T")[0] : "2026-07-20"}</div>
              <div><strong>Expires:</strong> {statusData?.trial_end ? statusData.trial_end.split("T")[0] : "2026-07-30"}</div>
            </div>
          </div>

        </div>

        <div style={{
          marginTop: "24px",
          paddingTop: "20px",
          borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px"
        }}>
          <span style={{ fontSize: "13px", color: "var(--text2)" }}>
            Need to extend or renew your organization's 1-Year subscription?
          </span>
          <RenewButton apiFetch={apiFetch} orgId={organizationId} onSuccess={handleSuccess} onError={handleError} />
        </div>
      </div>

      {/* PLAN BENEFITS SUMMARY */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginTop: "24px" }}>
        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>👥</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>All Students Included</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Students belonging to your organization automatically receive premium features.</div>
        </div>

        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>🤖</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>Unlimited AI Mock Interviews</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Live speech-to-text feedback, transcript analytics, and STAR method evaluations.</div>
        </div>

        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>💻</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>Coding Test Environment</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Automated code execution, complexity review, and collaborative WebRTC rooms.</div>
        </div>

        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>📄</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>Instant PDF Invoices</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>GST-compliant PDF invoices generated automatically after every payment.</div>
        </div>

        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>📊</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>Institutional Analytics</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Cohort breakdown, skill weakness tracking, and downloadable CSV candidate digests.</div>
        </div>

        <div style={{ background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>⚡</div>
          <div style={{ fontWeight: 800, color: "#fff", fontSize: "14px" }}>24/7 Priority Support & SLA</div>
          <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Dedicated account manager, custom API integrations, and guaranteed 99.9% uptime.</div>
        </div>
      </div>

      {/* PAYMENT HISTORY & INVOICES */}
      <PaymentHistory payments={payments} />

      {/* COVERED ORGANIZATION STUDENTS ROSTER (ADMIN ONLY) */}
      {isAdmin && (
        <div style={{ marginTop: "32px", background: "rgba(12, 18, 32, 0.6)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "20px", padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h3 style={{ color: "#fff", fontSize: "16px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <span>👥</span> Covered Organization Students ({students.length})
              </h3>
              <p style={{ color: "var(--text2)", fontSize: "12px", margin: "4px 0 0 0" }}>
                All students under your institution automatically inherit premium AI interview & coding test access.
              </p>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {selectedIds.length > 0 && (
                <button
                  onClick={handleBulkRenew}
                  disabled={bulkRenewing}
                  style={{
                    background: "linear-gradient(135deg, #7c4fe0, #00c4a7)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "12px",
                    padding: "8px 16px",
                    fontSize: "12px",
                    fontWeight: 800,
                    cursor: "pointer",
                    boxShadow: "0 4px 16px rgba(124, 79, 224, 0.4)",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                  }}
                >
                  <span>⚡</span> {bulkRenewing ? "Renewing..." : `Bulk Renew Access (${selectedIds.length} Selected)`}
                </button>
              )}
              <div style={{ background: "rgba(0, 196, 167, 0.15)", color: "#00c4a7", border: "1px solid rgba(0,196,167,0.3)", padding: "6px 14px", borderRadius: "20px", fontSize: "12px", fontWeight: 700 }}>
                Active Subscription Coverage
              </div>
            </div>
          </div>

          {students.length === 0 ? (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--text2)", fontSize: "13px" }}>
              No students currently registered under this organization.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "var(--text2)" }}>
                    <th style={{ padding: "10px", width: "40px" }}>
                      <input
                        type="checkbox"
                        onChange={handleSelectAll}
                        checked={students.length > 0 && selectedIds.length === students.length}
                        style={{ cursor: "pointer", accentColor: "#00c4a7" }}
                      />
                    </th>
                    <th style={{ padding: "10px" }}>Student Name</th>
                    <th style={{ padding: "10px" }}>Email</th>
                    <th style={{ padding: "10px" }}>Department</th>
                    <th style={{ padding: "10px" }}>Subscription Status</th>
                    <th style={{ padding: "10px" }}>AI & Coding Access</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s, idx) => (
                    <tr key={s.id || idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ padding: "12px 10px" }}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(s.id)}
                          onChange={() => handleToggleSelect(s.id)}
                          style={{ cursor: "pointer", accentColor: "#00c4a7" }}
                        />
                      </td>
                      <td style={{ padding: "12px 10px", fontWeight: 700, color: "#fff" }}>{s.name}</td>
                      <td style={{ padding: "12px 10px", color: "var(--text2)" }}>{s.email}</td>
                      <td style={{ padding: "12px 10px", color: "var(--text2)" }}>{s.department || "Computer Science"}</td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ background: "rgba(0, 196, 167, 0.15)", color: "#00c4a7", padding: "4px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>
                          {subStatus === "ACTIVE" || s.subscription === "PREMIUM" ? "PRO INCLUDED" : "TRIAL COVERED"}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", color: "#4ade80", fontWeight: 700 }}>✓ Unlimited</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
