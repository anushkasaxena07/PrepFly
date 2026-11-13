/**
 * Canonical Backend URL resolver across all PrepFly frontend API clients and components.
 * Uses explicit VITE_BACKEND_URL when configured, localhost:5000 in local browser sessions,
 * and https://prepfly-1.onrender.com as the production fallback.
 */
export function resolveBackendUrl() {
  const configured = (import.meta?.env?.VITE_BACKEND_URL || "").trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:5000";
    }
  }
  return "https://prepfly-1.onrender.com";
}

export const BACKEND_URL = resolveBackendUrl();
