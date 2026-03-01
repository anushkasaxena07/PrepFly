


// src/utils/sessionUtils.js

export const getOrCreateSessionId = () => {
  let sessionId = localStorage.getItem("session_id");

  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    localStorage.setItem("session_id", sessionId);
  }

  return sessionId;
};

