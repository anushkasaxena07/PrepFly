import React, { useState } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function PaymentTable({ payments = [] }) {
  const [statusFilter, setStatusFilter] = useState("All");
  const [search, setSearch] = useState("");

  const filtered = payments.filter(p => {
    if (statusFilter !== "All" && p.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (p.organization_name || "").toLowerCase().includes(q) || (p.transaction_id || "").toLowerCase().includes(q) || (p.invoice_number || "").toLowerCase().includes(q);
    }
    return true;
  });

  const totalRev = payments.reduce((sum, p) => sum + (p.amount || 0), 0);
  const totalGst = payments.reduce((sum, p) => sum + (p.gst || 0), 0);

  const handleExportCSV = () => {
    if (!filtered || filtered.length === 0) return alert("No payment transactions to export");
    const headers = ["Txn ID", "Invoice No", "Organization", "Plan", "Amount", "GST", "Method", "Status", "Date"];
    const rows = filtered.map(p => [
      `"${p.transaction_id || p.id}"`,
      `"${p.invoice_number || ''}"`,
      `"${(p.organization_name || '').replace(/"/g, '""')}"`,
      `"${p.plan}"`,
      p.amount,
      p.gst,
      `"${p.payment_method}"`,
      `"${p.status}"`,
      `"${p.created_at}"`
    ]);
    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "platform_payments_ledger.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadInvoice = (invoiceId) => {
    window.open(`${BACKEND_URL}/api/invoice/download/${invoiceId}`, '_blank');
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      
      {/* REVENUE METRIC CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "16px" }}>
          <div style={{ fontSize: "10px", color: "var(--text2)", fontWeight: 800 }}>TOTAL COLLECTED REVENUE</div>
          <div style={{ fontSize: "24px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>₹{totalRev.toFixed(2)}</div>
        </div>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "16px" }}>
          <div style={{ fontSize: "10px", color: "var(--text2)", fontWeight: 800 }}>TOTAL GST (18%)</div>
          <div style={{ fontSize: "24px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>₹{totalGst.toFixed(2)}</div>
        </div>
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "16px" }}>
          <div style={{ fontSize: "10px", color: "var(--text2)", fontWeight: 800 }}>TOTAL SUCCESSFUL TRANSACTIONS</div>
          <div style={{ fontSize: "24px", fontWeight: 900, color: "#8b5cf6", marginTop: "4px" }}>{payments.length}</div>
        </div>
      </div>

      {/* SEARCH AND FILTERS */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <input 
            type="text" 
            placeholder="🔍 Search organization or txn ID..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: "260px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff", fontSize: "13px" }}
          />

          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
            <option value="All">All Payment Statuses</option>
            <option value="Success">Success</option>
            <option value="Captured">Captured</option>
            <option value="Failed">Failed</option>
            <option value="Refunded">Refunded</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-ghost btn-sm" onClick={handleExportCSV}>📊 Export CSV</button>
        </div>
      </div>

      {/* TABLE */}
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--text2)", fontSize: "11px", textTransform: "uppercase" }}>
                <th style={{ padding: "10px" }}>Txn / Invoice ID</th>
                <th style={{ padding: "10px" }}>Organization</th>
                <th style={{ padding: "10px" }}>Plan Tier</th>
                <th style={{ padding: "10px" }}>Amount</th>
                <th style={{ padding: "10px" }}>GST (18%)</th>
                <th style={{ padding: "10px" }}>Method</th>
                <th style={{ padding: "10px" }}>Status</th>
                <th style={{ padding: "10px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "var(--cyan)", fontFamily: "monospace" }}>
                    <div>{p.transaction_id || p.id}</div>
                    <div style={{ fontSize: "10px", color: "var(--text2)" }}>{p.invoice_number || ''}</div>
                  </td>
                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>
                    <div>{p.organization_name}</div>
                  </td>
                  <td style={{ padding: "12px 10px" }}><span className="pill pill-purple" style={{ fontSize: "10px" }}>{p.plan || "Premium (1 Year)"}</span></td>
                  <td style={{ padding: "12px 10px", fontWeight: 900, color: "#00c4a7" }}>₹{p.amount}</td>
                  <td style={{ padding: "12px 10px", color: "var(--text2)" }}>₹{p.gst || round(p.amount * 0.18, 2)}</td>
                  <td style={{ padding: "12px 10px", color: "var(--text1)" }}>{p.payment_method || "Razorpay UPI / Card"}</td>
                  <td style={{ padding: "12px 10px" }}><span className="pill pill-cyan" style={{ fontSize: "10px" }}>● {p.status}</span></td>
                  <td style={{ padding: "12px 10px", textAlign: "right" }}>
                    <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                      <button className="btn btn-ghost btn-xs" onClick={() => handleDownloadInvoice(p.invoice_id || p.id)}>📥 Invoice PDF</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function round(val, dec) {
  return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
}
