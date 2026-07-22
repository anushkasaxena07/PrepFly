const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

const getHeaders = (isSuperAdmin = false) => {
  const headers = {};
  if (isSuperAdmin) {
    const token = localStorage.getItem("superadmin_access_token");
    headers["X-Super-Admin"] = "true";
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } else {
    const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
    const orgId = localStorage.getItem("admin_org_id") || "org_stanford_01";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (orgId) headers["X-Organization-Id"] = orgId;
  }
  return headers;
};

export const getSupportConversations = async (params = {}, isSuperAdmin = false) => {
  const query = new URLSearchParams(params).toString();
  const url = `${BACKEND_URL}/api/support/conversations${query ? `?${query}` : ''}`;
  const res = await fetch(url, {
    headers: getHeaders(isSuperAdmin)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to fetch support conversations");
  }
  return await res.json();
};

export const createSupportConversation = async (data, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/support/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(isSuperAdmin)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to create support conversation");
  }
  return await res.json();
};

export const getSupportConversationDetail = async (convId, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/support/conversations/${convId}`, {
    headers: getHeaders(isSuperAdmin)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to fetch conversation detail");
  }
  return await res.json();
};

export const sendSupportMessage = async (convId, data, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/support/conversations/${convId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(isSuperAdmin)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to send support message");
  }
  return await res.json();
};

export const updateSupportConversationStatus = async (convId, data, isSuperAdmin = false) => {
  const res = await fetch(`${BACKEND_URL}/api/support/conversations/${convId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(isSuperAdmin)
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to update conversation status");
  }
  return await res.json();
};

export const uploadSupportAttachment = async (file, isSuperAdmin = false) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_URL}/api/support/upload`, {
    method: "POST",
    headers: getHeaders(isSuperAdmin),
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to upload attachment");
  }
  return await res.json();
};

export const updateTypingStatus = async (convId, isTyping, isSuperAdmin = false) => {
  try {
    await fetch(`${BACKEND_URL}/api/support/conversations/${convId}/typing`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getHeaders(isSuperAdmin)
      },
      body: JSON.stringify({ is_typing: isTyping })
    });
  } catch (e) {
    // Non-blocking
  }
};

export const getTypingStatus = async (convId, isSuperAdmin = false) => {
  try {
    const res = await fetch(`${BACKEND_URL}/api/support/conversations/${convId}/typing`, {
      headers: getHeaders(isSuperAdmin)
    });
    if (res.ok) return await res.json();
  } catch (e) {
    // Non-blocking
  }
  return { is_typing: false };
};

export const getSupportUnreadCount = async (isSuperAdmin = false) => {
  try {
    const res = await fetch(`${BACKEND_URL}/api/support/unread-count`, {
      headers: getHeaders(isSuperAdmin)
    });
    if (res.ok) {
      const data = await res.json();
      return data.unread_count || 0;
    }
  } catch (e) {
    // Non-blocking
  }
  return 0;
};
