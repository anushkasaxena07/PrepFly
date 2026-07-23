import React, { useState, useEffect } from 'react';
import { getAdminQuestionBank, createAdminQuestion, updateAdminQuestion, deleteAdminQuestion, giveAdminQuestion } from '../../services/adminAPI';

export default function QuestionBank() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [editingQ, setEditingQ] = useState(null);
  const [toast, setToast] = useState("");

  const [newQ, setNewQ] = useState({
    title: '',
    category: 'Technical',
    difficulty: 'Medium',
    description: '',
    starter_code: '',
    test_cases: '',
    solution: '',
    constraints: ''
  });

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const data = await getAdminQuestionBank();
      setQuestions(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    try {
      await createAdminQuestion(newQ);
      setShowAdd(false);
      setNewQ({
        title: '',
        category: 'Technical',
        difficulty: 'Medium',
        description: '',
        starter_code: '',
        test_cases: '',
        solution: '',
        constraints: ''
      });
      fetchQuestions();
    } catch (e) {
      alert("Failed to add question");
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingQ) return;
    try {
      await updateAdminQuestion(editingQ.id, editingQ);
      setEditingQ(null);
      fetchQuestions();
    } catch (e) {
      alert("Failed to update question");
    }
  };

  const handleDelete = async (qId) => {
    if (!window.confirm("Are you sure you want to delete this question from the Question Bank?")) return;
    try {
      await deleteAdminQuestion(qId);
      fetchQuestions();
    } catch (e) {
      alert("Failed to delete question");
    }
  };

  const handleGive = async (qId) => {
    try {
      await giveAdminQuestion(qId);
      setToast("🎯 Question successfully assigned & student notifications updated!");
      setTimeout(() => setToast(""), 4000);
    } catch (e) {
      alert(e.message || "Failed to assign question");
    }
  };

  const filtered = questions.filter(q => activeCat === "All" || q.category === activeCat);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {toast && (
        <div style={{ position: "fixed", top: "20px", right: "20px", background: "linear-gradient(135deg, #00c4a7, #7c4fe0)", color: "#fff", padding: "12px 20px", borderRadius: "10px", fontWeight: 800, zIndex: 2000, boxShadow: "0 10px 30px rgba(0,0,0,0.3)" }}>
          {toast}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>📚 Central Question Bank</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Curate technical, HR, behavioral, and algorithmic questions for your organization.</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowAdd(true)} style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
          ➕ Add Question
        </button>
      </div>

      {/* CATEGORY TABS */}
      <div style={{ display: "flex", gap: "8px" }}>
        {["All", "HR", "Technical", "Behavioral", "Coding"].map(cat => (
          <button 
            key={cat} 
            className={`btn btn-xs ${activeCat === cat ? "btn-cyan" : "btn-ghost"}`}
            onClick={() => setActiveCat(cat)}
            style={{ fontWeight: 800 }}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading question bank...</div>
      ) : (
        <div className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {filtered.length === 0 ? (
              <div style={{ color: "var(--text3)", textAlign: "center", padding: "20px", fontSize: "13px" }}>No questions found in this category.</div>
            ) : (
              filtered.map(q => (
                <div key={q.id} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", padding: "14px 16px", borderRadius: "12px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                  <div style={{ flex: 1, minWidth: "250px" }}>
                    <div style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
                      <span className="pill pill-purple" style={{ fontSize: "10px" }}>{q.category}</span>
                      <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{q.difficulty}</span>
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff" }}>{q.title}</div>
                    {q.description && <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>{q.description.substring(0, 100)}{q.description.length > 100 ? "..." : ""}</div>}
                    {q.solution && <div style={{ fontSize: "11px", color: "var(--cyan)", marginTop: "4px" }}>💡 Solution: {q.solution.substring(0, 80)}{q.solution.length > 80 ? "..." : ""}</div>}
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button className="btn btn-xs" onClick={() => handleGive(q.id)} style={{ background: "rgba(0,196,167,0.15)", border: "1px solid #00c4a7", color: "#00e1bf", fontWeight: 800 }}>
                      📤 Give to Students
                    </button>
                    <button className="btn btn-ghost btn-xs" onClick={() => setEditingQ(q)}>✏️ Edit</button>
                    <button className="btn btn-danger btn-xs" onClick={() => handleDelete(q.id)}>🗑</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ADD QUESTION MODAL */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "600px", width: "100%", color: "#fff", maxHeight: "90vh", overflowY: "auto" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>📚 Add Question to Bank</h3>
            <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Question Title *</label>
                <input type="text" required value={newQ.title} onChange={e => setNewQ({ ...newQ, title: e.target.value })} placeholder="e.g. Valid Parentheses" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Category</label>
                  <select value={newQ.category} onChange={e => setNewQ({ ...newQ, category: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="HR">HR</option>
                    <option value="Technical">Technical</option>
                    <option value="Behavioral">Behavioral</option>
                    <option value="Coding">Coding</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Difficulty</label>
                  <select value={newQ.difficulty} onChange={e => setNewQ({ ...newQ, difficulty: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Detailed Description *</label>
                <textarea rows="3" required value={newQ.description} onChange={e => setNewQ({ ...newQ, description: e.target.value })} placeholder="Enter detailed question prompt, parameters, and instruction details..." style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>

              {newQ.category === "Coding" && (
                <>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Constraints (Optional)</label>
                    <textarea rows="2" value={newQ.constraints} onChange={e => setNewQ({ ...newQ, constraints: e.target.value })} placeholder="e.g. 1 <= s.length <= 10^4" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#e2e8f0", fontFamily: "monospace" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Starter Code / Template</label>
                    <textarea rows="3" value={newQ.starter_code} onChange={e => setNewQ({ ...newQ, starter_code: e.target.value })} placeholder="def isValid(s: str) -> bool:&#10;    # Write code here&#10;    pass" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#00ffcc", fontFamily: "monospace" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Test Cases (JSON format) *</label>
                    <textarea rows="4" required value={newQ.test_cases} onChange={e => setNewQ({ ...newQ, test_cases: e.target.value })} placeholder='[&#10;  {"input": "\"()\"", "output": "true", "is_hidden": false},&#10;  {"input": "\"(]\"", "output": "false", "is_hidden": false},&#10;  {"input": "\"]\"", "output": "false", "is_hidden": true}&#10;]' style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#e2e8f0", fontFamily: "monospace" }} />
                  </div>
                </>
              )}

              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Suggested Answer / Solution Guide</label>
                <textarea rows="2" value={newQ.solution} onChange={e => setNewQ({ ...newQ, solution: e.target.value })} placeholder="Key evaluation points or model answer..." style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>Save Question</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT QUESTION MODAL */}
      {editingQ && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "600px", width: "100%", color: "#fff", maxHeight: "90vh", overflowY: "auto" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>✏️ Edit Question</h3>
            <form onSubmit={handleSaveEdit} style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Question Title *</label>
                <input type="text" required value={editingQ.title} onChange={e => setEditingQ({ ...editingQ, title: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Category</label>
                  <select value={editingQ.category} onChange={e => setEditingQ({ ...editingQ, category: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="HR">HR</option>
                    <option value="Technical">Technical</option>
                    <option value="Behavioral">Behavioral</option>
                    <option value="Coding">Coding</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Difficulty</label>
                  <select value={editingQ.difficulty} onChange={e => setEditingQ({ ...editingQ, difficulty: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Detailed Description *</label>
                <textarea rows="3" required value={editingQ.description || ''} onChange={e => setEditingQ({ ...editingQ, description: e.target.value })} placeholder="Enter detailed question prompt..." style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>

              {editingQ.category === "Coding" && (
                <>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Constraints (Optional)</label>
                    <textarea rows="2" value={editingQ.constraints || ''} onChange={e => setEditingQ({ ...editingQ, constraints: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#e2e8f0", fontFamily: "monospace" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Starter Code / Template</label>
                    <textarea rows="3" value={editingQ.starter_code || ''} onChange={e => setEditingQ({ ...editingQ, starter_code: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#00ffcc", fontFamily: "monospace" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Test Cases (JSON format) *</label>
                    <textarea rows="4" required value={editingQ.test_cases || ''} onChange={e => setEditingQ({ ...editingQ, test_cases: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#e2e8f0", fontFamily: "monospace" }} />
                  </div>
                </>
              )}

              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Suggested Answer / Solution Guide</label>
                <textarea rows="2" value={editingQ.solution || ''} onChange={e => setEditingQ({ ...editingQ, solution: e.target.value })} placeholder="Key evaluation points or model answer..." style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" className="btn btn-ghost" onClick={() => setEditingQ(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>Update Question</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


