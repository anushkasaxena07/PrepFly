import React, { useState, useEffect, useRef } from 'react';

const defaultCodeTemplates = {
  python: `def twoSum(nums, target):
    # Write your code here
    pass
`,
  javascript: `function twoSum(nums, target) {
    // Write your code here
    
}
`,
  typescript: `function twoSum(nums: number[], target: number): number[] {
    // Write your code here
    return [];
}
`,
  java: `class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Write your code here
        return new int[]{};
    }
}
`,
  cpp: `#include <vector>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Write your code here
        return {};
    }
};
`,
  csharp: `public class Solution {
    public int[] TwoSum(int[] nums, int target) {
        // Write your code here
        return new int[]{};
    }
}
`,
  go: `func twoSum(nums []int, target int) []int {
    // Write your code here
    return []int{}
}
`,
  rust: `impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        // Write your code here
        vec![]
    }
}
`,
  php: `function twoSum($nums, $target) {
    // Write your code here
    return [];
}
`,
  ruby: `def two_sum(nums, target)
    # Write your code here
end
`,
  swift: `class Solution {
    func twoSum(_ nums: [Int], _ target: Int) -> [Int] {
        // Write your code here
        return []
    }
}
`,
  kotlin: `class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        // Write your code here
        return intArrayOf()
    }
}
`,
  sql: `-- Write your SQL query here
SELECT * FROM table_name;
`
};

export default function CodingTab({ apiFetch, isLoggedIn, user = {} }) {
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(defaultCodeTemplates.python);
  const [consoleOut, setConsoleOut] = useState("Ready to run...");
  const [consoleColor, setConsoleColor] = useState("var(--text2)");
  const [timeComplexity, setTimeComplexity] = useState("—");
  const [spaceComplexity, setSpaceComplexity] = useState("—");
  const [testPass, setTestPass] = useState("—");
  const [testPassColor, setTestPassColor] = useState("var(--text2)");
  const [aiReview, setAiReview] = useState("Run your code to get AI feedback on time complexity, space complexity, and edge cases.");
  const [hintBox, setHintBox] = useState("Click below to get a hint from your AI coach.");
  const [hintIdx, setHintIdx] = useState(0);

  // --- Coding Room and Sheet Upload States ---
  const [problems, setProblems] = useState([]);
  const [currentProblem, setCurrentProblem] = useState(null);
  
  const [roomId, setRoomId] = useState("");
  const [roomParticipants, setRoomParticipants] = useState([]);
  const [joinRoomInput, setJoinRoomInput] = useState("");
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [selectedSheetId, setSelectedSheetId] = useState("");
  const [sheetsList, setSheetsList] = useState([]); // tracks parsed sheets

  // Refs for typing state synchronization
  const lastTypedRef = useRef(Date.now());
  const isTypingRef = useRef(false);
  const syncIntervalRef = useRef(null);

  // 1. Fetch available problems on mount
  useEffect(() => {
    fetchProblems();
  }, []);

  const fetchProblems = async (sheetId = "") => {
    try {
      const url = sheetId ? `/api/coding/problems?sheet_id=${sheetId}` : '/api/coding/problems';
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        setProblems(data.problems || []);
        
        // Auto-select standard problem if none active
        if (!currentProblem && data.problems && data.problems.length > 0) {
          const twoSum = data.problems.find(p => p.problem_id === "two-sum") || data.problems[0];
          selectProblem(twoSum);
        }
      }
    } catch (e) {
      console.error("Error fetching problems:", e);
    }
  };

  // 2. Synchronization Polling loop
  useEffect(() => {
    if (roomId) {
      syncIntervalRef.current = setInterval(syncRoomState, 1500);
    } else {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    }
    return () => {
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
    };
  }, [roomId, code, lang]);

  const syncRoomState = async () => {
    if (!roomId) return;
    try {
      const payload = {
        room_id: roomId,
        user_id: user?._id || user?.user_id || "anonymous_user",
        cursor: getCursorPosition()
      };

      // Only send local code if we typed recently
      const timeSinceType = Date.now() - lastTypedRef.current;
      if (isTypingRef.current || timeSinceType < 2000) {
        payload.code = code;
        payload.lang = lang;
      }

      const res = await apiFetch('/api/coding/room/sync', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const data = await res.json();
        setRoomParticipants(data.participants || []);
        
        // If not typing, and server has newer/different code, update editor
        if (timeSinceType > 1500 && data.current_code !== code) {
          setCode(data.current_code);
          isTypingRef.current = false;
        }
        if (data.current_lang !== lang) {
          setLang(data.current_lang);
        }
      }
    } catch (err) {
      console.error("Room synchronization error:", err);
    }
  };

  const getCursorPosition = () => {
    const area = document.getElementById("code-textarea");
    if (!area) return null;
    const start = area.selectionStart;
    const lines = area.value.substring(0, start).split("\n");
    return { line: lines.length, ch: lines[lines.length - 1].length };
  };

  // 3. Selection of problem helper
  const selectProblem = (problem) => {
    setCurrentProblem(problem);
    setHintIdx(0);
    setHintBox("Click below to get a hint from your AI coach.");
    
    // Load starter code
    let starter = problem.starter_code || {};
    if (typeof starter === 'string') {
      try { starter = JSON.parse(starter); } catch(e) { starter = {}; }
    }
    
    const template = starter[lang] || starter["python"] || "";
    setCode(template);
  };

  const handleProblemChange = (e) => {
    const pid = e.target.value;
    const found = problems.find(p => p.problem_id === pid);
    if (found) {
      if (roomId) {
        // Assign new problem to room
        assignProblemToRoom(pid);
      } else {
        selectProblem(found);
      }
    }
  };

  const assignProblemToRoom = async (pid) => {
    try {
      const res = await apiFetch('/api/coding/room/assign-question', {
        method: 'POST',
        body: JSON.stringify({ room_id: roomId, problem_id: pid })
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        setLang(data.current_lang);
      }
    } catch (err) {
      console.error("Failed to assign problem to room:", err);
    }
  };

  // 4. Room operations
  const createRoom = async () => {
    try {
      const res = await apiFetch('/api/coding/room/create', {
        method: 'POST',
        body: JSON.stringify({
          user_id: user?._id || user?.user_id || "interviewer_user",
          user_name: user?.name || "Interviewer",
          problem_id: currentProblem?.problem_id,
          sheet_id: selectedSheetId
        })
      });
      if (res.ok) {
        const data = await res.json();
        setRoomId(data.room_id);
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        setLang(data.current_lang);
        setRoomParticipants(data.participants);
        setConsoleOut(`Joined Room ${data.room_id}. Editor synchronized!`);
      }
    } catch (err) {
      console.error("Create room error:", err);
    }
  };

  const joinRoom = async () => {
    const rId = joinRoomInput.trim().toUpperCase();
    if (!rId) return;
    try {
      const res = await apiFetch('/api/coding/room/join', {
        method: 'POST',
        body: JSON.stringify({
          room_id: rId,
          user_id: user?._id || user?.user_id || "candidate_user",
          user_name: user?.name || "Candidate",
          role: user?.role || "candidate"
        })
      });
      if (res.ok) {
        const data = await res.json();
        setRoomId(data.room_id);
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        setLang(data.current_lang);
        setRoomParticipants(data.participants);
        setConsoleOut(`Successfully joined Room ${data.room_id}!`);
      } else {
        const err = await res.json();
        alert(err.error || "Room not found");
      }
    } catch (err) {
      console.error("Join room error:", err);
    }
  };

  const leaveRoom = () => {
    setRoomId("");
    setRoomParticipants([]);
    setJoinRoomInput("");
    if (problems.length > 0) {
      selectProblem(problems[0]);
    }
    setConsoleOut("Left room. Local playground activated.");
  };

  // 5. Document Upload
  const handleSheetUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploading(true);
    setUploadError("");
    
    const formData = new FormData();
    formData.append("sheet", file);
    formData.append("user_id", user?._id || user?.user_id || "recruiter");
    
    try {
      const res = await apiFetch('/api/coding/upload-sheet', {
        method: "POST",
        body: formData
      });
      
      const data = await res.json();
      if (res.ok) {
        // Save sheet info to checklist
        setSheetsList(prev => [...prev, { id: data.sheet_id, name: data.filename }]);
        setSelectedSheetId(data.sheet_id);
        
        // Refresh problems list with parsed questions
        await fetchProblems(data.sheet_id);
        if (data.problems && data.problems.length > 0) {
          selectProblem(data.problems[0]);
        }
        
        alert(`Questions parsed successfully! Extracted ${data.problems.length} problems.`);
      } else {
        setUploadError(data.error || "Failed to parse document");
      }
    } catch (err) {
      setUploadError("Network error uploading sheet.");
    } finally {
      setIsUploading(false);
      e.target.value = ""; // reset file input
    }
  };

  // 6. Running Code & AI Hints
  const handleLangChange = (newLang) => {
    setLang(newLang);
    if (currentProblem) {
      let starter = currentProblem.starter_code || {};
      if (typeof starter === 'string') {
        try { starter = JSON.parse(starter); } catch(e) { starter = {}; }
      }
      setCode(starter[newLang] || defaultCodeTemplates[newLang] || "");
    }
  };

  const getHint = async () => {
    setHintBox("Getting hint...");
    try {
      const res = await apiFetch('/api/coding/hint', {
        method: 'POST',
        body: JSON.stringify({
          problem_id: currentProblem?.problem_id || 'two-sum',
          code: code,
          hint_index: hintIdx
        })
      });
      const data = await res.json();
      if (res.ok) {
        setHintBox('💡 ' + (data.hint || 'Analyze the constraints and loop conditions.'));
        setHintIdx(prev => prev + 1);
      }
    } catch (e) {
      setHintBox("Failed to get hint. Try thinking about optimal time limits.");
    }
  };

  const runCode = async () => {
    setConsoleOut("⏳ Compiling and running tests in secure sandbox environment...");
    setConsoleColor("var(--text2)");
    setTimeComplexity("—");
    setSpaceComplexity("—");
    setTestPass("—");
    setTestPassColor("var(--text2)");
    setAiReview("Analyzing logic...");

    try {
      const res = await apiFetch('/api/coding/submit', {
        method: 'POST',
        body: JSON.stringify({
          language: lang,
          code: code,
          problem_id: currentProblem?.problem_id || 'two-sum',
          user_id: user?._id || user?.user_id
        })
      });
      const d = await res.json();
      if (res.ok) {
        if (d.stderr) {
          setConsoleColor('var(--red)');
          setConsoleOut(`Error:\n${d.stderr}`);
          setTestPass("0/3");
          setTestPassColor('var(--red)');
          setAiReview(d.ai_review || "Code runner execution failed due to runtime exception.");
        } else {
          setConsoleColor(d.passed === d.total ? '#00d68f' : 'var(--orange)');
          setConsoleOut(d.stdout || 'Execution complete.');
          setTimeComplexity(d.time_complexity || '—');
          setSpaceComplexity(d.space_complexity || '—');
          setTestPass(`${d.passed}/${d.total}`);
          setTestPassColor(d.passed === d.total ? 'var(--cyan)' : 'var(--orange)');
          setAiReview(d.ai_review || 'No AI feedback generated.');
        }
      } else {
        setConsoleColor('var(--red)');
        setConsoleOut('Error: ' + (d.error || 'Execution sandbox error'));
      }
    } catch(e) {
      setConsoleColor('var(--red)');
      setConsoleOut('Execution error: Network connection timeout.');
    }
  };

  return (
    <div id="page-coding" className="page active" role="tabpanel">
      <div className="container">
        
        {/* Header */}
        <div className="sec-header mb16">
          <div className="flex items-center gap8">
            <h1 className="sec-title" style={{fontSize:"18px"}}>Coding Room</h1>
            <span className="pill pill-cyan">{roomId ? `Room ${roomId}` : "Local Playground"}</span>
            {roomId && <span className="pill pill-purple">Sync Polling Active</span>}
          </div>
        </div>

        {/* Dynamic Collaboration and Room Management Panel */}
        <div className="collab-bar mb16" style={{
          display: "flex", 
          flexWrap: "wrap", 
          gap: "12px", 
          padding: "14px 18px", 
          background: "var(--bg3)", 
          border: "1px solid var(--border)", 
          borderRadius: "14px"
        }}>
          {!roomId ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", width: "100%", alignItems: "center" }}>
              <div style={{ marginRight: "10px" }}>
                <div style={{fontSize:"10px", fontWeight:800, color:"var(--text2)", textTransform:"uppercase", marginBottom:"2px"}}>COLLABORATION</div>
                <div className="text-sm font-semibold">Join or create a live room to code together</div>
              </div>
              <button className="btn btn-primary btn-sm" onClick={createRoom}>➕ Create Room</button>
              <div style={{ display: "flex", gap: "4px" }}>
                <input 
                  type="text" 
                  className="lang-select" 
                  style={{ width: "110px", height: "32px", fontSize: "12px", padding: "0 8px", background: "rgba(255,255,255,0.03)" }}
                  placeholder="ROOM ID" 
                  value={joinRoomInput}
                  onChange={(e) => setJoinRoomInput(e.target.value)}
                />
                <button className="btn btn-ghost btn-sm" onClick={joinRoom}>Join</button>
              </div>
              
              {/* Question Sheet Uploader */}
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "8px" }}>
                <label className="btn btn-cyan btn-sm" style={{ cursor: "pointer", margin: 0 }}>
                  📂 Upload Sheet
                  <input type="file" style={{ display: "none" }} accept=".pdf,.doc,.docx,.xlsx,.csv,.txt,.md,.json" onChange={handleSheetUpload} />
                </label>
                {isUploading && <span style={{ fontSize: "11px", color: "var(--cyan)" }}>Parsing...</span>}
                {uploadError && <span style={{ fontSize: "11px", color: "var(--red)" }} title={uploadError}>⚠️ Error</span>}
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", width: "100%", alignItems: "center" }}>
              <div>
                <div style={{fontSize:"10px", fontWeight:800, color:"var(--cyan)", textTransform:"uppercase", marginBottom:"2px"}}>ACTIVE ROOM</div>
                <div style={{fontSize: "14px", fontWeight: 800, color: "#fff", display: "flex", alignItems: "center", gap: "6px"}}>
                  {roomId} 
                  <button className="btn-xs btn-ghost" style={{padding: "2px 6px"}} onClick={() => {
                    navigator.clipboard.writeText(roomId);
                    alert("Room ID copied to clipboard!");
                  }}>📋 Copy</button>
                </div>
              </div>
              
              {/* Connected participants list */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "10px" }}>
                <div style={{display:"flex", gap:"-4px", marginRight: "6px"}}>
                  {roomParticipants.map((p, idx) => (
                    <div 
                      key={p.user_id} 
                      className="c-av" 
                      style={{
                        background: p.role === "interviewer" ? "#7c3aed" : "#0e7a5e",
                        border: p.active ? "2px solid var(--cyan)" : "2px solid transparent",
                        color: "#fff",
                        marginLeft: idx > 0 ? "-6px" : 0
                      }}
                      title={`${p.name} (${p.role}) - ${p.active ? 'Active' : 'Idle'}`}
                    >
                      {p.name.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2)}
                    </div>
                  ))}
                </div>
                <span className="text-xs text-muted" style={{maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>
                  {roomParticipants.map(p => p.name).join(", ")} editing...
                </span>
              </div>

              {/* Leave Room */}
              <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto", borderColor: "rgba(255,84,114,0.3)", color: "var(--red)" }} onClick={leaveRoom}>🚪 Leave Room</button>
            </div>
          )}
        </div>

        {/* Main Coding Layout */}
        <div className="code-layout">
          
          {/* Left panel: Problem description */}
          <div className="prob-panel">
            <div className="flex items-center gap8 mb8" style={{justifyContent: "space-between"}}>
              <div className="flex gap8">
                <span className={`pill ${currentProblem?.difficulty === 'Hard' ? 'pill-red' : currentProblem?.difficulty === 'Medium' ? 'pill-gold' : 'pill-cyan'}`}>
                  {currentProblem?.difficulty || "Easy"}
                </span>
                <span className="tag">{currentProblem?.category || "Algorithm"}</span>
              </div>
              
              {/* Problem selector dropdown */}
              <select 
                className="lang-select prob-select" 
                style={{
                  height: "24px", 
                  padding: "0 6px", 
                  fontSize: "10.5px", 
                  maxWidth: "135px", 
                  overflow: "hidden", 
                  textOverflow: "ellipsis", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#0c1220",
                  color: "#f0f4fd",
                  borderRadius: "6px"
                }}
                value={currentProblem?.problem_id || ""} 
                onChange={handleProblemChange}
              >
                <option value="" disabled style={{ background: "#0c1220", color: "#8a9bc0" }}>Select Problem...</option>
                {problems.map(p => (
                  <option key={p.problem_id} value={p.problem_id} style={{ background: "#0c1220", color: "#f0f4fd" }}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div style={{fontSize:"17px", fontWeight:800, marginBottom:"3px"}}>{currentProblem?.title || "Loading Problem..."}</div>
              {currentProblem?.sheet_id && <div style={{fontSize:"10px", color:"var(--purple)", fontWeight:700}}>CUSTOM SHEET ASSIGNED</div>}
            </div>

            <div className="text-sm" style={{color:"#b0c0d8", lineHeight:1.7, marginTop: "10px", overflowY: "auto", maxHeight: "220px"}}>
              {currentProblem?.description}
            </div>

            {/* Constraints */}
            {currentProblem?.constraints && (
              <div style={{marginTop: "12px"}}>
                <div style={{fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", marginBottom: "4px"}}>Constraints</div>
                <ul style={{paddingLeft: "16px", margin: 0, fontSize: "12px", color: "var(--text2)"}}>
                  {(() => {
                    let cons = currentProblem.constraints;
                    if (typeof cons === 'string') {
                      try { cons = JSON.parse(cons); } catch(e) { cons = []; }
                    }
                    return Array.isArray(cons) ? cons.map((c, i) => <li key={i}>{c}</li>) : null;
                  })()}
                </ul>
              </div>
            )}

            {/* Examples */}
            {currentProblem?.examples && (
              <div style={{marginTop: "14px", display: "flex", flexDirection: "column", gap: "8px"}}>
                {(() => {
                  let ex = currentProblem.examples;
                  if (typeof ex === 'string') {
                    try { ex = JSON.parse(ex); } catch(e) { ex = []; }
                  }
                  return Array.isArray(ex) ? ex.map((e, idx) => (
                    <div key={idx} style={{
                      background: "rgba(0,0,0,0.3)", 
                      border: "1px solid var(--border)", 
                      borderRadius: "10px", 
                      padding: "8px 12px", 
                      fontFamily: "'DM Mono',monospace", 
                      fontSize: "11px", 
                      color: "var(--cyan)"
                    }}>
                      <strong>Example {idx + 1}:</strong><br/>
                      Input: {e.input}<br/>
                      Output: {e.output}<br/>
                      {e.explanation && <span style={{color: "var(--text3)"}}>Explanation: {e.explanation}</span>}
                    </div>
                  )) : null;
                })()}
              </div>
            )}

            <div style={{marginTop:"auto", paddingTop: "20px"}}>
              <div className="sec-sub fw7 mb8">AI Hints</div>
              <div className="hint-box" style={{color: hintBox.startsWith('Getting') ? 'var(--text2)' : '#b0c0d8'}}>{hintBox}</div>
              <button className="btn btn-ghost btn-sm" style={{width:"100%", justifyContent:"center", marginTop:"8px"}} onClick={getHint}>💡 Get AI Hint</button>
            </div>
          </div>

          {/* Right panel: Code editor, runner outcome */}
          <div className="flex-col gap10">
            <div className="flex items-center" style={{justifyContent:"space-between"}}>
              <select 
                className="lang-select" 
                style={{ backgroundColor: "#0c1220", color: "#f0f4fd" }}
                value={lang} 
                onChange={(e) => handleLangChange(e.target.value)} 
                aria-label="Select programming language"
              >
                <option value="python" style={{ background: "#0c1220", color: "#f0f4fd" }}>Python</option>
                <option value="javascript" style={{ background: "#0c1220", color: "#f0f4fd" }}>JavaScript</option>
                <option value="typescript" style={{ background: "#0c1220", color: "#f0f4fd" }}>TypeScript</option>
                <option value="java" style={{ background: "#0c1220", color: "#f0f4fd" }}>Java</option>
                <option value="cpp" style={{ background: "#0c1220", color: "#f0f4fd" }}>C++</option>
                <option value="csharp" style={{ background: "#0c1220", color: "#f0f4fd" }}>C#</option>
                <option value="go" style={{ background: "#0c1220", color: "#f0f4fd" }}>Go</option>
                <option value="rust" style={{ background: "#0c1220", color: "#f0f4fd" }}>Rust</option>
                <option value="php" style={{ background: "#0c1220", color: "#f0f4fd" }}>PHP</option>
                <option value="ruby" style={{ background: "#0c1220", color: "#f0f4fd" }}>Ruby</option>
                <option value="swift" style={{ background: "#0c1220", color: "#f0f4fd" }}>Swift</option>
                <option value="kotlin" style={{ background: "#0c1220", color: "#f0f4fd" }}>Kotlin</option>
                <option value="sql" style={{ background: "#0c1220", color: "#f0f4fd" }}>SQL</option>
              </select>
              <div className="flex gap8">
                <button className="btn btn-ghost btn-sm" onClick={() => setCode(defaultCodeTemplates[lang] || "")}>Reset Starter</button>
                <button className="btn btn-primary btn-sm" onClick={runCode}>▶ Run Code</button>
              </div>
            </div>
            
            <textarea 
              id="code-textarea"
              className="code-area" 
              value={code} 
              onChange={(e) => {
                setCode(e.target.value);
                lastTypedRef.current = Date.now();
                isTypingRef.current = true;
              }} 
              spellCheck="false" 
              aria-label="Code editor" 
            />
            
            {/* Console execution outputs */}
            <div>
              <div className="sec-sub fw7 mb8">Console Output</div>
              <div className="console-out" id="console-out" style={{
                color: consoleColor, 
                whiteSpace: "pre-wrap", 
                maxHeight: "140px", 
                overflowY: "auto",
                fontFamily: "'DM Mono', monospace",
                fontSize: "12px"
              }} aria-live="polite">
                {consoleOut}
              </div>
            </div>
            
            {/* AI Review Tab */}
            <div className="card-sm" style={{background:"rgba(0,240,200,0.03)", borderColor:"rgba(0,240,200,0.13)", flex: 1, overflowY: "auto", maxHeight: "180px"}}>
              <div className="sec-sub fw7 mb8">AI Code Review</div>
              <div id="ai-review" className="text-sm" style={{color:"#b0c0d8", lineHeight:"1.6", whiteSpace: "pre-wrap"}}>{aiReview}</div>
            </div>

            {/* Complexity and test indicators */}
            <div className="flex gap8">
              <div className="complexity-badge"><div className="cb-lbl">Time Complexity</div><div className="cb-val" style={{color:"var(--cyan)"}}>{timeComplexity}</div></div>
              <div className="complexity-badge"><div className="cb-lbl">Space Complexity</div><div className="cb-val" style={{color:"var(--blue)"}}>{spaceComplexity}</div></div>
              <div className="complexity-badge"><div className="cb-lbl">Test Cases Passed</div><div className="cb-val" style={{color: testPassColor}}>{testPass}</div></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
