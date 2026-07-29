import React, { useState, useEffect } from 'react';
import PaymentTable from '../../components/SuperAdmin/PaymentTable';
import { getSuperAdminPayments } from '../../services/superAdminAPI';

export default function Payments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      const data = await getSuperAdminPayments();
      setPayments(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>💳 Platform Revenue & Payment Transactions</h2>
        <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Global transaction ledger across all student subscriptions and enterprise contracts.</p>
      </div>

      {loading ? (
        <div style={{ color: "#ec4899", padding: "40px", textAlign: "center" }}>⚡ Loading payment ledger...</div>
      ) : (
        <PaymentTable payments={payments} />
      )}
    </div>
  );
}
