import React, { useState, useEffect } from 'react';
import {
  getSuperAdminQuestionBank,
  createSuperAdminQuestion,
  updateSuperAdminQuestion,
  deleteSuperAdminQuestion
} from '../../services/superAdminAPI';

export default function QuestionBank() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editingQ, setEditingQ] = useState(null);

  const [newQ, setNewQ] = useState({
    title: '',
    category: 'Technical',
    difficulty: 'Medium',
    solution: ''
  });

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const data = await getSuperAdminQuestionBank();
      setQuestions(data || []);
    } catch (e) {
      console.error("Error fetching global question bank:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newQ.title.trim()) return;
    try {
      await createSuperAdminQuestion(newQ);
      setShowAdd(false);
      setNewQ({ title: '', category: 'Technical', difficulty: 'Medium', solution: '' });
      fetchQuestions();
    } catch (e) {
      alert("Failed to add global question: " + e.message);
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingQ || !editingQ.title.trim()) return;
    try {
      await updateSuperAdminQuestion(editingQ.id, editingQ);
      setEditingQ(null);
      fetchQuestions();
    } catch (e) {
      alert("Failed to update global question: " + e.message);
    }
  };

  const handleDelete = async (qId) => {
    if (!window.confirm("Are you sure you want to delete this global question from the Master Question Bank?")) return;
    try {
      await deleteSuperAdminQuestion(qId);
      fetchQuestions();
    } catch (e) {
      alert("Failed to delete global question: " + e.message);
    }
  };

  const filtered = questions.filter(q => {
    const matchesCat = activeCat === "All" || q.category === activeCat;
    const matchesSearch = !searchQuery || 
      (q.title && q.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (q.solution && q.solution.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            📚 Global Platform Question Bank
          </h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>
            Master repository of interview, coding, and system design questions available across all institutions.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => setShowAdd(true)}
          style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", fontWeight: 800, padding: "10px 18px", borderRadius: "8px", color: "#fff", cursor: "pointer" }}
        >
          ➕ Add Global Question
        </button>
      </div>

      {/* SEARCH & CATEGORY FILTER BAR */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        
        {/* CATEGORY TABS */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {["All", "HR", "Behavioral", "Technical", "Coding", "System Design"].map(cat => (
            <button
              key={cat}
              className={`btn btn-xs ${activeCat === cat ? "btn-cyan" : "btn-ghost"}`}
              onClick={() => setActiveCat(cat)}
              style={{
                fontWeight: 800,
                padding: "6px 14px",
                borderRadius: "6px",
                border: activeCat === cat ? "none" : "1px solid rgba(255,255,255,0.1)",
                background: activeCat === cat ? "linear-gradient(135deg, #00c4a7, #7c4fe0)" : "rgba(255,255,255,0.03)",
                color: "#fff",
                cursor: "pointer"
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* SEARCH INPUT */}
        <div style={{ position: "relative", minWidth: "240px" }}>
          <input
            type="text"
            placeholder="Search questions or solutions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              background: "#0c1220",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "8px",
              padding: "8px 12px 8px 32px",
              color: "#fff",
              fontSize: "12px",
              outline: "none"
            }}
          />
          <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "#94a3b8", fontSize: "12px" }}>🔍</span>
        </div>
      </div>

      {/* QUESTION LIST */}
      {loading ? (
        <div style={{ color: "#ec4899", padding: "60px", textAlign: "center", fontWeight: 800 }}>
          ⚡ Loading master question bank...
        </div>
      ) : (
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          
          {filtered.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
              No global questions found matching the selected filters.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {filtered.map(q => (
                <div
                  key={q.id}
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    padding: "16px 18px",
                    borderRadius: "12px",
                    display: "flex",
                    justify: "space-between",
                    alignItems: "flex-start",
                    gap: "16px"
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "8px", marginBottom: "6px", alignItems: "center" }}>
                      <span className="pill pill-purple" style={{ fontSize: "10px", padding: "3px 8px", borderRadius: "4px", background: "rgba(139,92,246,0.15)", color: "#a78bfa", fontWeight: 800 }}>
                        {q.category || "Technical"}
                      </span>
                      
                      <span
                        style={{
                          fontSize: "10px",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          fontWeight: 800,
                          background: q.difficulty === 'Hard' ? 'rgba(239,68,68,0.15)' : q.difficulty === 'Medium' ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
                          color: q.difficulty === 'Hard' ? '#f87171' : q.difficulty === 'Medium' ? '#f59e0b' : '#10b981'
                        }}
                      >
                        {q.difficulty || "Medium"}
                      </span>

                      <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 700 }}>
                        ID: {q.id}
                      </span>
                    </div>

                    <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff", lineHeight: 1.4 }}>
                      {q.title}
                    </div>

                    {q.solution && (
                      <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "8px", background: "rgba(0,196,167,0.06)", borderLeft: "3px solid #00c4a7", padding: "6px 10px", borderRadius: "0 6px 6px 0" }}>
                        💡 <strong style={{ color: "#00c4a7" }}>Solution / Evaluation Guide:</strong> {q.solution}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      className="btn btn-ghost btn-xs"
                      onClick={() => setEditingQ(q)}
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}
                    >
                      ✏️ Edit
                    </button>
                    
                    <button
                      className="btn btn-danger btn-xs"
                      onClick={() => handleDelete(q.id)}
                      style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", color: "#f87171", padding: "6px 12px", borderRadius: "6px", fontSize: "11px", cursor: "pointer", fontWeight: 700 }}
                    >
                      🗑 Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ADD QUESTION MODAL */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(236,72,153,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "540px", width: "100%", color: "#fff" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px", margin: 0 }}>➕ Add Question to Global Master Bank</h3>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>This question will immediately become available across all institutional admin question pools.</p>

            <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Question Prompt *</label>
                <textarea
                  rows="3"
                  required
                  value={newQ.title}
                  onChange={e => setNewQ({ ...newQ, title: e.target.value })}
                  placeholder="e.g. Design a High-Throughput Distributed Rate Limiter..."
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Category</label>
                  <select
                    value={newQ.category}
                    onChange={e => setNewQ({ ...newQ, category: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="HR">HR</option>
                    <option value="Behavioral">Behavioral</option>
                    <option value="Technical">Technical</option>
                    <option value="Coding">Coding</option>
                    <option value="System Design">System Design</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Difficulty</label>
                  <select
                    value={newQ.difficulty}
                    onChange={e => setNewQ({ ...newQ, difficulty: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Suggested Solution / Evaluation Criteria</label>
                <textarea
                  rows="3"
                  value={newQ.solution}
                  onChange={e => setNewQ({ ...newQ, solution: e.target.value })}
                  placeholder="Key evaluation points, time complexity, or model answer..."
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setShowAdd(false)}
                  style={{ background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: "linear-gradient(135deg, #ec4899, #8b5cf6)", border: "none", color: "#fff", padding: "8px 18px", borderRadius: "8px", cursor: "pointer", fontWeight: 800 }}
                >
                  Save Global Question
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT QUESTION MODAL */}
      {editingQ && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(139,92,246,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "540px", width: "100%", color: "#fff" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px", margin: 0 }}>✏️ Edit Global Question</h3>

            <form onSubmit={handleSaveEdit} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Question Prompt *</label>
                <textarea
                  rows="3"
                  required
                  value={editingQ.title}
                  onChange={e => setEditingQ({ ...editingQ, title: e.target.value })}
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Category</label>
                  <select
                    value={editingQ.category}
                    onChange={e => setEditingQ({ ...editingQ, category: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="HR">HR</option>
                    <option value="Behavioral">Behavioral</option>
                    <option value="Technical">Technical</option>
                    <option value="Coding">Coding</option>
                    <option value="System Design">System Design</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Difficulty</label>
                  <select
                    value={editingQ.difficulty}
                    onChange={e => setEditingQ({ ...editingQ, difficulty: e.target.value })}
                    style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", outline: "none" }}
                  >
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", fontWeight: 700, marginBottom: "4px" }}>Suggested Solution / Evaluation Criteria</label>
                <textarea
                  rows="3"
                  value={editingQ.solution || ''}
                  onChange={e => setEditingQ({ ...editingQ, solution: e.target.value })}
                  placeholder="Key evaluation points or model answer..."
                  style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "10px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setEditingQ(null)}
                  style={{ background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 700 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", color: "#fff", padding: "8px 18px", borderRadius: "8px", cursor: "pointer", fontWeight: 800 }}
                >
                  Update Question
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
