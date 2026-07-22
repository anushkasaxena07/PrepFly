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

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/interview" element={<InterviewPage />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminDashboardContainer />} />
        <Route path="/admin/*" element={<AdminDashboardContainer />} />
        <Route path="/superadmin/login" element={<SuperAdminLogin />} />
        <Route path="/superadmin/dashboard" element={<SuperAdminContainer />} />
        <Route path="/superadmin/*" element={<SuperAdminContainer />} />
      </Routes>
    </Router>
  );
}

export default App;


