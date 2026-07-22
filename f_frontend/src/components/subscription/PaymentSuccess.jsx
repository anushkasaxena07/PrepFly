import React from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function PaymentSuccess({ data = {}, onClose }) {
  const invoiceId = data.invoice_id || data.invoice_number;

  const handleDownload = () => {
    if (invoiceId) {
      window.open(`${BACKEND_URL}/api/invoice/download/${invoiceId}`, '_blank');
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
      <div style={{ background: "linear-gradient(145deg, #0c1220, #141d30)", border: "1px solid rgba(0, 240, 200, 0.4)", borderRadius: "24px", padding: "36px", maxWidth: "480px", width: "100%", textAlign: "center", color: "#fff", boxShadow: "0 24px 64px rgba(0, 240, 200, 0.2)" }}>
        <div style={{ width: "72px", height: "72px", background: "rgba(0, 196, 167, 0.15)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "36px", margin: "0 auto 20px auto", border: "1px solid rgba(0, 196, 167, 0.4)" }}>
          🎉
        </div>

        <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", marginBottom: "8px" }}>Payment Successful!</h2>
        <p style={{ fontSize: "14px", color: "var(--cyan)", fontWeight: 700, marginBottom: "20px" }}>
          1-Year Premium Subscription Activated (₹500)
        </p>

        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "16px", fontSize: "13px", color: "var(--text2)", textAlign: "left", marginBottom: "24px", display: "flex", flexDirection: "column", gap: "8px" }}>
          <div><strong>Payment ID:</strong> <span style={{ color: "#fff" }}>{data.payment_id || "pay_verified"}</span></div>
          <div><strong>Invoice No:</strong> <span style={{ color: "#fff" }}>{data.invoice_number || "INV-GENERATE"}</span></div>
          <div><strong>Status:</strong> <span style={{ color: "#00c4a7", fontWeight: 700 }}>ACTIVE (365 Days)</span></div>
          <div><strong>Students Included:</strong> <span style={{ color: "#fff" }}>All Organization Members</span></div>
        </div>

        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          {invoiceId && (
            <button
              onClick={handleDownload}
              style={{ background: "linear-gradient(135deg, #00c4a7, #06b6d4)", border: "none", color: "#000", fontWeight: 800, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
            >
              📥 Download Invoice
            </button>
          )}
          <button
            onClick={onClose}
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff", fontWeight: 700, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
