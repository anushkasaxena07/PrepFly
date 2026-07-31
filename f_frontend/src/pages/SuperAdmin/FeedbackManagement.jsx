import React, { useState, useEffect } from 'react';
import {
  getSuperAdminFeedback,
  getSuperAdminFeedbackDetail,
  updateSuperAdminFeedback,
  deleteSuperAdminFeedback
} from '../../services/feedbackAPI';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function FeedbackManagement() {
  const [data, setData] = useState({ feedback: [], summary: {}, analytics: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [priorityFilter, setPriorityFilter] = useState('All');
  const [ratingFilter, setRatingFilter] = useState('All');

  // Active View / Detail Modal
  const [selectedFb, setSelectedFb] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // Detail Modal Editable Form
  const [adminNotes, setAdminNotes] = useState('');
  const [editStatus, setEditStatus] = useState('New');
  const [editPriority, setEditPriority] = useState('Medium');
  const [updating, setUpdating] = useState(false);

  // Image Preview Lightbox
  const [previewImage, setPreviewImage] = useState(null);

  // Confirmation Modal
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  useEffect(() => {
    fetchFeedbackData();
  }, [roleFilter, categoryFilter, statusFilter, priorityFilter, ratingFilter]);

  const fetchFeedbackData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSuperAdminFeedback({
        role: roleFilter,
        category: categoryFilter,
        status: statusFilter,
        priority: priorityFilter,
        rating: ratingFilter,
        search: search.trim()
      });
      setData(res || { feedback: [], summary: {}, analytics: {} });
    } catch (err) {
      setError(err.message || "Failed to load feedback records");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e?.preventDefault();
    fetchFeedbackData();
  };

  const openDetail = async (id) => {
    setShowDetailModal(true);
    setDetailLoading(true);
    try {
      const fb = await getSuperAdminFeedbackDetail(id);
      setSelectedFb(fb);
      setAdminNotes(fb.admin_notes || '');
      setEditStatus(fb.status || 'New');
      setEditPriority(fb.priority || 'Medium');
    } catch (err) {
      alert("Failed to load details: " + err.message);
      setShowDetailModal(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaveDetail = async () => {
    if (!selectedFb) return;
    setUpdating(true);
    try {
      await updateSuperAdminFeedback(selectedFb.id, {
        status: editStatus,
        priority: editPriority,
        admin_notes: adminNotes
      });
      alert("Feedback details updated successfully!");
      setShowDetailModal(false);
      fetchFeedbackData();
    } catch (err) {
      alert("Update failed: " + err.message);
    } finally {
      setUpdating(false);
    }
  };

  const handleQuickResolve = async (id) => {
    try {
      await updateSuperAdminFeedback(id, { status: "Resolved" });
      fetchFeedbackData();
      if (selectedFb?.id === id) {
        setSelectedFb(prev => ({ ...prev, status: "Resolved" }));
        setEditStatus("Resolved");
      }
    } catch (err) {
      alert("Failed to mark resolved: " + err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteSuperAdminFeedback(id);
      setConfirmDeleteId(null);
      if (showDetailModal && selectedFb?.id === id) {
        setShowDetailModal(false);
      }
      fetchFeedbackData();
    } catch (err) {
      alert("Failed to delete feedback: " + err.message);
    }
  };

  // Export functions
  const exportToCSV = () => {
    const feedbackList = Array.isArray(data?.feedback) ? data.feedback : (Array.isArray(data) ? data : []);
    if (feedbackList.length === 0) return alert("No feedback records available to export");
    const headers = ["Feedback ID", "Date", "Role", "Submitter", "Organization", "Category", "Rating", "Status", "Priority", "Subject", "Message"];
    const rows = feedbackList.map(f => [
      f.id,
      f.created_at,
      f.submitted_by_role,
      `"${(f.submitter_name || f.submitted_by || '').replace(/"/g, '""')}"`,
      `"${(f.organization_name || f.organization_id || '').replace(/"/g, '""')}"`,
      `"${(f.category || '').replace(/"/g, '""')}"`,
      f.rating,
      f.status,
      f.priority,
      `"${(f.subject || '').replace(/"/g, '""')}"`,
      `"${(f.message || '').replace(/"/g, '""')}"`
    ]);
    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `feedback_report_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportToPDF = () => {
    window.print();
  };

  const getPriorityColor = (p) => {
    switch (p) {
      case 'Critical': return { bg: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: 'rgba(239, 68, 68, 0.4)', icon: '🔴' };
      case 'High': return { bg: 'rgba(249, 115, 22, 0.2)', color: '#fb923c', border: 'rgba(249, 115, 22, 0.4)', icon: '🟠' };
      case 'Medium': return { bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)', icon: '🟡' };
      default: return { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)', icon: '🟢' };
    }
  };

  const getStatusBadge = (s) => {
    switch (s) {
      case 'New': return { bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' };
      case 'In Progress': return { bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
      case 'Resolved': return { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
      default: return { bg: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' };
    }
  };

  const summary = data.summary || {};
  const analytics = data.analytics || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* HEADER & EXPORT ACTIONS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 900, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            💬 Platform Feedback & Issue Intelligence
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text2, #94a3b8)', marginTop: '4px', margin: 0 }}>
            Centralized Feedback Hub for Student & Organization Admin reports, bug tracking, and ratings.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={exportToCSV}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 700,
              color: '#00c4a7',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            📊 Export CSV / Excel
          </button>

          <button
            onClick={exportToPDF}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 700,
              color: '#ec4899',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🖨 Export PDF
          </button>
        </div>
      </div>

      {/* SUMMARY STATS CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 800, textTransform: 'uppercase' }}>Total Feedback</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#fff', marginTop: '6px' }}>{summary.total_feedback || 0}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(56,189,248,0.2)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase' }}>New Feedback</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#38bdf8', marginTop: '6px' }}>{summary.new_feedback || 0}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#10b981', fontWeight: 800, textTransform: 'uppercase' }}>Resolved</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#10b981', marginTop: '6px' }}>{summary.resolved_feedback || 0}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#f87171', fontWeight: 800, textTransform: 'uppercase' }}>Bug Reports</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#f87171', marginTop: '6px' }}>{summary.bug_reports || 0}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(168,85,247,0.2)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#c084fc', fontWeight: 800, textTransform: 'uppercase' }}>Feature Requests</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#c084fc', marginTop: '6px' }}>{summary.feature_requests || 0}</div>
        </div>

        <div className="card" style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '14px', padding: '18px' }}>
          <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 800, textTransform: 'uppercase' }}>Average Rating</div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#f59e0b', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            {summary.average_rating || '5.0'} ⭐
          </div>
        </div>
      </div>

      {/* ANALYTICS SECTION */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* BY CATEGORY */}
        <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#fff', marginBottom: '14px', margin: 0 }}>📊 Feedback Distribution by Category</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
            {(analytics.by_category || []).map((item, i) => (
              <div key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                  <span>{item.category}</span>
                  <span style={{ fontWeight: 800, color: '#fff' }}>{item.count}</span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, (item.count / (summary.total_feedback || 1)) * 100)}%`, height: '100%', background: 'linear-gradient(90deg, #00c4a7, #7c4fe0)', borderRadius: '3px' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* TOP REPORTING ORGANIZATIONS */}
        <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#fff', marginBottom: '14px', margin: 0 }}>🏢 Top Organizations Submitting Feedback</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
            {(analytics.top_organizations || []).map((item, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '8px 12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '12px', color: '#fff', fontWeight: 700 }}>{item.organization}</span>
                <span style={{ fontSize: '11px', color: '#00c4a7', fontWeight: 800 }}>{item.count} submissions</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SEARCH AND FILTERS TOOLBAR */}
      <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
          <input
            type="text"
            placeholder="Search subject, message, student, or org..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
              minWidth: '240px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              padding: '9px 14px',
              fontSize: '12px',
              color: '#fff',
              outline: 'none'
            }}
          />

          <button type="submit" style={{ background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)', border: 'none', borderRadius: '8px', padding: '9px 18px', fontWeight: 800, fontSize: '12px', color: '#fff', cursor: 'pointer' }}>
            🔍 Search
          </button>
        </form>

        {/* FILTER DROPDOWNS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>ROLE</label>
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Roles</option>
              <option value="Student">Student</option>
              <option value="Organization Admin">Organization Admin</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>CATEGORY</label>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Categories</option>
              <option value="General Feedback">General Feedback</option>
              <option value="Bug Report">Bug Report</option>
              <option value="Feature Request">Feature Request</option>
              <option value="Payment Issue">Payment Issue</option>
              <option value="AI Interview">AI Interview</option>
              <option value="Coding Round">Coding Round</option>
              <option value="Dashboard">Dashboard</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>STATUS</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Statuses</option>
              <option value="New">New</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>PRIORITY</label>
            <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Priorities</option>
              <option value="Low">Low 🟢</option>
              <option value="Medium">Medium 🟡</option>
              <option value="High">High 🟠</option>
              <option value="Critical">Critical 🔴</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '10px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>RATING</label>
            <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)} style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 8px', fontSize: '11px', color: '#fff', outline: 'none' }}>
              <option value="All">All Ratings</option>
              <option value="5">5 Stars ⭐⭐⭐⭐⭐</option>
              <option value="4">4 Stars ⭐⭐⭐⭐</option>
              <option value="3">3 Stars ⭐⭐⭐</option>
              <option value="2">2 Stars ⭐⭐</option>
              <option value="1">1 Star ⭐</option>
            </select>
          </div>
        </div>
      </div>

      {/* MAIN DATA TABLE */}
      <div style={{ background: 'rgba(12,18,32,0.85)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '20px', overflowX: 'auto' }}>
        {loading ? (
          <div style={{ color: '#00c4a7', padding: '40px', textAlign: 'center', fontWeight: 800 }}>
            ⚡ Loading feedback records...
          </div>
        ) : error ? (
          <div style={{ color: '#f87171', padding: '30px', textAlign: 'center', background: 'rgba(239,68,68,0.1)', borderRadius: '12px' }}>
            ⚠️ Error: {error}
          </div>
        ) : data.feedback.length === 0 ? (
          <div style={{ color: '#94a3b8', padding: '40px', textAlign: 'center' }}>
            No feedback entries matching your criteria.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', color: '#f0f4fd' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', textAlign: 'left' }}>
                <th style={{ padding: '10px' }}>ID</th>
                <th style={{ padding: '10px' }}>Date</th>
                <th style={{ padding: '10px' }}>Submitted By</th>
                <th style={{ padding: '10px' }}>Role</th>
                <th style={{ padding: '10px' }}>Organization</th>
                <th style={{ padding: '10px' }}>Category</th>
                <th style={{ padding: '10px' }}>Rating</th>
                <th style={{ padding: '10px' }}>Priority</th>
                <th style={{ padding: '10px' }}>Status</th>
                <th style={{ padding: '10px' }}>Subject</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(data?.feedback) ? data.feedback : (Array.isArray(data) ? data : [])).map(fb => {
                const pInfo = getPriorityColor(fb.priority);
                const sInfo = getStatusBadge(fb.status);
                return (
                  <tr key={fb.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s ease' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 800, color: '#a78bfa' }}>{fb.id}</td>
                    <td style={{ padding: '12px 10px', color: '#94a3b8' }}>{fb.created_at ? fb.created_at.split(' ')[0] : ''}</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#fff' }}>{fb.submitter_name}</td>
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: fb.submitted_by_role === 'Organization Admin' ? 'rgba(124,79,224,0.15)' : 'rgba(0,196,167,0.15)', color: fb.submitted_by_role === 'Organization Admin' ? '#c084fc' : '#00c4a7', fontWeight: 800 }}>
                        {fb.submitted_by_role}
                      </span>
                    </td>
                    <td style={{ padding: '12px 10px', color: '#cbd5e1' }}>{fb.organization_name}</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#e2e8f0' }}>{fb.category}</td>
                    <td style={{ padding: '12px 10px', color: '#f59e0b', fontWeight: 800 }}>{fb.rating} ⭐</td>
                    
                    {/* PRIORITY WITH COLOR */}
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: pInfo.bg, color: pInfo.color, border: `1px solid ${pInfo.border}`, fontWeight: 800 }}>
                        {pInfo.icon} {fb.priority}
                      </span>
                    </td>

                    {/* STATUS BADGE */}
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: sInfo.bg, color: sInfo.color, border: `1px solid ${sInfo.border}`, fontWeight: 800 }}>
                        ● {fb.status}
                      </span>
                    </td>

                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#fff', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {fb.subject}
                    </td>

                    <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => openDetail(fb.id)}
                          style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer' }}
                        >
                          👁 Details
                        </button>
                        
                        {fb.status !== 'Resolved' && (
                          <button
                            onClick={() => handleQuickResolve(fb.id)}
                            style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', color: '#10b981', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer' }}
                          >
                            ✓ Resolve
                          </button>
                        )}

                        <button
                          onClick={() => setConfirmDeleteId(fb.id)}
                          style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', padding: '4px 8px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer' }}
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* FULL DETAIL MODAL */}
      {showDetailModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: '#0a0f1d',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '16px',
            width: '600px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '24px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
          }}>
            {detailLoading || !selectedFb ? (
              <div style={{ color: '#00c4a7', padding: '40px', textAlign: 'center' }}>⚡ Loading feedback detail...</div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
                  <div>
                    <span style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 800, color: '#a78bfa' }}>
                      Feedback #{selectedFb.id}
                    </span>
                    <h3 style={{ fontSize: '18px', fontWeight: 900, color: '#fff', margin: '2px 0 0 0' }}>
                      {selectedFb.subject}
                    </h3>
                  </div>
                  <button onClick={() => setShowDetailModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '18px', cursor: 'pointer' }}>✕</button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
                  
                  {/* METADATA GRID */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px' }}>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800 }}>SUBMITTED BY</div>
                      <div style={{ color: '#fff', fontWeight: 700, marginTop: '2px' }}>{selectedFb.submitter_name} ({selectedFb.submitted_by_role})</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800 }}>ORGANIZATION</div>
                      <div style={{ color: '#fff', fontWeight: 700, marginTop: '2px' }}>{selectedFb.organization_name}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800 }}>CATEGORY</div>
                      <div style={{ color: '#00c4a7', fontWeight: 700, marginTop: '2px' }}>{selectedFb.category}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800 }}>RATING</div>
                      <div style={{ color: '#f59e0b', fontWeight: 800, marginTop: '2px' }}>{selectedFb.rating} / 5 ⭐</div>
                    </div>
                  </div>

                  {/* COMPLETE MESSAGE */}
                  <div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 800, marginBottom: '4px' }}>FEEDBACK MESSAGE</div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '14px', color: '#e2e8f0', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                      {selectedFb.message}
                    </div>
                  </div>

                  {/* SCREENSHOT PREVIEW */}
                  {selectedFb.screenshot_url && (
                    <div>
                      <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 800, marginBottom: '4px' }}>ATTACHED SCREENSHOT</div>
                      <img
                        src={selectedFb.screenshot_url.startsWith('/') ? `${BACKEND_URL}${selectedFb.screenshot_url}` : selectedFb.screenshot_url}
                        alt="Screenshot Preview"
                        onClick={() => setPreviewImage(selectedFb.screenshot_url.startsWith('/') ? `${BACKEND_URL}${selectedFb.screenshot_url}` : selectedFb.screenshot_url)}
                        style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.15)', cursor: 'pointer', objectFit: 'cover' }}
                      />
                    </div>
                  )}

                  {/* SUPER ADMIN ACTIONS / EDIT STATUS & NOTES */}
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '14px', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>⚙️ Super Admin Controls</div>
                    
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, display: 'block', marginBottom: '4px' }}>STATUS</label>
                        <select
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value)}
                          style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '12px' }}
                        >
                          <option value="New">New</option>
                          <option value="In Progress">In Progress</option>
                          <option value="Resolved">Resolved</option>
                          <option value="Closed">Closed</option>
                        </select>
                      </div>

                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, display: 'block', marginBottom: '4px' }}>PRIORITY</label>
                        <select
                          value={editPriority}
                          onChange={(e) => setEditPriority(e.target.value)}
                          style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '12px' }}
                        >
                          <option value="Low">Low 🟢</option>
                          <option value="Medium">Medium 🟡</option>
                          <option value="High">High 🟠</option>
                          <option value="Critical">Critical 🔴</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 800, display: 'block', marginBottom: '4px' }}>INTERNAL ADMIN NOTES</label>
                      <textarea
                        rows={3}
                        placeholder="Add internal resolution notes or escalation comments..."
                        value={adminNotes}
                        onChange={(e) => setAdminNotes(e.target.value)}
                        style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', color: '#fff', fontSize: '12px', resize: 'vertical' }}
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                      <button
                        onClick={() => handleDelete(selectedFb.id)}
                        style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', padding: '8px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                      >
                        🗑 Delete Feedback
                      </button>

                      <button
                        onClick={handleSaveDetail}
                        disabled={updating}
                        style={{ background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: '8px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}
                      >
                        {updating ? 'Saving...' : '💾 Save Changes'}
                      </button>
                    </div>
                  </div>

                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* CONFIRMATION DELETE DIALOG */}
      {confirmDeleteId && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 2000
        }}>
          <div style={{ background: '#0a0f1d', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '14px', padding: '24px', width: '380px', textAlignment: 'center' }}>
            <h4 style={{ color: '#fff', fontSize: '16px', margin: '0 0 8px 0' }}>⚠️ Confirm Delete Feedback</h4>
            <p style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '20px' }}>Are you sure you want to permanently delete feedback #{confirmDeleteId}?</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => setConfirmDeleteId(null)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', borderRadius: '6px', padding: '6px 14px', cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => handleDelete(confirmDeleteId)} style={{ background: '#ef4444', border: 'none', color: '#fff', borderRadius: '6px', padding: '6px 16px', fontWeight: 800, cursor: 'pointer' }}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* IMAGE LIGHTBOX */}
      {previewImage && (
        <div onClick={() => setPreviewImage(null)} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 3000, cursor: 'zoom-out' }}>
          <img src={previewImage} alt="Fullscreen Preview" style={{ maxWidth: '90%', maxHeight: '90%', borderRadius: '12px' }} />
        </div>
      )}

    </div>
  );
}
