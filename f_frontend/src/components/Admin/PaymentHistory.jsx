import React, { useState, useEffect } from 'react';
import { adminFetch, downloadInvoice } from '../../services/adminAPI';
import { BACKEND_URL } from '../../config/apiConfig';

export default function PaymentHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await adminFetch("/payment/history");
      if (res.ok) {
        const data = await res.json();
        setHistory(data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadInvoice = async (invoiceId) => {
    try {
      await downloadInvoice(invoiceId, `Invoice-${invoiceId}`);
    } catch (e) {
      alert(e.message || "Failed to download invoice");
    }
  };

  if (loading) {
    return <div style={{ color: "var(--cyan)", padding: "20px", textAlign: "center" }}>⚡ Loading payment history...</div>;
  }

  return (
    <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "24px" }}>
      <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
        <span>📜</span> Payment & Subscription Receipts
      </h3>

      {history.length === 0 ? (
        <div style={{ padding: "24px", color: "var(--text2)", textAlign: "center", background: "#f8fafc", borderRadius: "10px" }}>
          No previous subscription payment transactions found.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #cbd5e1", color: "var(--text2)", fontSize: "11px", textTransform: "uppercase" }}>
                <th style={{ padding: "10px" }}>Invoice Number</th>
                <th style={{ padding: "10px" }}>Date</th>
                <th style={{ padding: "10px" }}>Amount</th>
                <th style={{ padding: "10px" }}>Payment Method</th>
                <th style={{ padding: "10px" }}>Status</th>
                <th style={{ padding: "10px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {history.map(item => (
                <tr key={item.id} style={{ borderBottom: "1px solid #e5e8f2" }}>
                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "var(--cyan)", fontFamily: "monospace" }}>{item.invoice_number || item.id}</td>
                  <td style={{ padding: "12px 10px", color: "var(--text2)" }}>{item.created_at ? item.created_at.slice(0, 10) : "2026-07-20"}</td>
                  <td style={{ padding: "12px 10px", fontWeight: 900, color: "#0f172a" }}>₹{item.amount || 500}</td>
                  <td style={{ padding: "12px 10px", color: "var(--text1)" }}>{item.payment_method || "Razorpay UPI"}</td>
                  <td style={{ padding: "12px 10px" }}><span className="pill pill-cyan" style={{ fontSize: "10px" }}>● {item.status || "Paid"}</span></td>
                  <td style={{ padding: "12px 10px", textAlign: "right" }}>
                    <button className="btn btn-ghost btn-xs" onClick={() => handleDownloadInvoice(item.invoice_id || item.invoice_number || item.id)}>
                      📥 Download Invoice
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
