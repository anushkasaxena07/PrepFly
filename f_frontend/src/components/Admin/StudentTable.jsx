import React, { useState } from 'react';

export default function StudentTable({ 
  students = [], 
  onView, 
  onEdit, 
  onDelete, 
  onImport, 
  onBulkDelete,
  onBulkRenew,
  departments = ["Computer Science", "Information Tech", "Electronics", "Mechanical"],
  semesters = ["Sem 2", "Sem 4", "Sem 6", "Sem 8"]
}) {
  const [selectedIds, setSelectedIds] = useState([]);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("All");
  const [semFilter, setSemFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(filtered.map(s => s.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const safeStudents = Array.isArray(students) ? students : (students?.students || students?.data || []);

  const filtered = safeStudents.filter(s => {
    if (deptFilter !== "All" && s.department !== deptFilter) return false;
    if (semFilter !== "All" && s.semester !== semFilter) return false;
    if (statusFilter !== "All" && s.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      const match = (s.name || "").toLowerCase().includes(q) || 
                    (s.roll_number || "").toLowerCase().includes(q) || 
                    (s.email || "").toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const totalPages = Math.ceil(filtered.length / itemsPerPage) || 1;
  const paginated = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const exportCSV = () => {
    const headers = "ID,Name,Roll Number,Department,Semester,Email,Interview Score,Coding Score,Status\n";
    const rows = filtered.map(s => `${s.id},${s.name},${s.roll_number},${s.department},${s.semester},${s.email},${s.interview_score},${s.coding_score},${s.status}`).join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Student_Roster_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
      
      {/* TOOLBAR: SEARCH & FILTERS */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        
        {/* SEARCH INPUT */}
        <div style={{ position: "relative", minWidth: "240px", flex: 1 }}>
          <input 
            type="text" 
            placeholder="🔍 Search name, roll no, or email..." 
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
            style={{
              width: "100%",
              background: "#0c1220",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "8px",
              padding: "8px 12px",
              color: "#fff",
              fontSize: "13px"
            }}
          />
        </div>

        {/* DROPDOWN FILTERS */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <select 
            value={deptFilter} 
            onChange={(e) => { setDeptFilter(e.target.value); setCurrentPage(1); }}
            style={{ background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 10px", fontSize: "12px" }}
          >
            <option value="All">All Departments</option>
            {departments.map(d => <option key={d} value={d}>{d}</option>)}
          </select>

          <select 
            value={semFilter} 
            onChange={(e) => { setSemFilter(e.target.value); setCurrentPage(1); }}
            style={{ background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 10px", fontSize: "12px" }}
          >
            <option value="All">All Semesters</option>
            {semesters.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <select 
            value={statusFilter} 
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            style={{ background: "#0c1220", color: "#f0f4fd", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 10px", fontSize: "12px" }}
          >
            <option value="All">All Status</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>

        {/* BULK EXPORT & ACTIONS */}
        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-ghost btn-xs" onClick={onImport}>
            📥 Import Excel
          </button>
          <button className="btn btn-ghost btn-xs" onClick={exportCSV}>
            📊 Export CSV
          </button>
          {selectedIds.length > 0 && (
            <>
              {onBulkRenew && (
                <button 
                  className="btn btn-xs" 
                  onClick={() => onBulkRenew(selectedIds)}
                  style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", color: "#fff", border: "none", fontWeight: 800 }}
                >
                  ⚡ Bulk Renew Sub ({selectedIds.length})
                </button>
              )}
              <button className="btn btn-danger btn-xs" onClick={() => onBulkDelete(selectedIds)}>
                🗑 Delete ({selectedIds.length})
              </button>
            </>
          )}
        </div>
      </div>

      {/* TABLE */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--text2)", fontSize: "11px", textTransform: "uppercase" }}>
              <th style={{ padding: "10px 8px" }}>
                <input 
                  type="checkbox" 
                  checked={selectedIds.length > 0 && selectedIds.length === filtered.length}
                  onChange={handleSelectAll} 
                />
              </th>
              <th style={{ padding: "10px 8px" }}>Student Name</th>
              <th style={{ padding: "10px 8px" }}>Roll Number</th>
              <th style={{ padding: "10px 8px" }}>Department</th>
              <th style={{ padding: "10px 8px" }}>Semester</th>
              <th style={{ padding: "10px 8px" }}>AI Score</th>
              <th style={{ padding: "10px 8px" }}>Coding Score</th>
              <th style={{ padding: "10px 8px" }}>Subscription</th>
              <th style={{ padding: "10px 8px" }}>Status</th>
              <th style={{ padding: "10px 8px", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginated.length > 0 ? (
              paginated.map((std) => {
                const isSelected = selectedIds.includes(std.id);
                return (
                  <tr key={std.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: isSelected ? "rgba(0,196,167,0.06)" : "transparent" }}>
                    <td style={{ padding: "10px 8px" }}>
                      <input 
                        type="checkbox" 
                        checked={isSelected}
                        onChange={() => handleSelectOne(std.id)} 
                      />
                    </td>
                    <td style={{ padding: "10px 8px", fontWeight: 700, color: "#fff" }}>
                      {std.name}
                    </td>
                    <td style={{ padding: "10px 8px", color: "var(--cyan)", fontFamily: "monospace" }}>
                      {std.roll_number}
                    </td>
                    <td style={{ padding: "10px 8px", color: "var(--text1)" }}>
                      {std.department}
                    </td>
                    <td style={{ padding: "10px 8px", color: "var(--text2)" }}>
                      {std.semester}
                    </td>
                    <td style={{ padding: "10px 8px", fontWeight: 800, color: "#00c4a7" }}>
                      {std.interview_score} / 10
                    </td>
                    <td style={{ padding: "10px 8px", fontWeight: 800, color: "#7c4fe0" }}>
                      {std.coding_score}%
                    </td>
                    <td style={{ padding: "10px 8px" }}>
                      <span className={`pill ${std.subscription === "PREMIUM" ? "pill-purple" : "pill-cyan"}`} style={{ fontSize: "10px" }}>
                        {std.subscription || "FREE"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 8px" }}>
                      <span className={`pill ${std.status === "Active" ? "pill-cyan" : "pill-red"}`} style={{ fontSize: "10px" }}>
                        ● {std.status || "Active"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 8px", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                        <button className="btn btn-ghost btn-xs" onClick={() => onView(std)} title="View Details">
                          👁
                        </button>
                        <button className="btn btn-ghost btn-xs" onClick={() => onEdit(std)} title="Edit Student">
                          ✏️
                        </button>
                        <button className="btn btn-danger btn-xs" onClick={() => onDelete(std.id)} title="Delete Student">
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="10" style={{ padding: "24px", textAlign: "center", color: "var(--text2)" }}>
                  No students match the selected filters or search query.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* PAGINATION FOOTER */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "12px" }}>
          <div style={{ fontSize: "12px", color: "var(--text2)" }}>
            Showing Page {currentPage} of {totalPages} ({filtered.length} total students)
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button 
              className="btn btn-ghost btn-xs" 
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            >
              Previous
            </button>
            <button 
              className="btn btn-ghost btn-xs" 
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            >
              Next
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
