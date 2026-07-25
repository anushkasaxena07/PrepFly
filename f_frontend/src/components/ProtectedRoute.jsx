import { Navigate } from 'react-router-dom';

/**
 * ProtectedRoute – requires a valid user session (any logged-in user).
 * Redirects to "/" (login) if no access_token or user is found in localStorage.
 */
export function ProtectedRoute({ children }) {
  const user  = localStorage.getItem("user");
  const token = localStorage.getItem("access_token");
  if (!user || !token) {
    return <Navigate to="/" replace />;
  }
  return children;
}

/**
 * AdminRoute – requires a valid admin access token.
 * Redirects to "/admin/login" if not present.
 */
export function AdminRoute({ children }) {
  const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }
  return children;
}

/**
 * SuperAdminRoute – requires a valid superadmin access token.
 * Redirects to "/superadmin/login" if not present.
 */
export function SuperAdminRoute({ children }) {
  const token = localStorage.getItem("superadmin_access_token");
  if (!token) {
    return <Navigate to="/superadmin/login" replace />;
  }
  return children;
}
