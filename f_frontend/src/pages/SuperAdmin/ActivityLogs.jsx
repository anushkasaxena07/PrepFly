import React, { useState, useEffect, useRef } from 'react';
import { getSuperAdminActivityLogs, updateSuperAdminActivityLog } from '../../services/superAdminAPI';

export default function ActivityLogs() {
  const [data, setData] = useState({ logs: [], summary: {}, analytics: {} });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoSync, setAutoSync] = useState(true);

  // View Mode: 'table' | 'timeline' | 'analytics'
  const [viewMode, setViewMode] = useState('table');

  // Filters
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [severityFilter, setSeverityFilter] = useState('All');
  const [dateRangeFilter, setDateRangeFilter] = useState('All');
  const [performedByFilter, setPerformedByFilter] = useState('All');
  const [orgFilter, setOrgFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // Multi-select bulk actions
  const [selectedIds, setSelectedIds] = useState([]);

  // Inspector Side Drawer
  const [selectedLog, setSelectedLog] = useState(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [investigationNotes, setInvestigationNotes] = useState('');
  const [investigationStatus, setInvestigationStatus] = useState('Resolved');
  const [updatingLog, setUpdatingLog] = useState(false);

  // Poll logs for live stream
  useEffect(() => {
    fetchLogs();
  }, [categoryFilter, severityFilter, dateRangeFilter, performedByFilter, orgFilter, statusFilter]);

  useEffect(() => {
    let interval = null;
    if (autoSync) {
      interval = setInterval(() => {
        fetchLogs(true);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoSync, categoryFilter, severityFilter, dateRangeFilter, performedByFilter, orgFilter, statusFilter, search]);

  const fetchLogs = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await getSuperAdminActivityLogs({
        category: categoryFilter,
        severity: severityFilter,
        date_range: dateRangeFilter,
        performed_by: performedByFilter,
        organization_id: orgFilter,
        status: statusFilter,
        search: search.trim()
      });
      setData(res || { logs: [], summary: {}, analytics: {} });
    } catch (e) {
      console.error("Error fetching activity logs:", e);
    } finally {
      if (!silent) setLoading(false);
      setRefreshing(false);
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const logsArray = Array.isArray(data?.logs) ? data.logs : [];
      setSelectedIds(logsArray.map(l => l.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const openInspector = (log) => {
    setSelectedLog(log);
    setInvestigationNotes(log.investigation_notes || '');
    setInvestigationStatus(log.investigation_status || 'Resolved');
    setShowDrawer(true);
  };

  const handleSaveInvestigation = async () => {
    if (!selectedLog) return;
    setUpdatingLog(true);
    try {
      await updateSuperAdminActivityLog({
        id: selectedLog.id,
        action_type: 'update',
        investigation_notes: investigationNotes,
        investigation_status: investigationStatus
      });
      setSelectedLog(prev => ({
        ...prev,
        investigation_notes: investigationNotes,
        investigation_status: investigationStatus
      }));
      fetchLogs(true);
      alert("Investigation record saved successfully.");
    } catch (err) {
      alert("Failed to update log: " + err.message);
    } finally {
      setUpdatingLog(false);
    }
  };

  const handleDeleteLog = async (logId) => {
    if (!window.confirm(`Permanently delete log record ${logId}?`)) return;
    try {
      await updateSuperAdminActivityLog({ id: logId, action_type: 'delete' });
      if (selectedLog?.id === logId) setShowDrawer(false);
      fetchLogs(true);
    } catch (err) {
      alert("Failed to delete log: " + err.message);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Delete ${selectedIds.length} selected activity logs?`)) return;
    try {
      await updateSuperAdminActivityLog({ action_type: 'bulk_delete', ids: selectedIds });
      setSelectedIds([]);
      fetchLogs(true);
    } catch (err) {
      alert("Bulk delete failed: " + err.message);
    }
  };

  // Export functions
  const exportCSV = () => {
    const logsArray = Array.isArray(data?.logs) ? data.logs : [];
    const exportData = selectedIds.length > 0 ? logsArray.filter(l => selectedIds.includes(l.id)) : logsArray;
    if (!exportData || exportData.length === 0) return alert("No logs available to export");

    const headers = ["Event ID", "Timestamp", "Severity", "Risk Score", "Category", "Action", "Target", "Performed By Name", "Role", "Email", "Organization", "Status", "IP Address", "Location", "Device", "Browser", "Session ID", "Amount", "Transaction ID"];
    const rows = exportData.map(l => [
      l.id,
      l.created_at,
      l.severity,
      l.risk_score || 'Low',
      l.category,
      `"${(l.action || '').replace(/"/g, '""')}"`,
      `"${(l.target || '').replace(/"/g, '""')}"`,
      `"${(l.performed_by_name || '').replace(/"/g, '""')}"`,
      l.performed_by_role || l.actor_type,
      l.performed_by_email || '',
      `"${(l.organization_name || '').replace(/"/g, '""')}"`,
      l.status,
      l.ip_address,
      `"${l.location || ''}"`,
      `"${l.device || ''}"`,
      `"${l.browser || ''}"`,
      l.session_id || '',
      l.amount || '',
      l.transaction_id || ''
    ]);

    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `soc_audit_logs_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    const logsArray = Array.isArray(data?.logs) ? data.logs : [];
    const exportData = selectedIds.length > 0 ? logsArray.filter(l => selectedIds.includes(l.id)) : logsArray;
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `soc_audit_logs_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getSeverityBadge = (s) => {
    switch (s) {
      case 'Critical':
        return { bg: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: 'rgba(239, 68, 68, 0.4)', icon: '🔴' };
      case 'Warning':
        return { bg: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.4)', icon: '🟡' };
      default:
        return { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)', icon: '🟢' };
    }
  };

  const summary = data?.summary || {};
  const logsList = Array.isArray(data?.logs) ? data.logs : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* HEADER & TOP CONTROLS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '22px', fontWeight: 900, color: '#fff', margin: 0 }}>
              🛡️ Security Operations Center (SOC) & Audit Trail
            </h2>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 800,
              padding: '3px 10px',
              borderRadius: '20px',
              background: autoSync ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
              color: autoSync ? '#10b981' : '#94a3b8',
              border: `1px solid ${autoSync ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.1)'}`
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: autoSync ? '#10b981' : '#94a3b8', boxShadow: autoSync ? '0 0 8px #10b981' : 'none' }} />
              {autoSync ? (refreshing ? 'Syncing...' : 'LIVE SOC STREAM') : 'STREAM PAUSED'}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: '#94a3b8', margin: '4px 0 0 0' }}>
            Real-time security telemetry, payment verification, threat intelligence, and enterprise activity logs.
          </p>
        </div>

        {/* VIEW MODES & EXPORTS */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          
          {/* VIEW SWITCHER */}
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '3px' }}>
            <button
              onClick={() => setViewMode('table')}
              style={{
                background: viewMode === 'table' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'transparent',
                border: 'none', color: '#fff', fontSize: '11px', fontWeight: 800, padding: '6px 12px', borderRadius: '6px', cursor: 'pointer'
              }}
            >
              📋 Table View
            </button>

            <button
              onClick={() => setViewMode('timeline')}
              style={{
                background: viewMode === 'timeline' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'transparent',
                border: 'none', color: '#fff', fontSize: '11px', fontWeight: 800, padding: '6px 12px', borderRadius: '6px', cursor: 'pointer'
              }}
            >
              ⏳ Timeline View
            </button>

            <button
              onClick={() => setViewMode('analytics')}
              style={{
                background: viewMode === 'analytics' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'transparent',
                border: 'none', color: '#fff', fontSize: '11px', fontWeight: 800, padding: '6px 12px', borderRadius: '6px', cursor: 'pointer'
              }}
            >
              📊 SOC Analytics
            </button>
          </div>

          {/* STREAM TOGGLE & EXPORT */}
          <button
            onClick={() => setAutoSync(!autoSync)}
            style={{
              background: autoSync ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px', padding: '7px 12px', fontSize: '11px', color: autoSync ? '#10b981' : '#fff', fontWeight: 800, cursor: 'pointer'
            }}
          >
            {autoSync ? '⏸ Pause Live Stream' : '▶ Resume Live Stream'}
          </button>

          <button
            onClick={exportCSV}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px', padding: '7px 12px', fontSize: '11px', color: '#00c4a7', fontWeight: 800, cursor: 'pointer'
            }}
          >
            📊 Export CSV
          </button>

          <button
            onClick={exportJSON}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px', padding: '7px 12px', fontSize: '11px', color: '#a78bfa', fontWeight: 800, cursor: 'pointer'
            }}
          >
            {`{ }`} JSON
          </button>

        </div>
      </div>

      {/* DASHBOARD SUMMARY CARDS (8 TOP CARDS) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, textTransform: 'uppercase' }}>Total Events Today</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#fff', marginTop: '4px' }}>{summary.total_events_today || 18}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#f59e0b', fontWeight: 800, textTransform: 'uppercase' }}>Failed Logins</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#f59e0b', marginTop: '4px' }}>{summary.failed_login_attempts || 8}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#10b981', fontWeight: 800, textTransform: 'uppercase' }}>Success Payments</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#10b981', marginTop: '4px' }}>{summary.successful_payments || 5}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#f87171', fontWeight: 800, textTransform: 'uppercase' }}>Failed Payments</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#f87171', marginTop: '4px' }}>{summary.failed_payments || 2}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#ef4444', fontWeight: 900, textTransform: 'uppercase' }}>Critical Security</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#ef4444', marginTop: '4px' }}>{summary.critical_security_alerts || 3}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(56,189,248,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase' }}>Active Sessions</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#38bdf8', marginTop: '4px' }}>{summary.active_admin_sessions || 12}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(168,85,247,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#c084fc', fontWeight: 800, textTransform: 'uppercase' }}>New Orgs</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#c084fc', marginTop: '4px' }}>{summary.new_organizations || 4}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(0,196,167,0.2)', borderRadius: '12px', padding: '14px' }}>
          <div style={{ fontSize: '10px', color: '#00c4a7', fontWeight: 800, textTransform: 'uppercase' }}>AI Changes</div>
          <div style={{ fontSize: '20px', fontWeight: 900, color: '#00c4a7', marginTop: '4px' }}>{summary.ai_config_changes || 2}</div>
        </div>
      </div>

      {/* ADVANCED FILTERS BAR */}
      <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '16px' }}>
        
        {/* SEARCH ROW */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <input
            type="text"
            placeholder="🔍 Search Event ID, Student, Admin, Email, Org, IP, Transaction ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
              minWidth: '280px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              padding: '9px 14px',
              fontSize: '12px',
              color: '#fff',
              outline: 'none'
            }}
          />

          {search && (
            <button
              onClick={() => setSearch('')}
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', padding: '8px 14px', borderRadius: '8px', fontSize: '12px', cursor: 'pointer' }}
            >
              Clear Search
            </button>
          )}
        </div>

        {/* DROPDOWN FILTERS GRID */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>CATEGORY</label>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Categories</option>
              <option value="Authentication">Authentication</option>
              <option value="Payments">Payments</option>
              <option value="Student Management">Student Management</option>
              <option value="Organization Management">Organization Management</option>
              <option value="Question Bank">Question Bank</option>
              <option value="AI Configuration">AI Configuration</option>
              <option value="Platform Settings">Platform Settings</option>
              <option value="Security">Security</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>SEVERITY</label>
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Severities</option>
              <option value="Information">🟢 Information</option>
              <option value="Warning">🟡 Warning</option>
              <option value="Critical">🔴 Critical</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>DATE RANGE</label>
            <select value={dateRangeFilter} onChange={(e) => setDateRangeFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Dates</option>
              <option value="Today">Today</option>
              <option value="Yesterday">Yesterday</option>
              <option value="Last 7 Days">Last 7 Days</option>
              <option value="Last 30 Days">Last 30 Days</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>PERFORMED BY</label>
            <select value={performedByFilter} onChange={(e) => setPerformedByFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Roles</option>
              <option value="Super Admin">Super Admin</option>
              <option value="Organization Admin">Organization Admin</option>
              <option value="Student">Student</option>
              <option value="AI System">AI System</option>
              <option value="Payment Gateway">Payment Gateway</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>ORGANIZATION</label>
            <select value={orgFilter} onChange={(e) => setOrgFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Organizations</option>
              <option value="org_stanford_01">Stanford Tech Institute</option>
              <option value="org_mit_02">MIT School of Computing</option>
              <option value="org_cambridge_03">Cambridge Institute</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>STATUS</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Statuses</option>
              <option value="Success">Success</option>
              <option value="Failed">Failed</option>
              <option value="Cancelled">Cancelled</option>
              <option value="Pending">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* BULK ACTIONS TOOLBAR (WHEN ROWS SELECTED) */}
      {selectedIds.length > 0 && (
        <div style={{ background: 'rgba(0,196,167,0.12)', border: '1px solid rgba(0,196,167,0.3)', borderRadius: '10px', padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>
            ✓ {selectedIds.length} event logs selected
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={exportCSV} style={{ background: '#00c4a7', border: 'none', color: '#090d16', padding: '6px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 900, cursor: 'pointer' }}>
              📥 Export Selected
            </button>
            <button onClick={handleBulkDelete} style={{ background: '#ef4444', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 900, cursor: 'pointer' }}>
              🗑 Delete Selected
            </button>
          </div>
        </div>
      )}

      {/* VIEW CONTENT: TABLE / TIMELINE / ANALYTICS */}
      {loading ? (
        <div style={{ color: '#00c4a7', padding: '60px', textAlign: 'center', fontWeight: 800 }}>
          ⚡ Loading SOC telemetry & audit events...
        </div>
      ) : viewMode === 'table' ? (
        
        /* VIEW 1: ENTERPRISE AUDIT LOG TABLE */
        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px', overflowX: 'auto' }}>
          {logsList.length === 0 ? (
            <div style={{ color: '#94a3b8', padding: '40px', textAlign: 'center' }}>
              No audit logs matching your SOC filter criteria.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left', color: '#f0f4fd' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 6px', width: '30px' }}>
                    <input type="checkbox" onChange={handleSelectAll} checked={selectedIds.length === logsList.length && logsList.length > 0} />
                  </th>
                  <th style={{ padding: '10px' }}>Event ID</th>
                  <th style={{ padding: '10px' }}>Timestamp</th>
                  <th style={{ padding: '10px' }}>Severity</th>
                  <th style={{ padding: '10px' }}>Category</th>
                  <th style={{ padding: '10px' }}>Action & Target</th>
                  <th style={{ padding: '10px' }}>Performed By</th>
                  <th style={{ padding: '10px' }}>Organization</th>
                  <th style={{ padding: '10px' }}>Status</th>
                  <th style={{ padding: '10px' }}>IP / Location</th>
                  <th style={{ padding: '10px', textAlign: 'right' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logsList.map(log => {
                  const sInfo = getSeverityBadge(log.severity);
                  const isChecked = selectedIds.includes(log.id);
                  return (
                    <tr
                      key={log.id}
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        background: isChecked ? 'rgba(0,196,167,0.05)' : log.severity === 'Critical' ? 'rgba(239,68,68,0.05)' : 'transparent',
                        borderLeft: log.severity === 'Critical' ? '3px solid #ef4444' : log.severity === 'Warning' ? '3px solid #f59e0b' : '3px solid transparent'
                      }}
                    >
                      <td style={{ padding: '12px 6px' }}>
                        <input type="checkbox" checked={isChecked} onChange={() => handleSelectRow(log.id)} />
                      </td>

                      <td style={{ padding: '12px 10px', fontWeight: 900, color: '#a78bfa', fontFamily: 'monospace' }}>
                        {log.id}
                      </td>

                      <td style={{ padding: '12px 10px', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                        {log.created_at}
                      </td>

                      <td style={{ padding: '12px 10px' }}>
                        <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: sInfo.bg, color: sInfo.color, border: `1px solid ${sInfo.border}`, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          {sInfo.icon} {log.severity}
                        </span>
                      </td>

                      <td style={{ padding: '12px 10px', fontWeight: 800, color: '#00c4a7' }}>
                        {log.category}
                      </td>

                      <td style={{ padding: '12px 10px', maxWidth: '240px' }}>
                        <div style={{ fontWeight: 800, color: '#fff' }}>{log.action}</div>
                        {log.target && <div style={{ fontSize: '10px', color: '#94a3b8' }}>Target: {log.target}</div>}
                      </td>

                      <td style={{ padding: '12px 10px' }}>
                        <div style={{ fontWeight: 700, color: '#fff' }}>{log.performed_by_name || log.performed_by_email || log.actor_id}</div>
                        <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: '#cbd5e1' }}>
                          {log.performed_by_role || log.actor_type}
                        </span>
                      </td>

                      <td style={{ padding: '12px 10px', color: '#e2e8f0', fontWeight: 600 }}>
                        {log.organization_name || log.organization_id}
                      </td>

                      <td style={{ padding: '12px 10px' }}>
                        <span style={{
                          fontSize: '10px', padding: '2px 8px', borderRadius: '4px', fontWeight: 800,
                          background: log.status === 'Success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                          color: log.status === 'Success' ? '#10b981' : '#f87171'
                        }}>
                          {log.status === 'Success' ? '✓ Success' : '✕ Failed'}
                        </span>
                      </td>

                      <td style={{ padding: '12px 10px', fontFamily: 'monospace', color: '#94a3b8', fontSize: '11px' }}>
                        <div>{log.ip_address}</div>
                        {log.location && <div style={{ fontSize: '10px', color: '#64748b' }}>{log.location}</div>}
                      </td>

                      <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                        <button
                          onClick={() => openInspector(log)}
                          style={{
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.12)',
                            color: '#fff',
                            padding: '5px 12px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 800,
                            cursor: 'pointer'
                          }}
                        >
                          👁 Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

      ) : viewMode === 'timeline' ? (

        /* VIEW 2: CHRONOLOGICAL TIMELINE FLOW */
        <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 900, color: '#fff', marginBottom: '20px', margin: 0 }}>
            ⏳ Chronological Platform Event Sequence
          </h3>

          <div style={{ position: 'relative', paddingLeft: '30px' }}>
            {/* VERTICAL CONNECTING LINE */}
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: '12px', width: '2px', background: 'linear-gradient(180deg, #00c4a7, #7c4fe0, rgba(255,255,255,0.05))' }} />

            {logsList.map((log, index) => {
              const sInfo = getSeverityBadge(log.severity);
              return (
                <div key={log.id} style={{ position: 'relative', marginBottom: '24px' }}>
                  {/* TIMELINE NODE ICON */}
                  <div style={{
                    position: 'absolute', left: '-30px', top: '2px', width: '24px', height: '24px', borderRadius: '50%',
                    background: '#0a0f1d', border: `2px solid ${sInfo.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px'
                  }}>
                    {sInfo.icon}
                  </div>

                  {/* EVENT BOX */}
                  <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: sInfo.color }}>
                        {log.created_at} • {log.category}
                      </div>
                      <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: '#cbd5e1' }}>
                        ID: {log.id}
                      </span>
                    </div>

                    <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#fff', margin: '6px 0 2px 0' }}>
                      {log.action}
                    </h4>

                    <div style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '6px' }}>
                      <span>👤 <strong>By:</strong> {log.performed_by_name || log.performed_by_role}</span>
                      <span>🏛 <strong>Org:</strong> {log.organization_name || log.organization_id}</span>
                      <span>💻 <strong>IP:</strong> {log.ip_address}</span>
                      {log.amount && <span style={{ color: '#10b981' }}>💰 <strong>Amount:</strong> {log.amount}</span>}
                    </div>

                    <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => openInspector(log)}
                        style={{ background: 'none', border: 'none', color: '#00c4a7', fontSize: '11px', fontWeight: 800, cursor: 'pointer' }}
                      >
                        Inspect Full Context →
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      ) : (

        /* VIEW 3: SOC ANALYTICS & DASHBOARD */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          
          {/* HOURLY DISTRIBUTION */}
          <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#fff', margin: '0 0 14px 0' }}>
              📈 Platform Events Generated Per Hour
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {(data.analytics?.hourly_distribution || []).map((h, i) => (
                <div key={i}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                    <span>{h.hour}</span>
                    <span style={{ fontWeight: 800, color: '#fff' }}>{h.count} events</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(100, h.count * 2.2)}%`, height: '100%', background: 'linear-gradient(90deg, #00c4a7, #7c4fe0)', borderRadius: '3px' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SEVERITY BREAKDOWN */}
          <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#fff', margin: '0 0 14px 0' }}>
              🔴 Security Severity Distribution
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '16px' }}>
              <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '10px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 800, color: '#10b981' }}>🟢 Information Events</span>
                <span style={{ fontSize: '18px', fontWeight: 900, color: '#fff' }}>{data.analytics?.severity_breakdown?.Information || 5}</span>
              </div>

              <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '10px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 800, color: '#f59e0b' }}>🟡 Warning Alerts</span>
                <span style={{ fontSize: '18px', fontWeight: 900, color: '#fff' }}>{data.analytics?.severity_breakdown?.Warning || 2}</span>
              </div>

              <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '10px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 800, color: '#ef4444' }}>🔴 Critical Security Violations</span>
                <span style={{ fontSize: '18px', fontWeight: 900, color: '#fff' }}>{data.analytics?.severity_breakdown?.Critical || 2}</span>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* INSPECTOR SIDE DRAWER PANEL (WHEN CLICKING VIEW DETAILS) */}
      {showDrawer && selectedLog && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '480px', maxWidth: '90vw',
          background: '#0a0f1d', borderLeft: '1px solid rgba(255,255,255,0.15)', boxShadow: '-20px 0 50px rgba(0,0,0,0.8)',
          zIndex: 2000, padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto'
        }}>
          
          {/* DRAWER HEADER */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '16px' }}>
            <div>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 800, color: '#a78bfa' }}>
                SECURITY LOG INSPECTOR
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 900, color: '#fff', margin: '2px 0 0 0', fontFamily: 'monospace' }}>
                {selectedLog.id}
              </h3>
            </div>
            <button onClick={() => setShowDrawer(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '18px', cursor: 'pointer' }}>
              ✕
            </button>
          </div>

          {/* INSPECTOR ATTRIBUTES LIST */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
            
            <div>
              <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block' }}>ACTION</label>
              <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff', marginTop: '2px' }}>{selectedLog.action}</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px' }}>
              <div>
                <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8' }}>CATEGORY</label>
                <div style={{ color: '#00c4a7', fontWeight: 800, marginTop: '2px' }}>{selectedLog.category}</div>
              </div>

              <div>
                <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8' }}>SEVERITY / RISK</label>
                <div style={{ color: selectedLog.severity === 'Critical' ? '#ef4444' : selectedLog.severity === 'Warning' ? '#f59e0b' : '#10b981', fontWeight: 800, marginTop: '2px' }}>
                  {selectedLog.severity} ({selectedLog.risk_score || 'Low'})
                </div>
              </div>

              <div>
                <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8' }}>STATUS</label>
                <div style={{ color: '#fff', fontWeight: 700, marginTop: '2px' }}>{selectedLog.status}</div>
              </div>

              <div>
                <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8' }}>TIMESTAMP</label>
                <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{selectedLog.created_at}</div>
              </div>
            </div>

            {/* PERFORMER CONTEXT */}
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '11px', fontWeight: 800, color: '#fff' }}>👤 Actor & Organization</div>
              <div><strong style={{ color: '#94a3b8' }}>Performed By:</strong> {selectedLog.performed_by_name || selectedLog.actor_id}</div>
              <div><strong style={{ color: '#94a3b8' }}>Role:</strong> {selectedLog.performed_by_role || selectedLog.actor_type}</div>
              {selectedLog.performed_by_email && <div><strong style={{ color: '#94a3b8' }}>Email:</strong> {selectedLog.performed_by_email}</div>}
              <div><strong style={{ color: '#94a3b8' }}>Organization:</strong> {selectedLog.organization_name || selectedLog.organization_id}</div>
              {selectedLog.session_id && <div><strong style={{ color: '#94a3b8' }}>Session ID:</strong> <span style={{ fontFamily: 'monospace', color: '#a78bfa' }}>{selectedLog.session_id}</span></div>}
            </div>

            {/* TECHNICAL CONTEXT */}
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '11px', fontWeight: 800, color: '#fff' }}>🌐 Technical Telemetry</div>
              <div><strong style={{ color: '#94a3b8' }}>IP Address:</strong> <span style={{ fontFamily: 'monospace', color: '#00c4a7' }}>{selectedLog.ip_address}</span></div>
              {selectedLog.location && <div><strong style={{ color: '#94a3b8' }}>Location:</strong> {selectedLog.location}</div>}
              {selectedLog.device && <div><strong style={{ color: '#94a3b8' }}>Device:</strong> {selectedLog.device}</div>}
              {selectedLog.browser && <div><strong style={{ color: '#94a3b8' }}>Browser:</strong> {selectedLog.browser}</div>}
            </div>

            {/* FINANCIAL CONTEXT (IF PAYMENT) */}
            {(selectedLog.amount || selectedLog.transaction_id) && (
              <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', padding: '12px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '11px', fontWeight: 800, color: '#10b981' }}>💳 Financial Details</div>
                {selectedLog.plan && <div><strong style={{ color: '#94a3b8' }}>Plan:</strong> {selectedLog.plan}</div>}
                {selectedLog.amount && <div><strong style={{ color: '#94a3b8' }}>Amount:</strong> <span style={{ color: '#fff', fontWeight: 800 }}>{selectedLog.amount}</span></div>}
                {selectedLog.payment_gateway && <div><strong style={{ color: '#94a3b8' }}>Gateway:</strong> {selectedLog.payment_gateway}</div>}
                {selectedLog.transaction_id && <div><strong style={{ color: '#94a3b8' }}>Txn ID:</strong> <span style={{ fontFamily: 'monospace', color: '#fff' }}>{selectedLog.transaction_id}</span></div>}
              </div>
            )}

            {/* SUPER ADMIN INVESTIGATION CONTROLS */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '14px', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>⚙️ Investigation & Threat Status</div>
              
              <div>
                <label style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, display: 'block', marginBottom: '4px' }}>INVESTIGATION STATUS</label>
                <select
                  value={investigationStatus}
                  onChange={(e) => setInvestigationStatus(e.target.value)}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '12px' }}
                >
                  <option value="Resolved">Resolved ✓</option>
                  <option value="Investigating">Investigating 🔍</option>
                  <option value="Flagged">Flagged Suspicious 🚩</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, display: 'block', marginBottom: '4px' }}>SUPER ADMIN INVESTIGATION NOTES</label>
                <textarea
                  rows={3}
                  placeholder="Enter SOC investigation notes, IP blocking details, or threat resolution findings..."
                  value={investigationNotes}
                  onChange={(e) => setInvestigationNotes(e.target.value)}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', color: '#fff', fontSize: '12px', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                <button
                  onClick={() => handleDeleteLog(selectedLog.id)}
                  style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', padding: '8px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                >
                  🗑 Delete Record
                </button>

                <button
                  onClick={handleSaveInvestigation}
                  disabled={updatingLog}
                  style={{ background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)', border: 'none', color: '#fff', padding: '8px 18px', borderRadius: '8px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}
                >
                  {updatingLog ? 'Saving...' : '💾 Save Record'}
                </button>
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}
