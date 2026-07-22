import React from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function InvoiceTable({ payments = [] }) {
  if (!payments || payments.length === 0) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "var(--text2)", background: "rgba(12, 18, 32, 0.6)", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.06)" }}>
        No payment invoices generated yet.
      </div>
    );
  }

  const handleDownload = (invoiceId) => {
    window.open(`${BACKEND_URL}/api/invoice/download/${invoiceId}`, '_blank');
  };

  const handleView = (invoiceId) => {
    window.open(`${BACKEND_URL}/api/invoice/${invoiceId}`, '_blank');
  };

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff", fontSize: "13px" }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.08)", textTransform: "uppercase", fontSize: "11px", color: "var(--text2)", letterSpacing: "0.5px" }}>
            <th style={{ padding: "14px 16px", textAlign: "left" }}>Invoice Number</th>
            <th style={{ padding: "14px 16px", textAlign: "left" }}>Date</th>
            <th style={{ padding: "14px 16px", textAlign: "left" }}>Amount</th>
            <th style={{ padding: "14px 16px", textAlign: "left" }}>GST (18%)</th>
            <th style={{ padding: "14px 16px", textAlign: "left" }}>Payment Method</th>
            <th style={{ padding: "14px 16px", textAlign: "center" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {payments.map((p, idx) => {
            const amount = p.amount || 500.0;
            const gst = round(amount * 0.18, 2);
            const invId = p.invoice_id || p.id;
            return (
              <tr key={p.id || idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: idx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                <td style={{ padding: "14px 16px", fontWeight: 700, color: "var(--cyan)" }}>
                  📄 {p.invoice_number || `INV-${p.id}`}
                </td>
                <td style={{ padding: "14px 16px", color: "var(--text2)" }}>
                  {p.created_at ? p.created_at.substring(0, 10) : "Today"}
                </td>
                <td style={{ padding: "14px 16px", fontWeight: 800, color: "#fff" }}>
                  ₹{amount.toFixed(2)}
                </td>
                <td style={{ padding: "14px 16px", color: "var(--text2)" }}>
                  ₹{gst.toFixed(2)}
                </td>
                <td style={{ padding: "14px 16px", color: "var(--text1)" }}>
                  {p.payment_method || "Razorpay UPI / Card"}
                </td>
                <td style={{ padding: "14px 16px", textAlign: "center" }}>
                  <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
                    <button
                      onClick={() => handleView(invId)}
                      style={{ background: "rgba(6, 182, 212, 0.15)", border: "1px solid rgba(6, 182, 212, 0.3)", color: "var(--cyan)", padding: "6px 12px", borderRadius: "8px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}
                    >
                      👁️ View
                    </button>
                    <button
                      onClick={() => handleDownload(invId)}
                      style={{ background: "rgba(168, 85, 247, 0.15)", border: "1px solid rgba(168, 85, 247, 0.3)", color: "#a855f7", padding: "6px 12px", borderRadius: "8px", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}
                    >
                      📥 Download PDF
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function round(val, dec) {
  return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
}
