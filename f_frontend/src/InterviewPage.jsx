import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = "http://localhost:5000";

// ── Anime SVG Avatar (Hana) ─────────────────────────────────────────────────
const AnimeAvatar = ({ isTalking, isThinking }) => {
  return (
    <svg
      viewBox="0 0 160 200"
      style={{ width: "100%", height: "100%", filter: "drop-shadow(0 0 18px rgba(0,229,195,0.4))" }}
    >
      {/* Hair back */}
      <ellipse cx="80" cy="68" rx="52" ry="58" fill="#1a0a2e" />
      {/* Long hair left */}
      <path d="M30 80 Q15 130 22 170 Q30 185 38 175 Q32 140 36 100 Z" fill="#1a0a2e" />
      {/* Long hair right */}
      <path d="M130 80 Q145 130 138 170 Q130 185 122 175 Q128 140 124 100 Z" fill="#1a0a2e" />
      {/* Hair streaks */}
      <path d="M32 85 Q20 120 25 160" stroke="#6b21a8" strokeWidth="2" fill="none" opacity="0.6" />
      <path d="M128 85 Q140 120 135 160" stroke="#6b21a8" strokeWidth="2" fill="none" opacity="0.6" />

      {/* Neck */}
      <rect x="68" y="128" width="24" height="20" rx="6" fill="#fde8d8" />

      {/* Face */}
      <ellipse cx="80" cy="95" rx="40" ry="44" fill="#fde8d8" />

      {/* Blush */}
      <ellipse cx="55" cy="105" rx="10" ry="6" fill="#ffb5c2" opacity="0.5" />
      <ellipse cx="105" cy="105" rx="10" ry="6" fill="#ffb5c2" opacity="0.5" />

      {/* Eyes */}
      {isThinking ? (
        <>
          {/* Squinting thinking eyes */}
          <path d="M60 90 Q67 94 74 90" stroke="#2d1654" strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M86 90 Q93 94 100 90" stroke="#2d1654" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          {/* Normal wide anime eyes */}
          <ellipse cx="67" cy="92" rx="10" ry="11" fill="#2d1654" />
          <ellipse cx="93" cy="92" rx="10" ry="11" fill="#2d1654" />
          {/* Iris */}
          <ellipse cx="67" cy="93" rx="7" ry="8" fill="#7c3aed" />
          <ellipse cx="93" cy="93" rx="7" ry="8" fill="#7c3aed" />
          {/* Pupil */}
          <ellipse cx="67" cy="93" rx="4" ry="5" fill="#1a0a2e" />
          <ellipse cx="93" cy="93" rx="4" ry="5" fill="#1a0a2e" />
          {/* Eye shine */}
          <circle cx="70" cy="89" r="2.5" fill="white" opacity="0.95" />
          <circle cx="96" cy="89" r="2.5" fill="white" opacity="0.95" />
          <circle cx="64" cy="95" r="1.2" fill="white" opacity="0.5" />
          <circle cx="90" cy="95" r="1.2" fill="white" opacity="0.5" />
        </>
      )}

      {/* Eyebrows */}
      <path d="M57 79 Q67 74 77 79" stroke="#2d1654" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <path d="M83 79 Q93 74 103 79" stroke="#2d1654" strokeWidth="2.5" fill="none" strokeLinecap="round" />

      {/* Nose */}
      <path d="M78 105 Q80 108 82 105" stroke="#d4a0a0" strokeWidth="1.5" fill="none" strokeLinecap="round" />

      {/* Mouth */}
      {isTalking ? (
        // Animated talking mouth
        <>
          <ellipse cx="80" cy="117" rx="10" ry="5" fill="#c96d8a" />
          <ellipse cx="80" cy="116" rx="8" ry="3" fill="#ff9ab0" />
          <ellipse cx="80" cy="117" rx="6" ry="2.5" fill="#2d1654" opacity="0.3" />
        </>
      ) : (
        // Smiling mouth
        <>
          <path d="M70 115 Q80 123 90 115" stroke="#c96d8a" strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d="M72 116 Q80 121 88 116" fill="#ff9ab0" opacity="0.4" />
        </>
      )}

      {/* Collar / outfit */}
      <path d="M40 152 Q60 145 80 148 Q100 145 120 152 L115 200 L45 200 Z" fill="#6d28d9" />
      <path d="M80 148 L72 165 L80 162 L88 165 Z" fill="#a78bfa" opacity="0.8" />
      {/* Collar trim */}
      <path d="M40 152 Q60 143 80 148" stroke="#a78bfa" strokeWidth="1.5" fill="none" />
      <path d="M80 148 Q100 143 120 152" stroke="#a78bfa" strokeWidth="1.5" fill="none" />

      {/* Hair front strands */}
      <path d="M44 72 Q38 88 40 100" stroke="#1a0a2e" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M52 60 Q44 75 46 90" stroke="#1a0a2e" strokeWidth="7" fill="none" strokeLinecap="round" />
      <path d="M116 72 Q122 88 120 100" stroke="#1a0a2e" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M108 60 Q116 75 114 90" stroke="#1a0a2e" strokeWidth="7" fill="none" strokeLinecap="round" />
      {/* Center bang */}
      <path d="M68 52 Q62 68 64 84" stroke="#1a0a2e" strokeWidth="9" fill="none" strokeLinecap="round" />
      <path d="M80 48 Q78 62 80 78" stroke="#1a0a2e" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M92 52 Q98 68 96 84" stroke="#1a0a2e" strokeWidth="9" fill="none" strokeLinecap="round" />

      {/* Hair shine */}
      <path d="M56 58 Q68 52 80 56" stroke="#7c3aed" strokeWidth="2" fill="none" opacity="0.5" />

      {/* Ears */}
      <ellipse cx="40" cy="96" rx="7" ry="9" fill="#fde8d8" />
      <ellipse cx="120" cy="96" rx="7" ry="9" fill="#fde8d8" />
      <ellipse cx="40" cy="96" rx="4" ry="6" fill="#ffb5c2" opacity="0.5" />
      <ellipse cx="120" cy="96" rx="4" ry="6" fill="#ffb5c2" opacity="0.5" />

      {/* AI headset / decoration */}
      <circle cx="37" cy="90" r="5" fill="#00e5c3" opacity="0.8" />
      <circle cx="37" cy="90" r="3" fill="#080c14" />
      <circle cx="37" cy="90" r="1.5" fill="#00e5c3" />
      <path d="M37 85 L37 75 Q50 68 55 70" stroke="#00e5c3" strokeWidth="1.5" fill="none" opacity="0.7" />
    </svg>
  );
};

// ── Talking animation dots ──────────────────────────────────────────────────
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
    <style>{`
      @keyframes wave {
        from { height: 6px; }
        to { height: 22px; }
      }
    `}</style>
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
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="8" />
        <circle
          cx={size/2} cy={size/2} r={r}
          fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - pct)}
          strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x={size/2} y={size/2 + 1} textAnchor="middle" dominantBaseline="middle"
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
  const [sessionId, setSessionId]     = useState(null);
  const [user, setUser]               = useState({ name: "", email: "", avatar: "", _id: "" });

  // ── Interview state ────────────────────────────────────────────────────
  const [interviewStarted, setInterviewStarted]   = useState(false);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [question, setQuestion]                   = useState("");
  const [questionNumber, setQuestionNumber]       = useState(0);
  const [response, setResponse]                   = useState("");
  const [feedback, setFeedback]                   = useState(null);   // { feedback, score, strength, improvement, tip }
  const [showNext, setShowNext]                   = useState(false);
  const [allFeedbacks, setAllFeedbacks]           = useState([]);
  const [finalResult, setFinalResult]             = useState(null);   // { overall_score, grade, report, ... }

  // ── Anime state ────────────────────────────────────────────────────────
  const [isHanaTalking, setIsHanaTalking]   = useState(false);
  const [isHanaThinking, setIsHanaThinking] = useState(false);
  const [hanaStatus, setHanaStatus]         = useState("Ready to interview you!");

  // ── Voice recording ────────────────────────────────────────────────────
  const [isRecording, setIsRecording]       = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [inputMode, setInputMode]           = useState("voice"); // "voice" | "text"
  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const recognitionRef   = useRef(null);
  const webSpeechTranscriptRef = useRef("");

  // ── Video (candidate webcam) ───────────────────────────────────────────
  const videoRef             = useRef(null);
  const videoStreamRef       = useRef(null);
  const sessionRecorderRef   = useRef(null);
  const sessionChunksRef     = useRef([]);

  // ── Audio playback ─────────────────────────────────────────────────────
  const currentAudioRef = useRef(null);
  const speechQueue     = useRef([]);
  const isAudioPlaying  = useRef(false);
  const speechSpeedRef  = useRef(1.5);
  const [speechSpeed, setSpeechSpeed] = useState(() => {
    const stored = localStorage.getItem("speechSpeed");
    const val = stored ? Number(stored) : 1.5;
    speechSpeedRef.current = val;
    return val;
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

  // ── Menu ───────────────────────────────────────────────────────────────
  const [menuOpen, setMenuOpen] = useState(false);

  // ── Results extras ─────────────────────────────────────────────────────
  const [videoBlob, setVideoBlob]     = useState(null);   // local blob for video download
  const [reportPolled, setReportPolled] = useState(false); // track if we started polling
  const reportPollRef = useRef(null);

  // ── Init ───────────────────────────────────────────────────────────────
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
    } catch { /* silent */ }
  }, []);

  // ── Webcam setup ───────────────────────────────────────────────────────
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      videoStreamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;

      // Start recording the full session with browser compatibility fallbacks
      let recorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType: "video/webm;codecs=vp9" });
      } catch (e) {
        try {
          recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
        } catch (e2) {
          try {
            recorder = new MediaRecorder(stream, { mimeType: "video/mp4" });
          } catch (e3) {
            recorder = new MediaRecorder(stream);
          }
        }
      }
      recorder.ondataavailable = e => { if (e.data.size > 0) sessionChunksRef.current.push(e.data); };
      recorder.start(3000); // collect every 3s
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
      setIsHanaTalking(false);
      return;
    }
    const item = speechQueue.current.shift();
    const nextText = item.text;
    isAudioPlaying.current = true;
    setIsHanaTalking(true);

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
        
        // Trigger callback if provided (e.g. to show text)
        if (item.onStart) item.onStart();
        
        audio.play();
        audio.playbackRate = speechSpeedRef.current;
        audio.onended = () => {
          isAudioPlaying.current = false;
          setIsHanaTalking(false);
          playNextInQueue();
        };
      })
      .catch(() => {
        if (item.onStart) item.onStart(); // Fallback to show text even if audio fails
        isAudioPlaying.current = false;
        setIsHanaTalking(false);
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
        
        rec.onstart = () => {
          setHanaStatus("Listening... Speak now! 🎙️");
        };
        
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
        
        rec.onerror = (err) => {
          console.warn("Web Speech API recognition error:", err);
        };
        
        rec.start();
        recognitionRef.current = rec;
        webSpeechActive = true;
      } catch (err) {
        console.warn("Could not start Web Speech Recognition:", err);
      }
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
          setHanaStatus("Got it! Review and submit when ready.");
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      if (!webSpeechActive) {
        setHanaStatus("Recording audio...");
      }
    } catch (err) {
      if (!webSpeechActive) {
        alert("Microphone access denied. Please allow microphone and try again.");
      }
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) { /* ignore */ }
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (blob) => {
    setIsTranscribing(true);
    setHanaStatus("Transcribing audio (backend fallback)...");
    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        try {
          const base64data = reader.result;
          const b64 = base64data.split(",")[1];

          const res  = await fetch(`${BACKEND_URL}/speech-to-text`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio_base64: b64, mime_type: "audio/webm" }),
          });
          const data = await res.json();
          if (data.transcript) {
            setResponse(data.transcript);
            setHanaStatus("Got it! Review and submit when ready.");
          } else {
            setHanaStatus("Couldn't catch that. Try again or type your answer.");
          }
        } catch {
          setHanaStatus("Transcription failed. Please type your answer.");
        } finally {
          setIsTranscribing(false);
        }
      };
      reader.readAsDataURL(blob);
    } catch {
      setHanaStatus("Transcription failed. Please type your answer.");
      setIsTranscribing(false);
    }
  };

  // ── Interview actions ──────────────────────────────────────────────────
  const fetchNextQuestion = async () => {
    if (!sessionId) return;
    setIsHanaThinking(true);
    setHanaStatus("Thinking of the next question...");
    setFeedback(null);
    setShowNext(false);
    setResponse("");

    try {
      const endpoint = questionNumber === 0 ? "/start-interview" : "/next";
      const res  = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();

      if (data.question) {
        setIsHanaThinking(true);
        setHanaStatus("Hana is preparing your question...");
        
        playSpeech(data.question, () => {
          setQuestion(data.question);
          setQuestionNumber(data.question_number || questionNumber + 1);
          setIsHanaThinking(false);
          setHanaStatus("Asking you a question...");
          setTimeout(() => setHanaStatus("Your turn to answer!"), 2000);
        });
      } else if (data.message === "Interview complete" || data.done) {
        endInterview();
      }
    } catch {
      setIsHanaThinking(false);
      setHanaStatus("Connection error. Try again.");
    }
  };

  const submitResponse = async () => {
    if (!response.trim()) return alert("Please record or type your response first.");
    setIsHanaThinking(true);
    setHanaStatus("Evaluating your answer...");

    try {
      const res  = await fetch(`${BACKEND_URL}/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer: response }),
      });
      const data = await res.json();

      if (res.ok) {
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
          setIsHanaThinking(false);
          const scoreVal = feedbackObj.score || 0;
          setHanaStatus(`Interview complete! Final score: ${scoreVal}/10`);
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
          setIsHanaThinking(false);
          const scoreVal = feedbackObj.score || 0;
          setHanaStatus(`Score: ${scoreVal}/10 — ${scoreVal >= 7 ? "Great job!" : "Keep going!"}`);
          playSpeech(scoreVal >= 7
            ? `Good answer! You scored ${scoreVal} out of 10.`
            : `Thanks for answering. You scored ${scoreVal} out of 10. Let me give you some feedback.`
          );
        }
      } else {
        setIsHanaThinking(false);
        setHanaStatus("Error submitting. Try again.");
      }
    } catch {
      setIsHanaThinking(false);
      setHanaStatus("Submission failed.");
    }
  };

  const isEndingRef = useRef(false);

  // ── PDF download ───────────────────────────────────────────────────────
  const downloadPDF = (result, feedbacks) => {
    const gradeColors = { S:"#ffd700", A:"#00e5c3", B:"#00b8ff", C:"#f59e0b", D:"#f97316", F:"#ff4f6a" };
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
    <div class="hdr"><div class="brand">⚡ InterviewAI Report</div><div class="meta">Generated: ${new Date().toLocaleString()}<br/>Questions: ${feedbacks.length}</div></div>
    <div class="hero">
      <div class="grade" style="border:3px solid ${gc};background:${gc}18;color:${gc}">${result.grade||"—"}</div>
      <div><div class="sl">Overall Score</div><div class="sv">${result.overall_score||0}/10</div>${result.report?`<div class="rpt">${result.report}</div>`:""}</div>
    </div>
    <div class="st">Question-by-Question Breakdown</div>
    ${feedbacks.map((item,i)=>{const sc=item.score||0;const c=sc>=8?"#00e5c3":sc>=6?"#00b8ff":sc>=4?"#f59e0b":"#ff4f6a";return `<div class="qa"><div class="ql">Question ${i+1}</div><div class="qt">${item.question||""}</div><span class="sc" style="background:${c}18;color:${c};border:1px solid ${c}44">Score: ${sc}/10</span><div class="al">Your Answer</div><div class="at">"${item.response||""}"</div><div class="fl">Feedback</div><div class="ft">${item.feedback||"—"}</div></div>`;}).join("")}
    <div class="ftr">Generated by InterviewAI · ${new Date().toLocaleString()}</div>
    </body></html>`;
    const win = window.open("", "_blank");
    win.document.write(html);
    win.document.close();
    setTimeout(() => win.print(), 600);
  };

  // ── Video download ─────────────────────────────────────────────────────
  const downloadVideo = (blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href = url; a.download = `interview-${Date.now()}.webm`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  };

  const endInterview = async () => {
    if (isEndingRef.current) return;
    isEndingRef.current = true;

    // Stop audio immediately
    speechQueue.current = [];
    isAudioPlaying.current = false;
    setIsHanaTalking(false);
    if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null; }

    setIsHanaThinking(true);
    setHanaStatus("Wrapping up...");

    // ── Save video blob locally for download (no upload wait) ──────────
    stopWebcam();
    let localVideoBlob = null;
    if (sessionChunksRef.current.length > 0) {
      localVideoBlob = new Blob(sessionChunksRef.current, { type: "video/webm" });
      setVideoBlob(localVideoBlob);
      // Upload to backend in background using FormData (no size limit, more efficient!)
      (async () => {
        try {
          const fd = new FormData();
          fd.append("video", localVideoBlob, `recording_${sessionId}.webm`);
          fd.append("session_id", sessionId);

          await fetch(`${BACKEND_URL}/save-recording`, {
            method: "POST",
            body: fd,
          });
        } catch (e) {
          console.warn("Background recording upload failed:", e);
        }
      })();
    }

    // ── Call end-interview — now instant from backend ──────────────────
    let data = { overall_score: 0, grade: "N/A", report: "Generating your report…" };
    try {
      const res = await fetch(`${BACKEND_URL}/end-interview`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      data = await res.json();
    } catch { /* use defaults */ }

    setFinalResult(data);
    playSpeech(`Interview complete! You scored ${data.overall_score} out of 10, grade ${data.grade}. Great job!`);

    setInterviewStarted(false);
    setInterviewComplete(true);
    setIsHanaThinking(false);

    // ── Poll for background Gemini report (max 30s) ────────────────────
    let attempts = 0;
    const poll = setInterval(async () => {
      attempts++;
      try {
        const r  = await fetch(`${BACKEND_URL}/session-report/${sessionId}`);
        const rd = await r.json();
        if (rd.final_report && !rd.final_report.includes("Generating")) {
          setFinalResult(prev => ({ ...prev, report: rd.final_report }));
          clearInterval(poll);
        }
      } catch { /* silent */ }
      if (attempts >= 12) clearInterval(poll); // stop after 60s
    }, 5000);
    reportPollRef.current = poll;
  };

  // ── Start interview ────────────────────────────────────────────────────
  const startInterview = async () => {
    setInterviewStarted(true);
    await startWebcam();
    playSpeech("Hello! I'm Hana, your AI interviewer. Let's begin. I'll ask you a few questions based on your resume. Please answer clearly and take your time.");
    setTimeout(() => fetchNextQuestion(), 1500);
  };

  // ── Derived ────────────────────────────────────────────────────────────
  const displayName = user.name
    ? user.name.split(" ")[0]
    : user.email?.split("@")[0] || "Candidate";

  const initials = user.name
    ? user.name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : (user.email?.[0] || "U").toUpperCase();

  const avgScore = allFeedbacks.length
    ? (allFeedbacks.reduce((s, f) => s + (f.score || 0), 0) / allFeedbacks.length).toFixed(1)
    : null;

  // ════════════════════════════════════════════════════════════════════════
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; font-family: 'Sora', sans-serif; }

        /* ── Navbar ── */
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

        /* ── Page ── */
        .iv-page {
          min-height: 100vh;
          padding: 80px 20px 40px;
          background: radial-gradient(ellipse at 20% 50%, rgba(124,58,237,0.08) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 20%, rgba(0,229,195,0.06) 0%, transparent 50%),
                      linear-gradient(160deg, #080c14 0%, #0a1020 100%);
        }

        /* ── Main grid ── */
        .iv-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          max-width: 1060px;
          margin: 0 auto 20px;
        }
        @media (max-width: 740px) { .iv-grid { grid-template-columns: 1fr; } }

        /* ── Panel ── */
        .iv-panel {
          background: rgba(12,18,35,0.85);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 24px;
          padding: 24px;
          display: flex; flex-direction: column; align-items: center; gap: 14px;
          position: relative; overflow: hidden;
        }
        .iv-panel::before {
          content: '';
          position: absolute; inset: 0;
          background: linear-gradient(135deg, rgba(124,58,237,0.04) 0%, transparent 60%);
          pointer-events: none;
        }

        /* ── Anime panel ── */
        .iv-anime-wrap {
          width: 170px; height: 210px;
          position: relative;
          animation: ${isHanaTalking ? "talkBob 0.3s ease-in-out infinite alternate" : isHanaThinking ? "thinkFloat 2s ease-in-out infinite" : "idleFloat 4s ease-in-out infinite"};
        }
        @keyframes idleFloat {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }
        @keyframes talkBob {
          from { transform: translateY(0) rotate(-0.5deg); }
          to { transform: translateY(-4px) rotate(0.5deg); }
        }
        @keyframes thinkFloat {
          0%, 100% { transform: translateY(0) rotate(-1deg); }
          50% { transform: translateY(-8px) rotate(1deg); }
        }
        .iv-aura {
          position: absolute; inset: -20px; border-radius: 50%;
          background: radial-gradient(ellipse, rgba(0,229,195,0.12) 0%, transparent 70%);
          animation: auraPulse 3s ease-in-out infinite;
          z-index: -1;
        }
        @keyframes auraPulse {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.1); }
        }
        .iv-panel-name { font-size: 16px; font-weight: 700; color: #e8edf8; }
        .iv-panel-sub { font-size: 12px; color: #7a8ba8; }
        .iv-status-chip {
          display: flex; align-items: center; gap: 8px;
          background: rgba(0,229,195,0.08); border: 1px solid rgba(0,229,195,0.2);
          border-radius: 20px; padding: 6px 14px;
          font-size: 12px; color: #00e5c3; font-weight: 500;
          min-height: 32px; text-align: center;
        }

        /* ── Voice Speed control ── */
        .iv-speed-control {
          display: flex; flex-direction: column; gap: 8px; width: 100%;
          margin: 4px 0 8px; padding: 12px;
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 16px;
        }
        .iv-speed-header {
          display: flex; justify-content: space-between; align-items: center;
          font-size: 10px; color: #7a8ba8; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.08em;
        }
        .iv-speed-current {
          color: #00e5c3; font-weight: 700;
        }
        .iv-speed-buttons {
          display: flex; gap: 6px; width: 100%;
        }
        .iv-speed-btn {
          flex: 1; padding: 6px 4px; border-radius: 8px; border: 1px solid transparent;
          font-family: 'Sora', sans-serif; font-size: 11px; font-weight: 600; cursor: pointer;
          color: #7a8ba8; background: rgba(255,255,255,0.03);
          transition: all 0.2s ease;
        }
        .iv-speed-btn:hover {
          background: rgba(255,255,255,0.07); color: #e8edf8;
        }
        .iv-speed-btn.active {
          background: rgba(0,229,195,0.15); color: #00e5c3;
          border-color: rgba(0,229,195,0.3);
          box-shadow: 0 0 10px rgba(0,229,195,0.15);
        }

        /* ── Question box ── */
        .iv-qbox {
          width: 100%;
          background: rgba(124,58,237,0.08); border: 1px solid rgba(124,58,237,0.2);
          border-radius: 16px; padding: 16px 18px;
          font-size: 14px; color: #e8edf8; line-height: 1.7;
        }
        .iv-qlabel {
          font-size: 10px; font-weight: 700; color: #a78bfa;
          text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;
          display: flex; align-items: center; gap: 6px;
        }

        /* ── Video panel ── */
        .iv-video-wrap {
          width: 100%; aspect-ratio: 16/9;
          background: #060910; border-radius: 16px; overflow: hidden;
          position: relative; border: 1px solid rgba(255,255,255,0.07);
        }
        .iv-video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
        .iv-video-off {
          position: absolute; inset: 0; display: flex; flex-direction: column;
          align-items: center; justify-content: center; gap: 8px; color: #7a8ba8;
          font-size: 13px;
        }
        .iv-rec-badge {
          position: absolute; top: 10px; right: 10px;
          display: flex; align-items: center; gap: 5px;
          background: rgba(255,79,106,0.15); border: 1px solid rgba(255,79,106,0.3);
          border-radius: 20px; padding: 4px 10px; font-size: 11px; color: #ff4f6a; font-weight: 600;
        }
        .iv-rec-dot {
          width: 6px; height: 6px; border-radius: 50%; background: #ff4f6a;
          animation: recPulse 1s ease-in-out infinite;
        }
        @keyframes recPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        /* ── Answer area ── */
        .iv-answer-area { width: 100%; display: flex; flex-direction: column; gap: 10px; }
        .iv-input-toggle {
          display: flex; gap: 6px;
          background: rgba(255,255,255,0.04); border-radius: 10px; padding: 4px;
        }
        .iv-toggle-btn {
          flex: 1; padding: 7px 10px; border-radius: 7px; border: none;
          font-family: 'Sora', sans-serif; font-size: 12px; font-weight: 600; cursor: pointer;
          transition: all 0.2s;
        }
        .iv-toggle-active { background: rgba(0,229,195,0.15); color: #00e5c3; border: 1px solid rgba(0,229,195,0.3); }
        .iv-toggle-inactive { background: transparent; color: #7a8ba8; }

        .iv-textarea {
          width: 100%; min-height: 100px; resize: none;
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
          border-radius: 14px; padding: 14px 16px;
          color: #e8edf8; font-family: 'Sora', sans-serif; font-size: 13px; line-height: 1.7;
          outline: none; transition: border-color 0.2s;
        }
        .iv-textarea:focus { border-color: rgba(0,229,195,0.4); }
        .iv-textarea::placeholder { color: #3a4a68; }

        /* ── Record button ── */
        .iv-record-btn {
          width: 100%; padding: 13px; border-radius: 14px; border: none; cursor: pointer;
          font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 700;
          display: flex; align-items: center; justify-content: center; gap: 10px;
          transition: all 0.2s;
        }
        .iv-record-idle {
          background: rgba(124,58,237,0.15); color: #a78bfa;
          border: 1.5px solid rgba(124,58,237,0.3);
        }
        .iv-record-idle:hover { background: rgba(124,58,237,0.25); }
        .iv-record-active {
          background: rgba(255,79,106,0.15); color: #ff4f6a;
          border: 1.5px solid rgba(255,79,106,0.4);
          animation: recordGlow 1s ease-in-out infinite alternate;
        }
        @keyframes recordGlow { from { box-shadow: 0 0 0 rgba(255,79,106,0); } to { box-shadow: 0 0 20px rgba(255,79,106,0.3); } }

        /* ── Buttons ── */
        .iv-btn {
          width: 100%; padding: 12px 20px; border-radius: 12px; border: none;
          font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 600; cursor: pointer;
          transition: all 0.2s;
        }
        .iv-btn-primary { background: linear-gradient(135deg,#00e5c3,#00b8ff); color: #050d14; }
        .iv-btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
        .iv-btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .iv-btn-ghost { background: rgba(255,255,255,0.05); color: #e8edf8; border: 1px solid rgba(255,255,255,0.1); }
        .iv-btn-ghost:hover { background: rgba(255,255,255,0.09); }
        .iv-btn-danger { background: rgba(255,79,106,0.12); color: #ff4f6a; border: 1px solid rgba(255,79,106,0.25); max-width: 200px; margin: 0 auto; }
        .iv-btn-danger:hover { background: rgba(255,79,106,0.22); }

        /* ── Feedback box ── */
        .iv-feedback {
          width: 100%;
          background: rgba(0,229,195,0.05); border: 1px solid rgba(0,229,195,0.18);
          border-radius: 16px; padding: 16px 18px;
          font-size: 13px; color: #b8c8d8; line-height: 1.8; white-space: pre-wrap;
        }
        .iv-feedback-header {
          display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
        }
        .iv-feedback-label { font-size: 10px; font-weight: 700; color: #00e5c3; text-transform: uppercase; letter-spacing: 0.08em; }

        /* ── Score progress ── */
        .iv-score-bar {
          width: 100%; display: flex; align-items: center; gap: 10px;
          background: rgba(255,255,255,0.04); border-radius: 10px; padding: 10px 14px;
        }
        .iv-score-bar-fill { height: 6px; border-radius: 3px; background: linear-gradient(90deg,#00e5c3,#00b8ff); transition: width 1s ease; }
        .iv-score-bar-bg { flex: 1; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.08); overflow: hidden; }

        /* ── Bottom row ── */
        .iv-bottom { display: flex; justify-content: center; max-width: 1060px; margin: 0 auto 20px; }

        /* ── Start screen ── */
        .iv-start-screen {
          max-width: 520px; margin: 40px auto 0; text-align: center;
          display: flex; flex-direction: column; align-items: center; gap: 20px;
        }
        .iv-start-avatar { width: 180px; height: 220px; }
        .iv-start-title { font-size: 24px; font-weight: 800; color: #e8edf8; }
        .iv-start-sub { font-size: 14px; color: #7a8ba8; line-height: 1.6; }
        .iv-btn-start {
          background: linear-gradient(135deg,#7c3aed,#00b8ff); color: #fff;
          padding: 14px 40px; font-size: 16px; border-radius: 16px; border: none;
          cursor: pointer; font-weight: 700; font-family: 'Sora', sans-serif;
          transition: all 0.2s; box-shadow: 0 0 30px rgba(124,58,237,0.3);
        }
        .iv-btn-start:hover { opacity: 0.9; transform: translateY(-2px); box-shadow: 0 8px 30px rgba(124,58,237,0.4); }

        /* ── Results screen ── */
        .iv-results { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
        .iv-results-hero {
          background: rgba(12,18,35,0.9); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 24px; padding: 32px;
          display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center;
        }
        .iv-results-row { display: flex; align-items: center; gap: 24px; }
        .iv-results-title { font-size: 22px; font-weight: 800; color: #e8edf8; }
        .iv-results-sub { font-size: 14px; color: #7a8ba8; max-width: 460px; line-height: 1.7; }
        .iv-summary-card {
          background: rgba(12,18,35,0.7); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 16px; padding: 18px 20px;
        }
        .iv-sq { font-size: 13px; font-weight: 600; color: #a78bfa; margin-bottom: 5px; }
        .iv-sa { font-size: 12px; color: #4a5a78; margin-bottom: 10px; font-style: italic; }
        .iv-sf { font-size: 13px; color: #b8c8d8; line-height: 1.7; white-space: pre-wrap; }
        .iv-score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
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
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {avgScore && interviewStarted && (
            <div style={{ fontSize: 12, color: "#7a8ba8" }}>
              Avg: <span style={{ color: "#00e5c3", fontWeight: 700 }}>{avgScore}/10</span>
            </div>
          )}
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
        </div>
      </nav>

      <div className="iv-page">

        {/* ══ RESULTS SCREEN ══ */}
        {interviewComplete && finalResult ? (
          <div className="iv-results">
            <div className="iv-results-hero">
              <div style={{ fontSize: 40 }}>🎌</div>
              <div className="iv-results-title">Interview Complete!</div>
              <div className="iv-results-row">
                <GradeBadge grade={finalResult.grade} />
                <ScoreRing score={finalResult.overall_score} size={90} label="Overall" />
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: 13, color: "#7a8ba8" }}>Questions answered</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#e8edf8" }}>{allFeedbacks.length}</div>
                </div>
              </div>

              {/* Report — updates once background Gemini finishes */}
              <div className="iv-results-sub" style={{ position: "relative" }}>
                {finalResult.report}
                {finalResult.report?.includes("Generating") && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: "#7a8ba8", animation: "pulse 1.5s ease-in-out infinite" }}>⟳ generating…</span>
                )}
              </div>

              {/* Action buttons */}
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
                <button className="iv-btn-start" onClick={() => navigate("/dashboard")}
                  style={{ padding: "11px 22px", fontSize: 13 }}>
                  ← Dashboard
                </button>
                <button onClick={() => downloadPDF(finalResult, allFeedbacks)}
                  style={{
                    padding: "11px 22px", fontSize: 13, fontWeight: 700, borderRadius: 14, border: "none",
                    background: "linear-gradient(135deg,#00e5c3,#00b8ff)", color: "#050d14",
                    cursor: "pointer", display: "flex", alignItems: "center", gap: 7, fontFamily: "inherit"
                  }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>
                  </svg>
                  Download PDF Report
                </button>
                {videoBlob && (
                  <button onClick={() => downloadVideo(videoBlob)}
                    style={{
                      padding: "11px 22px", fontSize: 13, fontWeight: 700, borderRadius: 14,
                      background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.4)",
                      color: "#a78bfa", cursor: "pointer", display: "flex", alignItems: "center", gap: 7,
                      fontFamily: "inherit"
                    }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    Download Recording
                  </button>
                )}
              </div>
            </div>

            {allFeedbacks.map((item, i) => (
              <div className="iv-summary-card" key={i}>
                <div className="iv-score-row">
                  <ScoreRing score={item.score || 0} size={48} />
                  <div className="iv-sq">Q{i + 1}: {item.question}</div>
                </div>
                <div className="iv-sa">"{item.response}"</div>
                <div className="iv-sf">{item.feedback}</div>
              </div>
            ))}
          </div>

        ) : !interviewStarted ? (
          /* ══ START SCREEN ══ */
          <div className="iv-start-screen">
            <div className="iv-start-avatar">
              <AnimeAvatar isTalking={false} isThinking={false} />
            </div>
            <div className="iv-start-title">Meet Hana, Your AI Interviewer</div>
            <div className="iv-start-sub">
              Hana will ask you interview questions based on your resume using voice audio.
              Your camera will be on and the session will be recorded and scored.
            </div>
            <button className="iv-btn-start" onClick={startInterview}>
              🎙 Start Interview
            </button>
          </div>

        ) : (
          /* ══ INTERVIEW SCREEN ══ */
          <>
            <div className="iv-grid">

              {/* ── Hana panel ── */}
              <div className="iv-panel">
                <div className="iv-anime-wrap">
                  <div className="iv-aura" />
                  <AnimeAvatar isTalking={isHanaTalking} isThinking={isHanaThinking} />
                </div>
                <div className="iv-panel-name">Hana</div>
                <div className="iv-panel-sub">AI Interviewer · Powered by Gemini</div>

                <div className="iv-status-chip">
                  <AudioWave active={isHanaTalking} />
                  <span>{hanaStatus}</span>
                </div>

                {/* Voice Speed Control */}
                <div className="iv-speed-control">
                  <div className="iv-speed-header">
                    <span>Voice Speed</span>
                    <span className="iv-speed-current">{speechSpeed}x</span>
                  </div>
                  <div className="iv-speed-buttons">
                    {[1.0, 1.25, 1.5, 1.75, 2.0].map(speed => (
                      <button
                        key={speed}
                        className={`iv-speed-btn ${speechSpeed === speed ? "active" : ""}`}
                        onClick={() => handleSpeedChange(speed)}
                      >
                        {speed}x
                      </button>
                    ))}
                  </div>
                </div>

                {question && (
                  <div className="iv-qbox">
                    <div className="iv-qlabel">
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
                        <circle cx="5" cy="5" r="5" />
                      </svg>
                      Question {questionNumber}
                    </div>
                    {question}
                  </div>
                )}

                {/* Per-question scores so far */}
                {allFeedbacks.length > 0 && (
                  <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ fontSize: 11, color: "#7a8ba8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Progress
                    </div>
                    {allFeedbacks.map((f, i) => (
                      <div key={i} className="iv-score-bar">
                        <div style={{ fontSize: 11, color: "#7a8ba8", minWidth: 16 }}>Q{i+1}</div>
                        <div className="iv-score-bar-bg">
                          <div className="iv-score-bar-fill" style={{ width: `${(f.score || 0) * 10}%` }} />
                        </div>
                        <div style={{ fontSize: 12, color: "#00e5c3", fontWeight: 700, minWidth: 28 }}>{f.score}/10</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ── Candidate panel ── */}
              <div className="iv-panel">
                {/* Video */}
                <div className="iv-video-wrap">
                  <video ref={videoRef} autoPlay muted playsInline className="iv-video" />
                  {!videoStreamRef.current && (
                    <div className="iv-video-off">
                      <span style={{ fontSize: 32 }}>📷</span>
                      <span>Camera starting...</span>
                    </div>
                  )}
                  <div className="iv-rec-badge">
                    <div className="iv-rec-dot" />
                    REC
                  </div>
                </div>

                <div className="iv-panel-name">{displayName}</div>
                <div className="iv-panel-sub">{user.email}</div>

                {/* Answer area */}
                <div className="iv-answer-area">
                  {/* Input mode toggle */}
                  <div className="iv-input-toggle">
                    <button
                      className={`iv-toggle-btn ${inputMode === "voice" ? "iv-toggle-active" : "iv-toggle-inactive"}`}
                      onClick={() => setInputMode("voice")}
                    >
                      🎤 Voice
                    </button>
                    <button
                      className={`iv-toggle-btn ${inputMode === "text" ? "iv-toggle-active" : "iv-toggle-inactive"}`}
                      onClick={() => setInputMode("text")}
                    >
                      ⌨️ Type
                    </button>
                  </div>

                  {inputMode === "voice" ? (
                    <>
                      <button
                        className={`iv-record-btn ${isRecording ? "iv-record-active" : "iv-record-idle"}`}
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isTranscribing}
                      >
                        {isTranscribing
                          ? <><span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span> Transcribing...</>
                          : isRecording
                          ? <><span>⏹</span> Stop Recording</>
                          : <><span>🎤</span> Hold to Record Answer</>
                        }
                      </button>
                      {response && (
                        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "12px 14px", fontSize: 13, color: "#b8c8d8", lineHeight: 1.7 }}>
                          <div style={{ fontSize: 10, color: "#7a8ba8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Transcribed</div>
                          {response}
                        </div>
                      )}
                    </>
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
                    <button
                      className="iv-btn iv-btn-primary"
                      onClick={submitResponse}
                      disabled={isHanaThinking}
                    >
                      {isHanaThinking ? "Evaluating..." : "Submit Answer →"}
                    </button>
                  )}

                  {showNext && (
                    <button className="iv-btn iv-btn-ghost" onClick={fetchNextQuestion}>
                      Next Question →
                    </button>
                  )}
                </div>

                {/* Per-answer feedback */}
                {feedback && (
                  <div className="iv-feedback">
                    <div className="iv-feedback-header">
                      <div className="iv-feedback-label">Hana's Feedback</div>
                      <ScoreRing score={feedback.score} size={52} />
                    </div>
                    {feedback.feedback}
                  </div>
                )}
              </div>
            </div>

            {/* End interview */}
            <div className="iv-bottom">
              <button className="iv-btn iv-btn-danger" onClick={endInterview}
                style={{ padding: "10px 24px", fontSize: 13, borderRadius: 12 }}>
                End Interview & Get Score
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
      `}</style>
    </>
  );
};

export default InterviewPage;