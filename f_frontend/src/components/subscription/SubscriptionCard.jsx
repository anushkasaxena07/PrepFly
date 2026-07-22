import React from 'react';

export default function SubscriptionCard({ subscription, onUpgrade }) {
  const isPremium = subscription?.plan === "PREMIUM";
  const status = subscription?.status || "Active";

  const getStatusBadge = (st) => {
    if (st === "Active") return <span className="pill pill-cyan" style={{ background: "rgba(0,240,200,0.15)", color: "#00f0c8", border: "1px solid rgba(0,240,200,0.3)" }}>● Active</span>;
    if (st === "Trial") return <span className="pill pill-gold" style={{ background: "rgba(255,184,0,0.15)", color: "#ffb800", border: "1px solid rgba(255,184,0,0.3)" }}>● Trial</span>;
    return <span className="pill pill-red" style={{ background: "rgba(255,84,114,0.15)", color: "#ff5472", border: "1px solid rgba(255,84,114,0.3)" }}>● Expired</span>;
  };

  return (
    <div className="card" style={{ background: "linear-gradient(135deg, rgba(12,18,32,0.9), rgba(20,29,48,0.9))", border: "1px solid rgba(155,109,255,0.25)", borderRadius: "16px", padding: "24px", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: "-40px", right: "-40px", width: "160px", height: "160px", background: "radial-gradient(circle, rgba(155,109,255,0.15) 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none" }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "var(--cyan)", letterSpacing: "1px", marginBottom: "4px" }}>
            Current Subscription Plan
          </div>
          <h2 style={{ fontSize: "24px", fontWeight: 900, margin: 0, color: "#fff", display: "flex", alignItems: "center", gap: "10px" }}>
            <span>{isPremium ? "💎 PREMIUM PLAN" : "🌱 FREE TIER"}</span>
            {getStatusBadge(status)}
          </h2>
        </div>

        {!isPremium && (
          <button 
            className="btn btn-primary" 
            style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", boxShadow: "0 8px 24px rgba(124,79,224,0.35)", padding: "10px 20px", fontWeight: 800 }}
            onClick={onUpgrade}
          >
            👑 Upgrade to Premium
          </button>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "16px", background: "rgba(0,0,0,0.25)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.06)" }}>
        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Start Date</div>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>{subscription?.start_date || "2026-07-01"}</div>
        </div>

        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Expiry Date</div>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>{subscription?.expiry_date || "2027-07-01"}</div>
        </div>

        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Days Remaining</div>
          <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--cyan)" }}>{subscription?.days_remaining ?? 365} Days</div>
        </div>

        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Auto Renewal</div>
          <div style={{ fontSize: "13px", fontWeight: 700, color: subscription?.auto_renew ? "var(--cyan)" : "var(--text2)" }}>
            {subscription?.auto_renew ? "Enabled" : "Disabled"}
          </div>
        </div>

        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Next Billing Date</div>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>{subscription?.next_billing_date || "N/A"}</div>
        </div>

        <div>
          <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "4px" }}>Payment Status</div>
          <div style={{ fontSize: "13px", fontWeight: 800, color: "#00f0c8" }}>{subscription?.payment_status || "Paid"}</div>
        </div>
      </div>
    </div>
  );
}
