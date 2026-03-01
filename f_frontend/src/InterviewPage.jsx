import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = "http://localhost:5000";

const InterviewPage = () => {
  const navigate = useNavigate();

  // ── Read session_id & user from localStorage (set by Dashboard) ──
  const [sessionId, setSessionId]           = useState(null);
  const [question, setQuestion]             = useState("");
  const [response, setResponse]             = useState("");
  const [feedback, setFeedback]             = useState("");
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [showNext, setShowNext]             = useState(false);
  const [menuOpen, setMenuOpen]             = useState(false);
  const [showFeedback, setShowFeedback]     = useState(false);
  const [allFeedbacks, setAllFeedbacks]     = useState([]);
  const [user, setUser]                     = useState({ name: "", email: "", avatar: "", _id: "" });

  const currentAudioRef  = useRef(null);
  const speechQueue      = useRef([]);
  const isAudioPlaying   = useRef(false);

  useEffect(() => {
    // Load session_id saved by Dashboard after resume upload
    const sid = localStorage.getItem("session_id");
    if (!sid) {
      alert("No interview session found. Please upload your resume on the Dashboard first.");
      navigate("/dashboard");
      return;
    }
    setSessionId(sid);

    // Load user info
    try {
      const stored = localStorage.getItem("user");
      if (stored) setUser(JSON.parse(stored));
    } catch { /* silent */ }
  }, []);

  // ── Audio helpers ─────────────────────────────────────────────────
  const playSpeech = (text) => {
    speechQueue.current.push(text);
    if (!isAudioPlaying.current) playNextInQueue();
  };

  const playNextInQueue = () => {
    if (!speechQueue.current.length) { isAudioPlaying.current = false; return; }
    const nextText = speechQueue.current.shift();
    isAudioPlaying.current = true;
    fetch(`${BACKEND_URL}/text-to-speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: nextText }),
    })
      .then(res => res.blob())
      .then(blob => {
        const audio = new Audio(URL.createObjectURL(blob));
        currentAudioRef.current = audio;
        audio.play();
        audio.onended = () => { isAudioPlaying.current = false; playNextInQueue(); };
      })
      .catch(() => { isAudioPlaying.current = false; playNextInQueue(); });
  };

  // ── Interview actions ─────────────────────────────────────────────
  const fetchNextQuestion = async () => {
    if (!sessionId) return;
    try {
      const res  = await fetch(`${BACKEND_URL}/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      if (data.question) {
        setQuestion(data.question);
        setResponse("");
        setShowNext(false);
        setFeedback("");
        playSpeech(data.question);
      } else if (data.message === "Interview complete") {
        setInterviewComplete(true);
      }
    } catch {
      alert("Failed to fetch question. Check your connection.");
    }
  };

  const submitResponse = async () => {
    if (!response.trim()) return alert("Please type your response first.");
    try {
      const res  = await fetch(`${BACKEND_URL}/response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, response }),
      });
      const data = await res.json();
      if (res.ok) {
        setFeedback(data.feedback);
        setAllFeedbacks(prev => [...prev, { question, response, feedback: data.feedback }]);
        setShowNext(true);
        setResponse("");
      } else {
        alert(data.error);
      }
    } catch {
      alert("Failed to submit response.");
    }
  };

  const endInterview = async () => {
    // Stop audio
    speechQueue.current = [];
    isAudioPlaying.current = false;
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }

    // Call backend end-interview endpoint
    try {
      await fetch(`${BACKEND_URL}/end-interview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch { /* best-effort */ }

    setQuestion("");
    setResponse("");
    setShowNext(false);
    setInterviewStarted(false);
    setInterviewComplete(true);
    setShowFeedback(true);
  };

  // ── Derived display info ──────────────────────────────────────────
  const displayName = user.name
    ? user.name.split(" ")[0]
    : user.email?.split("@")[0] || "Candidate";

  const initials = user.name
    ? user.name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : (user.email?.[0] || "U").toUpperCase();

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; font-family: 'Sora', sans-serif; }

        /* ── Navbar ── */
        .iv-navbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: rgba(8, 12, 20, 0.92);
          backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(255,255,255,0.07);
          padding: 0 28px;
          height: 64px;
          position: fixed;
          top: 0; left: 0; right: 0;
          z-index: 100;
        }
        .iv-brand { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; color: #e8edf8; }
        .iv-brand-icon { width: 34px; height: 34px; background: linear-gradient(135deg,#00e5c3,#00b8ff); border-radius: 9px; display: flex; align-items: center; justify-content: center; color: #080c14; }
        .iv-avatar-btn { width: 36px; height: 36px; border-radius: 50%; background: rgba(0,229,195,0.15); border: 1.5px solid rgba(0,229,195,0.35); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #00e5c3; cursor: pointer; position: relative; }
        .iv-dropdown { position: absolute; top: 44px; right: 0; background: #0d1220; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 6px; min-width: 160px; box-shadow: 0 16px 40px rgba(0,0,0,0.5); }
        .iv-dropdown li { list-style: none; padding: 10px 14px; font-size: 13px; color: #e8edf8; border-radius: 8px; cursor: pointer; transition: background 0.15s; }
        .iv-dropdown li:hover { background: rgba(255,255,255,0.07); }

        /* ── Page ── */
        .iv-page {
          min-height: 100vh;
          padding: 88px 24px 40px;
          background: linear-gradient(160deg, #080c14 0%, #0a1628 50%, #080c14 100%);
        }

        /* ── Two-panel layout ── */
        .iv-panels {
          display: flex;
          gap: 24px;
          max-width: 1000px;
          margin: 0 auto 28px;
        }
        @media (max-width: 720px) { .iv-panels { flex-direction: column; } }

        .iv-panel {
          flex: 1;
          background: rgba(15,22,40,0.75);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 20px;
          padding: 28px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          backdrop-filter: blur(16px);
        }

        /* ── Avatars ── */
        .iv-avatar-ring {
          width: 120px; height: 120px; border-radius: 50%;
          border: 3px solid rgba(0,229,195,0.4);
          object-fit: cover;
          background: rgba(0,229,195,0.1);
          display: flex; align-items: center; justify-content: center;
          font-size: 36px; font-weight: 700; color: #00e5c3;
          overflow: hidden;
        }
        .iv-avatar-ring img { width: 100%; height: 100%; object-fit: cover; }
        .iv-panel-name { font-size: 18px; font-weight: 700; color: #e8edf8; }
        .iv-panel-role { font-size: 13px; color: #7a8ba8; }

        /* ── Question bubble ── */
        .iv-question-box {
          background: rgba(0,229,195,0.07);
          border: 1px solid rgba(0,229,195,0.2);
          border-radius: 14px;
          padding: 16px 18px;
          font-size: 14px;
          color: #e8edf8;
          line-height: 1.6;
          width: 100%;
          text-align: left;
        }
        .iv-question-label { font-size: 11px; font-weight: 600; color: #00e5c3; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 6px; }

        /* ── Answer area ── */
        .iv-answer-wrap { width: 100%; display: flex; flex-direction: column; gap: 10px; }
        .iv-textarea {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 12px 14px;
          color: #e8edf8;
          font-family: 'Sora', sans-serif;
          font-size: 14px;
          resize: vertical;
          min-height: 90px;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .iv-textarea:focus { border-color: rgba(0,229,195,0.5); box-shadow: 0 0 0 3px rgba(0,229,195,0.1); }
        .iv-textarea::placeholder { color: #4a5a72; }

        /* ── Buttons ── */
        .iv-btn {
          width: 100%;
          padding: 12px 20px;
          border-radius: 12px;
          border: none;
          font-family: 'Sora', sans-serif;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .iv-btn-primary { background: linear-gradient(135deg,#00e5c3,#00b8ff); color: #050d14; }
        .iv-btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
        .iv-btn-ghost { background: rgba(255,255,255,0.05); color: #e8edf8; border: 1px solid rgba(255,255,255,0.1); }
        .iv-btn-ghost:hover { background: rgba(255,255,255,0.09); }
        .iv-btn-danger { background: rgba(255,79,106,0.15); color: #ff4f6a; border: 1px solid rgba(255,79,106,0.3); max-width: 220px; margin: 0 auto; }
        .iv-btn-danger:hover { background: rgba(255,79,106,0.25); }
        .iv-btn-start { background: linear-gradient(135deg,#00e5c3,#00b8ff); color: #050d14; padding: 14px 32px; font-size: 15px; border-radius: 14px; border: none; cursor: pointer; font-weight: 700; font-family: 'Sora', sans-serif; transition: all 0.2s; }
        .iv-btn-start:hover { opacity: 0.9; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,229,195,0.3); }

        /* ── Feedback ── */
        .iv-feedback {
          background: rgba(0,229,195,0.06);
          border: 1px solid rgba(0,229,195,0.2);
          border-radius: 14px;
          padding: 16px 18px;
          font-size: 13.5px;
          color: #b8c8d8;
          line-height: 1.7;
          width: 100%;
          text-align: left;
          white-space: pre-wrap;
        }
        .iv-feedback-label { font-size: 11px; font-weight: 600; color: #00e5c3; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }

        /* ── Complete banner ── */
        .iv-complete {
          max-width: 1000px;
          margin: 0 auto 28px;
          background: rgba(0,214,143,0.08);
          border: 1px solid rgba(0,214,143,0.25);
          border-radius: 20px;
          padding: 28px 32px;
          text-align: center;
        }
        .iv-complete h2 { color: #00d68f; font-size: 22px; margin-bottom: 8px; }
        .iv-complete p  { color: #7a8ba8; font-size: 14px; margin-bottom: 20px; }

        /* ── Feedback summary ── */
        .iv-summary { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
        .iv-summary-card {
          background: rgba(15,22,40,0.75);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 16px;
          padding: 20px;
        }
        .iv-summary-q { font-size: 13px; font-weight: 600; color: #00e5c3; margin-bottom: 6px; }
        .iv-summary-a { font-size: 13px; color: #7a8ba8; margin-bottom: 10px; }
        .iv-summary-f { font-size: 13px; color: #b8c8d8; line-height: 1.7; white-space: pre-wrap; }

        .iv-end-row { display: flex; justify-content: center; margin-top: 8px; }
      `}</style>

      {/* ── Navbar ── */}
      <nav className="iv-navbar">
        <div className="iv-brand">
          <div className="iv-brand-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9"/>
              <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          InterviewAI
        </div>
        <div style={{ position: "relative" }}>
          <div className="iv-avatar-btn" onClick={() => setMenuOpen(!menuOpen)}>
            {user.avatar
              ? <img src={user.avatar} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }} />
              : initials}
          </div>
          {menuOpen && (
            <ul className="iv-dropdown">
              <li onClick={() => navigate("/profile")}>My Profile</li>
              <li onClick={() => navigate("/dashboard")}>Dashboard</li>
              <li onClick={() => { localStorage.clear(); navigate("/"); }}>Logout</li>
            </ul>
          )}
        </div>
      </nav>

      <div className="iv-page">

        {/* ── Interview Complete view ── */}
        {interviewComplete ? (
          <>
            <div className="iv-complete">
              <h2>🎉 Interview Complete!</h2>
              <p>Great job, {displayName}! Here's a summary of your performance.</p>
              <button className="iv-btn-start" onClick={() => navigate("/dashboard")}>
                Back to Dashboard
              </button>
            </div>

            {allFeedbacks.length > 0 && (
              <div className="iv-summary">
                {allFeedbacks.map((item, i) => (
                  <div className="iv-summary-card" key={i}>
                    <div className="iv-summary-q">Q{i + 1}: {item.question}</div>
                    <div className="iv-summary-a">Your answer: {item.response}</div>
                    <div className="iv-summary-f">{item.feedback}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            {/* ── Two panels ── */}
            <div className="iv-panels">

              {/* AI Interviewer panel */}
              <div className="iv-panel">
                <div className="iv-avatar-ring">🤖</div>
                <div className="iv-panel-name">AI Interviewer</div>
                <div className="iv-panel-role">Powered by Gemini</div>

                {!interviewStarted ? (
                  <button className="iv-btn-start" onClick={() => { setInterviewStarted(true); fetchNextQuestion(); }}>
                    Start Interview
                  </button>
                ) : (
                  question && (
                    <div className="iv-question-box">
                      <div className="iv-question-label">Question</div>
                      {question}
                    </div>
                  )
                )}
              </div>

              {/* Candidate panel */}
              <div className="iv-panel">
                <div className="iv-avatar-ring">
                  {user.avatar
                    ? <img src={user.avatar} alt="you" />
                    : <span style={{ fontSize: 36 }}>{initials}</span>}
                </div>
                <div className="iv-panel-name">{displayName}</div>
                <div className="iv-panel-role">{user.email}</div>

                {interviewStarted && (
                  <div className="iv-answer-wrap">
                    <textarea
                      className="iv-textarea"
                      value={response}
                      onChange={e => setResponse(e.target.value)}
                      placeholder="Type your answer here..."
                      onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) submitResponse(); }}
                    />
                    <button className="iv-btn iv-btn-primary" onClick={submitResponse}>
                      Submit Answer
                    </button>
                    {showNext && (
                      <button className="iv-btn iv-btn-ghost" onClick={fetchNextQuestion}>
                        Next Question →
                      </button>
                    )}
                  </div>
                )}

                {feedback && (
                  <div className="iv-feedback">
                    <div className="iv-feedback-label">Feedback</div>
                    {feedback}
                  </div>
                )}
              </div>
            </div>

            {/* End interview button */}
            {interviewStarted && (
              <div className="iv-end-row">
                <button className="iv-btn iv-btn-danger" onClick={endInterview}>
                  End Interview
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
};

export default InterviewPage;