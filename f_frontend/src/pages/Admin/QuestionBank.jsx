import React, { useState, useEffect } from 'react';
import { getAdminQuestionBank, createAdminQuestion, updateAdminQuestion, deleteAdminQuestion } from '../../services/adminAPI';

export default function QuestionBank() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [editingQ, setEditingQ] = useState(null);

  const [newQ, setNewQ] = useState({ title: '', category: 'Technical', difficulty: 'Medium', solution: '' });

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
      setNewQ({ title: '', category: 'Technical', difficulty: 'Medium', solution: '' });
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

  const filtered = questions.filter(q => activeCat === "All" || q.category === activeCat);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
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
            {filtered.map(q => (
              <div key={q.id} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", padding: "14px 16px", borderRadius: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
                    <span className="pill pill-purple" style={{ fontSize: "10px" }}>{q.category}</span>
                    <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{q.difficulty}</span>
                  </div>
                  <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff" }}>{q.title}</div>
                  {q.solution && <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "4px" }}>💡 {q.solution}</div>}
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button className="btn btn-ghost btn-xs" onClick={() => setEditingQ(q)}>✏️ Edit</button>
                  <button className="btn btn-danger btn-xs" onClick={() => handleDelete(q.id)}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ADD QUESTION MODAL */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "520px", width: "100%", color: "#fff" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>📚 Add Question to Bank</h3>
            <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Question Prompt *</label>
                <textarea rows="3" required value={newQ.title} onChange={e => setNewQ({ ...newQ, title: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
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
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "520px", width: "100%", color: "#fff" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>✏️ Edit Question</h3>
            <form onSubmit={handleSaveEdit} style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px" }}>Question Prompt *</label>
                <textarea rows="3" required value={editingQ.title} onChange={e => setEditingQ({ ...editingQ, title: e.target.value })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
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

