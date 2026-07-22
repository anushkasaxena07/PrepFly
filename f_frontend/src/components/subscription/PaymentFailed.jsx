import React from 'react';

export default function PaymentFailed({ errorMsg, onRetry, onClose }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
      <div style={{ background: "linear-gradient(145deg, #0c1220, #1a1020)", border: "1px solid rgba(239, 68, 68, 0.4)", borderRadius: "24px", padding: "36px", maxWidth: "440px", width: "100%", textAlign: "center", color: "#fff", boxShadow: "0 24px 64px rgba(239, 68, 68, 0.2)" }}>
        <div style={{ width: "72px", height: "72px", background: "rgba(239, 68, 68, 0.15)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "36px", margin: "0 auto 20px auto", border: "1px solid rgba(239, 68, 68, 0.4)" }}>
          ❌
        </div>

        <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", marginBottom: "8px" }}>Payment Failed</h2>
        <p style={{ fontSize: "13px", color: "#f87171", marginBottom: "20px" }}>
          {errorMsg || "Transaction verification failed or payment was cancelled by user."}
        </p>

        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "16px", fontSize: "12px", color: "var(--text2)", textAlign: "center", marginBottom: "24px" }}>
          No funds were charged. You can retry payment at any time to activate your 1-Year Premium subscription.
        </div>

        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          {onRetry && (
            <button
              onClick={onRetry}
              style={{ background: "linear-gradient(135deg, #ef4444, #f97316)", border: "none", color: "#fff", fontWeight: 800, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
            >
              🔄 Retry Payment
            </button>
          )}
          <button
            onClick={onClose}
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff", fontWeight: 700, padding: "12px 20px", borderRadius: "12px", cursor: "pointer", fontSize: "13px" }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
