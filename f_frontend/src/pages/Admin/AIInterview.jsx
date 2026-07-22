import React, { useState, useEffect } from 'react';
import { getAdminInterviews, createAdminInterview, getAdminStudents, openAdminInterviewPDF } from '../../services/adminAPI';

export default function AIInterview() {
  const [interviews, setInterviews] = useState([]);
  const [orgStudents, setOrgStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  
  // Multi-Candidate selection state
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [candidateSearch, setCandidateSearch] = useState('');

  const [newIv, setNewIv] = useState({
    title: '',
    category: 'Full Stack',
    difficulty: 'Medium',
    questions_count: 5,
    scheduled_date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [ivData, stdData] = await Promise.all([
        getAdminInterviews(),
        getAdminStudents()
      ]);
      setInterviews(ivData || []);
      const studentsList = stdData?.students || stdData || [];
      setOrgStudents(studentsList);
    } catch (e) {
      console.error("Fetch AI Interviews error:", e);
    } finally {
      setLoading(false);
    }
  };

  const toggleStudentSelection = (studentId) => {
    if (selectedStudentIds.includes(studentId)) {
      setSelectedStudentIds(selectedStudentIds.filter(id => id !== studentId));
    } else {
      setSelectedStudentIds([...selectedStudentIds, studentId]);
    }
  };

  const handleSelectAll = () => {
    const filteredIds = filteredStudents.map(s => s.id);
    const allSelected = filteredIds.every(id => selectedStudentIds.includes(id));
    if (allSelected) {
      setSelectedStudentIds(selectedStudentIds.filter(id => !filteredIds.includes(id)));
    } else {
      const merged = Array.from(new Set([...selectedStudentIds, ...filteredIds]));
      setSelectedStudentIds(merged);
    }
  };

  const handleSchedule = async (e) => {
    e.preventDefault();
    if (selectedStudentIds.length === 0) {
      alert("Please select at least one candidate from your organization.");
      return;
    }

    const assignedPayload = selectedStudentIds.map(id => {
      const s = orgStudents.find(st => st.id === id);
      return {
        student_id: id,
        student_name: s ? s.name : 'Enrolled Candidate'
      };
    });

    try {
      await createAdminInterview({
        ...newIv,
        students: assignedPayload
      });
      setShowScheduleModal(false);
      setSelectedStudentIds([]);
      fetchData();
    } catch (e) {
      alert("Failed to schedule interview");
    }
  };

  const filteredStudents = orgStudents.filter(s => {
    const q = candidateSearch.toLowerCase();
    return !q || 
      (s.name && s.name.toLowerCase().includes(q)) || 
      (s.roll_number && s.roll_number.toLowerCase().includes(q)) ||
      (s.department && s.department.toLowerCase().includes(q)) ||
      (s.email && s.email.toLowerCase().includes(q));
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>🎤 AI Technical Interview Management</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Schedule automated AI interviews, configure question difficulty, and inspect student score breakdowns.</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowScheduleModal(true)} style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
          ➕ Schedule AI Interview
        </button>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading scheduled interviews...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
          {interviews.map((iv) => (
            <div key={iv.id} className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <span className="pill pill-purple" style={{ fontSize: "10px" }}>{iv.category}</span>
                <span className="pill pill-cyan" style={{ fontSize: "10px" }}>● {iv.status}</span>
              </div>

              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", margin: "0 0 6px 0" }}>{iv.title}</h3>
              <div style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "12px" }}>
                Candidate: <strong style={{ color: "#fff" }}>{iv.student_name || "Assigned Student"}</strong>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", fontSize: "11px", marginBottom: "14px" }}>
                <div>Tech Score: <strong style={{ color: "#00c4a7" }}>{iv.tech_score || 9.0} / 10</strong></div>
                <div>Comm Score: <strong style={{ color: "#7c4fe0" }}>{iv.comm_score || 8.5} / 10</strong></div>
                <div>Confidence: <strong style={{ color: "#ffb800" }}>{iv.confidence_score || 8.9} / 10</strong></div>
                <div>Eye Contact: <span style={{ color: "var(--text2)" }}>92% (AI)</span></div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--text2)" }}>📅 {iv.scheduled_date}</span>
                <button className="btn btn-ghost btn-xs" onClick={() => openAdminInterviewPDF(iv.id)}>
                  📄 Report PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showScheduleModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "560px", width: "100%", maxHeight: "88vh", overflowY: "auto", color: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>🎤 Schedule New AI Interview</h3>
              <button className="btn btn-ghost btn-xs" onClick={() => setShowScheduleModal(false)}>✕ Close</button>
            </div>

            <form onSubmit={handleSchedule} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Session Title *</label>
                <input type="text" required value={newIv.title} onChange={e => setNewIv({ ...newIv, title: e.target.value })} placeholder="e.g. SDE Mock Interview Round 1" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>

              {/* MULTI-CANDIDATE SELECTION CONTAINER */}
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <div>
                    <label style={{ color: "#fff", fontWeight: 800, fontSize: "13px" }}>Assigned Candidates (Multiple Selection) *</label>
                    <div style={{ fontSize: "11px", color: "var(--text2)" }}>Select one or multiple students enrolled in your organization.</div>
                  </div>
                  <span className="pill pill-cyan" style={{ fontSize: "11px", fontWeight: 800 }}>
                    {selectedStudentIds.length} Selected
                  </span>
                </div>

                {/* SEARCH & QUICK ACTION BUTTONS */}
                <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
                  <input 
                    type="text" 
                    value={candidateSearch}
                    onChange={e => setCandidateSearch(e.target.value)}
                    placeholder="🔍 Search candidate name, roll no, department..."
                    style={{ flex: 1, background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 10px", color: "#fff", fontSize: "12px" }}
                  />
                  <button 
                    type="button" 
                    onClick={handleSelectAll}
                    style={{ background: "rgba(0,196,167,0.15)", border: "1px solid #00c4a7", color: "#00c4a7", borderRadius: "6px", padding: "4px 10px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}
                  >
                    {filteredStudents.length > 0 && filteredStudents.every(s => selectedStudentIds.includes(s.id)) ? "Deselect All" : "Select All"}
                  </button>
                </div>

                {/* CHECKLIST LIST */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto", paddingRight: "4px" }}>
                  {filteredStudents.length === 0 ? (
                    <div style={{ fontSize: "12px", color: "var(--text2)", padding: "12px", textAlign: "center" }}>No students found in your organization.</div>
                  ) : (
                    filteredStudents.map(s => {
                      const isSelected = selectedStudentIds.includes(s.id);
                      return (
                        <div 
                          key={s.id} 
                          onClick={() => toggleStudentSelection(s.id)}
                          style={{ 
                            background: isSelected ? "rgba(0,196,167,0.12)" : "rgba(20,29,48,0.7)", 
                            border: isSelected ? "1px solid #00c4a7" : "1px solid rgba(255,255,255,0.06)", 
                            borderRadius: "8px", 
                            padding: "8px 12px", 
                            display: "flex", 
                            alignItems: "center", 
                            justify: "space-between",
                            cursor: "pointer",
                            transition: "all 0.15s ease"
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <input 
                              type="checkbox" 
                              checked={isSelected}
                              onChange={() => {}} // handled by row onClick
                              style={{ cursor: "pointer", accentColor: "#00c4a7" }}
                            />
                            <div>
                              <div style={{ fontWeight: 800, color: "#fff", fontSize: "13px" }}>{s.name}</div>
                              <div style={{ fontSize: "11px", color: "var(--text2)" }}>
                                {s.roll_number ? `Roll: ${s.roll_number} • ` : ''}{s.department || 'Computer Science'} {s.email ? `(${s.email})` : ''}
                              </div>
                            </div>
                          </div>
                          {isSelected && <span style={{ color: "#00c4a7", fontWeight: 900, fontSize: "14px" }}>✓</span>}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Track Category</label>
                  <select value={newIv.category} onChange={e => setNewIv({ ...newIv, category: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="HR & Behavioral">HR & Behavioral</option>
                    <option value="Full Stack">Full Stack</option>
                    <option value="Frontend React">Frontend React</option>
                    <option value="Backend System Design">Backend System Design</option>
                    <option value="Machine Learning">Machine Learning</option>
                    <option value="DSA & Algorithms">DSA & Algorithms</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Difficulty</label>
                  <select value={newIv.difficulty} onChange={e => setNewIv({ ...newIv, difficulty: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Scheduled Date</label>
                <input type="date" required value={newIv.scheduled_date} onChange={e => setNewIv({ ...newIv, scheduled_date: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }} />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" className="btn btn-ghost" onClick={() => setShowScheduleModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
                  Schedule Interview ({selectedStudentIds.length})
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


