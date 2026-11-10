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
    <div style={{ display: "flex", minHeight: "100vh", background: "#f6f7fb", color: "#0f172a" }}>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />

      <div className="pf-portal-main" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: "#f6f7fb" }}>
        <Navbar activeTab={activeTab} setActiveTab={setActiveTab} superAdmin={superAdmin} />
        
        <main className="pf-body-surface" style={{ flex: 1, padding: "24px 28px 48px", overflowY: "auto", marginTop: "-14px" }}>
          <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  );
}
