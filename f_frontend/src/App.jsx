import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Login from './Login';
import Dashboard from './Dashboard';
import InterviewPage from './InterviewPage';
import Profile from './profile';
import AdminLogin from './pages/Admin/AdminLogin';
import AdminDashboardContainer from './pages/Admin/AdminDashboardContainer';
import SuperAdminLogin from './pages/SuperAdmin/SuperAdminLogin';
import SuperAdminContainer from './pages/SuperAdmin/SuperAdminContainer';
import { ProtectedRoute, AdminRoute, SuperAdminRoute } from './components/ProtectedRoute';
import { ThemeProvider } from './components/ui/ThemeContext';

function App() {
  // Non-blocking Render cold-start wake-up call on app load
  useEffect(() => {
    const apiBase = import.meta.env.VITE_BACKEND_URL || (
      (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
        ? "http://localhost:5000"
        : "https://prepfly.up.railway.app"
    );
    fetch(`${apiBase}/health`, { method: "GET" }).catch(() => {});
  }, []);

  return (
    <ThemeProvider>
      <Router>
        <Routes>
          {/* ── Public ── */}
          <Route path="/" element={<Login />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/superadmin/login" element={<SuperAdminLogin />} />

          {/* ── Regular user (must be logged in) ── */}
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/interview" element={<ProtectedRoute><InterviewPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />

          {/* ── Admin ── */}
          <Route path="/admin/dashboard" element={<AdminRoute><AdminDashboardContainer /></AdminRoute>} />
          <Route path="/admin/*" element={<AdminRoute><AdminDashboardContainer /></AdminRoute>} />

          {/* ── Super Admin ── */}
          <Route path="/superadmin/dashboard" element={<SuperAdminRoute><SuperAdminContainer /></SuperAdminRoute>} />
          <Route path="/superadmin/*" element={<SuperAdminRoute><SuperAdminContainer /></SuperAdminRoute>} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;


