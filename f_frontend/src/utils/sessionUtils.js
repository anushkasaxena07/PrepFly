


// src/utils/sessionUtils.js

export const getOrCreateSessionId = () => {
  let sessionId = localStorage.getItem("session_id");

  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    localStorage.setItem("session_id", sessionId);
  }

  return sessionId;
};

export const handleSessionInvalidation = (message) => {
  const defaultMsg = "Your session has been ended because your account was logged into on another device.";
  const alertText = message || defaultMsg;

  // Clear tokens and stored profiles
  const keysToRemove = [
    "access_token", "user", "session_id",
    "admin_access_token", "admin_user", "admin_org_id", "admin_organization",
    "superadmin_access_token", "superadmin_user"
  ];
  keysToRemove.forEach(k => localStorage.removeItem(k));

  alert(`⚠️ Session Notice:\n\n${alertText}`);

  if (window.location.pathname.startsWith("/superadmin")) {
    window.location.href = "/superadmin/login";
  } else if (window.location.pathname.startsWith("/admin")) {
    window.location.href = "/admin/login";
  } else {
    window.location.href = "/";
  }
};


