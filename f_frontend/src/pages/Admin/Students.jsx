import React, { useState, useEffect } from 'react';
import StudentTable from '../../components/Admin/StudentTable';
import StudentModal from '../../components/Admin/StudentModal';
import { getAdminStudents, createAdminStudent, updateAdminStudent, deleteAdminStudent, importAdminStudents } from '../../services/adminAPI';
import { BACKEND_URL } from '../../config/apiConfig';

export default function Students({ organization }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [toast, setToast] = useState("");

  // CSV Import State
  const [showImportModal, setShowImportModal] = useState(false);
  const [csvContent, setCsvContent] = useState("");
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");

  const orgJoinCode = organization?.join_code || (JSON.parse(localStorage.getItem("admin_organization") || "{}"))?.join_code || "SUN2026";

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const data = await getAdminStudents();
      setStudents(data.students || []);
    } catch (e) {
      console.error("Fetch students error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setSelectedStudent(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (std) => {
    setSelectedStudent(std);
    setModalOpen(true);
  };

  const handleSaveStudent = async (formData) => {
    try {
      if (formData.id) {
        await updateAdminStudent(formData.id, formData);
        showToast("Student record updated successfully!");
      } else {
        await createAdminStudent(formData);
        showToast("New student created successfully!");
      }
      setModalOpen(false);
      fetchStudents();
    } catch (e) {
      alert(e.message || "Operation failed");
    }
  };

  const handleDeleteStudent = async (id) => {
    if (window.confirm("Are you sure you want to delete this student record?")) {
      try {
        await deleteAdminStudent(id);
        showToast("Student deleted successfully!");
        fetchStudents();
      } catch (e) {
        alert(e.message || "Failed to delete student");
      }
    }
  };

  const handleBulkDelete = async (ids) => {
    if (window.confirm(`Delete ${ids.length} selected students?`)) {
      for (const id of ids) {
        await deleteAdminStudent(id);
      }
      showToast(`Bulk deleted ${ids.length} students!`);
      fetchStudents();
    }
  };

  const handleBulkRenew = async (ids) => {
    try {
      const token = localStorage.getItem("admin_access_token") || localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${BACKEND_URL}/api/admin/students/bulk-renew`, {
        method: "POST",
        headers,
        body: JSON.stringify({ student_ids: ids })
      });
      if (res.ok) {
        showToast(`🎉 Bulk renewed 1-Year subscription access for ${ids.length} selected students!`);
        fetchStudents();
      }
    } catch (e) {
      alert("Failed to bulk renew students");
    }
  };

  const handleOpenImport = () => {
    setCsvContent("");
    setImportPreview(null);
    setImportError("");
    setShowImportModal(true);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result || "";
      setCsvContent(text);
      setImportPreview(null);
      setImportError("");
    };
    reader.readAsText(file);
  };

  const handlePreviewImport = async () => {
    if (!csvContent.trim()) {
      setImportError("Please upload or paste CSV text first.");
      return;
    }
    setImporting(true);
    setImportError("");
    try {
      const res = await importAdminStudents({ csv_text: csvContent, preview: true });
      setImportPreview(res);
    } catch (e) {
      setImportError(e.message || "Failed to validate CSV data");
    } finally {
      setImporting(false);
    }
  };

  const handleCommitImport = async () => {
    setImporting(true);
    setImportError("");
    try {
      const res = await importAdminStudents({ csv_text: csvContent, preview: false });
      showToast(res.message || "Successfully imported student roster!");
      setShowImportModal(false);
      fetchStudents();
    } catch (e) {
      setImportError(e.message || "Import failed. Institutional seat limit reached or database error.");
    } finally {
      setImporting(false);
    }
  };

  const copyJoinCode = () => {
    navigator.clipboard.writeText(orgJoinCode);
    showToast(`Copied Join Code: ${orgJoinCode}`);
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #6d28d9, #7c3aed)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000, boxShadow: "0 10px 30px rgba(109,40,217,0.3)" }}>
          ✨ {toast}
        </div>
      )}

      {/* COLLEGE JOIN CODE BANNER */}
      <div style={{
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        padding: "16px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "12px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.02)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "#f5f3ff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px" }}>
            🏛️
          </div>
          <div>
            <div style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a" }}>
              Student Self-Registration Join Code: <span style={{ fontFamily: "monospace", color: "#6d28d9", background: "#ede9fe", padding: "2px 8px", borderRadius: "6px", fontSize: "15px", letterSpacing: "1px" }}>{orgJoinCode}</span>
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
              Students can link their PrepFly candidate account to this college under <strong>Settings &rarr; My College Affiliation</strong> using this code.
            </div>
          </div>
        </div>
        <button className="btn btn-ghost btn-xs" onClick={copyJoinCode} style={{ border: "1px solid #cbd5e1", fontWeight: 700 }}>
          📋 Copy Code
        </button>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#0f172a", margin: 0 }}>🎓 Student Management Directory</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>View, edit, filter, and onboard candidate records for your organization.</p>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-ghost" onClick={handleOpenImport} style={{ border: "1px solid #cbd5e1", fontWeight: 700 }}>
            📥 Import CSV Roster
          </button>
          <button className="btn btn-primary" onClick={handleOpenAdd} style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)", border: "none", fontWeight: 800 }}>
            ➕ Add New Student
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading student roster...</div>
      ) : (
        <StudentTable
          students={students}
          onView={handleOpenEdit}
          onEdit={handleOpenEdit}
          onDelete={handleDeleteStudent}
          onImport={handleOpenImport}
          onBulkDelete={handleBulkDelete}
          onBulkRenew={handleBulkRenew}
        />
      )}

      {/* CSV IMPORT MODAL */}
      {showImportModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100, padding: "20px" }}>
          <div style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "16px", padding: "24px", maxWidth: "620px", width: "100%", maxHeight: "88vh", overflowY: "auto", color: "#0f172a" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>📥 Import Student Roster via CSV</h3>
                <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>Batch enroll verified institutional candidates.</p>
              </div>
              <button className="btn btn-ghost btn-xs" onClick={() => setShowImportModal(false)}>✕ Close</button>
            </div>

            {importError && (
              <div style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#b91c1c", padding: "10px 14px", borderRadius: "8px", fontSize: "12px", marginBottom: "14px" }}>
                ⚠️ {importError}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "6px" }}>
                  Select CSV File (.csv)
                </label>
                <input 
                  type="file" 
                  accept=".csv,text/csv" 
                  onChange={handleFileUpload}
                  style={{ width: "100%", fontSize: "12px", padding: "8px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px" }}
                />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Or Paste CSV Text</label>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Format: name,email,roll_number,department,year</span>
                </div>
                <textarea
                  rows={5}
                  value={csvContent}
                  onChange={(e) => { setCsvContent(e.target.value); setImportPreview(null); }}
                  placeholder="name,email,roll_number,department,year&#10;Aditi Sen,aditi@sunrise.edu,CS-01,Computer Science,2026&#10;Bikram Roy,bikram@sunrise.edu,CS-02,Computer Science,2026"
                  style={{ width: "100%", fontFamily: "monospace", fontSize: "12px", padding: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px" }}
                />
              </div>

              {/* DRY RUN PREVIEW STATS */}
              {importPreview && (
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "14px" }}>
                  <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a", marginBottom: "8px" }}>
                    Dry-Run Validation Summary
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px" }}>
                    <div>Total Detected Rows: <strong>{importPreview.total_rows}</strong></div>
                    <div>Valid Formatted Rows: <strong style={{ color: "#16a34a" }}>{importPreview.valid_rows}</strong></div>
                    <div>Invalid Rows (Skipped): <strong style={{ color: importPreview.invalid_rows > 0 ? "#dc2626" : "#64748b" }}>{importPreview.invalid_rows}</strong></div>
                    <div>Active Institutional Seats: <strong>{importPreview.seat_status?.active_members} / {importPreview.seat_status?.max_seats}</strong></div>
                  </div>
                  {importPreview.seat_status?.remaining_seats < importPreview.valid_rows && (
                    <div style={{ marginTop: "10px", padding: "8px", background: "#fef3c7", border: "1px solid #fde68a", color: "#92400e", borderRadius: "6px", fontSize: "11px" }}>
                      ⚠️ Notice: Valid rows ({importPreview.valid_rows}) exceed remaining institutional seat capacity ({importPreview.seat_status?.remaining_seats}). Upgrade plan or remove excess rows before importing.
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button 
                  className="btn btn-ghost" 
                  onClick={handlePreviewImport}
                  disabled={importing || !csvContent.trim()}
                  style={{ border: "1px solid #cbd5e1", fontWeight: 700 }}
                >
                  {importing ? "Validating..." : "🔍 Validate & Preview"}
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={handleCommitImport}
                  disabled={importing || !importPreview || importPreview.valid_rows === 0 || (importPreview.seat_status?.remaining_seats < importPreview.valid_rows)}
                  style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)", border: "none", fontWeight: 800 }}
                >
                  {importing ? "Importing..." : `✅ Confirm & Import (${importPreview ? importPreview.valid_rows : 0})`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <StudentModal
        isOpen={modalOpen}
        student={selectedStudent}
        onClose={() => setModalOpen(false)}
        onSave={handleSaveStudent}
      />
    </div>
  );
}
