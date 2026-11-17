import React, { useState, useEffect } from 'react';
import { getSuperAdminIntegrityAudit } from '../../services/superAdminAPI';

export default function DataIntegrity() {
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);

  useEffect(() => {
    runAudit();
  }, []);

  const runAudit = async () => {
    setRecalculating(true);
    try {
      const data = await getSuperAdminIntegrityAudit();
      setAudit(data);
    } catch (e) {
      console.error("Integrity audit error:", e);
    } finally {
      setLoading(false);
      setRecalculating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ color: "#6d28d9", padding: "60px", textAlign: "center", fontWeight: 800 }}>
        ⚡ Running Automated Database Integrity & Balance Audit...
      </div>
    );
  }

  const checks = audit?.checks || [];
  const metrics = audit?.database_metrics || {};
  const isHealthy = audit?.healthy === true || audit?.status === "HEALTHY";
  const passedChecksCount = audit?.passed_checks ?? audit?.passed_checks_count ?? 0;
  const totalChecksCount = audit?.total_checks ?? audit?.total_checks_count ?? checks.length;
  const healthScore = audit?.overall_health_score ?? (totalChecksCount > 0 ? Math.round((passedChecksCount / totalChecksCount) * 100) : 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#0f172a", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            ⚖️ Data Integrity & Financial Reconciliation Audit
          </h2>
          <p style={{ fontSize: "12px", color: "#64748b", margin: "4px 0 0 0" }}>
            Automated verification engine checking entity balances, ledger consistency, zero-fabrication constraints, and orphaned records.
          </p>
        </div>

        <button
          onClick={runAudit}
          disabled={recalculating}
          style={{
            background: "linear-gradient(135deg, #6d28d9, #7c3aed)",
            border: "none",
            borderRadius: "8px",
            padding: "9px 18px",
            color: "#fff",
            fontSize: "12px",
            fontWeight: 800,
            cursor: recalculating ? "not-allowed" : "pointer",
            boxShadow: "0 4px 12px rgba(109,40,217,0.3)",
            opacity: recalculating ? 0.7 : 1
          }}
        >
          {recalculating ? "🔄 Auditing Database..." : "🔄 Recalculate Now"}
        </button>
      </div>

      {/* TOP AUDIT SUMMARY CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
        
        <div style={{ background: "#ffffff", border: `1px solid ${isHealthy ? "#a7f3d0" : "#fed7aa"}`, borderRadius: "14px", padding: "18px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 800 }}>INTEGRITY STATUS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: isHealthy ? "#059669" : "#ea580c", marginTop: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>{isHealthy ? "🟢 HEALTHY" : "⚠️ ATTENTION"}</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
            {passedChecksCount} of {totalChecksCount} invariant checks passed
          </div>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "18px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 800 }}>HEALTH SCORE</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#6d28d9", marginTop: "4px" }}>
            {healthScore}%
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
            Database Balance Compliance
          </div>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "18px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 800 }}>TOTAL REVENUE AUDITED</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#0f172a", marginTop: "4px" }}>
            ₹{(metrics?.total_revenue_inr || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
            {metrics?.total_revenue_paise?.toLocaleString() || 0} paise computed
          </div>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "18px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 800 }}>DATABASE ENTITIES AUDITED</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#0f172a", marginTop: "4px" }}>
            {(metrics?.total_users || 0) + (metrics?.total_sessions || 0) + (metrics?.total_payments || 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
            {metrics?.total_users || 0} users · {metrics?.total_sessions || 0} sessions
          </div>
        </div>

      </div>

      {/* CHECK RESULTS TABLE */}
      <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "20px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: "0 0 16px 0" }}>
          📋 Invariant Verification Checks
        </h3>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #cbd5e1", color: "#64748b", textAlign: "left", fontSize: "11px", textTransform: "uppercase" }}>
                <th style={{ padding: "10px" }}>Check Name</th>
                <th style={{ padding: "10px" }}>Result</th>
                <th style={{ padding: "10px" }}>Audit Finding</th>
                <th style={{ padding: "10px" }}>Expected Value</th>
                <th style={{ padding: "10px" }}>Actual Value</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((chk, idx) => {
                const isPassed = chk.passed === true || chk.status === "PASS";
                return (
                  <tr key={chk.id || chk.check || idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "12px 10px", fontWeight: 700, color: "#0f172a" }}>
                      {chk.check || chk.name}
                    </td>
                    <td style={{ padding: "12px 10px" }}>
                      <span style={{
                        display: "inline-block",
                        padding: "3px 8px",
                        borderRadius: "6px",
                        fontWeight: 800,
                        fontSize: "10px",
                        background: isPassed ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                        color: isPassed ? "#059669" : "#dc2626"
                      }}>
                        {isPassed ? "✓ PASSED" : "✕ ATTENTION"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 10px", color: "#475569" }}>
                      {chk.description || chk.message}
                    </td>
                    <td style={{ padding: "12px 10px", color: "#64748b", fontFamily: "monospace" }}>
                      {String(chk.expected ?? "—")}
                    </td>
                    <td style={{ padding: "12px 10px", color: "#0f172a", fontWeight: 700, fontFamily: "monospace" }}>
                      {String(chk.actual ?? "—")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
