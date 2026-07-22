import React, { useState } from 'react';

export default function OrganizationTable({
  orgs = [],
  onDelete,
  onResetPassword,
  onResetSubscription,
  onViewDetails
}) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [healthFilter, setHealthFilter] = useState("All");
  const [sortBy, setSortBy] = useState("name");
  const [selectedIds, setSelectedIds] = useState([]);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(filtered.map(o => o.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const handleExportCSV = (dataToExport) => {
    const list = dataToExport && dataToExport.length > 0 ? dataToExport : filtered;
    if (!list || list.length === 0) return alert("No organization records to export");

    const headers = ["Org ID", "Organization Name", "Type", "Industry", "Primary Admin", "Email", "Phone", "City", "Country", "Students", "Admins", "Recruiters", "Subscription", "Revenue", "Health Score", "Status", "Expiry Date"];
    const rows = list.map(o => [
      `"${o.id}"`,
      `"${(o.name || '').replace(/"/g, '""')}"`,
      `"${o.type}"`,
      `"${o.industry || ''}"`,
      `"${(o.admin_name || '').replace(/"/g, '""')}"`,
      `"${o.email}"`,
      `"${o.phone || ''}"`,
      `"${o.city || ''}"`,
      `"${o.country || ''}"`,
      o.student_count || 0,
      o.admins_count || 0,
      o.recruiters_count || 0,
      `"${o.subscription_plan || 'ENTERPRISE'}"`,
      o.monthly_revenue || 0,
      `"${o.health_badge || '🟢 Healthy'}"`,
      `"${o.status || 'Active'}"`,
      `"${o.subscription_expiry || ''}"`
    ]);

    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `prepfly_organizations_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const filtered = orgs.filter(o => {
    if (typeFilter !== "All" && o.type !== typeFilter) return false;
    if (statusFilter !== "All" && o.status !== statusFilter) return false;
    if (healthFilter !== "All" && !(o.health_badge || "").includes(healthFilter)) return false;
    if (search) {
      const q = search.toLowerCase();
      return (o.name || "").toLowerCase().includes(q) ||
             (o.email || "").toLowerCase().includes(q) ||
             (o.id || "").toLowerCase().includes(q) ||
             (o.admin_name || "").toLowerCase().includes(q);
    }
    return true;
  }).sort((a, b) => {
    if (sortBy === "name") return (a.name || "").localeCompare(b.name || "");
    if (sortBy === "students") return (b.student_count || 0) - (a.student_count || 0);
    if (sortBy === "health") return (b.health_score || 0) - (a.health_score || 0);
    return 0;
  });

  const handleExportPDF = () => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) return alert("Please allow popups to generate PDF report.");

    const rowsHtml = filtered.map(o => `
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">${(o.name || '').replace(/</g, "&lt;")}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${o.type || ''}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${(o.admin_name || '').replace(/</g, "&lt;")} (${o.email || ''})</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${o.student_count || 0}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #7c4fe0; font-weight: bold;">${o.subscription_plan || 'ENTERPRISE'}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${o.health_badge || '🟢 Healthy'}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${o.status || 'Active'}</td>
      </tr>
    `).join("");

    const docHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>PrepFly Global Organizations Executive Audit Report</title>
          <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; color: #1e293b; }
            h1 { color: #00c4a7; margin-bottom: 4px; }
            p { color: #64748b; font-size: 13px; margin-top: 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th { background: #0c1220; color: #fff; text-align: left; padding: 10px; }
            .footer { margin-top: 40px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #eee; padding-top: 10px; }
          </style>
        </head>
        <body>
          <h1>PrepFly Global Organizations Executive Report</h1>
          <p>Generated on ${new Date().toLocaleString()} • Total Organizations: ${filtered.length}</p>
          <table>
            <thead>
              <tr>
                <th>Organization Name</th>
                <th>Type</th>
                <th>Primary Admin</th>
                <th>Students</th>
                <th>Plan Tier</th>
                <th>Health Score</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
          <div class="footer">
            PrepFly Enterprise Platform • Official SOC Audit Digest
          </div>
          <script>
            window.onload = function() { window.print(); }
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(docHtml);
    printWindow.document.close();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* FILTER & EXPORT BAR */}
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
        
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center", flex: 1 }}>
          <input 
            type="text" 
            placeholder="🔍 Search name, org ID, admin, email..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: "260px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff", fontSize: "12px", outline: "none" }}
          />

          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
            <option value="All">All Institution Types</option>
            <option value="College">Colleges / Universities</option>
            <option value="Company">Companies / Recruiters</option>
            <option value="Training Institute">Training Institutes</option>
          </select>

          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
            <option value="All">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Trial">In Free Trial</option>
            <option value="Suspended">Suspended</option>
          </select>

          <select value={healthFilter} onChange={e => setHealthFilter(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
            <option value="All">All Health Scores</option>
            <option value="Healthy">🟢 Healthy (&gt;90)</option>
            <option value="Attention">🟡 Needs Attention (70-89)</option>
            <option value="Critical">🔴 Critical (&lt;70)</option>
          </select>

          <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ background: "#0c1220", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px" }}>
            <option value="name">Sort by Name</option>
            <option value="students">Sort by Students</option>
            <option value="health">Sort by Health Score</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          {selectedIds.length > 0 && (
            <button className="btn btn-danger btn-sm" onClick={() => { if (window.confirm(`Bulk delete ${selectedIds.length} organizations?`)) setSelectedIds([]); }} style={{ background: "rgba(239,68,68,0.2)", border: "1px solid #f87171", color: "#f87171", fontWeight: 800 }}>
              🗑 Delete Selected ({selectedIds.length})
            </button>
          )}

          <button onClick={() => handleExportCSV()} style={{ background: "rgba(0,196,167,0.15)", border: "1px solid rgba(0,196,167,0.3)", color: "#00c4a7", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "6px 12px", cursor: "pointer" }}>
            📊 Export CSV
          </button>
          
          <button onClick={() => handleExportCSV()} style={{ background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)", color: "#a78bfa", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "6px 12px", cursor: "pointer" }}>
            📗 Export Excel
          </button>

          <button onClick={handleExportPDF} style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)", color: "#ec4899", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "6px 12px", cursor: "pointer" }}>
            📕 Export PDF
          </button>
        </div>
      </div>

      {/* TABLE */}
      <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", fontSize: "11px", textTransform: "uppercase" }}>
                <th style={{ padding: "10px", width: "30px" }}>
                  <input type="checkbox" checked={selectedIds.length === filtered.length && filtered.length > 0} onChange={handleSelectAll} style={{ accentColor: "#ec4899" }} />
                </th>
                <th style={{ padding: "10px" }}>Organization & Domain</th>
                <th style={{ padding: "10px" }}>Type & Industry</th>
                <th style={{ padding: "10px" }}>Primary Admin</th>
                <th style={{ padding: "10px" }}>Location</th>
                <th style={{ padding: "10px" }}>Students</th>
                <th style={{ padding: "10px" }}>Recruiters</th>
                <th style={{ padding: "10px" }}>Subscription</th>
                <th style={{ padding: "10px" }}>Health Index</th>
                <th style={{ padding: "10px" }}>Status</th>
                <th style={{ padding: "10px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(o => (
                <tr key={o.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <td style={{ padding: "12px 10px" }}>
                    <input type="checkbox" checked={selectedIds.includes(o.id)} onChange={() => handleSelectOne(o.id)} style={{ accentColor: "#ec4899" }} />
                  </td>

                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "#fff" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "30px", height: "30px", borderRadius: "6px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px" }}>
                        {o.name?.[0] || "O"}
                      </div>
                      <div>
                        <div>{o.name}</div>
                        <div style={{ fontSize: "10px", color: "#94a3b8" }}>{o.domain || o.website}</div>
                      </div>
                    </div>
                  </td>

                  <td style={{ padding: "12px 10px" }}>
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: o.type === "College" ? "rgba(139,92,246,0.15)" : "rgba(0,196,167,0.15)", color: o.type === "College" ? "#a78bfa" : "#00c4a7", fontWeight: 800 }}>
                      {o.type}
                    </span>
                    <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>{o.industry}</div>
                  </td>

                  <td style={{ padding: "12px 10px", color: "#e2e8f0" }}>
                    <div style={{ fontWeight: 700 }}>{o.admin_name}</div>
                    <div style={{ fontSize: "10px", color: "#94a3b8" }}>{o.email}</div>
                  </td>

                  <td style={{ padding: "12px 10px", color: "#94a3b8" }}>
                    {o.city || "San Francisco"}, {o.country || "USA"}
                  </td>

                  <td style={{ padding: "12px 10px", fontWeight: 800, color: "#00c4a7" }}>
                    {o.student_count} / {o.student_limit || 500}
                  </td>

                  <td style={{ padding: "12px 10px", color: "#a78bfa", fontWeight: 800 }}>
                    {o.recruiters_count || 14} Rec
                  </td>

                  <td style={{ padding: "12px 10px" }}>
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: "rgba(236,72,153,0.15)", color: "#ec4899", fontWeight: 800 }}>
                      {o.subscription_plan || "ENTERPRISE"}
                    </span>
                    <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px" }}>Expires: {o.subscription_expiry}</div>
                  </td>

                  <td style={{ padding: "12px 10px" }}>
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: (o.health_badge || "").includes('Healthy') ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)", color: (o.health_badge || "").includes('Healthy') ? "#10b981" : "#f59e0b", fontWeight: 800 }}>
                      {o.health_badge || "🟢 Healthy"} ({o.health_score || 96})
                    </span>
                  </td>

                  <td style={{ padding: "12px 10px" }}>
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", background: o.status === "Active" ? "rgba(0,196,167,0.15)" : "rgba(239,68,68,0.15)", color: o.status === "Active" ? "#00c4a7" : "#f87171", fontWeight: 800 }}>
                      ● {o.status || "Active"}
                    </span>
                  </td>

                  <td style={{ padding: "12px 10px", textAlign: "right" }}>
                    <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                      <button onClick={() => onViewDetails ? onViewDetails(o) : alert(`Viewing ${o.name}`)} style={{ background: "rgba(255,255,255,0.06)", border: "none", color: "#fff", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                        👁 Details
                      </button>

                      <button onClick={() => onResetPassword ? onResetPassword(o) : alert(`Resetting Admin password for ${o.name}...`)} style={{ background: "rgba(0,196,167,0.15)", border: "none", color: "#00c4a7", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                        🔑 Pass
                      </button>

                      <button onClick={() => onResetSubscription ? onResetSubscription(o) : alert(`Resetting Subscription for ${o.name}...`)} style={{ background: "rgba(139,92,246,0.15)", border: "none", color: "#a78bfa", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
                        🔄 Sub
                      </button>

                      <button onClick={() => onDelete ? onDelete(o.id) : null} style={{ background: "rgba(239,68,68,0.15)", border: "none", color: "#f87171", padding: "5px 10px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}>
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
  );
}
