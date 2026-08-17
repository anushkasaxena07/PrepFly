import React, { useState, useEffect } from 'react';
import Sidebar from '../../components/SuperAdmin/Sidebar';
import Navbar from '../../components/SuperAdmin/Navbar';
import Dashboard from './Dashboard';
import Organizations from './Organizations';
import CreateOrganization from './CreateOrganization';
import Admins from './Admins';
import Students from './Students';
import Subscriptions from './Subscriptions';
import Payments from './Payments';
import QuestionBank from './QuestionBank';
import AIConfiguration from './AIConfiguration';
import Analytics from './Analytics';
import ActivityLogs from './ActivityLogs';
import Notifications from './Notifications';
import FeedbackManagement from './FeedbackManagement';
import Support from './Support';
import PlatformSettings from './PlatformSettings';
import Profile from './Profile';
import { superAdminFetch } from '../../services/superAdminAPI';

export default function SuperAdminContainer() {
  const [activeTab, setActiveTabState] = useState(() => {
    return sessionStorage.getItem("superadmin_active_tab") || 'dashboard';
  });
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [superAdmin, setSuperAdmin] = useState(null);

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    sessionStorage.setItem("superadmin_active_tab", tab);
  };

  useEffect(() => {
    const token = localStorage.getItem("superadmin_access_token") || localStorage.getItem("access_token") || "superadmin_session_token";
    if (!token) {
      window.location.href = "/superadmin/login";
      return;
    }

    try {
      const u = JSON.parse(localStorage.getItem("superadmin_user") || "{}");
      setSuperAdmin(u);
    } catch (e) {
      console.error("Parse SuperAdmin session error:", e);
    }
  }, []);

  useEffect(() => {
    const checkSuperAdminSession = async () => {
      try {
        await superAdminFetch("/superadmin/dashboard-stats");
      } catch (e) {
        // Handled by superAdminFetch 401 interceptor
      }
    };
    const interval = setInterval(checkSuperAdminSession, 10000);
    return () => clearInterval(interval);
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'organizations':
        return <Organizations onNavigateCreate={() => setActiveTab('createorg')} />;
      case 'createorg':
        return <CreateOrganization onDone={() => setActiveTab('organizations')} />;
      case 'admins':
        return <Admins />;
      case 'students':
        return <Students />;
      case 'subscriptions':
        return <Subscriptions />;
      case 'payments':
        return <Payments />;
      case 'qbank':
        return <QuestionBank />;
      case 'aiconfig':
        return <AIConfiguration />;
      case 'analytics':
        return <Analytics />;
      case 'activitylogs':
        return <ActivityLogs />;
      case 'notifications':
        return <Notifications />;
      case 'feedback':
        return <FeedbackManagement />;
      case 'support':
        return <Support />;
      case 'settings':
        return <PlatformSettings />;
      case 'profile':
        return <Profile />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#050811", color: "#f0f4fd" }}>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Navbar activeTab={activeTab} setActiveTab={setActiveTab} superAdmin={superAdmin} />
        
        <main style={{ flex: 1, padding: "24px", overflowY: "auto" }}>
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
