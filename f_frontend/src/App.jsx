import React from 'react';
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

function App() {
  return (
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
  );
}

export default App;


