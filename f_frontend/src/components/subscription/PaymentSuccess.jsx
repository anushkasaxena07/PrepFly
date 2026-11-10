import { downloadInvoice } from '../../services/adminAPI';
import React from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function PaymentSuccess({ data = {}, onClose }) {
  const invoiceId = data.invoice_id || data.invoice_number;

  const handleDownload = async () => {
    if (invoiceId) {
      try {
        await downloadInvoice(invoiceId, `Invoice-${invoiceId}`);
      } catch (e) {
        alert(e.message || "Failed to download invoice");
      }
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
      <div style={{ background: "linear-gradient(145deg, #0c1220, #141d30)", border: "1px solid rgba(0, 240, 200, 0.4)", borderRadius: "24px", padding: "36px", maxWidth: "480px", width: "100%", textAlign: "center", color: "#fff", boxShadow: "0 24px 64px rgba(0, 240, 200, 0.2)" }}>
        <div style={{ width: "72px", height: "72px", background: "rgba(109, 40, 217, 0.15)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "36px", margin: "0 auto 20px auto", border: "1px solid rgba(109, 40, 217, 0.4)" }}>
          🎉
        </div>

        <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#0f172a", marginBottom: "8px" }}>Payment Successful!</h2>
        <p style={{ fontSize: "14px", color: "var(--cyan)", fontWeight: 700, marginBottom: "20px" }}>
          1-Year Premium Subscription Activated (₹500)
        </p>

        <div style={{ background: "#f8fafc", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "16px", fontSize: "13px", color: "var(--text2)", textAlign: "left", marginBottom: "24px", display: "flex", flexDirection: "column", gap: "8px" }}>
          <div><strong>Payment ID:</strong> <span style={{ color: "#0f172a" }}>{data.payment_id || "pay_verified"}</span></div>
          <div><strong>Invoice No:</strong> <span style={{ color: "#0f172a" }}>{data.invoice_number || "INV-GENERATE"}</span></div>
          <div><strong>Status:</strong> <span style={{ color: "#6d28d9", fontWeight: 700 }}>ACTIVE (365 Days)</span></div>
          <div><strong>Students Included:</strong> <span style={{ color: "#0f172a" }}>All Organization Members</span></div>
        </div>

        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          {invoiceId && (
            <button
              onClick={handleDownload}
              style={{ background: "linear-gradient(135deg, #6d28d9, #06b6d4)", border: "none", color: "#000", fontWeight: 800, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
            >
              📥 Download Invoice
            </button>
          )}
          <button
            onClick={onClose}
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid #cbd5e1", color: "#0f172a", fontWeight: 700, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
