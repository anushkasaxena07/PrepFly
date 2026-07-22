const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export const fetchSubscriptionStatus = async (apiFetch, orgId) => {
  try {
    const id = orgId || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";
    const res = await apiFetch(`/subscription/status?org_id=${id}`);
    if (res && res.ok) return await res.json();
  } catch (e) {
    console.error("fetchSubscriptionStatus error:", e);
  }
  return {
    organization_id: orgId || "org_default",
    subscription_status: "TRIAL",
    current_plan: "Trial",
    days_remaining: 10,
    trial_start: new Date().toISOString(),
    trial_end: new Date(Date.now() + 10 * 86400000).toISOString(),
    subscription_start: null,
    subscription_expiry: null,
    is_blocked: false,
    reminders: []
  };
};

export const fetchPaymentHistory = async (apiFetch, orgId) => {
  try {
    const id = orgId || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";
    const res = await apiFetch(`/payment/history?org_id=${id}`);
    if (res && res.ok) return await res.json();
  } catch (e) {
    console.error("fetchPaymentHistory error:", e);
  }
  return [];
};

export const createPaymentOrder = async (apiFetch, { amount = 500, orgId }) => {
  const id = orgId || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";
  const res = await apiFetch('/payment/create-order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount, organization_id: id })
  });
  if (res && res.ok) return await res.json();
  throw new Error("Failed to create Razorpay payment order");
};

export const verifyPayment = async (apiFetch, paymentData) => {
  const res = await apiFetch('/payment/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(paymentData)
  });
  if (res && res.ok) return await res.json();
  const data = res ? await res.json() : {};
  throw new Error(data.error || "Failed to verify Razorpay payment");
};

export const recordFailedPayment = async (apiFetch, failedData) => {
  try {
    const res = await apiFetch('/payment/record-failed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(failedData)
    });
    if (res && res.ok) return await res.json();
  } catch (e) {
    console.error("recordFailedPayment error:", e);
  }
};
