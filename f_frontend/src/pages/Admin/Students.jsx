import React, { useState, useEffect } from 'react';
import StudentTable from '../../components/Admin/StudentTable';
import StudentModal from '../../components/Admin/StudentModal';
import { getAdminStudents, createAdminStudent, updateAdminStudent, deleteAdminStudent, importAdminStudents } from '../../services/adminAPI';

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [toast, setToast] = useState("");

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

      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL || "http://localhost:5000"}/api/admin/students/bulk-renew`, {
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

  const handleImportExcel = async () => {
    try {
      const res = await importAdminStudents({});
      showToast(res.message);
      fetchStudents();
    } catch (e) {
      alert("Import failed");
    }
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000, boxShadow: "0 10px 30px rgba(0,240,200,0.3)" }}>
          ✨ {toast}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>🎓 Student Management Directory</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>View, edit, filter, and onboard candidate records for your organization.</p>
        </div>

        <button className="btn btn-primary" onClick={handleOpenAdd} style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
          ➕ Add New Student
        </button>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading student roster...</div>
      ) : (
        <StudentTable 
          students={students}
          onView={handleOpenEdit}
          onEdit={handleOpenEdit}
          onDelete={handleDeleteStudent}
          onImport={handleImportExcel}
          onBulkDelete={handleBulkDelete}
          onBulkRenew={handleBulkRenew}
        />
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
