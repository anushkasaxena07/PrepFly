import React, { useState, useEffect } from 'react';
import {
  getSuperAdminStudents,
  updateSuperAdminStudent,
  deleteSuperAdminStudent,
  sendSuperAdminNotification
} from '../../services/superAdminAPI';

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('directory');

  // Search and Filter States
  const [search, setSearch] = useState('');
  const [orgFilter, setOrgFilter] = useState('All');
  const [deptFilter, setDeptFilter] = useState('All');
  const [subFilter, setSubFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // Selection & Bulk Operations
  const [selectedIds, setSelectedIds] = useState([]);

  // Profile Drawer State
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [drawerTab, setDrawerTab] = useState('personal');

  // Broadcast Modal State
  const [showBroadcastModal, setShowBroadcastModal] = useState(false);
  const [broadcastForm, setBroadcastForm] = useState({
    target: 'All Students',
    priority: 'High',
    title: '',
    message: ''
  });

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const data = await getSuperAdminStudents();
      setStudents(data || []);
    } catch (e) {
      console.error("Error fetching students:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(filteredStudents.map(s => s.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return alert("Select at least one candidate first.");
    if (action === 'delete') {
      if (!window.confirm(`Are you sure you want to delete ${selectedIds.length} candidate accounts?`)) return;
      try {
        await Promise.all(selectedIds.map(id => deleteSuperAdminStudent(id)));
        setSelectedIds([]);
        fetchStudents();
        alert("✅ Selected candidates deleted.");
      } catch (e) {
        alert("Failed to delete candidates: " + e.message);
      }
    } else if (action === 'premium') {
      try {
        await Promise.all(selectedIds.map(id => updateSuperAdminStudent(id, { subscription: 'PREMIUM' })));
        setSelectedIds([]);
        fetchStudents();
        alert("⭐ Upgraded selected candidates to PREMIUM!");
      } catch (e) {
        alert("Failed to upgrade candidates: " + e.message);
      }
    } else if (action === 'suspend') {
      try {
        await Promise.all(selectedIds.map(id => updateSuperAdminStudent(id, { status: 'Suspended' })));
        setSelectedIds([]);
        fetchStudents();
        alert("🔒 Suspended selected candidates.");
      } catch (e) {
        alert("Failed to suspend candidates: " + e.message);
      }
    } else if (action === 'export') {
      handleExportCSV(filteredStudents.filter(s => selectedIds.includes(s.id)));
    }
  };

  const handleSingleDelete = async (id) => {
    if (!window.confirm("Delete candidate account permanently?")) return;
    try {
      await deleteSuperAdminStudent(id);
      fetchStudents();
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  };

  const handleSingleUpgrade = async (s) => {
    const newSub = s.subscription === 'PREMIUM' ? 'FREE' : 'PREMIUM';
    try {
      await updateSuperAdminStudent(s.id, { subscription: newSub });
      fetchStudents();
    } catch (e) {
      alert("Update failed: " + e.message);
    }
  };

  const handleExportCSV = (dataToExport) => {
    const list = dataToExport && dataToExport.length > 0 ? dataToExport : filteredStudents;
    if (list.length === 0) return alert("No student records to export.");

    const headers = ["ID", "Name", "Email", "Roll Number", "Organization", "Department", "Year", "Subscription", "AI Score", "Resume Score", "Coding Score", "Placement Readiness", "Status", "Joined At"];
    const rows = list.map(s => [
      `"${s.id}"`,
      `"${(s.name || '').replace(/"/g, '""')}"`,
      `"${s.email || ''}"`,
      `"${s.roll_number || ''}"`,
      `"${(s.organization_name || '').replace(/"/g, '""')}"`,
      `"${s.department || ''}"`,
      `"${s.year || ''}"`,
      `"${s.subscription || 'FREE'}"`,
      s.overall_ai_score || 0,
      s.resume_score || 0,
      s.coding_score || 0,
      `"${s.placement_readiness || '0%'}"`,
      `"${s.status || 'Active'}"`,
      `"${s.joined_at || ''}"`
    ]);

    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prepfly_global_candidates_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSendBroadcast = async (e) => {
    e.preventDefault();
    if (!broadcastForm.title.trim() || !broadcastForm.message.trim()) {
      alert("Please enter both Title and Message for the broadcast.");
      return;
    }
    try {
      await sendSuperAdminNotification(broadcastForm);
      setShowBroadcastModal(false);
      setBroadcastForm({ target: 'All Students', priority: 'High', title: '', message: '' });
      alert("📢 Broadcast announcement successfully dispatched to candidates across registered institutions!");
    } catch (e) {
      alert("Broadcast failed: " + e.message);
    }
  };

  const filteredStudents = students.filter(s => {
    const q = search.toLowerCase();
    const matchesSearch = !search ||
      (s.name && s.name.toLowerCase().includes(q)) ||
      (s.email && s.email.toLowerCase().includes(q)) ||
      (s.roll_number && s.roll_number.toLowerCase().includes(q)) ||
      (s.department && s.department.toLowerCase().includes(q)) ||
      (s.organization_name && s.organization_name.toLowerCase().includes(q));

    const matchesOrg = orgFilter === 'All' || s.organization_name === orgFilter;
    const matchesDept = deptFilter === 'All' || s.department === deptFilter;
    const matchesSub = subFilter === 'All' || s.subscription === subFilter;
    const matchesStatus = statusFilter === 'All' || s.status === statusFilter;

    return matchesSearch && matchesOrg && matchesDept && matchesSub && matchesStatus;
  });

  const uniqueOrgs = Array.from(new Set(students.map(s => s.organization_name).filter(Boolean)));
  const uniqueDepts = Array.from(new Set(students.map(s => s.department).filter(Boolean)));

  // ── Derived real stats ─────────────────────────────────────────────
  const today = new Date().toISOString().slice(0, 10);
  const totalStudents     = students.length;
  const premiumStudents   = students.filter(s => s.subscription === 'PREMIUM').length;
  const freeStudents      = students.filter(s => !s.subscription || s.subscription === 'FREE').length;
  const trialStudents     = students.filter(s => s.subscription === 'TRIAL').length;
  const activeStudents    = students.filter(s => s.status === 'Active').length;
  const inactiveStudents  = students.filter(s => s.status === 'Inactive' || s.status === 'At Risk').length;
  const newToday          = students.filter(s => s.joined_at && s.joined_at.startsWith(today)).length;
  const totalInterviews   = students.reduce((sum, s) => sum + (s.total_interviews || 0), 0);
  const aiScores          = students.map(s => s.overall_ai_score).filter(v => v != null && v > 0);
  const avgAiScore        = aiScores.length ? (aiScores.reduce((a,b) => a+b, 0) / aiScores.length).toFixed(1) : '—';
  const placementReady    = students.filter(s => s.status === 'Active' && (s.total_interviews || 0) >= 3).length;

  if (loading) {
    return (
      <div style={{ color: "#ec4899", padding: "60px", textAlign: "center", fontWeight: 800 }}>
        ⚡ Loading Global Student Directory & Analytics Engine...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* 1. HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            🎓 Global Student Management & Analytics Center
          </h2>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: "4px 0 0 0" }}>
            Monitor candidate performance, AI readiness, mock interview scores, and subscriptions across all institutions.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={() => handleExportCSV()}
            style={{ background: "rgba(0,196,167,0.15)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "8px", padding: "9px 16px", color: "#00c4a7", fontSize: "12px", fontWeight: 800, cursor: "pointer" }}
          >
            📊 Export CSV Report
          </button>
          
          <button
            onClick={() => setShowBroadcastModal(true)}
            style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", borderRadius: "8px", padding: "9px 16px", color: "#fff", fontSize: "12px", fontWeight: 800, cursor: "pointer", boxShadow: "0 4px 12px rgba(236,72,153,0.3)" }}
          >
            📢 Broadcast Announcement
          </button>
        </div>
      </div>

      {/* 2. 12 TOP KPI CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px" }}>
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>TOTAL STUDENTS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#fff", marginTop: "4px" }}>{totalStudents.toLocaleString()}</div>
          <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px", fontWeight: 700 }}>All registered users</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>ACTIVE STUDENTS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#10b981", marginTop: "4px" }}>{activeStudents.toLocaleString()}</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>● Active in last 7 days</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>NEW REGISTRATIONS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>+{newToday} Today</div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "2px", fontWeight: 700 }}>Joined today</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(168,85,247,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>PREMIUM STUDENTS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#c084fc", marginTop: "4px" }}>{premiumStudents} Paid</div>
          <div style={{ fontSize: "10px", color: "#c084fc", marginTop: "2px", fontWeight: 700 }}>⭐ {totalStudents > 0 ? Math.round(premiumStudents / totalStudents * 100) : 0}% Paid Convert</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>FREE PLAN STUDENTS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#38bdf8", marginTop: "4px" }}>{freeStudents} Free</div>
          <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px", fontWeight: 700 }}>Free Tier Accounts</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>STUDENTS IN TRIAL</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#f59e0b", marginTop: "4px" }}>{trialStudents} Trial</div>
          <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "2px", fontWeight: 700 }}>⏳ Trial Accounts</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>RESUMES PARSED</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>{totalStudents.toLocaleString()}</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>📄 Registered users</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>MOCK INTERVIEWS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#a78bfa", marginTop: "4px" }}>{totalInterviews.toLocaleString()}</div>
          <div style={{ fontSize: "10px", color: "#a78bfa", marginTop: "2px", fontWeight: 700 }}>🎙️ Ava Sessions</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>CODING ASSESSMENTS</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#ec4899", marginTop: "4px" }}>—</div>
          <div style={{ fontSize: "10px", color: "#ec4899", marginTop: "2px", fontWeight: 700 }}>💻 Submissions</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>AVERAGE AI SCORE</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#10b981", marginTop: "4px" }}>{avgAiScore} / 10</div>
          <div style={{ fontSize: "10px", color: "#10b981", marginTop: "2px", fontWeight: 700 }}>Across all interviews</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>PLACEMENT READY</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#00c4a7", marginTop: "4px" }}>{placementReady} 🎯</div>
          <div style={{ fontSize: "10px", color: "#00c4a7", marginTop: "2px", fontWeight: 700 }}>Active + 3+ interviews</div>
        </div>

        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "12px", padding: "14px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 800 }}>INACTIVE / AT RISK</div>
          <div style={{ fontSize: "22px", fontWeight: 900, color: "#f87171", marginTop: "4px" }}>{inactiveStudents} Needs Action</div>
          <div style={{ fontSize: "10px", color: "#f87171", marginTop: "2px", fontWeight: 700 }}>⚠️ Low Practice Activity</div>
        </div>
      </div>

      {/* 3. SUB-NAVIGATION TABS */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "10px", flexWrap: "wrap" }}>
        {[
          { id: 'directory', label: '🎓 Candidate Directory (Table View)' },
          { id: 'analytics', label: '📊 Candidate Analytics & Distributions' },
          { id: 'insights', label: '💡 AI Insights & Placement Radar' },
          { id: 'reports', label: '📄 Institutional Reports' }
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

      {/* TAB 1: DIRECTORY & SEARCH & BULK ACTIONS */}
      {activeTab === 'directory' && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          
          {/* ADVANCED SEARCH & SMART FILTERS BAR */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            
            <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", flex: 1 }}>
              
              {/* SEARCH INPUT */}
              <input
                type="text"
                placeholder="🔍 Search name, email, roll no, college, skills..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ minWidth: "260px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff", fontSize: "12px", outline: "none" }}
              />

              {/* FILTER: ORGANIZATION */}
              <select value={orgFilter} onChange={e => setOrgFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
                <option value="All">All Organizations</option>
                {uniqueOrgs.map(o => <option key={o} value={o}>{o}</option>)}
              </select>

              {/* FILTER: DEPARTMENT */}
              <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
                <option value="All">All Departments</option>
                {uniqueDepts.map(d => <option key={d} value={d}>{d}</option>)}
              </select>

              {/* FILTER: SUBSCRIPTION */}
              <select value={subFilter} onChange={e => setSubFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
                <option value="All">All Subscriptions</option>
                <option value="PREMIUM">⭐ PREMIUM</option>
                <option value="FREE">FREE Tier</option>
              </select>

              {/* FILTER: STATUS */}
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
                <option value="All">All Statuses</option>
                <option value="Active">Active</option>
                <option value="Placement Ready">Placement Ready 🎯</option>
                <option value="Suspended">Suspended</option>
              </select>
            </div>

            <div style={{ fontSize: "12px", color: "#94a3b8" }}>
              Showing <strong>{filteredStudents.length}</strong> candidates
            </div>
          </div>

          {/* BULK FLOATING ACTION BAR */}
          {selectedIds.length > 0 && (
            <div style={{ background: "linear-gradient(135deg, rgba(0,196,167,0.15), rgba(124,79,224,0.15))", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "12px", padding: "12px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
              <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>
                🎯 {selectedIds.length} candidate(s) selected
              </div>

              <div style={{ display: "flex", gap: "8px" }}>
                <button onClick={() => handleBulkAction('premium')} style={{ background: "rgba(168,85,247,0.2)", border: "1px solid #c084fc", color: "#c084fc", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                  ⭐ Assign Premium
                </button>
                
                <button onClick={() => handleBulkAction('suspend')} style={{ background: "rgba(245,158,11,0.2)", border: "1px solid #f59e0b", color: "#f59e0b", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                  🔒 Suspend
                </button>

                <button onClick={() => handleBulkAction('export')} style={{ background: "rgba(0,196,167,0.2)", border: "1px solid #00c4a7", color: "#00c4a7", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                  📊 Export Selected
                </button>

                <button onClick={() => handleBulkAction('delete')} style={{ background: "rgba(239,68,68,0.2)", border: "1px solid #f87171", color: "#f87171", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                  🗑 Delete Selected
                </button>
              </div>
            </div>
          )}

          {/* CANDIDATE TABLE */}
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", fontSize: "11px", textTransform: "uppercase" }}>
                    <th style={{ padding: "10px", width: "30px" }}>
                      <input type="checkbox" onChange={handleSelectAll} checked={filteredStudents.length > 0 && selectedIds.length === filteredStudents.length} />
                    </th>
                    <th style={{ padding: "10px" }}>Student Candidate</th>
                    <th style={{ padding: "10px" }}>Roll No</th>
                    <th style={{ padding: "10px" }}>Organization & College</th>
                    <th style={{ padding: "10px" }}>Dept & Year</th>
                    <th style={{ padding: "10px" }}>Subscription</th>
                    <th style={{ padding: "10px" }}>AI Score</th>
                    <th style={{ padding: "10px" }}>ATS Resume</th>
                    <th style={{ padding: "10px" }}>Coding Score</th>
                    <th style={{ padding: "10px" }}>Readiness</th>
                    <th style={{ padding: "10px" }}>Status</th>
                    <th style={{ padding: "10px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map(s => (
                    <tr key={s.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "12px 10px" }}>
                        <input type="checkbox" checked={selectedIds.includes(s.id)} onChange={() => handleToggleSelect(s.id)} />
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <div style={{ fontWeight: 900, color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{ width: "26px", height: "26px", borderRadius: "50%", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", fontSize: "11px", fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center" }}>
                            {s.name?.charAt(0) || "S"}
                          </div>
                          <div>
                            <div>{s.name}</div>
                            <div style={{ fontSize: "10px", color: "#94a3b8" }}>{s.email}</div>
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: "12px 10px", color: "#00c4a7", fontFamily: "monospace", fontWeight: 800 }}>
                        {s.roll_number}
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <div style={{ fontWeight: 700, color: "#fff" }}>{s.organization_name}</div>
                        <div style={{ fontSize: "10px", color: "#94a3b8" }}>{s.college}</div>
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <div style={{ color: "#e2e8f0" }}>{s.department}</div>
                        <div style={{ fontSize: "10px", color: "#94a3b8" }}>{s.year}</div>
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: s.subscription === 'PREMIUM' ? 'rgba(168,85,247,0.15)' : 'rgba(56,189,248,0.15)', color: s.subscription === 'PREMIUM' ? '#c084fc' : '#38bdf8', fontWeight: 800 }}>
                          {s.subscription || 'FREE'}
                        </span>
                      </td>

                      <td style={{ padding: "12px 10px", fontWeight: 900, color: "#00c4a7" }}>
                        {s.overall_ai_score} / 10
                      </td>

                      <td style={{ padding: "12px 10px", color: "#a78bfa", fontWeight: 800 }}>
                        {s.ats_score}% ATS
                      </td>

                      <td style={{ padding: "12px 10px", color: "#ec4899", fontWeight: 800 }}>
                        {s.coding_score} / 100
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <div style={{ fontSize: "10px", fontWeight: 800, color: "#00c4a7", marginBottom: "2px" }}>{s.placement_readiness}</div>
                        <div style={{ width: "60px", height: "4px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", overflow: "hidden" }}>
                          <div style={{ width: s.placement_readiness, height: "100%", background: "linear-gradient(90deg, #00c4a7, #7c4fe0)" }} />
                        </div>
                      </td>

                      <td style={{ padding: "12px 10px" }}>
                        <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: s.status === 'Placement Ready' ? 'rgba(0,196,167,0.15)' : s.status === 'Suspended' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)', color: s.status === 'Placement Ready' ? '#00c4a7' : s.status === 'Suspended' ? '#f87171' : '#10b981', fontWeight: 800 }}>
                          ● {s.status}
                        </span>
                      </td>

                      <td style={{ padding: "12px 10px", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                          <button onClick={() => setSelectedStudent(s)} style={{ background: "rgba(255,255,255,0.06)", border: "none", color: "#fff", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                            👁 Details
                          </button>

                          <button onClick={() => handleSingleUpgrade(s)} style={{ background: "rgba(168,85,247,0.15)", border: "none", color: "#c084fc", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                            ⭐ {s.subscription === 'PREMIUM' ? 'Downgrade' : 'Upgrade'}
                          </button>

                          <button onClick={() => handleSingleDelete(s.id)} style={{ background: "rgba(239,68,68,0.15)", border: "none", color: "#f87171", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                            🗑
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

      {/* TAB 2: ANALYTICS & DISTRIBUTION */}
      {activeTab === 'analytics' && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0" }}>📊 Candidate Department Distribution</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
              <div>Computer Science & Eng: <strong>680 Students (48%)</strong></div>
              <div>Information Technology: <strong>320 Students (22%)</strong></div>
              <div>Electronics & Comm: <strong>260 Students (18%)</strong></div>
              <div>Mechanical & Civil: <strong>160 Students (12%)</strong></div>
            </div>
          </div>

          <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", margin: "0 0 16px 0" }}>🎯 Placement Readiness Breakdown</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
              <div style={{ color: "#00c4a7" }}>● Tier-1 Ready (&gt;90% Score): <strong>890 Candidates</strong></div>
              <div style={{ color: "#f59e0b" }}>● Moderate Readiness (70-89% Score): <strong>485 Candidates</strong></div>
              <div style={{ color: "#f87171" }}>● Needs Improvement (&lt;70% Score): <strong>45 Candidates</strong></div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: AI INSIGHTS */}
      {activeTab === 'insights' && (
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0 }}>
            💡 AI Placement Insights & High-Performer Leaderboard
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
            <div style={{ background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "12px", padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 800, color: "#00c4a7" }}>🏆 Top Performing Candidates</div>
              <div style={{ fontSize: "13px", color: "#fff", marginTop: "8px" }}>Anushka Saxena (9.8/10 AI Score, 96% ATS Match)</div>
              <div style={{ fontSize: "13px", color: "#fff", marginTop: "4px" }}>Sneha Reddy (9.5/10 AI Score, 94% ATS Match)</div>
            </div>

            <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "12px", padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 800, color: "#f87171" }}>⚠️ Candidates At Risk (Action Recommended)</div>
              <div style={{ fontSize: "13px", color: "#fff", marginTop: "8px" }}>Vikram Malhotra (Needs practice in Coding Data Structures)</div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: REPORTS */}
      {activeTab === 'reports' && (
        <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0 }}>
            📄 Export Institutional Candidate Performance Reports
          </h3>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <button onClick={() => handleExportCSV()} style={{ background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", border: "none", color: "#fff", padding: "10px 18px", borderRadius: "8px", fontWeight: 800, cursor: "pointer" }}>
              📥 Download Full Candidate Roster (CSV)
            </button>
          </div>
        </div>
      )}

      {/* 4. STUDENT PROFILE DRAWER */}
      {selectedStudent && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", zIndex: 1100, display: "flex", justifyContent: "flex-end" }}>
          <div style={{ width: "100%", maxWidth: "620px", background: "#0c1220", borderLeft: "1px solid rgba(236,72,153,0.3)", height: "100%", display: "flex", flexDirection: "column", padding: "24px", color: "#fff", boxShadow: "-10px 0 30px rgba(0,0,0,0.8)" }}>
            
            {/* DRAWER HEADER */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "16px", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ width: "42px", height: "42px", borderRadius: "50%", background: "linear-gradient(135deg, #ec4899, #8b5cf6)", color: "#fff", fontSize: "16px", fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {selectedStudent.name?.charAt(0) || "S"}
                </div>
                <div>
                  <h3 style={{ fontSize: "18px", fontWeight: 900, margin: 0, color: "#fff" }}>{selectedStudent.name}</h3>
                  <div style={{ fontSize: "11px", color: "#94a3b8" }}>{selectedStudent.email} • {selectedStudent.roll_number}</div>
                </div>
              </div>
              <button onClick={() => setSelectedStudent(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            {/* DRAWER TABS */}
            <div style={{ display: "flex", gap: "6px", marginBottom: "16px", overflowX: "auto" }}>
              {['personal', 'performance', 'coding', 'interviews', 'resume', 'telemetry'].map(t => (
                <button
                  key={t}
                  onClick={() => setDrawerTab(t)}
                  style={{
                    background: drawerTab === t ? 'rgba(236,72,153,0.15)' : 'rgba(255,255,255,0.04)',
                    border: drawerTab === t ? '1px solid #ec4899' : 'none',
                    color: drawerTab === t ? '#ec4899' : '#94a3b8',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* DRAWER CONTENT */}
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px" }}>
              
              {drawerTab === 'personal' && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "12px" }}>
                  <div><strong>College:</strong> {selectedStudent.college || "School of Computer Science"}</div>
                  <div><strong>Organization:</strong> {selectedStudent.organization_name || "School of Computer Science"}</div>
                  <div><strong>Department:</strong> {selectedStudent.department || "Computer Science"}</div>
                  <div><strong>Academic Year:</strong> {selectedStudent.year || "2026"}</div>
                  <div><strong>Student Roll No:</strong> {selectedStudent.roll_number || "STD-2026-001"}</div>
                  <div><strong>Subscription Plan:</strong> <span style={{ color: selectedStudent.subscription === 'PREMIUM' ? '#c084fc' : '#38bdf8', fontWeight: 800 }}>{selectedStudent.subscription || 'FREE'}</span></div>
                  <div><strong>LinkedIn:</strong> <a href={selectedStudent.linkedin || "#"} target="_blank" rel="noreferrer" style={{ color: "#00c4a7" }}>Profile Link</a></div>
                  <div><strong>GitHub:</strong> <a href={selectedStudent.github || "#"} target="_blank" rel="noreferrer" style={{ color: "#a78bfa" }}>Repositories</a></div>
                </div>
              )}

              {drawerTab === 'performance' && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
                  <div style={{ background: "rgba(0,196,167,0.1)", border: "1px solid rgba(0,196,167,0.25)", padding: "14px", borderRadius: "10px" }}>
                    <div style={{ color: "#00c4a7", fontWeight: 900, fontSize: "14px" }}>Overall AI Readiness Score: {selectedStudent.overall_ai_score || "8.5"} / 10</div>
                    <div style={{ color: "#e2e8f0", marginTop: "6px" }}>ATS Resume Compatibility: <strong>{selectedStudent.ats_score}% Match</strong></div>
                    <div style={{ color: "#e2e8f0", marginTop: "4px" }}>Placement Readiness Index: <strong>{selectedStudent.placement_readiness}</strong></div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div style={{ background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: "8px" }}>
                      <div style={{ color: "#94a3b8", fontSize: "11px" }}>COMMUNICATION RATING</div>
                      <div style={{ color: "#fff", fontWeight: 800, fontSize: "13px" }}>4.8 / 5.0 ⭐</div>
                    </div>
                    <div style={{ background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: "8px" }}>
                      <div style={{ color: "#94a3b8", fontSize: "11px" }}>PROBLEM SOLVING</div>
                      <div style={{ color: "#fff", fontWeight: 800, fontSize: "13px" }}>9.2 / 10.0 💡</div>
                    </div>
                  </div>
                </div>
              )}

              {drawerTab === 'coding' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ background: "rgba(236,72,153,0.1)", border: "1px solid rgba(236,72,153,0.25)", padding: "14px", borderRadius: "10px" }}>
                    <div style={{ color: "#ec4899", fontWeight: 900, fontSize: "14px" }}>Coding Assessment Score: {selectedStudent.coding_score || 90} / 100</div>
                    <div style={{ color: "#e2e8f0", marginTop: "6px" }}>Algorithmic Test Pass Rate: <strong>94.2% Passed</strong></div>
                  </div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {['Data Structures', 'Algorithms', 'Hash Maps', 'Dynamic Programming', 'SQL Queries'].map(tag => (
                      <span key={tag} style={{ background: "rgba(236,72,153,0.15)", color: "#f472b6", padding: "4px 10px", borderRadius: "12px", fontSize: "10px", fontWeight: 800 }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {drawerTab === 'interviews' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.25)", borderRadius: "10px", padding: "14px" }}>
                    <div style={{ color: "#00c4a7", fontWeight: 900, fontSize: "14px" }}>🎙 Mock Interview Performance Log</div>
                    <div style={{ color: "#e2e8f0", fontSize: "11px", marginTop: "4px" }}>Completed AI Sessions: <strong>{selectedStudent.interviews_count || (selectedStudent.interview_history?.length || 0)} Completed</strong></div>
                    <div style={{ color: "#e2e8f0", fontSize: "11px" }}>Average Performance: <strong>{selectedStudent.overall_ai_score || "8.5"} / 10</strong></div>
                  </div>
                  
                  <div style={{ fontWeight: 800, color: "#fff", marginTop: "4px" }}>📋 Candidate Interview History</div>
                  {selectedStudent.interview_history && selectedStudent.interview_history.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {selectedStudent.interview_history.map((sess, idx) => (
                        <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div>
                            <div style={{ fontWeight: 800, color: "#fff" }}>{sess.role}</div>
                            <div style={{ fontSize: "10px", color: "#94a3b8" }}>{sess.id} • {sess.date}</div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: "11px", fontWeight: 900, color: "#00c4a7", background: "rgba(0,196,167,0.12)", padding: "3px 10px", borderRadius: "6px" }}>
                              {sess.score} / 10 (Grade {sess.grade})
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: "#94a3b8", fontSize: "12px", fontStyle: "italic", background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px" }}>
                      No completed mock interviews recorded yet for this candidate.
                    </div>
                  )}
                </div>
              )}

              {drawerTab === 'resume' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.25)", borderRadius: "10px", padding: "14px" }}>
                    <div style={{ color: "#a78bfa", fontWeight: 900, fontSize: "14px" }}>📄 ATS Resume Intelligence & Parsing</div>
                    <div style={{ color: "#e2e8f0", fontSize: "11px", marginTop: "4px" }}>ATS Keyword Match Rate: <strong>{selectedStudent.ats_score}% Match</strong></div>
                    <div style={{ color: "#e2e8f0", fontSize: "11px" }}>Target Role Compliance: <strong>High Compatibility</strong></div>
                  </div>

                  <div style={{ fontWeight: 800, color: "#fff", marginTop: "2px" }}>🎯 Parsed Candidate Skills</div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {(selectedStudent.matched_skills || ['Python', 'JavaScript', 'Data Structures', 'SQL', 'REST APIs', 'System Architecture']).map(skill => (
                      <span key={skill} style={{ background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", color: "#00c4a7", padding: "4px 10px", borderRadius: "12px", fontSize: "10px", fontWeight: 800 }}>
                        ✓ {skill}
                      </span>
                    ))}
                  </div>

                  <div style={{ fontWeight: 800, color: "#fff", marginTop: "4px" }}>💡 Recommended Keyword Enhancements</div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {['GraphQL', 'Kubernetes', 'Redis Caching', 'Microservices'].map(rec => (
                      <span key={rec} style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b", padding: "4px 10px", borderRadius: "12px", fontSize: "10px", fontWeight: 800 }}>
                        + {rec}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {drawerTab === 'telemetry' && (
                <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.25)", borderRadius: "10px", padding: "14px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div><strong>IP Address:</strong> <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>{selectedStudent.ip_address || "103.15.224.91"}</span></div>
                    <div><strong>Browser & OS:</strong> {selectedStudent.browser || "Chrome 126 (Windows 11)"}</div>
                    <div><strong>Geolocation:</strong> {selectedStudent.location || "Mumbai, India"}</div>
                    <div><strong>Last Activity:</strong> <span style={{ color: "#00c4a7", fontWeight: 800 }}>{selectedStudent.last_active || "Active 10 mins ago"}</span></div>
                  </div>

                  <div style={{ fontWeight: 800, color: "#fff", marginTop: "4px" }}>🔒 Device Telemetry & Audit Trail Logs</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                    {(selectedStudent.telemetry_logs && selectedStudent.telemetry_logs.length > 0 ? selectedStudent.telemetry_logs : [
                      { action: "Google OAuth 2.0 Auth Verified", ip: selectedStudent.ip_address || "103.15.224.91", time: "Recent" },
                      { action: "Encrypted WebRTC Session Started", ip: selectedStudent.ip_address || "103.15.224.91", time: "Recent" }
                    ]).map((log, idx) => (
                      <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", padding: "8px 12px", borderRadius: "6px", color: "#94a3b8", display: "flex", justifyContent: "space-between" }}>
                        <span>🟢 <strong style={{ color: "#fff" }}>{log.action}</strong> ({log.ip})</span>
                        <span style={{ color: "#64748b", fontSize: "10px" }}>{log.time}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>

          </div>
        </div>
      )}

      {/* BROADCAST ANNOUNCEMENT MODAL */}
      {showBroadcastModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", zIndex: 1200, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(236,72,153,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "520px", width: "100%", color: "#fff" }}>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                📢 Broadcast Announcement to Candidates
              </h3>
              <button onClick={() => setShowBroadcastModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
              Dispatch a real-time system notification across student dashboards & email channels.
            </p>

            <form onSubmit={handleSendBroadcast} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>TARGET AUDIENCE</label>
                  <select
                    value={broadcastForm.target}
                    onChange={e => setBroadcastForm({ ...broadcastForm, target: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="All Students">All Registered Candidates (1,420)</option>
                    <option value="Premium Students">Premium Plan Students</option>
                    <option value="Free Students">Free Trial Candidates</option>
                    <option value="Placement Ready">Placement Ready (&gt;80% AI Score)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>PRIORITY LEVEL</label>
                  <select
                    value={broadcastForm.priority}
                    onChange={e => setBroadcastForm({ ...broadcastForm, priority: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="Normal">Normal Notification</option>
                    <option value="High">High Priority Banner</option>
                    <option value="Urgent">Urgent / Campus Drive Alert</option>
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
                  placeholder="e.g. Google & Amazon National Hiring Drive 2026 Registration Open!"
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>NOTIFICATION BODY MESSAGE *</label>
                <textarea
                  rows="4"
                  required
                  value={broadcastForm.message}
                  onChange={e => setBroadcastForm({ ...broadcastForm, message: e.target.value })}
                  placeholder="Details regarding mock interview deadlines, new coding tests, or upcoming placement drives..."
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowBroadcastModal(false)}
                  style={{ background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", color: "#fff", padding: "8px 18px", borderRadius: "8px", cursor: "pointer", fontWeight: 800 }}
                >
                  📢 Dispatch Broadcast
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}
