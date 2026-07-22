import React from 'react';
import InvoiceTable from './InvoiceTable';

export default function PaymentHistory({ payments = [] }) {
  return (
    <div className="card" style={{ background: "rgba(12, 18, 32, 0.95)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px", marginTop: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🧾</span> Billing & Payment History
          </h3>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px", margin: 0 }}>
            Official transaction receipts and downloadable invoices for your annual subscription.
          </p>
        </div>
        <span className="pill pill-purple" style={{ fontSize: "11px" }}>
          {payments.length} Transaction(s)
        </span>
      </div>

      <InvoiceTable payments={payments} />
    </div>
  );
}
