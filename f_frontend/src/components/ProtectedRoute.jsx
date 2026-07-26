import { Navigate } from 'react-router-dom';

/* ─────────────────────────────────────────────────────────────────────────────
   Auth helpers
   All checks are purely client-side (localStorage) — the real security gate
   is on the backend (JWT verification on every API call). These guards prevent
   naive direct-URL access and improve UX; they are NOT a substitute for server
   auth.
───────────────────────────────────────────────────────────────────────────── */

function getStoredUser() {
  try {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function hasValidToken(key = 'access_token') {
  const token = localStorage.getItem(key) || localStorage.getItem('access_token');
  if (!token) return false;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return false; // Must be valid 3-part JWT
    const payload = JSON.parse(atob(parts[1]));
    if (payload.exp && Date.now() / 1000 > payload.exp) {
      // Token expired — clear stale keys
      localStorage.removeItem(key);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      return false;
    }
    return true;
  } catch {
    // Malformed token — reject access
    return false;
  }
}


/* ─────────────────────────────────────────────────────────────────────────────
   ProtectedRoute — any authenticated user (student / candidate)
───────────────────────────────────────────────────────────────────────────── */
export function ProtectedRoute({ children }) {
  const user  = getStoredUser();
  const valid = hasValidToken('access_token');

  if (!user || !valid) {
    return <Navigate to="/" replace />;
  }

  // Prevent students from accessing admin routes directly
  const role = user.role || '';
  if (role === 'SUPER_ADMIN') return <Navigate to="/superadmin/dashboard" replace />;
  if (role === 'ADMIN' || role === 'admin' || role === 'Organization Admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  return children;
}

/* ─────────────────────────────────────────────────────────────────────────────
   AdminRoute — organization admin only
───────────────────────────────────────────────────────────────────────────── */
export function AdminRoute({ children }) {
  const user  = getStoredUser();
  // Accept either the admin-specific token or the general access_token
  const valid = hasValidToken('admin_access_token') || hasValidToken('access_token');

  if (!user || !valid) {
    return <Navigate to="/admin/login" replace />;
  }

  // Role gate — only ADMIN / Organization Admin may access
  const role = user.role || '';
  const isAdmin = (
    role === 'ADMIN' ||
    role === 'admin' ||
    role === 'Organization Admin' ||
    user.email === 'aditya20522113@gmail.com'   // explicit admin email bypass
  );
  const isSuperAdmin = (
    role === 'SUPER_ADMIN' ||
    user.email === 'saxenaanushka9645@gmail.com'
  );

  if (isSuperAdmin) return <Navigate to="/superadmin/dashboard" replace />;
  if (!isAdmin)     return <Navigate to="/admin/login" replace />;

  return children;
}

/* ─────────────────────────────────────────────────────────────────────────────
   SuperAdminRoute — PrepFly super-admin only
───────────────────────────────────────────────────────────────────────────── */
export function SuperAdminRoute({ children }) {
  const user  = getStoredUser();
  const valid = hasValidToken('superadmin_access_token') || hasValidToken('access_token');

  if (!user || !valid) {
    return <Navigate to="/superadmin/login" replace />;
  }

  const role = user.role || '';
  const isSuperAdmin = (
    role === 'SUPER_ADMIN' ||
    user.email === 'saxenaanushka9645@gmail.com'
  );

  if (!isSuperAdmin) {
    // Demote gracefully: redirect to the right place based on their actual role
    const isAdmin = role === 'ADMIN' || role === 'admin' || role === 'Organization Admin';
    return <Navigate to={isAdmin ? '/admin/dashboard' : '/'} replace />;
  }

  return children;
}
