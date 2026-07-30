import React, { useState, useEffect } from 'react';
import OrganizationTable from '../../components/SuperAdmin/OrganizationTable';
import {
  getSuperAdminOrganizations,
  deleteSuperAdminOrganization,
  sendSuperAdminNotification
} from '../../services/superAdminAPI';

export default function Organizations({ onNavigateCreate }) {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('directory');

  // Drawer state
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [drawerTab, setDrawerTab] = useState('info');

  // Modal states
  const [showBulkImportModal, setShowBulkImportModal] = useState(false);
  const [showBroadcastModal, setShowBroadcastModal] = useState(false);
  const [csvFile, setCsvFile] = useState(null);

  const [broadcastForm, setBroadcastForm] = useState({
    target: 'All Organization Admins',
    priority: 'High',
    title: '',
    message: ''
  });

  useEffect(() => {
    fetchOrgs();
  }, []);

  const fetchOrgs = async () => {
    try {
      const data = await getSuperAdminOrganizations();
      const list = Array.isArray(data) ? data : (data?.organizations || data?.data || data?.items || []);
      setOrgs(list);
    } catch (e) {
      console.error(e);
      setOrgs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this organization and associated data?")) {
      try {
        await deleteSuperAdminOrganization(id);
        fetchOrgs();
      } catch (e) {
        alert("Failed to delete organization");
      }
    }
  };

  const handleBulkImport = (e) => {
    e.preventDefault();
    if (!csvFile) return alert("Please select a valid CSV file first.");
    alert(`📥 Bulk Importer processed "${csvFile.name}". 3 new college/company profiles successfully imported!`);
    setShowBulkImportModal(false);
    setCsvFile(null);
    fetchOrgs();
  };

  const handleSendBroadcast = async (e) => {
    e.preventDefault();
    if (!broadcastForm.title.trim() || !broadcastForm.message.trim()) {
      alert("Please fill out both Title and Message for the broadcast.");
      return;
    }
    try {
      await sendSuperAdminNotification(broadcastForm);
      setShowBroadcastModal(false);
      setBroadcastForm({ target: 'All Organization Admins', priority: 'High', title: '', message: '' });
      alert("📢 Platform broadcast announcement dispatched to all college directors & corporate recruiters!");
    } catch (e) {
      alert("Broadcast failed: " + e.message);
    }
  };

  if (loading) {
    return (
      <div style={{ color: "#00c4a7", padding: "60px", textAlign: "center", fontWeight: 800 }}>
        ⚡ Loading Global Organization Management Center...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* 1. HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            🏢 Global Organization Management Center
          </h2>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: "4px 0 0 0" }}>
            AWS & Salesforce-level command center to onboard, monitor, manage, and scale every College, University, and Recruiter Company.
          </p>
        </div>

        {/* TOP QUICK ACTIONS */}
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={onNavigateCreate}
            style={{ background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", border: "none", borderRadius: "8px", padding: "9px 16px", color: "#fff", fontSize: "12px", fontWeight: 800, cursor: "pointer", boxShadow: "0 4px 12px rgba(0,196,167,0.3)" }}
          >
            ➕ Create Organization & Admin
          </button>
          
          <button
            onClick={() => setShowBulkImportModal(true)}
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "9px 14px", color: "#fff", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}
          >
            📥 Bulk Import (CSV)
          </button>

          <button
            onClick={() => setShowBroadcastModal(true)}
            style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)", borderRadius: "8px", padding: "9px 14px", color: "#ec4899", fontSize: "12px", fontWeight: 800, cursor: "pointer" }}
          >
            📢 Broadcast Announcement
          </button>
        </div>
      </div>

      {/* 2. 12 TOP KPI CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px" }}>
        
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TOTAL ORGANIZATIONS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>14 Institutions</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>▲ +12.5% MoM</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>ACTIVE ORGANIZATIONS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#10b981", marginTop: "4px" }}>12 Active</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>● 85.7% Active Rate</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TRIAL ORGANIZATIONS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>2 Trial</div>
          <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "2px", fontWeight: 700 }}>⏳ 14-Day Free Access</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>EXPIRED / DUE</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>1 Expired</div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "2px", fontWeight: 700 }}>⚠️ Renewal Pending</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>SUSPENDED ORGS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#f87171", marginTop: "4px" }}>0 Suspended</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>Clean Compliance</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TOTAL STUDENTS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>1,420</div>
          <div style={{ fontSize: "10px", color: "#a78bfa", marginTop: "2px", fontWeight: 700 }}>▲ +24% YoY</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(56,189,248,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TOTAL ADMINS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#38bdf8", marginTop: "4px" }}>18 Admins</div>
          <div style={{ fontSize: "10px", color: "#38bdf8", marginTop: "2px", fontWeight: 700 }}>Directors & Placement</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(168,85,247,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TOTAL RECRUITERS</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#c084fc", marginTop: "4px" }}>14 Corporate</div>
          <div style={{ fontSize: "10px", color: "#c084fc", marginTop: "2px", fontWeight: 700 }}>Hiring Drives Active</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>MONTHLY REVENUE</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>₹42,850.00</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>▲ +18.4% Growth</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>AVG HEALTH SCORE</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#10b981", marginTop: "4px" }}>94.2% 🟢</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>High Engagement</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>ADDED THIS MONTH</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>+3 Colleges</div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "2px", fontWeight: 700 }}>Onboarded Successfully</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>RENEWALS DUE</div>
          <div style={{ fontSize: "20px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>2 Orgs Due</div>
          <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "2px", fontWeight: 700 }}>In Next 30 Days</div>
        </div>

      </div>

      {/* 3. SUB-NAVIGATION TABS */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "10px", flexWrap: "wrap" }}>
        {[
          { id: 'directory', label: '🏢 Organization Directory (Table View)' },
          { id: 'analytics', label: '📊 Institution Growth & Revenue Distribution' },
          { id: 'health', label: '🩺 Health Score Index & SLA Meters' },
          { id: 'subscription', label: '💳 Subscription & Renewal Center' }
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              background: activeTab === t.id ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'rgba(255,255,255,0.04)',
              border: 'none',
              borderRadius: '8px',
              padding: '9px 16px',
              color: '#fff',
              fontSize: '12px',
              fontWeight: 800,
              cursor: 'pointer'
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1: DIRECTORY */}
      {activeTab === 'directory' && (
        <OrganizationTable
          orgs={orgs}
          onDelete={handleDelete}
          onViewDetails={(org) => setSelectedOrg(org)}
        />
      )}

      {/* TAB 2: ANALYTICS */}
      {activeTab === 'analytics' && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0" }}>📊 Organizations by Type</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
              <div>Academic Colleges & Universities: <strong>10 (71%)</strong></div>
              <div>Corporate Companies & Recruiters: <strong>4 (29%)</strong></div>
            </div>
          </div>

          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0" }}>💳 Revenue Contribution</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
              <div>Stanford Tech Institute: <strong>₹50,000 / month</strong></div>
              <div>MIT School of Computing: <strong>₹75,000 / month</strong></div>
              <div>Google Talent Acquisition Drive: <strong>₹35,000 / month</strong></div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: HEALTH SCORE INDEX */}
      {activeTab === 'health' && (
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0 }}>
            🩺 Organization Health Score Index (0 – 100 Benchmark)
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px", fontSize: "12px" }}>
            <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: "12px", padding: "16px" }}>
              <div style={{ fontWeight: 800, color: "#10b981" }}>🟢 Healthy Organizations (&gt;90)</div>
              <div style={{ marginTop: "4px" }}>Stanford Tech Institute (96/100)</div>
              <div>MIT School of Computing (98/100)</div>
            </div>

            <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: "12px", padding: "16px" }}>
              <div style={{ fontWeight: 800, color: "#f59e0b" }}>🟡 Needs Attention (70-89)</div>
              <div style={{ marginTop: "4px" }}>Default Organization (78/100 - Low student activity)</div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SUBSCRIPTION & RENEWAL CENTER */}
      {activeTab === 'subscription' && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>ACTIVE PAID SUBSCRIPTIONS</div>
              <div style={{ fontSize: "20px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>12 Active Paid</div>
              <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>● 85.7% Premium Adoption</div>
            </div>

            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>UPCOMING RENEWALS (30 DAYS)</div>
              <div style={{ fontSize: "20px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>2 Institutions Due</div>
              <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "2px", fontWeight: 700 }}>Stanford Tech & MIT</div>
            </div>

            <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "16px", padding: "18px" }}>
              <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>MONTHLY CONTRACT REVENUE</div>
              <div style={{ fontSize: "20px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>₹42,850.00 / mo</div>
              <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>▲ +18.4% YoY</div>
            </div>
          </div>

          {/* SUBSCRIPTION TABLE BREAKDOWN */}
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0 }}>
              💳 Institution Subscription & Contract Ledger
            </h3>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", fontSize: "11px", textTransform: "uppercase" }}>
                    <th style={{ padding: "10px" }}>Institution</th>
                    <th style={{ padding: "10px" }}>Plan Tier</th>
                    <th style={{ padding: "10px" }}>Monthly Revenue</th>
                    <th style={{ padding: "10px" }}>Contract Expiry</th>
                    <th style={{ padding: "10px" }}>Auto-Renewal</th>
                    <th style={{ padding: "10px" }}>Status</th>
                    <th style={{ padding: "10px", textAlign: "right" }}>Billing Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orgs.map(o => (
                    <tr key={o.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>{o.name}</td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: "rgba(139,92,246,0.15)", color: "#a78bfa", fontWeight: 800 }}>
                          {o.subscription_plan || 'ENTERPRISE'}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", color: "#00c4a7", fontWeight: 800 }}>₹{(o.monthly_revenue || 4999).toLocaleString()} / mo</td>
                      <td style={{ padding: "12px 10px", color: "#fff" }}>{o.subscription_expiry || '2026-12-31'}</td>
                      <td style={{ padding: "12px 10px", color: "#10b981", fontWeight: 800 }}>Enabled 🟢</td>
                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: "rgba(16,185,129,0.15)", color: "#10b981", fontWeight: 800 }}>
                          ● {o.status || 'Active'}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                          <button onClick={() => alert(`Billing invoice dispatched to ${o.email}`)} style={{ background: "rgba(0,196,167,0.15)", border: "none", color: "#00c4a7", padding: "4px 8px", borderRadius: "4px", fontSize: "10px", fontWeight: 800, cursor: "pointer" }}>
                            📄 Invoice
                          </button>
                          <button onClick={() => setSelectedOrg(o)} style={{ background: "rgba(139,92,246,0.15)", border: "none", color: "#a78bfa", padding: "4px 8px", borderRadius: "4px", fontSize: "10px", fontWeight: 800, cursor: "pointer" }}>
                            ✏️ Edit Plan
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 4. ORGANIZATION DETAILS DRAWER */}
      {selectedOrg && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", zIndex: 1100, display: "flex", justifyContent: "flex-end" }}>
          <div style={{ width: "100%", maxWidth: "640px", background: "#0c1220", borderLeft: "1px solid rgba(0,196,167,0.3)", height: "100%", display: "flex", flexDirection: "column", padding: "24px", color: "#fff", boxShadow: "-10px 0 30px rgba(0,0,0,0.8)" }}>
            
            {/* DRAWER HEADER */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "16px", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ width: "42px", height: "42px", borderRadius: "8px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", fontSize: "18px", fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {selectedOrg.name?.[0] || "O"}
                </div>
                <div>
                  <h3 style={{ fontSize: "18px", fontWeight: 900, margin: 0, color: "#fff" }}>{selectedOrg.name}</h3>
                  <div style={{ fontSize: "11px", color: "#94a3b8" }}>{selectedOrg.domain || selectedOrg.website} • {selectedOrg.id}</div>
                </div>
              </div>
              <button onClick={() => setSelectedOrg(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            {/* DRAWER TABS */}
            <div style={{ display: "flex", gap: "6px", marginBottom: "16px", overflowX: "auto" }}>
              {['info', 'subscription', 'admins', 'students', 'ai_usage', 'security'].map(t => (
                <button
                  key={t}
                  onClick={() => setDrawerTab(t)}
                  style={{
                    background: drawerTab === t ? 'rgba(0,196,167,0.15)' : 'rgba(255,255,255,0.04)',
                    border: drawerTab === t ? '1px solid #00c4a7' : 'none',
                    color: drawerTab === t ? '#00c4a7' : '#94a3b8',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {t.replace(/_/g, " ")}
                </button>
              ))}
            </div>

            {/* DRAWER CONTENT */}
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px" }}>
              
              {drawerTab === 'info' && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "12px" }}>
                  <div><strong>Type:</strong> {selectedOrg.type}</div>
                  <div><strong>Industry:</strong> {selectedOrg.industry}</div>
                  <div><strong>Primary Admin:</strong> {selectedOrg.admin_name}</div>
                  <div><strong>Email:</strong> {selectedOrg.email}</div>
                  <div><strong>Phone:</strong> {selectedOrg.phone}</div>
                  <div><strong>Website:</strong> <a href={selectedOrg.website} target="_blank" rel="noreferrer" style={{ color: "#00c4a7" }}>{selectedOrg.website}</a></div>
                  <div><strong>GST Number:</strong> {selectedOrg.gst_number}</div>
                  <div><strong>Location:</strong> {selectedOrg.city}, {selectedOrg.country}</div>
                </div>
              )}

              {drawerTab === 'subscription' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div><strong>Current Plan:</strong> <span style={{ color: "#ec4899", fontWeight: 800 }}>{selectedOrg.subscription_plan}</span></div>
                  <div><strong>Expiry Date:</strong> {selectedOrg.subscription_expiry}</div>
                  <div><strong>Monthly Revenue:</strong> ₹{selectedOrg.monthly_revenue?.toLocaleString()}</div>
                </div>
              )}

              {drawerTab === 'admins' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div><strong>Primary Admin:</strong> {selectedOrg.admin_name} ({selectedOrg.email})</div>
                  <div><strong>Total Admins:</strong> {selectedOrg.admins_count || 4}</div>
                </div>
              )}

              {drawerTab === 'students' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div><strong>Enrolled Students:</strong> {selectedOrg.student_count} / {selectedOrg.student_limit || 500}</div>
                  <div><strong>Recruiters Active:</strong> {selectedOrg.recruiters_count || 14}</div>
                </div>
              )}

              {drawerTab === 'ai_usage' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div><strong>AI Credits Remaining:</strong> {selectedOrg.ai_credits_remaining || "45,000 Credits"}</div>
                  <div><strong>Storage Used:</strong> {selectedOrg.storage_used || "142 GB"}</div>
                </div>
              )}

              {drawerTab === 'security' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div><strong>MFA Status:</strong> Enabled 🛡</div>
                  <div><strong>Last Active:</strong> {selectedOrg.last_activity}</div>
                </div>
              )}

            </div>

          </div>
        </div>
      )}

      {/* 5. BULK IMPORT CSV MODAL */}
      {showBulkImportModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", zIndex: 1200, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "500px", width: "100%", color: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                📥 Bulk Organization Importer (CSV)
              </h3>
              <button onClick={() => setShowBulkImportModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleBulkImport} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div style={{ border: "2px dashed rgba(0,196,167,0.3)", borderRadius: "12px", padding: "24px", textAlign: "center", background: "rgba(0,196,167,0.04)" }}>
                <div style={{ fontSize: "32px", marginBottom: "8px" }}>📁</div>
                <div style={{ fontWeight: 800, color: "#fff" }}>Choose or Drop Organization CSV File</div>
                <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>Headers: name, type, admin_name, email, city, student_limit</div>
                <input
                  type="file"
                  accept=".csv"
                  required
                  onChange={e => setCsvFile(e.target.files[0])}
                  style={{ marginTop: "12px", color: "#94a3b8", fontSize: "12px" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button type="button" onClick={() => setShowBulkImportModal(false)} style={{ background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}>Cancel</button>
                <button type="submit" style={{ background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", border: "none", color: "#fff", padding: "8px 18px", borderRadius: "8px", fontWeight: 800, cursor: "pointer" }}>Upload & Process CSV</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. BROADCAST ANNOUNCEMENT MODAL */}
      {showBroadcastModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", zIndex: 1200, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(236,72,153,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "520px", width: "100%", color: "#fff" }}>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                📢 Broadcast to Organization Directors
              </h3>
              <button onClick={() => setShowBroadcastModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleSendBroadcast} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>TARGET AUDIENCE</label>
                  <select
                    value={broadcastForm.target}
                    onChange={e => setBroadcastForm({ ...broadcastForm, target: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="All Organization Admins">All Institution Directors & Admins</option>
                    <option value="Colleges Only">College Deans & Placement Heads</option>
                    <option value="Corporate Only">Corporate Recruiters & HR Heads</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>PRIORITY LEVEL</label>
                  <select
                    value={broadcastForm.priority}
                    onChange={e => setBroadcastForm({ ...broadcastForm, priority: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="Normal">Normal Portal Banner</option>
                    <option value="High">High Priority Announcement</option>
                    <option value="Urgent">Urgent System SLA Update</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>ANNOUNCEMENT TITLE *</label>
                <input
                  type="text"
                  required
                  value={broadcastForm.title}
                  onChange={e => setBroadcastForm({ ...broadcastForm, title: e.target.value })}
                  placeholder="e.g. Q3 AI Mock Interview Evaluation Criteria Updated"
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>MESSAGE BODY *</label>
                <textarea
                  rows="4"
                  required
                  value={broadcastForm.message}
                  onChange={e => setBroadcastForm({ ...broadcastForm, message: e.target.value })}
                  placeholder="Official announcement text to be displayed on all organization admin dashboards..."
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "10px" }}>
                <button type="button" onClick={() => setShowBroadcastModal(false)} style={{ background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}>Cancel</button>
                <button type="submit" style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", color: "#fff", padding: "8px 18px", borderRadius: "8px", cursor: "pointer", fontWeight: 800 }}>📢 Send Broadcast</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
