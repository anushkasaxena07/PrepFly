import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import AI_INTERVIEWER from "./config/aiInterviewerConfig";
import { getGradeInfo, computeSectionGrades, getBadges } from "./utils/gradingSystem";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

// ── futur21 Circle Waves Avatar for Ava AI ──────────────────────────────────
// ── futur21 Circle Waves Avatar for Ava AI (GIF only) ───────────────────────
const CircleWavesAvatar = ({ isTalking, isThinking }) => {
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "180px",
          height: "180px",
          borderRadius: "50%",
          overflow: "hidden",
          transform: isTalking ? "scale(1.05)" : "scale(1)",
          transition: "transform 0.3s ease",
          boxShadow: isTalking
            ? "0 0 30px rgba(0, 229, 195, 0.6)"
            : isThinking
              ? "0 0 20px rgba(139, 92, 246, 0.5)"
              : "0 0 15px rgba(0, 229, 195, 0.3)",
        }}
      >
        <img
          src="/ava-circle-waves.gif"
          alt="Ava AI"
          onError={(e) => (e.target.style.display = "none")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            borderRadius: "50%",
          }}
        />
      </div>
    </div>
  );
};

// ── AudioWave Component ─────────────────────────────────────────────────────
const AudioWave = ({ active }) => (
  <div style={{ display: "flex", gap: 4, alignItems: "center", height: 24 }}>
    {[0, 1, 2, 3, 4].map(i => (
      <div
        key={i}
        style={{
          width: 4,
          borderRadius: 2,
          background: active ? "#00e5c3" : "rgba(0,229,195,0.3)",
          height: active ? `${8 + Math.sin(i * 1.2) * 8 + 8}px` : "6px",
          transition: "height 0.15s ease",
          animation: active ? `wave 0.8s ease-in-out ${i * 0.12}s infinite alternate` : "none",
        }}
      />
    ))}
  </div>
);

// ── Score Ring ──────────────────────────────────────────────────────────────
const ScoreRing = ({ score, max = 10, size = 80, label }) => {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, score / max));
  const color = pct >= 0.8 ? "#00e5c3" : pct >= 0.6 ? "#00b8ff" : pct >= 0.4 ? "#f59e0b" : "#ff4f6a";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="8" />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - pct)}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x={size / 2} y={size / 2 + 1} textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize={size * 0.22} fontWeight="700" fontFamily="'Sora', sans-serif">
          {score}
        </text>
      </svg>
      {label && <div style={{ fontSize: 11, color: "#7a8ba8", fontFamily: "'Sora', sans-serif" }}>{label}</div>}
    </div>
  );
};

// ── Grade Badge ─────────────────────────────────────────────────────────────
const GradeBadge = ({ grade }) => {
  const colors = { S: "#ffd700", A: "#00e5c3", B: "#00b8ff", C: "#f59e0b", D: "#f97316", F: "#ff4f6a" };
  const color = colors[grade] || "#7a8ba8";
  return (
    <div style={{
      width: 72, height: 72, borderRadius: "50%",
      border: `3px solid ${color}`,
      background: `${color}18`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 32, fontWeight: 800, color,
      fontFamily: "'Sora', sans-serif",
      boxShadow: `0 0 24px ${color}44`,
    }}>
      {grade}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
//  MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════════════
const InterviewPage = () => {
  const navigate = useNavigate();

  // ── Session & user ─────────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState(null);
  const [user, setUser] = useState({ name: "", email: "", avatar: "", _id: "" });
  const [atsScore, setAtsScore] = useState(null);

  // ── Interview state & stage ────────────────────────────────────────────
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [question, setQuestion] = useState("");
  const [questionNumber, setQuestionNumber] = useState(0);
  const [currentStage, setCurrentStage] = useState("Greeting & Icebreaker");
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [response, setResponse] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [showNext, setShowNext] = useState(false);
  const [allFeedbacks, setAllFeedbacks] = useState([]);
  const [finalResult, setFinalResult] = useState(null);
  const [hintText, setHintText] = useState("");
  const [isFetchingHint, setIsFetchingHint] = useState(false);
  const [liveMetrics, setLiveMetrics] = useState(null);

  // ── Ava state ────────────────────────────────────────────────────────
  const [isAvaTalking, setIsAvaTalking] = useState(false);
  const [isAvaThinking, setIsAvaThinking] = useState(false);
  const [selectedEvidenceDimension, setSelectedEvidenceDimension] = useState(null);
  const [avaStatus, setAvaStatus] = useState("Ready to interview you!");

  // ── Voice recording ────────────────────────────────────────────────────
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [inputMode, setInputMode] = useState("voice");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const webSpeechTranscriptRef = useRef("");

  // ── Video (candidate webcam) ───────────────────────────────────────────
  const videoRef = useRef(null);
  const videoStreamRef = useRef(null);
  const sessionRecorderRef = useRef(null);
  const sessionChunksRef = useRef([]);

  // ── Audio playback ─────────────────────────────────────────────────────
  const currentAudioRef = useRef(null);
  const speechQueue = useRef([]);
  const isAudioPlaying = useRef(false);
  const speechSpeedRef = useRef(1.5);
  const [speechSpeed, setSpeechSpeed] = useState(() => {
    const stored = localStorage.getItem("speechSpeed");
    return stored ? Number(stored) : 1.5;
  });

  const handleSpeedChange = (speed) => {
    setSpeechSpeed(speed);
    speechSpeedRef.current = speed;
    localStorage.setItem("speechSpeed", speed.toString());
    if (currentAudioRef.current) {
      currentAudioRef.current.playbackRate = speed;
      currentAudioRef.current.defaultPlaybackRate = speed;
    }
  };

  const [menuOpen, setMenuOpen] = useState(false);
  const [videoBlob, setVideoBlob] = useState(null);

  const formatAvaMessage = (text) => {
    if (!text || typeof text !== "string") return text || "";
    let clean = text.trim();
    if (clean.includes("```")) {
      clean = clean.replace(/```(?:json)?\s*/gi, "").replace(/```/g, "").trim();
    }
    if ((clean.startsWith('"') && clean.endsWith('"')) || (clean.startsWith("'") && clean.endsWith("'"))) {
      clean = clean.slice(1, -1).trim();
    }
    if (clean.includes('"message":') || clean.includes('"message" :') || (clean.startsWith('{') && clean.endsWith('}'))) {
      try {
        const parsed = JSON.parse(clean);
        if (parsed && typeof parsed === 'object') {
          const msg = parsed.message || parsed.acknowledgment;
          if (msg) return msg.trim();
        }
      } catch (e) {
        const match = clean.match(/"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"/);
        if (match && match[1]) {
          return match[1].replace(/\\"/g, '"').replace(/\\n/g, ' ').trim();
        }
      }
    }
    return clean;
  };

  // ── Init & Auto-Save Recovery ──────────────────────────────────────────
  useEffect(() => {
    const sid = localStorage.getItem("session_id");
    if (!sid) {
      alert("No interview session found. Please upload your resume on the Dashboard first.");
      navigate("/dashboard");
      return;
    }
    setSessionId(sid);

    try {
      const stored = localStorage.getItem("user");
      if (stored) setUser(JSON.parse(stored));
      const savedAts = localStorage.getItem(`ats_score_${sid}`);
      if (savedAts) setAtsScore(savedAts);
    } catch { /* silent */ }

    // Auto-recover draft response if internet disconnected
    const savedDraft = localStorage.getItem(`interview_autosave_${sid}`);
    if (savedDraft) {
      setResponse(savedDraft);
    }
  }, []);

  // Save response draft on change for offline protection
  useEffect(() => {
    if (sessionId && response) {
      localStorage.setItem(`interview_autosave_${sessionId}`, response);
    }
  }, [response, sessionId]);

  // ── Webcam setup ───────────────────────────────────────────────────────
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      videoStreamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;

      let mimeType = "video/webm";
      if (!MediaRecorder.isTypeSupported("video/webm")) {
        mimeType = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "";
      }
      const options = mimeType ? { mimeType } : undefined;

      sessionChunksRef.current = [];
      const recorder = new MediaRecorder(stream, options);
      recorder.ondataavailable = e => {
        if (e.data && e.data.size > 0) sessionChunksRef.current.push(e.data);
      };
      recorder.start(1000);
      sessionRecorderRef.current = recorder;
    } catch (err) {
      console.warn("Webcam not available:", err);
    }
  };

  const stopWebcam = () => {
    if (sessionRecorderRef.current && sessionRecorderRef.current.state !== "inactive") {
      sessionRecorderRef.current.stop();
    }
    if (videoStreamRef.current) {
      videoStreamRef.current.getTracks().forEach(t => t.stop());
    }
  };

  // ── Audio / TTS ────────────────────────────────────────────────────────
  const playSpeech = useCallback((text, onStartCallback) => {
    speechQueue.current.push({ text, onStart: onStartCallback });
    if (!isAudioPlaying.current) playNextInQueue();
  }, []);

  const playNextInQueue = () => {
    if (!speechQueue.current.length) {
      isAudioPlaying.current = false;
      setIsAvaTalking(false);
      return;
    }
    const item = speechQueue.current.shift();
    const nextText = item.text;
    isAudioPlaying.current = true;
    setIsAvaTalking(true);

    fetch(`${BACKEND_URL}/text-to-speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: nextText }),
    })
      .then(res => res.blob())
      .then(blob => {
        const audio = new Audio(URL.createObjectURL(blob));
        audio.defaultPlaybackRate = speechSpeedRef.current;
        audio.playbackRate = speechSpeedRef.current;
        currentAudioRef.current = audio;

        if (item.onStart) item.onStart();

        audio.play();
        audio.playbackRate = speechSpeedRef.current;
        audio.onended = () => {
          isAudioPlaying.current = false;
          setIsAvaTalking(false);
          playNextInQueue();
        };
      })
      .catch(() => {
        if (item.onStart) item.onStart();
        isAudioPlaying.current = false;
        setIsAvaTalking(false);
        playNextInQueue();
      });
  };

  // ── Voice recording ────────────────────────────────────────────────────
  const startRecording = async () => {
    webSpeechTranscriptRef.current = "";
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let webSpeechActive = false;

    if (SpeechRecognition) {
      try {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "en-US";

        rec.onstart = () => { setAvaStatus("Listening... Speak now! 🎙️"); };
        rec.onresult = (e) => {
          let transcript = "";
          for (let i = e.resultIndex; i < e.results.length; i++) {
            transcript += e.results[i][0].transcript;
          }
          if (transcript) {
            setResponse(transcript);
            webSpeechTranscriptRef.current = transcript;
          }
        };
        rec.start();
        recognitionRef.current = rec;
        webSpeechActive = true;
      } catch (err) { console.warn("Speech Rec error:", err); }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      audioChunksRef.current = [];
      recorder.ondataavailable = e => audioChunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (!webSpeechTranscriptRef.current.trim()) {
          const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          await transcribeAudio(blob);
        } else {
          setAvaStatus("Got it! Review and submit when ready.");
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      if (!webSpeechActive) setAvaStatus("Recording audio...");
    } catch {
      if (!webSpeechActive) alert("Microphone access denied. Please allow microphone and try again.");
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { }
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (blob) => {
    setIsTranscribing(true);
    setAvaStatus("Transcribing audio (backend fallback)...");
    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        try {
          const base64data = reader.result;
          const b64 = base64data.split(",")[1];
          const res = await fetch(`${BACKEND_URL}/speech-to-text`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio_base64: b64, mime_type: "audio/webm" }),
          });
          const data = await res.json();
          if (data.transcript) {
            setResponse(data.transcript);
            setAvaStatus("Got it! Review and submit when ready.");
          } else {
            setAvaStatus("Couldn't catch that. Try again or type your answer.");
          }
        } catch { setAvaStatus("Transcription failed. Please type your answer."); }
        finally { setIsTranscribing(false); }
      };
      reader.readAsDataURL(blob);
    } catch {
      setAvaStatus("Transcription failed. Please type your answer.");
      setIsTranscribing(false);
    }
  };

  // ── Request Hint & Repeat ──────────────────────────────────────────────
  const requestHint = async () => {
    if (!sessionId || isFetchingHint) return;
    setIsFetchingHint(true);
    try {
      const res = await fetch(`${BACKEND_URL}/get-hint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await res.json();
      if (data.hint) {
        setHintText(data.hint);
        playSpeech(`Here is a quick hint: ${data.hint}`);
      }
    } catch (e) {
      console.error("Fetch hint error:", e);
    } finally {
      setIsFetchingHint(false);
    }
  };

  const requestRepeat = async () => {
    if (!sessionId || !question) return;
    playSpeech(`Sure, let me repeat the question: ${question}`);
  };

  // ── Interview actions ──────────────────────────────────────────────────
  const fetchNextQuestion = async () => {
    if (!sessionId) return;
    setIsAvaThinking(true);
    setAvaStatus("Thinking of the next question...");
    setFeedback(null);
    setHintText("");
    setShowNext(false);
    setResponse("");

    try {
      const endpoint = questionNumber === 0 ? "/start-interview" : "/next";
      const res = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();

      if (data.question) {
        const cleanQ = formatAvaMessage(data.question);
        setIsAvaThinking(true);
        if (data.stage) setCurrentStage(data.stage);
        if (data.total_questions) setTotalQuestions(data.total_questions);

        setAvaStatus(`${AI_INTERVIEWER.name} is preparing your question...`);
        playSpeech(cleanQ, () => {
          setQuestion(cleanQ);
          setQuestionNumber(data.question_number || questionNumber + 1);
          setIsAvaThinking(false);
          setAvaStatus("Asking you a question...");
          setTimeout(() => setAvaStatus("Your turn to answer!"), 2000);
        });
      } else if (data.message === "Interview complete" || data.done) {
        endInterview();
      }
    } catch {
      setIsAvaThinking(false);
      setAvaStatus("Connection error. Retrying...");
    }
  };

  const submitResponse = async () => {
    if (!response.trim()) return alert("Please record or type your response first.");
    setIsAvaThinking(true);
    setAvaStatus("Evaluating your answer...");

    try {
      const res = await fetch(`${BACKEND_URL}/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer: response }),
      });
      const data = await res.json();

      if (res.ok) {
        if (data.message === "Repeating question") {
          setIsAvaThinking(false);
          setAvaStatus("Repeating question... Speak or type when ready!");
          playSpeech(data.next_question);
          return;
        }
        if (data.feedback && data.feedback.live_metrics) {
          setLiveMetrics(data.feedback.live_metrics);
        }

        if (data.done) {
          const feedbackObj = data.final_feedback || {};
          setFeedback(feedbackObj);
          setAllFeedbacks(prev => [...prev, {
            question,
            response,
            feedback: feedbackObj.feedback || "Good attempt.",
            score: feedbackObj.score || 0,
          }]);
          setShowNext(true);
          setResponse("");
          if (sessionId) localStorage.removeItem(`interview_autosave_${sessionId}`);
          setIsAvaThinking(false);
          const scoreVal = feedbackObj.score || 0;
          setAvaStatus(`Interview complete! Final score: ${scoreVal}/10`);
          playSpeech(`Thanks for completing the interview! You scored ${scoreVal} out of 10 on the final question.`);
        } else {
          const feedbackObj = data.feedback || {};
          setFeedback(feedbackObj);
          setAllFeedbacks(prev => [...prev, {
            question,
            response,
            feedback: feedbackObj.feedback || "Good attempt.",
            score: feedbackObj.score || 0,
          }]);
          setShowNext(true);
          setResponse("");
          if (sessionId) localStorage.removeItem(`interview_autosave_${sessionId}`);
          setIsAvaThinking(false);
          const scoreVal = feedbackObj.score || 0;
          setAvaStatus(`Score: ${scoreVal}/10 — ${scoreVal >= 7 ? "Great job!" : "Keep going!"}`);
          playSpeech(scoreVal >= 7
            ? `Good answer! You scored ${scoreVal} out of 10.`
            : `Thanks for answering. You scored ${scoreVal} out of 10. Let me give you some feedback.`
          );
        }
      } else {
        setIsAvaThinking(false);
        setAvaStatus("Error submitting. Try again.");
      }
    } catch {
      setIsAvaThinking(false);
      setAvaStatus("Submission failed.");
    }
  };

  const isEndingRef = useRef(false);

  const downloadPDF = (result, feedbacks) => {
    const gradeColors = { S: "#ffd700", A: "#00e5c3", B: "#00b8ff", C: "#f59e0b", D: "#f97316", F: "#ff4f6a" };
    const gc = gradeColors[result.grade] || "#7a8ba8";
    const html = `<!DOCTYPE html><html><head>
    <meta charset="UTF-8"/><title>Interview Report</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&display=swap');
      *{box-sizing:border-box;margin:0;padding:0}body{font-family:'Sora',sans-serif;background:#0a0f1e;color:#e8edf8;padding:40px}
      .hdr{display:flex;justify-content:space-between;padding-bottom:18px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:28px}
      .brand{font-size:20px;font-weight:800;background:linear-gradient(135deg,#00e5c3,#00b8ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
      .meta{font-size:12px;color:#7a8ba8;text-align:right;line-height:1.8}
      .hero{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:22px;margin-bottom:22px;display:flex;align-items:center;gap:22px}
      .grade{width:68px;height:68px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:800}
      .sl{font-size:11px;color:#7a8ba8;margin-bottom:3px}.sv{font-size:30px;font-weight:800;color:#00e5c3}
      .rpt{font-size:13px;color:#b8c8d8;line-height:1.8;margin-top:8px}
      .st{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#00e5c3;margin:22px 0 12px}
      .qa{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:16px;margin-bottom:10px}
      .ql{font-size:10px;color:#a78bfa;font-weight:700;margin-bottom:5px}.qt{font-size:14px;font-weight:600;color:#e8edf8;margin-bottom:10px;line-height:1.5}
      .sc{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;margin-bottom:8px}
      .al{font-size:10px;color:#7a8ba8;font-weight:600;margin-bottom:3px}.at{font-size:13px;color:#7a8ba8;margin-bottom:10px;font-style:italic;line-height:1.6}
      .fl{font-size:10px;color:#00e5c3;font-weight:600;margin-bottom:3px}.ft{font-size:13px;color:#9ab0c8;line-height:1.7;white-space:pre-wrap}
      .ftr{margin-top:36px;padding-top:14px;border-top:1px solid rgba(255,255,255,.07);font-size:11px;color:#3a4a68;text-align:center}
    </style></head><body>
    <div class="hdr"><div class="brand">🚀 PrepFly Report</div><div class="meta">Candidate: ${user.name || "Candidate"}<br/>Generated: ${new Date().toLocaleString()}<br/>Questions: ${feedbacks.length}</div></div>
    <div class="hero">
      <div class="grade" style="border:3px solid ${gc};background:${gc}18;color:${gc}">${result.grade || "—"}</div>
      <div><div class="sl">Overall Score</div><div class="sv">${result.overall_score || 0}/10</div>${result.report ? `<div class="rpt">${result.report}</div>` : ""}</div>
    </div>
    <div class="st">Question-by-Question Breakdown</div>
    ${feedbacks.map((item, i) => { const sc = item.score || 0; const c = sc >= 8 ? "#00e5c3" : sc >= 6 ? "#00b8ff" : sc >= 4 ? "#f59e0b" : "#ff4f6a"; return `<div class="qa"><div class="ql">Question ${i + 1}</div><div class="qt">${item.question || ""}</div><span class="sc" style="background:${c}18;color:${c};border:1px solid ${c}44">Score: ${sc}/10</span><div class="al">Your Answer</div><div class="at">"${item.response || ""}"</div><div class="fl">Feedback</div><div class="ft">${item.feedback || "—"}</div></div>`; }).join("")}
    <div class="ftr">Generated by PrepFly · ${new Date().toLocaleString()}</div>
    </body></html>`;
    const win = window.open("", "_blank");
    win.document.write(html);
    win.document.close();
    setTimeout(() => win.print(), 600);
  };

  const downloadVideo = (blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `interview-${Date.now()}.webm`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  };

  const endInterview = async () => {
    if (isEndingRef.current) return;
    isEndingRef.current = true;

    speechQueue.current = [];
    isAudioPlaying.current = false;
    setIsAvaTalking(false);
    if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null; }

    setIsAvaThinking(true);
    setAvaStatus("Wrapping up...");

    stopWebcam();
    if (sessionChunksRef.current.length > 0) {
      const localVideoBlob = new Blob(sessionChunksRef.current, { type: "video/webm" });
      setVideoBlob(localVideoBlob);
      (async () => {
        try {
          const fd = new FormData();
          fd.append("video", localVideoBlob, `recording_${sessionId}.webm`);
          fd.append("session_id", sessionId);
          await fetch(`${BACKEND_URL}/save-recording`, { method: "POST", body: fd });
        } catch (e) { console.warn("Background recording upload failed:", e); }
      })();
    }

    let data = { overall_score: 0, grade: "N/A", report: "Generating your report…" };
    try {
      const res = await fetch(`${BACKEND_URL}/end-interview`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      data = await res.json();
    } catch { }

    setFinalResult(data);
    playSpeech(AI_INTERVIEWER.closing);

    setInterviewStarted(false);
    setInterviewComplete(true);
    setIsAvaThinking(false);

    let attempts = 0;
    const poll = setInterval(async () => {
      attempts++;
      try {
        const r = await fetch(`${BACKEND_URL}/session-report/${sessionId}`);
        const rd = await r.json();
        if (rd.final_report && !rd.final_report.includes("Generating")) {
          try {
            const parsed = JSON.parse(rd.final_report);
            setFinalResult(prev => ({
              ...prev,
              ...parsed,
              report: rd.final_report
            }));
          } catch (e) {
            setFinalResult(prev => ({ ...prev, report: rd.final_report }));
          }
          clearInterval(poll);
        }
      } catch { }
      if (attempts >= 12) clearInterval(poll);
    }, 5000);
  };

  const startInterview = async () => {
    setInterviewStarted(true);
    await startWebcam();
    playSpeech(AI_INTERVIEWER.greeting);
    setTimeout(() => fetchNextQuestion(), 1500);
  };

  const displayName = user.name ? user.name.split(" ")[0] : user.email?.split("@")[0] || "Candidate";
  const initials = user.name ? user.name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) : (user.email?.[0] || "U").toUpperCase();
  const avgScore = allFeedbacks.length ? (allFeedbacks.reduce((s, f) => s + (f.score || 0), 0) / allFeedbacks.length).toFixed(1) : null;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; font-family: 'Sora', sans-serif; }

        .iv-navbar {
          display: flex; justify-content: space-between; align-items: center;
          background: rgba(8,12,20,0.95); backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(255,255,255,0.07);
          padding: 0 28px; height: 64px;
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
        }
        .iv-brand { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; color: #e8edf8; }
        .iv-brand-icon { width: 34px; height: 34px; background: linear-gradient(135deg,#00e5c3,#00b8ff); border-radius: 9px; display: flex; align-items: center; justify-content: center; color: #080c14; }
        .iv-avatar-btn { width: 36px; height: 36px; border-radius: 50%; background: rgba(0,229,195,0.15); border: 1.5px solid rgba(0,229,195,0.35); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #00e5c3; cursor: pointer; position: relative; }
        .iv-dropdown { position: absolute; top: 44px; right: 0; background: #0d1220; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 6px; min-width: 160px; box-shadow: 0 16px 40px rgba(0,0,0,0.5); }
        .iv-dropdown li { list-style: none; padding: 10px 14px; font-size: 13px; color: #e8edf8; border-radius: 8px; cursor: pointer; transition: background 0.15s; }
        .iv-dropdown li:hover { background: rgba(255,255,255,0.07); }

        .iv-page {
          min-height: 100vh;
          padding: 80px 20px 40px;
          background: radial-gradient(ellipse at 20% 50%, rgba(124,58,237,0.08) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 20%, rgba(0,229,195,0.06) 0%, transparent 50%),
                      linear-gradient(160deg, #080c14 0%, #0a1020 100%);
        }

        .iv-grid {
          display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
          max-width: 1060px; margin: 0 auto 20px;
        }
        @media (max-width: 740px) { .iv-grid { grid-template-columns: 1fr; } }

        .iv-panel {
          background: rgba(12,18,35,0.85); border: 1px solid rgba(255,255,255,0.07);
          border-radius: 24px; padding: 24px;
          display: flex; flex-direction: column; align-items: center; gap: 14px;
          position: relative; overflow: hidden;
        }
        .iv-anime-wrap {
          width: 170px; height: 210px; position: relative;
        }
        .iv-aura {
          position: absolute; inset: -20px; border-radius: 50%;
          background: radial-gradient(ellipse, rgba(0,229,195,0.12) 0%, transparent 70%);
          animation: auraPulse 3s ease-in-out infinite; z-index: -1;
        }
        @keyframes auraPulse { 0%, 100% { opacity: 0.5; transform: scale(1); } 50% { opacity: 1; transform: scale(1.1); } }
        .iv-panel-name { font-size: 16px; font-weight: 700; color: #e8edf8; }
        .iv-panel-sub { font-size: 12px; color: #7a8ba8; }
        .iv-status-chip {
          display: flex; align-items: center; gap: 8px;
          background: rgba(0,229,195,0.08); border: 1px solid rgba(0,229,195,0.2);
          border-radius: 20px; padding: 6px 14px;
          font-size: 12px; color: #00e5c3; font-weight: 500; min-height: 32px; text-align: center;
        }

        .iv-speed-control {
          display: flex; flex-direction: column; gap: 8px; width: 100%;
          margin: 4px 0 8px; padding: 12px;
          background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px;
        }
        .iv-speed-header { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #7a8ba8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
        .iv-speed-current { color: #00e5c3; font-weight: 700; }
        .iv-speed-buttons { display: flex; gap: 6px; width: 100%; }
        .iv-speed-btn { flex: 1; padding: 6px 4px; border-radius: 8px; border: 1px solid transparent; font-family: 'Sora', sans-serif; font-size: 11px; font-weight: 600; cursor: pointer; color: #7a8ba8; background: rgba(255,255,255,0.03); transition: all 0.2s ease; }
        .iv-speed-btn.active { background: rgba(0,229,195,0.15); color: #00e5c3; border-color: rgba(0,229,195,0.3); }

        .iv-qbox {
          width: 100%; background: rgba(124,58,237,0.08); border: 1px solid rgba(124,58,237,0.2);
          border-radius: 16px; padding: 16px 18px; font-size: 14px; color: #e8edf8; line-height: 1.6; font-weight: 600;
        }
        .iv-qlabel { font-size: 10px; font-weight: 700; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
        .iv-video-wrap { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 16px; position: relative; overflow: hidden; }
        .iv-video { width: 100%; height: 100%; object-fit: cover; }
        .iv-rec-badge { position: absolute; top: 12px; right: 12px; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); border-radius: 20px; padding: 4px 10px; font-size: 10px; font-weight: 700; color: #ff4f6a; display: flex; align-items: center; gap: 6px; }
        .iv-rec-dot { width: 6px; height: 6px; border-radius: 50%; background: #ff4f6a; animation: pulse 1s ease-in-out infinite alternate; }

        .iv-answer-area { width: 100%; display: flex; flex-direction: column; gap: 12px; }
        .iv-input-toggle { display: flex; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 3px; gap: 4px; }
        .iv-toggle-btn { flex: 1; padding: 7px; border-radius: 9px; border: none; font-family: 'Sora', sans-serif; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .iv-toggle-active { background: rgba(0,229,195,0.15); color: #00e5c3; border: 1px solid rgba(0,229,195,0.3); }
        .iv-toggle-inactive { background: transparent; color: #7a8ba8; }

        .iv-textarea { width: 100%; height: 90px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px 16px; color: #e8edf8; font-family: 'Sora', sans-serif; font-size: 13px; line-height: 1.7; outline: none; }
        .iv-record-btn { width: 100%; padding: 13px; border-radius: 14px; border: none; cursor: pointer; font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .iv-record-idle { background: rgba(124,58,237,0.15); color: #a78bfa; border: 1.5px solid rgba(124,58,237,0.3); }
        .iv-record-active { background: rgba(255,79,106,0.15); color: #ff4f6a; border: 1.5px solid rgba(255,79,106,0.4); animation: recordGlow 1s ease-in-out infinite alternate; }
        @keyframes recordGlow { from { box-shadow: 0 0 0 rgba(255,79,106,0); } to { box-shadow: 0 0 20px rgba(255,79,106,0.3); } }

        .iv-btn { width: 100%; padding: 12px 20px; border-radius: 12px; border: none; font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .iv-btn-primary { background: linear-gradient(135deg,#00e5c3,#00b8ff); color: #050d14; }
        .iv-btn-ghost { background: rgba(255,255,255,0.05); color: #e8edf8; border: 1px solid rgba(255,255,255,0.1); }
        .iv-btn-danger { background: rgba(255,79,106,0.12); color: #ff4f6a; border: 1px solid rgba(255,79,106,0.25); max-width: 200px; margin: 0 auto; }

        .iv-feedback { width: 100%; background: rgba(0,229,195,0.05); border: 1px solid rgba(0,229,195,0.18); border-radius: 16px; padding: 16px 18px; font-size: 13px; color: #b8c8d8; line-height: 1.8; white-space: pre-wrap; }
        .iv-score-bar { width: 100%; display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.04); border-radius: 10px; padding: 10px 14px; }
        .iv-score-bar-fill { height: 6px; border-radius: 3px; background: linear-gradient(90deg,#00e5c3,#00b8ff); transition: width 1s ease; }
        .iv-score-bar-bg { flex: 1; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.08); overflow: hidden; }

        .iv-action-row { display: flex; gap: 8px; width: 100%; margin-top: 4px; }
        .iv-action-btn { flex: 1; padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04); color: #e8edf8; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .iv-action-btn:hover { background: rgba(255,255,255,0.08); border-color: rgba(0,229,195,0.3); }

        .iv-live-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; width: 100%; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 10px; text-align: center; }
        .iv-metric-val { font-size: 13px; font-weight: 800; color: #00e5c3; }
        .iv-metric-lbl { font-size: 10px; color: #7a8ba8; text-transform: uppercase; margin-top: 2px; }

        .iv-results { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
        .iv-results-hero { background: rgba(12,18,35,0.9); border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; padding: 32px; display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }
      `}</style>

      {/* ── Navbar ── */}
      <nav className="iv-navbar">
        <div className="iv-brand" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <img src="/prepfly-logo.png" alt="PrepFly" style={{ width: "32px", height: "32px", borderRadius: "50%", objectFit: "cover", boxShadow: "0 0 10px rgba(0,196,167,0.4)" }} />
          <span style={{ fontSize: "18px", fontWeight: 900, color: "#fff", letterSpacing: "-0.5px" }}>Prep<span style={{ color: "#00c4a7" }}>Fly</span></span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {atsScore && (
            <div style={{ background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "8px", padding: "4px 10px", fontSize: "11px", color: "#00c4a7", fontWeight: 700 }}>
              ATS Match: {atsScore}%
            </div>
          )}
          {avgScore && interviewStarted && (
            <div style={{ fontSize: 12, color: "#7a8ba8" }}>
              Avg Score: <span style={{ color: "#00e5c3", fontWeight: 700 }}>{avgScore}/10</span>
            </div>
          )}
          <div style={{ position: "relative" }}>
            <div className="iv-avatar-btn" onClick={() => setMenuOpen(!menuOpen)}>
              {user.avatar ? <img src={user.avatar} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }} /> : initials}
            </div>
            {menuOpen && (
              <ul className="iv-dropdown">
                <li onClick={() => navigate("/profile")}>My Profile</li>
                <li onClick={() => navigate("/dashboard")}>Dashboard</li>
                <li onClick={() => { localStorage.clear(); navigate("/"); }}>Logout</li>
              </ul>
            )}
          </div>
        </div>
      </nav>

      <div className="iv-page">
        {interviewComplete && finalResult ? (() => {
          const score100 = finalResult.overall_score_100 || Math.round((finalResult.overall_score || 7.5) * 10);
          const gInfo = getGradeInfo(score100);
          const sectionGrades = finalResult.section_grades || computeSectionGrades(score100, allFeedbacks);
          const earnedBadges = finalResult.badges || getBadges(score100, sectionGrades);
          const topStrengths = finalResult.top_strengths || ["Excellent Communication", "Strong Technical Knowledge", "Good Leadership", "Confident Speaker", "Excellent Resume Understanding"];
          const topImprovements = finalResult.top_improvements || ["Reduce filler words", "Improve DSA explanations", "Improve STAR responses", "Increase confidence", "Speak with more structure"];
          const prevScore100 = Number(localStorage.getItem("last_interview_score_100")) || Math.max(40, score100 - 6);
          const prevGInfo = getGradeInfo(prevScore100);
          const diffPct = prevScore100 > 0 ? Math.round(((score100 - prevScore100) / prevScore100) * 100) : 0;

          return (
            <div className="iv-results">
              {/* MAIN HERO CARD */}
              <div className="iv-results-hero" style={{ background: "rgba(12,18,35,0.95)", border: `1px solid ${gInfo.color}44`, boxShadow: `0 0 40px ${gInfo.color}15`, padding: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "16px" }}>
                  <div style={{ textAlign: "left" }}>
                    <div style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Executive Candidate Evaluation</div>
                    <div style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>{gInfo.label} Candidate</div>
                    <div style={{ fontSize: "13px", color: gInfo.color, fontWeight: 800, marginTop: "2px" }}>📌 Hiring Recommendation: {gInfo.rec}</div>
                  </div>

                  {/* Circular Grade Badge */}
                  <div style={{ width: "96px", height: "96px", borderRadius: "50%", background: gInfo.bgColor, border: `4px solid ${gInfo.color}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: `0 0 24px ${gInfo.color}44`, flexShrink: 0 }}>
                    <div style={{ fontSize: "32px", fontWeight: 900, color: gInfo.color, lineHeight: 1 }}>{gInfo.grade}</div>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "#fff", marginTop: "2px" }}>{score100}/100</div>
                  </div>
                </div>

                {/* Performance Level & Progress Indicator */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", width: "100%", margin: "12px 0" }}>
                  <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "12px", textAlign: "center" }}>
                    <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>PERFORMANCE LEVEL</div>
                    <div style={{ fontSize: "15px", fontWeight: 900, color: "#fff", marginTop: "2px" }}>{gInfo.level}</div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "12px", textAlign: "center" }}>
                    <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>LAST vs CURRENT GRADE</div>
                    <div style={{ fontSize: "14px", fontWeight: 900, color: "#fff", marginTop: "2px" }}>
                      {prevGInfo.grade} ➔ <span style={{ color: gInfo.color }}>{gInfo.grade}</span>
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "12px", textAlign: "center" }}>
                    <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>SCORE IMPROVEMENT</div>
                    <div style={{ fontSize: "15px", fontWeight: 900, color: diffPct >= 0 ? "#00c4a7" : "#ef4444", marginTop: "2px" }}>
                      {diffPct >= 0 ? `+${diffPct}%` : `${diffPct}%`}
                    </div>
                  </div>
                </div>

                {/* EARNED BADGES */}
                <div style={{ width: "100%", textAlign: "left", marginBottom: "8px" }}>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#94a3b8", textTransform: "uppercase", marginBottom: "8px" }}>🎖️ EARNED CANDIDATE BADGES</div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {earnedBadges.map((b, idx) => (
                      <span key={idx} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", padding: "6px 12px", borderRadius: "20px", fontSize: "12px", color: "#fff", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <span>{b.icon}</span> {b.name}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 12, marginTop: 10 }}>
                  <button className="iv-btn-primary" onClick={() => navigate("/dashboard")} style={{ padding: "10px 24px", width: "auto" }}>
                    ← Return to Dashboard
                  </button>
                  <button className="iv-btn-ghost" onClick={() => downloadPDF(finalResult, allFeedbacks)} style={{ width: "auto" }}>
                    📄 Download PDF Report
                  </button>
                </div>
              </div>

              {/* 10 SECTION GRADES BREAKDOWN */}
              <div style={{ background: "rgba(12,18,35,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>📊 Section Grades Breakdown (10 Dimensions)</h3>
                <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>Click on any dimension card below to view detailed FAANG-style behavioral evidence.</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "12px" }}>
                  {sectionGrades.map((sec, idx) => {
                    const isSelected = selectedEvidenceDimension?.name === sec.name;
                    return (
                      <div 
                        key={idx} 
                        onClick={() => setSelectedEvidenceDimension(isSelected ? null : sec)}
                        style={{ 
                          background: isSelected ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)", 
                          border: isSelected ? `2.5px solid ${sec.color}` : `1px solid ${sec.color}33`, 
                          borderRadius: "12px", 
                          padding: "12px", 
                          textAlign: "center",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          transform: isSelected ? "scale(1.03)" : "none"
                        }}
                      >
                        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>{sec.name}</div>
                        <div style={{ fontSize: "18px", fontWeight: 900, color: sec.color, marginTop: "4px" }}>
                          {sec.score} <span style={{ fontSize: "12px", opacity: 0.8 }}>({sec.grade})</span>
                        </div>
                        <div style={{ fontSize: "9px", color: "rgba(255,255,255,0.3)", marginTop: "4px" }}>
                          {isSelected ? "Hide Evidence ▲" : "View Evidence ▼"}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Evidence Viewer Panel */}
                {selectedEvidenceDimension && (
                  <div style={{ 
                    marginTop: "20px", 
                    background: "rgba(255,255,255,0.015)", 
                    border: `1.5px solid ${selectedEvidenceDimension.color}44`, 
                    borderRadius: "12px", 
                    padding: "16px",
                    textAlign: "left"
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 800, color: selectedEvidenceDimension.color }}>
                        🔍 Evidence Log: {selectedEvidenceDimension.name} ({selectedEvidenceDimension.score !== undefined ? `${selectedEvidenceDimension.score}/100` : "N/A"})
                      </div>
                      <span style={{ 
                        background: selectedEvidenceDimension.bgColor || "rgba(255,255,255,0.05)", 
                        color: selectedEvidenceDimension.color, 
                        fontSize: "10px", 
                        fontWeight: 800,
                        padding: "2px 8px",
                        borderRadius: "20px",
                        border: `1px solid ${selectedEvidenceDimension.color}33`
                      }}>
                        Confidence: {selectedEvidenceDimension.evidence_level || "Medium"}
                      </span>
                    </div>

                    {selectedEvidenceDimension.evidence && selectedEvidenceDimension.evidence.length > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", color: "#cbd5e1", lineHeight: "1.7" }}>
                        {selectedEvidenceDimension.evidence.map((point, pIdx) => (
                          <li key={pIdx} style={{ marginBottom: "6px" }}>{point}</li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ fontSize: "12px", color: "#94a3b8", fontStyle: "italic" }}>
                        No specific transcript evidence recorded for this dimension.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* TOP STRENGTHS & IMPROVEMENTS */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div style={{ background: "rgba(0,196,167,0.06)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "20px", padding: "20px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#00c4a7", marginBottom: "12px" }}>💪 Top Strengths</h4>
                  <ul style={{ paddingLeft: "0", listStyle: "none", margin: 0, fontSize: "13px", color: "#e2e8f0", lineHeight: "1.8" }}>
                    {finalResult.strengths && finalResult.strengths.length > 0 && typeof finalResult.strengths[0] === 'object' ? (
                      finalResult.strengths.map((str, idx) => (
                        <li key={idx} style={{ marginBottom: "12px" }}>
                          <strong style={{ color: "#fff", display: "block", fontSize: "13px" }}>✅ {str.title}</strong>
                          <span style={{ fontSize: "12px", color: "#94a3b8", display: "block", paddingLeft: "16px", marginTop: "2px" }}>↳ Evidence: {str.evidence}</span>
                        </li>
                      ))
                    ) : (
                      topStrengths.map((str, idx) => (
                        <li key={idx} style={{ marginBottom: "6px" }}>✅ {str}</li>
                      ))
                    )}
                  </ul>
                </div>
                <div style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "20px", padding: "20px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#f59e0b", marginBottom: "12px" }}>🎯 Focus Areas & Weaknesses</h4>
                  <ul style={{ paddingLeft: "0", listStyle: "none", margin: 0, fontSize: "13px", color: "#e2e8f0", lineHeight: "1.8" }}>
                    {finalResult.weaknesses && finalResult.weaknesses.length > 0 && typeof finalResult.weaknesses[0] === 'object' ? (
                      finalResult.weaknesses.map((imp, idx) => (
                        <li key={idx} style={{ marginBottom: "12px" }}>
                          <strong style={{ color: "#fff", display: "block", fontSize: "13px" }}>⚠️ {imp.title}</strong>
                          <span style={{ fontSize: "12px", color: "#94a3b8", display: "block", paddingLeft: "16px", marginTop: "2px" }}>↳ Evidence: {imp.evidence}</span>
                        </li>
                      ))
                    ) : (
                      topImprovements.map((imp, idx) => (
                        <li key={idx} style={{ marginBottom: "6px" }}>⚠️ {imp}</li>
                      ))
                    )}
                  </ul>
                </div>
              </div>

              {/* QUESTION BY QUESTION BREAKDOWN */}
              {allFeedbacks.map((item, i) => (
                <div key={i} className="iv-feedback" style={{ background: "rgba(12,18,35,0.7)", borderColor: "rgba(255,255,255,0.08)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#a78bfa" }}>Q{i + 1}: {item.question}</div>
                    <ScoreRing score={item.score || 0} size={42} />
                  </div>
                  <div style={{ fontSize: 13, color: "#94a3b8", fontStyle: "italic", marginBottom: 8 }}>"{item.response}"</div>
                  <div style={{ fontSize: 13, color: "#e2e8f0" }}>{item.feedback}</div>
                </div>
              ))}
            </div>
          );
        })() : !interviewStarted ? (
          /* ══ START SCREEN ══ */
          <div style={{ maxWidth: 520, margin: "40px auto", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
            <div style={{ width: 180, height: 220 }}>
              <CircleWavesAvatar isTalking={false} isThinking={false} />
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: "#e8edf8" }}>Meet {AI_INTERVIEWER.name}, Your AI Recruiter</h1>
            <p style={{ fontSize: 14, color: "#7a8ba8", lineHeight: 1.6 }}>
              {AI_INTERVIEWER.name} will conduct a 1-on-1 recruiter interview with warm voice interactions, real-time live performance tracking, and dynamic follow-up questions.
            </p>
            <button className="iv-btn-primary" onClick={startInterview} style={{ padding: "14px 40px", fontSize: 16, borderRadius: 16, width: "auto" }}>
              🎙 Start Recruiter Interview
            </button>
          </div>
        ) : (
          /* ══ ACTIVE INTERVIEW ══ */
          <>
            <div className="iv-grid">
              {/* AI Panel */}
              <div className="iv-panel">
                <div className="iv-anime-wrap">
                  <div className="iv-aura" />
                  <CircleWavesAvatar isTalking={isAvaTalking} isThinking={isAvaThinking} />
                </div>
                <div className="iv-panel-name">{AI_INTERVIEWER.name}</div>
                <div className="iv-panel-sub">{AI_INTERVIEWER.role}</div>

                <div className="iv-status-chip">
                  <AudioWave active={isAvaTalking} />
                  <span>{avaStatus}</span>
                </div>

                {/* Voice Speed */}
                <div className="iv-speed-control">
                  <div className="iv-speed-header">
                    <span>Voice Speed</span>
                    <span className="iv-speed-current">{speechSpeed}x</span>
                  </div>
                  <div className="iv-speed-buttons">
                    {[1.0, 1.25, 1.5, 1.75, 2.0].map(speed => (
                      <button key={speed} className={`iv-speed-btn ${speechSpeed === speed ? "active" : ""}`} onClick={() => handleSpeedChange(speed)}>
                        {speed}x
                      </button>
                    ))}
                  </div>
                </div>

                {/* Question & Stage Card */}
                {question && (
                  <div className="iv-qbox">
                    <div className="iv-qlabel">
                      <span>Question {questionNumber} of {totalQuestions}</span>
                      <span style={{ color: "#00e5c3", fontSize: "11px" }}>Stage: {currentStage}</span>
                    </div>
                    {formatAvaMessage(question)}
                  </div>
                )}

                {/* Hint & Repeat Controls */}
                <div className="iv-action-row">
                  <button className="iv-action-btn" onClick={requestHint} disabled={isFetchingHint}>
                    💡 {isFetchingHint ? "Thinking..." : "Ask Hint"}
                  </button>
                  <button className="iv-action-btn" onClick={requestRepeat}>
                    🔁 Repeat Question
                  </button>
                </div>

                {hintText && (
                  <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: "12px", padding: "10px 14px", fontSize: "12px", color: "#fbbf24", width: "100%" }}>
                    💡 <strong>Interviewer Hint:</strong> {hintText}
                  </div>
                )}
              </div>

              {/* Candidate Panel */}
              <div className="iv-panel">
                <div className="iv-video-wrap">
                  <video ref={videoRef} autoPlay muted playsInline className="iv-video" />
                  <div className="iv-rec-badge">
                    <div className="iv-rec-dot" /> REC
                  </div>
                </div>

                <div className="iv-panel-name">{displayName}</div>
                <div className="iv-panel-sub">{user.email}</div>

                {/* Live Real-Time Analytics Bar */}
                {liveMetrics && (
                  <div className="iv-live-metrics">
                    <div>
                      <div className="iv-metric-val">{liveMetrics.wpm} WPM</div>
                      <div className="iv-metric-lbl">Speed</div>
                    </div>
                    <div>
                      <div className="iv-metric-val">{liveMetrics.filler_words_count}</div>
                      <div className="iv-metric-lbl">Fillers</div>
                    </div>
                    <div>
                      <div className="iv-metric-val">{liveMetrics.confidence_score}/10</div>
                      <div className="iv-metric-lbl">Confidence</div>
                    </div>
                  </div>
                )}

                {/* Response Input */}
                <div className="iv-answer-area">
                  <div className="iv-input-toggle">
                    <button className={`iv-toggle-btn ${inputMode === "voice" ? "iv-toggle-active" : "iv-toggle-inactive"}`} onClick={() => setInputMode("voice")}>
                      🎤 Voice
                    </button>
                    <button className={`iv-toggle-btn ${inputMode === "text" ? "iv-toggle-active" : "iv-toggle-inactive"}`} onClick={() => setInputMode("text")}>
                      ⌨️ Type
                    </button>
                  </div>

                  {inputMode === "voice" ? (
                    <button className={`iv-record-btn ${isRecording ? "iv-record-active" : "iv-record-idle"}`} onClick={isRecording ? stopRecording : startRecording} disabled={isTranscribing}>
                      {isTranscribing ? "Transcribing..." : isRecording ? "⏹ Stop Recording" : "🎤 Hold to Record Answer"}
                    </button>
                  ) : (
                    <textarea
                      className="iv-textarea"
                      value={response}
                      onChange={e => setResponse(e.target.value)}
                      placeholder="Type your answer here... (Ctrl+Enter to submit)"
                      onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) submitResponse(); }}
                    />
                  )}

                  {response && (
                    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "10px 14px", fontSize: 13, color: "#b8c8d8" }}>
                      <div style={{ fontSize: 10, color: "#7a8ba8", fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>Current Draft</div>
                      {response}
                    </div>
                  )}

                  {response && (
                    <button className="iv-btn iv-btn-primary" onClick={submitResponse} disabled={isAvaThinking}>
                      {isAvaThinking ? "Evaluating..." : "Submit Answer →"}
                    </button>
                  )}

                  {showNext && (
                    <button className="iv-btn iv-btn-ghost" onClick={fetchNextQuestion}>
                      Next Question →
                    </button>
                  )}
                </div>

                {feedback && (
                  <div className="iv-feedback">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#00e5c3", textTransform: "uppercase" }}>{AI_INTERVIEWER.name}'s Evaluation</span>
                      <ScoreRing score={feedback.score} size={44} />
                    </div>
                    {feedback.feedback}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "center" }}>
              <button className="iv-btn iv-btn-danger" onClick={endInterview}>
                End Interview & Get Score
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
};

export default InterviewPage;