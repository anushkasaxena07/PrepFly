import React, { useState, useEffect } from 'react';
import { getAdminCodingTests, createAdminCodingTest, getAdminCodingLeaderboard, downloadCodingLeaderboardCSV, generateAdminCodingTestCases } from '../../services/adminAPI';

export default function Coding() {
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  
  // Leaderboard modal state
  const [selectedTest, setSelectedTest] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);

  // Test Case Editor Tab in Modal
  const [testCaseTab, setTestCaseTab] = useState('hidden'); // 'visible' | 'hidden'
  const [generatingAI, setGeneratingAI] = useState(false);
  const [templateLangTab, setTemplateLangTab] = useState('python');

  const [newTest, setNewTest] = useState({
    title: '',
    description: '',
    duration: 60,
    time_limit_sec: 2,
    language: 'Python 3',
    difficulty: 'Medium',
    visible_tests: 3,
    hidden_tests: 7,
    sample_input: 'nums = [2, 7, 11, 15], target = 9',
    sample_output: '[0, 1]',
    visible_test_cases: [
      { input: 'nums = [2, 7, 11, 15], target = 9', output: '[0, 1]', description: 'Sample Test 1' },
      { input: 'nums = [3, 2, 4], target = 6', output: '[1, 2]', description: 'Sample Test 2' },
      { input: 'nums = [3, 3], target = 6', output: '[0, 1]', description: 'Sample Test 3' }
    ],
    hidden_test_cases: [
      { input: 'nums = [-1, -8, 0, 5], target = -9', output: '[0, 1]', description: 'Edge Case 1: Negative numbers' },
      { input: 'nums = [100000, 500000, 200000], target = 700000', output: '[1, 2]', description: 'Edge Case 2: Large integers' },
      { input: 'nums = [0, 4, 3, 0], target = 0', output: '[0, 3]', description: 'Edge Case 3: Zero values' },
      { input: 'nums = [5, 5, 5, 5], target = 10', output: '[0, 1]', description: 'Edge Case 4: Duplicate elements' },
      { input: 'nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], target = 19', output: '[8, 9]', description: 'Edge Case 5: Larger array bounds' },
      { input: 'nums = [-10, 20, -30, 40], target = 10', output: '[0, 1]', description: 'Edge Case 6: Mixed sign values' },
      { input: 'nums = [100], target = 100', output: '[]', description: 'Edge Case 7: Single element boundary' }
    ],
    starter_code: {
      python: "def solve(nums, target):\n    # Write Python 3 code here\n    pass\n",
      javascript: "function solve(nums, target) {\n    // Write JavaScript code here\n    \n}\n",
      cpp: "class Solution {\npublic:\n    vector<int> solve(vector<int>& nums, int target) {\n        // Write C++ code here\n        return {};\n    }\n};\n",
      java: "class Solution {\n    public int[] solve(int[] nums, int target) {\n        // Write Java code here\n        return new int[]{};\n    }\n}\n"
    },
    constraints: 'Time: 2.0s | Memory: 256MB'
  });

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      const data = await getAdminCodingTests();
      setTests(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await createAdminCodingTest(newTest);
      setShowModal(false);
      fetchTests();
      setNewTest({
        title: '',
        description: '',
        duration: 60,
        time_limit_sec: 2,
        language: 'Python 3',
        difficulty: 'Medium',
        visible_tests: 3,
        hidden_tests: 7,
        sample_input: 'nums = [2, 7, 11, 15], target = 9',
        sample_output: '[0, 1]',
        visible_test_cases: [],
        hidden_test_cases: [],
        starter_code: {
          python: "def solve(nums, target):\n    # Write Python 3 code here\n    pass\n",
          javascript: "function solve(nums, target) {\n    // Write JavaScript code here\n    \n}\n",
          cpp: "class Solution {\npublic:\n    vector<int> solve(vector<int>& nums, int target) {\n        // Write C++ code here\n        return {};\n    }\n};\n",
          java: "class Solution {\n    public int[] solve(int[] nums, int target) {\n        // Write Java code here\n        return new int[]{};\n    }\n}\n"
        },
        constraints: 'Time: 2.0s | Memory: 256MB'
      });
    } catch (e) {
      alert("Failed to create coding test");
    }
  };

  const handleAIGenerateTestCases = async () => {
    if (!newTest.title && !newTest.description) {
      alert("Please enter a Challenge Title or Description first so AI can generate relevant test cases.");
      return;
    }
    setGeneratingAI(true);
    try {
      const res = await generateAdminCodingTestCases({
        title: newTest.title,
        description: newTest.description,
        visible_tests: newTest.visible_tests,
        hidden_tests: newTest.hidden_tests,
        sample_input: newTest.sample_input,
        sample_output: newTest.sample_output
      });

      if (res.visible_test_cases && res.hidden_test_cases) {
        setNewTest({
          ...newTest,
          visible_tests: res.visible_test_cases.length,
          hidden_tests: res.hidden_test_cases.length,
          visible_test_cases: res.visible_test_cases,
          hidden_test_cases: res.hidden_test_cases
        });
      }
    } catch (e) {
      alert("Failed to auto-generate AI test cases");
    } finally {
      setGeneratingAI(false);
    }
  };

  const handleTestCaseChange = (type, index, field, value) => {
    const listKey = type === 'visible' ? 'visible_test_cases' : 'hidden_test_cases';
    const list = [...newTest[listKey]];
    list[index] = { ...list[index], [field]: value };
    setNewTest({
      ...newTest,
      [listKey]: list
    });
  };

  const handleAddTestCase = (type) => {
    const listKey = type === 'visible' ? 'visible_test_cases' : 'hidden_test_cases';
    const countKey = type === 'visible' ? 'visible_tests' : 'hidden_tests';
    const list = [...newTest[listKey]];
    list.push({ input: '', output: '', description: `${type === 'visible' ? 'Visible' : 'Hidden Evaluation'} Test #${list.length + 1}` });
    setNewTest({
      ...newTest,
      [listKey]: list,
      [countKey]: list.length
    });
  };

  const handleRemoveTestCase = (type, index) => {
    const listKey = type === 'visible' ? 'visible_test_cases' : 'hidden_test_cases';
    const countKey = type === 'visible' ? 'visible_tests' : 'hidden_tests';
    const list = newTest[listKey].filter((_, i) => i !== index);
    setNewTest({
      ...newTest,
      [listKey]: list,
      [countKey]: list.length
    });
  };

  const handleDownloadCSV = async (testId) => {
    try {
      await downloadCodingLeaderboardCSV(testId);
    } catch (e) {
      console.error("CSV Download error:", e);
      alert("Failed to download CSV leaderboard.");
    }
  };

  const handleOpenSubmissions = async (test) => {
    setSelectedTest(test);
    setLoadingLeaderboard(true);
    try {
      const data = await getAdminCodingLeaderboard(test.id);
      setLeaderboard(data || []);
    } catch (e) {
      console.error("Fetch leaderboard error:", e);
    } finally {
      setLoadingLeaderboard(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", margin: 0 }}>💻 Coding Test & Assessment Manager</h2>
          <p style={{ fontSize: "12px", color: "var(--text2)", marginTop: "2px" }}>Create automated coding challenges, configure hidden test cases, and inspect student leaderboards.</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)} style={{ background: "linear-gradient(135deg, #7c4fe0, #00c4a7)", border: "none", fontWeight: 800 }}>
          ➕ Create Coding Challenge
        </button>
      </div>

      {loading ? (
        <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Loading coding tests...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
          {tests.map((t) => (
            <div key={t.id} className="card" style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span className="pill pill-cyan" style={{ fontSize: "10px" }}>{t.difficulty}</span>
                <span style={{ fontSize: "11px", color: "var(--cyan)", fontWeight: 700 }}>⏱ {t.duration} Mins</span>
              </div>

              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#fff", margin: "0 0 6px 0" }}>{t.title}</h3>
              <div style={{ fontSize: "12px", color: "var(--text2)", marginBottom: "12px" }}>Supported Languages: <strong style={{ color: "#fff" }}>{t.language}</strong></div>

              <div style={{ background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", fontSize: "11px", display: "flex", justifyContent: "space-between", marginBottom: "14px" }}>
                <div>Visible Tests: <strong>{t.visible_tests || (t.visible_test_cases ? t.visible_test_cases.length : 3)}</strong></div>
                <div>Hidden Tests: <strong>{t.hidden_tests || (t.hidden_test_cases ? t.hidden_test_cases.length : 7)}</strong></div>
                <div>Acceptance: <strong style={{ color: "#00c4a7" }}>{t.accepted_rate || "84%"}</strong></div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <button className="btn btn-ghost btn-xs" onClick={() => handleDownloadCSV(t.id)}>
                  📊 Leaderboard CSV
                </button>
                <button className="btn btn-ghost btn-xs" onClick={() => handleOpenSubmissions(t)}>
                  👁 Submissions
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SUBMISSIONS LEADERBOARD MODAL */}
      {selectedTest && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "800px", width: "100%", maxHeight: "85vh", display: "flex", flexDirection: "column", color: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>🏆 Student Submissions & Leaderboard</h3>
                <p style={{ fontSize: "12px", color: "var(--text2)", margin: "2px 0 0 0" }}>Test: <strong style={{ color: "var(--cyan)" }}>{selectedTest.title}</strong></p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="btn btn-primary btn-xs" onClick={() => handleDownloadCSV(selectedTest.id)} style={{ background: "linear-gradient(135deg,#7c4fe0,#00c4a7)", border: "none", fontWeight: 800 }}>
                  📥 Download CSV
                </button>
                <button className="btn btn-ghost btn-xs" onClick={() => setSelectedTest(null)}>✕ Close</button>
              </div>
            </div>

            {loadingLeaderboard ? (
              <div style={{ color: "var(--cyan)", padding: "40px", textAlign: "center" }}>⚡ Fetching candidate submissions...</div>
            ) : leaderboard.length === 0 ? (
              <div style={{ color: "var(--text2)", padding: "30px", textAlign: "center" }}>No student submissions recorded for this test yet.</div>
            ) : (
              <div style={{ overflowY: "auto", flex: 1 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--text2)", fontSize: "11px", textTransform: "uppercase" }}>
                      <th style={{ padding: "10px 8px" }}>Rank</th>
                      <th style={{ padding: "10px 8px" }}>Candidate Name</th>
                      <th style={{ padding: "10px 8px" }}>Roll No</th>
                      <th style={{ padding: "10px 8px" }}>Department</th>
                      <th style={{ padding: "10px 8px" }}>Score (%)</th>
                      <th style={{ padding: "10px 8px" }}>Test Cases</th>
                      <th style={{ padding: "10px 8px" }}>Language</th>
                      <th style={{ padding: "10px 8px" }}>Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((r, idx) => (
                      <tr key={r.id || idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <td style={{ padding: "10px 8px", fontWeight: 800, color: idx === 0 ? "#ffb800" : idx === 1 ? "#00c4a7" : "var(--text2)" }}>#{idx + 1}</td>
                        <td style={{ padding: "10px 8px", fontWeight: 700, color: "#fff" }}>{r.student_name}</td>
                        <td style={{ padding: "10px 8px", color: "var(--text2)" }}>{r.roll_number}</td>
                        <td style={{ padding: "10px 8px", color: "var(--text2)" }}>{r.department}</td>
                        <td style={{ padding: "10px 8px", fontWeight: 800, color: r.score_pct >= 80 ? "#00c4a7" : r.score_pct >= 60 ? "#ffb800" : "#ff4d4f" }}>{r.score_pct}%</td>
                        <td style={{ padding: "10px 8px" }}>{r.passed}/{r.total}</td>
                        <td style={{ padding: "10px 8px", color: "var(--cyan)" }}>{r.language}</td>
                        <td style={{ padding: "10px 8px", fontSize: "11px", color: "var(--text2)" }}>{r.submitted_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "16px", padding: "24px", maxWidth: "780px", width: "100%", maxHeight: "90vh", overflowY: "auto", color: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>💻 Create Coding Challenge</h3>
              <button className="btn btn-ghost btn-xs" onClick={() => setShowModal(false)}>✕ Close</button>
            </div>

            <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              
              {/* TITLE & DIFFICULTY */}
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Challenge Title *</label>
                  <input type="text" required value={newTest.title} onChange={e => setNewTest({ ...newTest, title: e.target.value })} placeholder="e.g. Dynamic Programming & Subarrays" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Difficulty Level *</label>
                  <select value={newTest.difficulty} onChange={e => setNewTest({ ...newTest, difficulty: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              {/* PROBLEM DESCRIPTION */}
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Problem Description & Input/Output Specs</label>
                <textarea rows="3" value={newTest.description} onChange={e => setNewTest({ ...newTest, description: e.target.value })} placeholder="Write problem statement, input formats, constraints, and instructions for candidates..." style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>

              {/* TIMINGS & LANGUAGES */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Total Duration (Mins) *</label>
                  <input type="number" required min="5" max="300" value={newTest.duration} onChange={e => setNewTest({ ...newTest, duration: Number(e.target.value) })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Execution Limit (Secs)</label>
                  <input type="number" required min="1" max="15" value={newTest.time_limit_sec} onChange={e => setNewTest({ ...newTest, time_limit_sec: Number(e.target.value) })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
                </div>
                <div>
                  <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Allowed Language</label>
                  <select value={newTest.language} onChange={e => setNewTest({ ...newTest, language: e.target.value })} style={{ width: "100%", background: "#141d30", color: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px" }}>
                    <option value="Python 3">Python 3</option>
                    <option value="C++">C++</option>
                    <option value="Java 17">Java 17</option>
                    <option value="JavaScript Node">JavaScript Node</option>
                    <option value="Multi-Language">Multi-Language (All)</option>
                  </select>
                </div>
              </div>

              {/* TEST CASE CONFIGURATION HEADER & AI AUTO GENERATE BUTTON */}
              <div style={{ background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "12px", padding: "14px", marginTop: "4px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <div>
                    <strong style={{ fontSize: "14px", color: "#fff" }}>🧪 Test Cases & Automated Evaluation Suite</strong>
                    <div style={{ fontSize: "11px", color: "var(--text2)" }}>Configure visible sample test cases and hidden edge-case evaluation inputs.</div>
                  </div>
                  <button 
                    type="button" 
                    className="btn btn-xs" 
                    onClick={handleAIGenerateTestCases}
                    disabled={generatingAI}
                    style={{ background: "linear-gradient(135deg, #00c4a7, #7c3aed)", border: "none", color: "#fff", fontWeight: 800, padding: "6px 12px" }}
                  >
                    {generatingAI ? "⚡ Auto-Generating AI Cases..." : "🤖 Auto-Generate All Test Cases with AI"}
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                  <div>
                    <label style={{ display: "block", color: "var(--cyan)", marginBottom: "4px", fontWeight: 700, fontSize: "12px" }}>Visible Test Cases Count</label>
                    <input type="number" min="1" max="20" value={newTest.visible_tests} onChange={e => setNewTest({ ...newTest, visible_tests: Number(e.target.value) })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "6px 10px", color: "#fff" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "#a855f7", marginBottom: "4px", fontWeight: 700, fontSize: "12px" }}>Hidden Evaluation Test Cases</label>
                    <input type="number" min="0" max="50" value={newTest.hidden_tests} onChange={e => setNewTest({ ...newTest, hidden_tests: Number(e.target.value) })} style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "6px 10px", color: "#fff" }} />
                  </div>
                </div>

                {/* TEST CASE MANAGEMENT TABS */}
                <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px", marginBottom: "12px" }}>
                  <button 
                    type="button" 
                    onClick={() => setTestCaseTab('hidden')}
                    style={{ 
                      background: testCaseTab === 'hidden' ? "rgba(168,85,247,0.25)" : "transparent", 
                      border: testCaseTab === 'hidden' ? "1px solid #a855f7" : "none", 
                      color: testCaseTab === 'hidden' ? "#fff" : "var(--text2)", 
                      borderRadius: "6px", 
                      padding: "6px 12px", 
                      fontSize: "12px", 
                      fontWeight: 800, 
                      cursor: "pointer" 
                    }}
                  >
                    🔒 Hidden Evaluation Cases ({newTest.hidden_test_cases.length || newTest.hidden_tests})
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setTestCaseTab('visible')}
                    style={{ 
                      background: testCaseTab === 'visible' ? "rgba(0,196,167,0.25)" : "transparent", 
                      border: testCaseTab === 'visible' ? "1px solid #00c4a7" : "none", 
                      color: testCaseTab === 'visible' ? "#fff" : "var(--text2)", 
                      borderRadius: "6px", 
                      padding: "6px 12px", 
                      fontSize: "12px", 
                      fontWeight: 800, 
                      cursor: "pointer" 
                    }}
                  >
                    👁 Visible Cases ({newTest.visible_test_cases.length || newTest.visible_tests})
                  </button>
                </div>

                {/* ACTIVE TEST CASES LIST EDITOR */}
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "220px", overflowY: "auto", paddingRight: "4px" }}>
                  {(testCaseTab === 'visible' ? newTest.visible_test_cases : newTest.hidden_test_cases).map((tc, idx) => (
                    <div key={idx} style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.08)", padding: "10px", borderRadius: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 800, color: testCaseTab === 'visible' ? "var(--cyan)" : "#a855f7" }}>
                          #{idx + 1} {tc.description || (testCaseTab === 'visible' ? 'Visible Sample Case' : 'Hidden Evaluation Case')}
                        </span>
                        <button type="button" onClick={() => handleRemoveTestCase(testCaseTab, idx)} style={{ background: "none", border: "none", color: "#ff4d4f", cursor: "pointer", fontSize: "12px", fontWeight: 800 }}>✕ Remove</button>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                        <textarea 
                          rows="1" 
                          value={tc.input} 
                          onChange={e => handleTestCaseChange(testCaseTab, idx, 'input', e.target.value)} 
                          placeholder="Input (e.g. nums = [-1, 0, 5], target = -1)" 
                          style={{ background: "#141d30", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "4px 8px", color: "#fff", fontSize: "11px", fontFamily: "monospace" }} 
                        />
                        <textarea 
                          rows="1" 
                          value={tc.output} 
                          onChange={e => handleTestCaseChange(testCaseTab, idx, 'output', e.target.value)} 
                          placeholder="Expected Output (e.g. [0, 1])" 
                          style={{ background: "#141d30", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "4px 8px", color: "#fff", fontSize: "11px", fontFamily: "monospace" }} 
                        />
                      </div>
                    </div>
                  ))}

                  <button 
                    type="button" 
                    onClick={() => handleAddTestCase(testCaseTab)}
                    style={{ background: "rgba(255,255,255,0.05)", border: "1px dashed rgba(255,255,255,0.2)", color: "#fff", padding: "6px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
                  >
                    ➕ Add Custom {testCaseTab === 'visible' ? 'Visible' : 'Hidden Evaluation'} Test Case
                  </button>
                </div>

              </div>

              {/* STARTER CODE TEMPLATE */}
              <div style={{ background: "rgba(0,240,200,0.03)", border: "1px solid rgba(0,240,200,0.15)", borderRadius: "12px", padding: "14px" }}>
                <strong style={{ fontSize: "14px", color: "#fff", display: "block", marginBottom: "4px" }}>💻 Starter Code Template Editor</strong>
                <div style={{ fontSize: "11px", color: "var(--text2)", marginBottom: "10px" }}>Set the initial code boilerplate candidates see when loading the problem in the IDE.</div>
                
                <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
                  {['python', 'javascript', 'cpp', 'java'].map(lang => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setTemplateLangTab(lang)}
                      style={{
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontWeight: 800,
                        borderRadius: "6px",
                        border: "none",
                        cursor: "pointer",
                        background: templateLangTab === lang ? "var(--cyan)" : "rgba(255,255,255,0.05)",
                        color: templateLangTab === lang ? "#000" : "var(--text2)"
                      }}
                    >
                      {lang.toUpperCase()}
                    </button>
                  ))}
                </div>
                <textarea
                  rows="5"
                  value={newTest.starter_code[templateLangTab] || ""}
                  onChange={e => {
                    const updatedStarter = { ...newTest.starter_code, [templateLangTab]: e.target.value };
                    setNewTest({ ...newTest, starter_code: updatedStarter });
                  }}
                  placeholder={`Write the starter template code that candidates will see in the editor for ${templateLangTab}...`}
                  style={{ width: "100%", background: "#141d30", fontFamily: "monospace", fontSize: "12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff", resize: "vertical", lineHeight: "1.5" }}
                />
              </div>

              {/* CONSTRAINTS */}
              <div>
                <label style={{ display: "block", color: "var(--text2)", marginBottom: "4px", fontWeight: 700 }}>Execution Constraints</label>
                <input type="text" value={newTest.constraints} onChange={e => setNewTest({ ...newTest, constraints: e.target.value })} placeholder="e.g. 1 <= N <= 10^5, Time: 2.0s | Memory: 256MB" style={{ width: "100%", background: "#141d30", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }} />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg,#7c4fe0,#00c4a7)", border: "none", fontWeight: 800 }}>
                  🚀 Save & Launch Coding Challenge
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}

