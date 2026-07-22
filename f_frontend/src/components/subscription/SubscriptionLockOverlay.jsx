import React from 'react';
import RenewButton from './RenewButton';

export default function SubscriptionLockOverlay({ featureName = "This Feature", apiFetch, orgId, isAdmin = false }) {
  const organizationId = orgId || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";

  return (
    <div style={{
      width: "100%",
      minHeight: "420px",
      background: "linear-gradient(145deg, rgba(12, 18, 32, 0.95), rgba(24, 18, 40, 0.98))",
      border: "1px solid rgba(239, 68, 68, 0.4)",
      borderRadius: "24px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justify: "center",
      padding: "48px 24px",
      textAlign: "center",
      boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
      color: "#fff",
      position: "relative",
      overflow: "hidden"
    }}>
      
      {/* BACKGROUND GLOW */}
      <div style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        width: "300px",
        height: "300px",
        background: "radial-gradient(circle, rgba(239, 68, 68, 0.15) 0%, rgba(0, 0, 0, 0) 70%)",
        pointerEvents: "none"
      }} />

      <div style={{
        width: "80px",
        height: "80px",
        background: "rgba(239, 68, 68, 0.12)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "36px",
        marginBottom: "20px"
      }}>
        🔒
      </div>

      <span className="pill pill-red" style={{ fontSize: "11px", marginBottom: "12px" }}>
        Subscription Required
      </span>

      <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: "0 0 8px 0", maxWidth: "540px" }}>
        Your organization's trial has expired.
      </h2>

      <p style={{ fontSize: "14px", color: "var(--text2)", maxWidth: "480px", margin: "0 0 28px 0", lineHeight: 1.5 }}>
        Access to <strong>{featureName}</strong> is temporarily locked. Renew your organization's subscription to continue practicing and generating reports.
      </p>

      {isAdmin ? (
        <RenewButton
          apiFetch={apiFetch}
          orgId={organizationId}
          onSuccess={() => window.location.reload()}
          label="Renew Subscription (₹500 / Year)"
          style={{ padding: "14px 28px", fontSize: "14px" }}
        />
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "12px",
          padding: "14px 20px",
          fontSize: "13px",
          color: "var(--text1)",
          maxWidth: "400px"
        }}>
          💡 Please inform your Organization / College Administrator to renew the subscription plan.
        </div>
      )}

    </div>
  );
}
