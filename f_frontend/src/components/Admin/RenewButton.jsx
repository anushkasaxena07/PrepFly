import React, { useState } from 'react';
import { adminFetch } from '../../services/adminAPI';

export default function RenewButton({ onSuccess, label = "Renew Subscription (₹500 / Year)", style = {} }) {
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    setLoading(true);
    try {
      const orderRes = await adminFetch("/payment/create-order", { method: "POST" });
      if (!orderRes.ok) throw new Error("Failed to create payment order");
      const orderData = await orderRes.json();

      const { order_id, amount, currency, key_id } = orderData;

      const options = {
        key: key_id || "rzp_test_demoKey123",
        amount: amount || 50000,
        currency: currency || "INR",
        name: "PrepFly Enterprise SaaS",
        image: "/prepfly-logo.png",
        description: "1-Year Unlimited Annual Subscription (₹500)",
        order_id: order_id,
        handler: async function (response) {
          try {
            const verifyRes = await adminFetch("/payment/verify", {
              method: "POST",
              body: JSON.stringify({
                order_id: response.razorpay_order_id || order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature
              })
            });

            if (!verifyRes.ok) {
              const err = await verifyRes.json();
              throw new Error(err.error || "Server-side payment verification failed!");
            }

            const verifyData = await verifyRes.json();
            alert("🎉 Payment Verified Successfully! Your 1-Year Enterprise Subscription is now ACTIVE.");
            if (onSuccess) onSuccess(verifyData);
          } catch (err) {
            alert("❌ Payment Verification Failed: " + err.message);
          } finally {
            setLoading(false);
          }
        },
        prefill: {
          name: "Organization Admin",
          email: "admin@college.edu",
          contact: "+91 9876543210"
        },
        theme: {
          color: "#7c3aed"
        }
      };

      const isDemoKey = !key_id || key_id.includes("demoKey") || key_id.includes("test_demo") || order_id.includes("order_sim");

      if (window.Razorpay && !isDemoKey) {
        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
        const simPaymentId = `pay_rzp_sim_${Date.now()}`;
        const simSig = `sig_valid_${Date.now()}`;
        
        if (window.confirm(`Proceed with simulated payment verification of ₹500 for Order ${order_id}?`)) {
          const verifyRes = await adminFetch("/payment/verify", {
            method: "POST",
            body: JSON.stringify({
              order_id: order_id,
              payment_id: simPaymentId,
              signature: simSig
            })
          });

          if (!verifyRes.ok) {
            const err = await verifyRes.json();
            throw new Error(err.error || "Server payment verification failed");
          }

          const verifyData = await verifyRes.json();
          alert("🎉 Payment Verified Successfully! 1-Year Premium Subscription Activated.");
          if (onSuccess) onSuccess(verifyData);
        }
        setLoading(false);
      }

    } catch (err) {
      alert("Payment Error: " + err.message);
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handlePayment}
      disabled={loading}
      className="btn btn-primary"
      style={{
        background: "linear-gradient(135deg, #7c3aed, #00c4a7)",
        border: "none",
        color: "#ffffff",
        fontWeight: 800,
        fontSize: "14px",
        padding: "14px 28px",
        borderRadius: "14px",
        boxShadow: "0 8px 24px rgba(124, 58, 237, 0.4)",
        cursor: loading ? "not-allowed" : "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        whiteSpace: "nowrap",
        lineHeight: 1,
        transition: "all 0.2s ease",
        ...style
      }}
    >
      {loading ? (
        <>
          <span style={{ fontSize: "16px" }}>⚡</span>
          <span>Processing Payment...</span>
        </>
      ) : (
        <>
          <span style={{ fontSize: "16px", lineHeight: 1 }}>👑</span>
          <span style={{ whiteSpace: "nowrap", lineHeight: 1 }}>{label}</span>
        </>
      )}
    </button>
  );
}
