const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

const getHeaders = (isSuperAdmin = false) => {
  const headers = {};
  if (isSuperAdmin) {
    const token = localStorage.getItem("superadmin_access_token");
    headers["X-Super-Admin"] = "true";
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } else {
    const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
    const orgId = localStorage.getItem("admin_org_id") || "d258e381-6a6e-4376-8bf2-2865731b1939";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (orgId) headers["X-Organization-Id"] = orgId;
  }
  return headers;
};

export const submitFeedback = async (data, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(isSuperAdmin)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to submit feedback");
  }
  return await res.json();
};

export const uploadFeedbackScreenshot = async (file, isSuperAdmin = false) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_URL}/api/feedback/upload`, {
    method: "POST",
    headers: getHeaders(isSuperAdmin),
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to upload screenshot");
  }
  return await res.json();
};

export const getMyFeedback = async (isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/feedback/my`, {
    headers: getHeaders(isSuperAdmin)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to fetch your feedback history");
  }
  return await res.json();
};

export const updateMyFeedback = async (id, data, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/feedback/my/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(isSuperAdmin)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to update feedback");
  }
  return await res.json();
};

export const getSuperAdminFeedback = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${BACKEND_URL}/api/admin/feedback${query ? `?${query}` : ''}`, {
    headers: getHeaders(true)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to fetch feedback records");
  }
  return await res.json();
};

export const getSuperAdminFeedbackDetail = async (id) => {
  const res = await fetch(`${BACKEND_URL}/api/admin/feedback/${id}`, {
    headers: getHeaders(true)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to fetch feedback details");
  }
  return await res.json();
};

export const updateSuperAdminFeedback = async (id, data) => {
  const res = await fetch(`${BACKEND_URL}/api/admin/feedback/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(true)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to update feedback record");
  }
  return await res.json();
};

export const deleteSuperAdminFeedback = async (id) => {
  const res = await fetch(`${BACKEND_URL}/api/admin/feedback/${id}`, {
    method: "DELETE",
    headers: getHeaders(true)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to delete feedback record");
  }
  return await res.json();
};
