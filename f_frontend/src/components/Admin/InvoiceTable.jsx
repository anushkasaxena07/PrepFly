import React from 'react';

export default function InvoiceTable({ invoices = [] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--text2)", fontSize: "11px", textTransform: "uppercase" }}>
            <th style={{ padding: "10px" }}>Invoice ID</th>
            <th style={{ padding: "10px" }}>Date</th>
            <th style={{ padding: "10px" }}>Base Amount</th>
            <th style={{ padding: "10px" }}>GST (18%)</th>
            <th style={{ padding: "10px" }}>Total</th>
            <th style={{ padding: "10px", textAlign: "right" }}>Download</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(inv => (
            <tr key={inv.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <td style={{ padding: "12px 10px", fontWeight: 800, color: "var(--cyan)", fontFamily: "monospace" }}>{inv.invoice_number}</td>
              <td style={{ padding: "12px 10px", color: "var(--text2)" }}>{inv.created_at?.slice(0, 10)}</td>
              <td style={{ padding: "12px 10px" }}>₹{inv.amount}</td>
              <td style={{ padding: "12px 10px", color: "var(--text2)" }}>₹{inv.gst}</td>
              <td style={{ padding: "12px 10px", fontWeight: 900, color: "#00c4a7" }}>₹{(inv.amount + inv.gst).toFixed(2)}</td>
              <td style={{ padding: "12px 10px", textAlign: "right" }}>
                <a className="btn btn-ghost btn-xs" href={`http://localhost:5000/api/invoice/${inv.id}`} target="_blank" rel="noreferrer">📥 View PDF</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
