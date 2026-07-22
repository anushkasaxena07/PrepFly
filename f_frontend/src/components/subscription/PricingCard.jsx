import React from 'react';

export default function PricingCard({ currentPlan, onUpgrade, isProcessing }) {
  const isPremium = currentPlan === "PREMIUM";

  return (
    <div style={{ margin: "24px 0" }}>
      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0 }}>Flexible Pricing Plans</h2>
        <p style={{ fontSize: "13px", color: "var(--text2)", marginTop: "4px" }}>Choose the plan that fits your career growth and technical preparation.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px", maxWidth: "800px", margin: "0 auto" }}>
        
        {/* CARD 1: FREE */}
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "16px", padding: "28px", display: "flex", flexDirection: "column", position: "relative" }}>
          <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--text2)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>FREE PLAN</div>
          <div style={{ fontSize: "36px", fontWeight: 900, color: "#fff", marginBottom: "16px" }}>
            ₹0 <span style={{ fontSize: "14px", color: "var(--text2)", fontWeight: 500 }}>/ forever</span>
          </div>

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "16px", marginBottom: "24px", flex: 1, display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px", color: "var(--text1)" }}>
            <div>✓ 3 AI Interviews</div>
            <div>✓ 5 Coding Tests</div>
            <div>✓ Basic Reports</div>
            <div>✓ Community Support</div>
          </div>

          <button 
            className="btn btn-ghost" 
            style={{ width: "100%", justifyContent: "center", fontWeight: 700, cursor: !isPremium ? "default" : "pointer" }}
            disabled={!isPremium}
          >
            {!isPremium ? "Current Plan" : "Downgrade to Free"}
          </button>
        </div>

        {/* CARD 2: PREMIUM (HIGHLIGHTED) */}
        <div style={{ background: "linear-gradient(145deg, rgba(20,29,50,0.95), rgba(30,22,60,0.95))", border: "2px solid var(--purple)", borderRadius: "16px", padding: "28px", display: "flex", flexDirection: "column", position: "relative", boxShadow: "0 16px 48px rgba(124,79,224,0.3)" }}>
          <div style={{ position: "absolute", top: "-12px", right: "20px", background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", color: "#fff", fontSize: "10px", fontWeight: 900, textTransform: "uppercase", padding: "4px 12px", borderRadius: "12px", letterSpacing: "1px" }}>
            MOST POPULAR
          </div>

          <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--cyan)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>PREMIUM PLAN</div>
          <div style={{ fontSize: "36px", fontWeight: 900, color: "#fff", marginBottom: "16px" }}>
            ₹299 <span style={{ fontSize: "14px", color: "var(--cyan)", fontWeight: 600 }}>/ month</span>
          </div>

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", paddingTop: "16px", marginBottom: "24px", flex: 1, display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px", color: "#fff" }}>
            <div style={{ fontWeight: 700, color: "var(--cyan)" }}>✓ Unlimited AI Interviews</div>
            <div style={{ fontWeight: 700, color: "var(--cyan)" }}>✓ Unlimited Coding Tests</div>
            <div style={{ fontWeight: 700, color: "var(--cyan)" }}>✓ Unlimited Resume Analysis</div>
            <div>✓ Detailed AI Feedback & Coaching</div>
            <div>✓ Certificates of Completion</div>
            <div>✓ Priority Support & Direct Guidance</div>
            <div>✓ Advanced Performance Analytics</div>
          </div>

          <button 
            className="btn btn-primary" 
            style={{ width: "100%", justifyContent: "center", background: isPremium ? "var(--cyan)" : "linear-gradient(135deg, #7c4fe0, #00c4a7)", color: isPremium ? "#0c1220" : "#fff", fontWeight: 900, padding: "12px", fontSize: "14px", border: "none", boxShadow: "0 8px 24px rgba(0,240,200,0.3)" }}
            onClick={onUpgrade}
            disabled={isProcessing || isPremium}
          >
            {isPremium ? "✓ Active Premium Plan" : isProcessing ? "⏳ Processing Razorpay..." : "👑 Upgrade Now"}
          </button>
        </div>

      </div>
    </div>
  );
}
