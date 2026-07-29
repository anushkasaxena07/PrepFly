const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export const superAdminFetch = async (endpoint, options = {}) => {
  const token = localStorage.getItem("superadmin_access_token") || localStorage.getItem("access_token") || "superadmin_session_token";

  const headers = {
    "Content-Type": "application/json",
    "X-User-Role": "SUPER_ADMIN",
    "X-Super-Admin": "true",
    ...(options.headers || {})
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let urlPath = endpoint.startsWith("/api") ? endpoint : `/api${endpoint}`;

  const res = await fetch(`${BACKEND_URL}${urlPath}`, {
    ...options,
    headers
  });

  if (res.status === 403) {
    throw new Error("403 Forbidden: Super Admin privileges required");
  }

  return res;
};

export const superAdminLogin = async (email, password) => {
  const res = await superAdminFetch("/superadmin/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  if (res.ok) return await res.json();
  const data = await res.json();
  throw new Error(data.error || "Super Admin Login failed");
};

export const getSuperAdminDashboardStats = async () => {
  const res = await superAdminFetch("/superadmin/dashboard");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch superadmin dashboard stats");
};

export const getSuperAdminOrganizations = async () => {
  const res = await superAdminFetch("/superadmin/organizations");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch organizations");
};

export const createSuperAdminOrganization = async (orgData) => {
  const res = await superAdminFetch("/superadmin/organization", {
    method: "POST",
    body: JSON.stringify(orgData)
  });
  if (res.ok) return await res.json();
  const data = await res.json();
  throw new Error(data.error || "Failed to create organization");
};

export const updateSuperAdminOrganization = async (id, orgData) => {
  const res = await superAdminFetch(`/superadmin/organization/${id}`, {
    method: "PUT",
    body: JSON.stringify(orgData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update organization");
};

export const deleteSuperAdminOrganization = async (id) => {
  const res = await superAdminFetch(`/superadmin/organization/${id}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete organization");
};

export const getSuperAdminAdmins = async () => {
  const res = await superAdminFetch("/superadmin/admins");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch admins");
};

export const createSuperAdminAdmin = async (adminData) => {
  const res = await superAdminFetch("/superadmin/admins", {
    method: "POST",
    body: JSON.stringify(adminData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to create admin");
};

export const updateSuperAdminAdmin = async (adminId, adminData) => {
  const res = await superAdminFetch(`/superadmin/admins/${adminId}`, {
    method: "PUT",
    body: JSON.stringify(adminData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update admin");
};

export const deleteSuperAdminAdmin = async (adminId) => {
  const res = await superAdminFetch(`/superadmin/admins/${adminId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete admin");
};

export const getSuperAdminStudents = async () => {
  const res = await superAdminFetch("/superadmin/students");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch students");
};

export const updateSuperAdminStudent = async (stdId, stdData) => {
  const res = await superAdminFetch(`/superadmin/students/${stdId}`, {
    method: "PUT",
    body: JSON.stringify(stdData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update student profile");
};

export const deleteSuperAdminStudent = async (stdId) => {
  const res = await superAdminFetch(`/superadmin/students/${stdId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete student account");
};

export const getSuperAdminPayments = async () => {
  const res = await superAdminFetch("/superadmin/payments");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch payments");
};

export const getSuperAdminAIConfig = async () => {
  const res = await superAdminFetch("/superadmin/ai-config");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch AI Config");
};

export const saveSuperAdminAIConfig = async (configData) => {
  const res = await superAdminFetch("/superadmin/ai-config", {
    method: "POST",
    body: JSON.stringify(configData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to save AI Config");
};

export const testSuperAdminAIProvider = async (testData) => {
  const res = await superAdminFetch("/superadmin/ai-config/test", {
    method: "POST",
    body: JSON.stringify(testData)
  });
  if (res.ok) return await res.json();
  const err = await res.json().catch(() => ({}));
  throw new Error(err.message || "Failed to test AI provider connection");
};

export const getSuperAdminAnalytics = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await superAdminFetch(`/superadmin/analytics${query ? `?${query}` : ''}`);
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch analytics");
};

export const getSuperAdminActivityLogs = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await superAdminFetch(`/superadmin/activity-logs${query ? `?${query}` : ''}`);
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch activity logs");
};

export const updateSuperAdminActivityLog = async (logData) => {
  const res = await superAdminFetch("/superadmin/activity-logs", {
    method: "POST",
    body: JSON.stringify(logData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update activity log");
};

export const sendSuperAdminNotification = async (notifData) => {
  const res = await superAdminFetch("/superadmin/notifications", {
    method: "POST",
    body: JSON.stringify(notifData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to send notification");
};

export const getSuperAdminSupportTickets = async () => {
  const res = await superAdminFetch("/superadmin/support");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch support tickets");
};

export const getSuperAdminSettings = async () => {
  const res = await superAdminFetch("/superadmin/settings");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch platform settings");
};

export const saveSuperAdminSettings = async (settingsData) => {
  const res = await superAdminFetch("/superadmin/settings", {
    method: "POST",
    body: JSON.stringify(settingsData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to save platform settings");
};

export const getSuperAdminQuestionBank = async () => {
  const res = await superAdminFetch("/superadmin/qbank");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch global question bank");
};

export const createSuperAdminQuestion = async (qData) => {
  const res = await superAdminFetch("/superadmin/qbank", {
    method: "POST",
    body: JSON.stringify(qData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to create global question");
};

export const updateSuperAdminQuestion = async (qId, qData) => {
  const res = await superAdminFetch(`/superadmin/qbank/${qId}`, {
    method: "PUT",
    body: JSON.stringify(qData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update global question");
};

export const deleteSuperAdminQuestion = async (qId) => {
  const res = await superAdminFetch(`/superadmin/qbank/${qId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete global question");
};

export const getSuperAdminSubscriptions = async () => {
  const res = await superAdminFetch("/superadmin/subscriptions");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch subscription plans");
};

export const saveSuperAdminSubscription = async (planData) => {
  const res = await superAdminFetch("/superadmin/subscriptions", {
    method: "POST",
    body: JSON.stringify(planData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to save subscription plan");
};

export const deleteSuperAdminSubscription = async (planId) => {
  const res = await superAdminFetch(`/superadmin/subscriptions/${planId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete subscription plan");
};

export const getSuperAdminCoupons = async () => {
  const res = await superAdminFetch("/superadmin/coupons");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch coupons");
};

export const saveSuperAdminCoupon = async (couponData) => {
  const res = await superAdminFetch("/superadmin/coupons", {
    method: "POST",
    body: JSON.stringify(couponData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to save coupon");
};

export const deleteSuperAdminCoupon = async (couponId) => {
  const res = await superAdminFetch(`/superadmin/coupons?id=${couponId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete coupon");
};
