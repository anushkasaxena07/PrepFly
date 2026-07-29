import React, { useState } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function PaymentTable({ payments = [] }) {
  const [statusFilter, setStatusFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [selectedTxn, setSelectedTxn] = useState(null);

  const filtered = payments.filter(p => {
    if (statusFilter !== "All" && p.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        (p.organization_name || "").toLowerCase().includes(q) ||
        (p.student_name || "").toLowerCase().includes(q) ||
        (p.transaction_id || "").toLowerCase().includes(q) ||
        (p.invoice_number || "").toLowerCase().includes(q) ||
        (p.plan || "").toLowerCase().includes(q) ||
        (p.payment_method || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const successfulPayments = payments.filter(p => p.status === 'Success' || p.status === 'Captured');
  const totalRev = successfulPayments.reduce((sum, p) => sum + (p.amount || 0), 0);
  const totalGst = successfulPayments.reduce((sum, p) => sum + (p.gst || round((p.amount || 0) * 0.18, 2)), 0);
  const avgOrderValue = successfulPayments.length ? (totalRev / successfulPayments.length) : 0;

  const handleExportCSV = () => {
    if (!filtered || filtered.length === 0) return alert("No payment transactions to export");
    const headers = ["Txn ID", "Invoice No", "Purchaser / Student", "Organization", "Plan Tier", "Amount (INR)", "GST 18% (INR)", "Payment Method", "Status", "Date"];
    const rows = filtered.map(p => [
      `"${p.transaction_id || p.id}"`,
      `"${p.invoice_number || ''}"`,
      `"${(p.student_name || 'N/A').replace(/"/g, '""')}"`,
      `"${(p.organization_name || 'PrepFly Global').replace(/"/g, '""')}"`,
      `"${p.plan}"`,
      p.amount,
      p.gst || round(p.amount * 0.18, 2),
      `"${p.payment_method}"`,
      `"${p.status}"`,
      `"${p.created_at}"`
    ]);
    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "platform_global_payments_ledger.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadInvoice = (invoiceId) => {
    window.open(`${BACKEND_URL}/api/invoice/download/${invoiceId}`, '_blank');
  };

  const getStatusBadge = (status = "") => {
    if (status === "Success" || status === "Captured") {
      return { bg: "rgba(16,185,129,0.15)", color: "#10b981", label: "● Success" };
    } else if (status === "Failed" || status === "Cancelled") {
      return { bg: "rgba(239,68,68,0.15)", color: "#f87171", label: "● Failed" };
    } else if (status === "Refunded") {
      return { bg: "rgba(245,158,11,0.15)", color: "#f59e0b", label: "● Refunded" };
    }
    return { bg: "rgba(56,189,248,0.15)", color: "#38bdf8", label: `● ${status || 'Pending'}` };
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      
      {/* REVENUE METRIC CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,240,200,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 800 }}>TOTAL COLLECTED REVENUE</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>
            ₹{totalRev.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "4px", fontWeight: 700 }}>▲ Gross revenue across student & admin plans</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--text2)", fontWeight: 800 }}>TOTAL GST (18%)</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>
            ₹{totalGst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "4px", fontWeight: 700 }}>🏛 Automated Tax Ledger Compliant</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(139,92,246,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#a78bfa", fontWeight: 800 }}>SUCCESSFUL TRANSACTIONS</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>{successfulPayments.length}</div>
          <div style={{ fontSize: "10px", color: "#a78bfa", marginTop: "4px", fontWeight: 700 }}>💳 Razorpay & Stripe Combined</div>
        </div>

        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(56,189,248,0.25)", borderRadius: "14px", padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800 }}>AVERAGE ORDER VALUE</div>
          <div style={{ fontSize: "26px", fontWeight: 900, color: "#38bdf8", marginTop: "4px" }}>
            ₹{avgOrderValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "10px", color: "#38bdf8", marginTop: "4px", fontWeight: 700 }}>📈 Blended ARPU per invoice</div>
        </div>
      </div>

      {/* SEARCH AND FILTERS TOOLBAR */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", flex: 1 }}>
          <input 
            type="text" 
            placeholder="🔍 Search student, admin, txn ID, org, or invoice #..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ minWidth: "280px", flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px 14px", color: "#fff", fontSize: "12px", outline: "none" }}
          />

          <select 
            value={statusFilter} 
            onChange={e => setStatusFilter(e.target.value)} 
            style={{ background: "rgba(255,255,255,0.04)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", outline: "none" }}
          >
            <option value="All" style={{ background: "#0c1220" }}>All Payment Statuses</option>
            <option value="Success" style={{ background: "#0c1220" }}>🟢 Success / Captured</option>
            <option value="Failed" style={{ background: "#0c1220" }}>🔴 Failed</option>
            <option value="Refunded" style={{ background: "#0c1220" }}>🟡 Refunded</option>
          </select>

          {search && (
            <button onClick={() => setSearch('')} style={{ background: "rgba(255,255,255,0.06)", border: "none", color: "#94a3b8", padding: "8px 12px", borderRadius: "8px", fontSize: "12px", cursor: "pointer" }}>
              Clear
            </button>
          )}
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleExportCSV}
            style={{
              background: "rgba(0,196,167,0.15)",
              border: "1px solid rgba(0,196,167,0.3)",
              color: "#00c4a7",
              fontWeight: 800,
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "12px",
              cursor: "pointer"
            }}
          >
            📊 Export CSV ({filtered.length})
          </button>
        </div>
      </div>

      {/* PAYMENTS TABLE */}
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left", color: "#f0f4fd" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "#94a3b8", textTransform: "uppercase", fontSize: "11px" }}>
                <th style={{ padding: "12px 10px" }}>Txn / Invoice ID</th>
                <th style={{ padding: "12px 10px" }}>Purchaser / Student</th>
                <th style={{ padding: "12px 10px" }}>Organization</th>
                <th style={{ padding: "12px 10px" }}>Plan Tier</th>
                <th style={{ padding: "12px 10px" }}>Amount (INR)</th>
                <th style={{ padding: "12px 10px" }}>GST (18%)</th>
                <th style={{ padding: "12px 10px" }}>Method</th>
                <th style={{ padding: "12px 10px" }}>Status</th>
                <th style={{ padding: "12px 10px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map(p => {
                  const badge = getStatusBadge(p.status);
                  const gstVal = p.gst || round((p.amount || 0) * 0.18, 2);
                  return (
                    <tr key={p.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ padding: "12px 10px", fontWeight: 800, color: "var(--cyan)", fontFamily: "monospace" }}>
                        <div>{p.transaction_id || p.id}</div>
                        <div style={{ fontSize: "10px", color: "var(--text2)" }}>{p.invoice_number || ''}</div>
                      </td>
                      <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>
                        <div>{p.student_name || "N/A (Enterprise)"}</div>
                      </td>
                      <td style={{ padding: "12px 10px", color: "#94a3b8" }}>
                        {p.organization_name || "PrepFly Global"}
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "3px 8px", borderRadius: "6px", background: "rgba(139,92,246,0.15)", color: "#a78bfa", fontWeight: 800 }}>
                          {p.plan || "Premium Tier"}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", fontWeight: 900, color: "#00c4a7" }}>
                        ₹{Number(p.amount || 0).toLocaleString('en-IN')}
                      </td>
                      <td style={{ padding: "12px 10px", color: "var(--text2)" }}>
                        ₹{Number(gstVal).toLocaleString('en-IN')}
                      </td>
                      <td style={{ padding: "12px 10px", color: "#cbd5e1" }}>
                        {p.payment_method || "Razorpay UPI"}
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "3px 9px", borderRadius: "12px", background: badge.bg, color: badge.color, fontWeight: 800 }}>
                          {badge.label}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                          <button
                            onClick={() => setSelectedTxn(p)}
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}
                          >
                            🔍 Inspect
                          </button>
                          <button
                            onClick={() => handleDownloadInvoice(p.invoice_id || p.id)}
                            style={{ background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", color: "#00c4a7", padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}
                          >
                            📥 PDF
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="9" style={{ padding: "40px", textAlign: "center", color: "var(--text2)" }}>
                    No payment transactions found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* TRANSACTION & INVOICE INSPECTOR MODAL */}
      {selectedTxn && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.8)",
          backdropFilter: "blur(6px)",
          zIndex: 2000,
          display: "flex",
          justifyContent: "flex-end"
        }}>
          <div style={{
            width: "440px",
            maxWidth: "92%",
            height: "100%",
            background: "#0c1220",
            borderLeft: "1px solid rgba(255,255,255,0.1)",
            padding: "24px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "18px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "14px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", margin: 0 }}>Transaction & Invoice Inspector</h3>
                <span style={{ fontSize: "11px", color: "var(--cyan)", fontFamily: "monospace" }}>{selectedTxn.invoice_number || selectedTxn.transaction_id}</span>
              </div>
              <button onClick={() => setSelectedTxn(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "18px", cursor: "pointer" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>PURCHASER / ACCOUNT</div>
                <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff", marginTop: "4px" }}>{selectedTxn.student_name || "Enterprise Admin"}</div>
                <div style={{ fontSize: "11px", color: "var(--cyan)", marginTop: "2px" }}>{selectedTxn.organization_name}</div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>PLAN / SUBSCRIPTION ITEM</div>
                <div style={{ fontSize: "14px", fontWeight: 800, color: "#a78bfa", marginTop: "4px" }}>{selectedTxn.plan}</div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700 }}>BASE AMOUNT</div>
                  <div style={{ fontSize: "16px", fontWeight: 900, color: "#00c4a7", marginTop: "2px" }}>₹{selectedTxn.amount}</div>
                </div>
                <div>
                  <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700 }}>GST (18%)</div>
                  <div style={{ fontSize: "16px", fontWeight: 900, color: "#ec4899", marginTop: "2px" }}>₹{selectedTxn.gst || round(selectedTxn.amount * 0.18, 2)}</div>
                </div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px" }}>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>PAYMENT METHOD & REFERENCE</div>
                <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff", marginTop: "4px" }}>{selectedTxn.payment_method}</div>
                <div style={{ fontSize: "11px", color: "#94a3b8", fontFamily: "monospace", marginTop: "2px" }}>Ref: {selectedTxn.transaction_id}</div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>TRANSACTION STATUS</div>
                  <div style={{ fontSize: "12px", fontWeight: 800, color: "#10b981", marginTop: "2px" }}>{selectedTxn.status}</div>
                </div>
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  📅 {selectedTxn.created_at}
                </div>
              </div>
            </div>

            <div style={{ marginTop: "auto", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", gap: "10px" }}>
              <button
                onClick={() => handleDownloadInvoice(selectedTxn.invoice_id || selectedTxn.id)}
                style={{ flex: 1, padding: "10px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", border: "none", borderRadius: "8px", color: "#fff", fontWeight: 800, cursor: "pointer" }}
              >
                📥 Download Tax Invoice PDF
              </button>
              <button
                onClick={() => setSelectedTxn(null)}
                style={{ padding: "10px 14px", background: "rgba(255,255,255,0.08)", border: "none", borderRadius: "8px", color: "#fff", fontWeight: 800, cursor: "pointer" }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

function round(val, dec) {
  return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
}

