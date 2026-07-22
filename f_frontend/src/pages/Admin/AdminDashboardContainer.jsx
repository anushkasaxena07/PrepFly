import React, { useState, useEffect } from 'react';
import Sidebar from '../../components/Admin/Sidebar';
import Navbar from '../../components/Admin/Navbar';
import Dashboard from './Dashboard';
import Students from './Students';
import AddStudent from './AddStudent';
import AIInterview from './AIInterview';
import Coding from './Coding';
import QuestionBank from './QuestionBank';
import Reports from './Reports';
import Analytics from './Analytics';
import Announcements from './Announcements';
import Organization from './Organization';
import Subscription from './Subscription';
import Settings from './Settings';
import SupportChat from '../../components/Support/SupportChat';
import { fetchSubscriptionStatus } from '../../components/subscription/subscriptionAPI';
import { adminFetch } from '../../services/adminAPI';

export default function AdminDashboardContainer() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [admin, setAdmin] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    // Authenticate admin token presence
    const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/admin/login";
      return;
    }

    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "Light" || savedTheme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
      document.body.classList.add("light-mode");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      document.body.classList.remove("light-mode");
    }

    try {
      const storedAdmin = localStorage.getItem("admin_user");
      const u = storedAdmin ? JSON.parse(storedAdmin) : (JSON.parse(localStorage.getItem("user") || "{}"));
      const o = JSON.parse(localStorage.getItem("admin_organization") || "{}");
      
      const adminObj = {
        name: u.name || "Aditya",
        email: u.email || "aditya20522113@gmail.com",
        role: u.role || "Organization Admin"
      };

      setAdmin(adminObj);
      setOrganization(o);

      const orgId = o?.id || u?.organization_id || localStorage.getItem("admin_org_id") || "org_default";
      
      // Check Subscription & Trial Expiry from backend
      fetchSubscriptionStatus(adminFetch, orgId).then((subData) => {
        if (subData && (subData.is_blocked || subData.subscription_status === 'EXPIRED')) {
          setIsExpired(true);
          setActiveTab('subscription');
        } else {
          setIsExpired(false);
        }
      });
    } catch (e) {
      console.error("Parse admin stored session error:", e);
    }
  }, []);

  const handleTabChange = (tabId) => {
    if (isExpired && tabId !== 'subscription') {
      setActiveTab('subscription');
      return;
    }
    setActiveTab(tabId);
  };

  const renderTabContent = () => {
    if (isExpired && activeTab !== 'subscription') {
      return <Subscription />;
    }

    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'students':
        return <Students />;
      case 'add-student':
        return <AddStudent />;
      case 'interviews':
        return <AIInterview />;
      case 'coding':
        return <Coding />;
      case 'qbank':
        return <QuestionBank />;
      case 'reports':
        return <Reports />;
      case 'analytics':
        return <Analytics />;
      case 'announcements':
        return <Announcements />;
      case 'support':
        return <SupportChat role="Organization Admin" />;
      case 'organization':
        return <Organization />;
      case 'subscription':
        return <Subscription />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#070b14", color: "#f0f4fd" }}>
      
      {/* SIDEBAR */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={handleTabChange} 
        isCollapsed={isCollapsed} 
        setIsCollapsed={setIsCollapsed} 
        organization={organization}
        isExpired={isExpired}
      />

      {/* MAIN CONTAINER */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        
        {/* NAVBAR */}
        <Navbar activeTab={activeTab} admin={admin} organization={organization} />

        {/* PAGE CONTENT */}
        <main style={{ flex: 1, padding: "24px", overflowY: "auto" }}>
          {renderTabContent()}
        </main>
      </div>

    </div>
  );
}
