import React from 'react';

export default function PremiumBenefits() {
  const benefits = [
    { title: "Unlimited AI Interview", desc: "Unlimited 24/7 AI-driven mock interviews with instant voice and text evaluation.", icon: "🎤" },
    { title: "ATS Resume Score", desc: "Scan and optimize your resume against top tech company job descriptions.", icon: "📄" },
    { title: "Detailed Reports", desc: "Comprehensive executive reports covering code complexity, filler words, and STAR responses.", icon: "📊" },
    { title: "AI Career Suggestions", desc: "Personalized skill roadmap recommendations based on your performance trends.", icon: "🚀" },
    { title: "Coding Leaderboard", desc: "Compete with global engineering candidates on real-time coding assessments.", icon: "🏆" },
    { title: "Premium Badge", desc: "Stand out with an verified Premium Badge on your profile and shared credentials.", icon: "👑" },
    { title: "Certificate Download", desc: "Earn and download verified certificates of achievement upon completing interview tracks.", icon: "📜" },
    { title: "Priority Support", desc: "Direct 1-on-1 priority support and mentor guidance for technical interview prep.", icon: "⚡" }
  ];

  return (
    <div style={{ margin: "32px 0" }}>
      <div style={{ fontSize: "18px", fontWeight: 900, color: "#fff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
        <span>💎</span> Premium Member Benefits
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
        {benefits.map((b, idx) => (
          <div key={idx} style={{ background: "rgba(12,18,32,0.75)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "14px", padding: "18px", transition: "transform 0.2s ease, border-color 0.2s ease" }}>
            <div style={{ fontSize: "28px", marginBottom: "10px" }}>{b.icon}</div>
            <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff", marginBottom: "4px" }}>{b.title}</div>
            <div style={{ fontSize: "12px", color: "var(--text2)", lineHeight: "1.5" }}>{b.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
