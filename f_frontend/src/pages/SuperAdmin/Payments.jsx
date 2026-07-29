import React, { useState, useEffect } from 'react';
import PaymentTable from '../../components/SuperAdmin/PaymentTable';
import { getSuperAdminPayments } from '../../services/superAdminAPI';

export default function Payments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoSync, setAutoSync] = useState(true);

  useEffect(() => {
    fetchPayments();
  }, []);

  useEffect(() => {
    let interval = null;
    if (autoSync) {
      interval = setInterval(() => {
        fetchPayments(true);
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoSync]);

  const fetchPayments = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await getSuperAdminPayments();
      setPayments(data || []);
    } catch (e) {
      console.error("Failed to fetch payments:", e);
    } finally {
      if (!silent) setLoading(false);
      setRefreshing(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
      
      {/* HEADER BAR */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            💳 Platform Revenue & Payment Transactions
            {refreshing && <span style={{ fontSize: "12px", color: "var(--cyan)", fontWeight: 700 }}>⚡ Syncing...</span>}
          </h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "3px" }}>
            Global transaction ledger across all student subscriptions, AI practice passes, and enterprise admin contracts.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            onClick={() => setAutoSync(!autoSync)}
            style={{
              background: autoSync ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${autoSync ? "#10b981" : "rgba(255,255,255,0.12)"}`,
              borderRadius: "8px",
              padding: "7px 12px",
              fontSize: "11px",
              color: autoSync ? "#10b981" : "#94a3b8",
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            {autoSync ? '🟢 Live Sync (5s)' : '⏸ Sync Off'}
          </button>

          <button
            onClick={() => fetchPayments(false)}
            style={{
              background: "linear-gradient(135deg, #00c4a7, #7c4fe0)",
              border: "none",
              borderRadius: "8px",
              padding: "7px 14px",
              fontSize: "11px",
              color: "#fff",
              fontWeight: 800,
              cursor: "pointer"
            }}
          >
            🔄 Refresh Ledger
          </button>
        </div>
      </div>

      {loading && !payments.length ? (
        <div style={{ color: "#00c4a7", padding: "60px", textAlign: "center", fontWeight: 800 }}>⚡ Synchronizing platform global payments ledger...</div>
      ) : (
        <PaymentTable payments={payments} />
      )}
    </div>
  );
}
