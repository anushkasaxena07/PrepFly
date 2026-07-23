import React, { useState, useEffect, useRef } from 'react';
import AI_INTERVIEWER from '../config/aiInterviewerConfig';
import { getGradeInfo, computeSectionGrades, getBadges } from '../utils/gradingSystem';

// ── futur21 Concentric Circle Waves Avatar for Ava ──────────────────────────
const CircleWavesAvatar = ({ isTalking, isThinking }) => {
  return (
    <div style={{ position: "relative", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <style>{`
        @keyframes futurWave1 { 0% { transform: scale(0.5); opacity: 1; border-width: 3px; } 100% { transform: scale(1.75); opacity: 0; border-width: 1px; } }
        @keyframes futurWave2 { 0% { transform: scale(0.5); opacity: 1; border-width: 3px; } 100% { transform: scale(1.75); opacity: 0; border-width: 1px; } }
        @keyframes futurWave3 { 0% { transform: scale(0.5); opacity: 1; border-width: 3px; } 100% { transform: scale(1.75); opacity: 0; border-width: 1px; } }
        @keyframes futurWave4 { 0% { transform: scale(0.5); opacity: 1; border-width: 3px; } 100% { transform: scale(1.75); opacity: 0; border-width: 1px; } }
        @keyframes coreGlowPulse { 0%, 100% { transform: scale(1); filter: drop-shadow(0 0 25px #00e5c3) drop-shadow(0 0 45px rgba(124,58,237,0.7)); } 50% { transform: scale(1.1); filter: drop-shadow(0 0 40px #00b8ff) drop-shadow(0 0 60px rgba(0,229,195,0.9)); } }
        @keyframes ringRotateClockwise { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes ringRotateCounter { from { transform: rotate(360deg); } to { transform: rotate(0deg); } }
      `}</style>
      
      {/* Circle Waves GIF by futur21 Asset */}
      <img src="/Circle Waves GIF by futur21.gif" alt="" onError={e => e.target.style.display='none'} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "contain", borderRadius: "50%", pointerEvents: "none" }} />

      {/* futur21 Concentric Expanding Waves */}
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #00e5c3", animation: isTalking ? "futurWave1 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : isThinking ? "futurWave1 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : "futurWave1 5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite", animationDelay: "0s", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #00b8ff", animation: isTalking ? "futurWave2 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : isThinking ? "futurWave2 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : "futurWave2 5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite", animationDelay: "0.55s", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #8b5cf6", animation: isTalking ? "futurWave3 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : isThinking ? "futurWave3 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : "futurWave3 5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite", animationDelay: "1.1s", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #ec4899", animation: isTalking ? "futurWave4 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : isThinking ? "futurWave4 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite" : "futurWave4 5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite", animationDelay: "1.65s", pointerEvents: "none" }} />

      {/* Rotating Orb Rings */}
      <svg viewBox="0 0 200 200" style={{ width: "180px", height: "180px", position: "absolute", animation: isThinking ? "ringRotateClockwise 4s linear infinite" : isTalking ? "ringRotateClockwise 8s linear infinite" : "ringRotateClockwise 16s linear infinite" }}>
        <circle cx="100" cy="100" r="92" fill="none" stroke="rgba(0, 229, 195, 0.35)" strokeWidth="1.5" strokeDasharray="8 12" />
        <circle cx="100" cy="100" r="78" fill="none" stroke="rgba(0, 184, 255, 0.4)" strokeWidth="1" strokeDasharray="16 8" />
      </svg>

      <svg viewBox="0 0 200 200" style={{ width: "180px", height: "180px", position: "absolute", animation: isThinking ? "ringRotateCounter 5s linear infinite" : isTalking ? "ringRotateCounter 10s linear infinite" : "ringRotateCounter 20s linear infinite" }}>
        <circle cx="100" cy="100" r="64" fill="none" stroke="rgba(139, 92, 246, 0.5)" strokeWidth="1.5" strokeDasharray="6 6" />
      </svg>

      {/* Central Glowing futur21 Core with Wave GIF */}
      <div style={{ width: "96px", height: "96px", borderRadius: "50%", background: isTalking ? "radial-gradient(circle, #00e5c3 0%, #00b8ff 45%, #8b5cf6 85%, #050811 100%)" : isThinking ? "radial-gradient(circle, #8b5cf6 0%, #00b8ff 55%, #050811 100%)" : "radial-gradient(circle, #00e5c3 0%, #081226 80%)", animation: isTalking ? "coreGlowPulse 0.7s ease-in-out infinite" : "coreGlowPulse 2.2s ease-in-out infinite", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 3, boxShadow: "0 0 35px rgba(0, 229, 195, 0.6)", overflow: "hidden" }}>
        <img src="/Circle Waves GIF by futur21.gif" alt="" onError={e => e.target.style.display='none'} style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }} />
      </div>
    </div>
  );
};

const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    
    // Filter out common raw JSON brackets or prompt leaks
    if (trimmed === "{" || trimmed === "}" || trimmed === "}," || trimmed === "[{" || trimmed === "}]" || trimmed === '"' || trimmed === "'") {
      return null;
    }
    const lowerLine = trimmed.toLowerCase();
    if (
      lowerLine.startsWith("return only") || 
      lowerLine.startsWith("expected json") || 
      lowerLine.startsWith("return a json") ||
      lowerLine.includes("preamble") ||
      lowerLine.includes("markdown codeblock") ||
      (lowerLine.includes("time_complexity") && lowerLine.includes("string")) ||
      (lowerLine.includes("space_complexity") && lowerLine.includes("string")) ||
      (lowerLine.includes("ai_review") && lowerLine.includes("string"))
    ) {
      return null;
    }

    // Clean up em-dashes and en-dashes from headers and content
    let cleanLine = line
      .replace(/—/g, "-")
      .replace(/–/g, "-");

    // Headers
    if (cleanLine.startsWith("## ")) {
      const headerText = cleanLine.replace("## ", "").replace(/^[-—–\s]+/, "").trim();
      return <h2 key={idx} style={{ fontSize: "15px", fontWeight: 800, marginTop: "12px", marginBottom: "6px", color: "#00e5c3" }}>{headerText}</h2>;
    }
    if (cleanLine.startsWith("### ")) {
      const headerText = cleanLine.replace("### ", "").replace(/^[-—–\s]+/, "").trim();
      return <h3 key={idx} style={{ fontSize: "13px", fontWeight: 700, marginTop: "10px", marginBottom: "4px", color: "#fff" }}>{headerText}</h3>;
    }
    if (cleanLine.startsWith("#### ")) {
      const headerText = cleanLine.replace("#### ", "").replace(/^[-—–\s]+/, "").trim();
      return <h4 key={idx} style={{ fontSize: "12px", fontWeight: 700, marginTop: "8px", marginBottom: "4px", color: "#a78bfa" }}>{headerText}</h4>;
    }
    
    // Check if bullet point (supporting *, -, and dashes)
    let content = cleanLine;
    let isBullet = false;
    const cleanTrimmed = cleanLine.trim();
    if (cleanTrimmed.startsWith("* ") || cleanTrimmed.startsWith("- ")) {
      isBullet = true;
      content = cleanTrimmed.substring(2);
    }
    
    // Parse bold text like **something**
    const parts = [];
    let lastIndex = 0;
    const regex = /\*\*(.*?)\*\*/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      parts.push(<strong key={match.index} style={{ color: "#00e5c3", fontWeight: 700 }}>{match[1]}</strong>);
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }
    
    const displayContent = parts.length > 0 ? parts : content;
    
    if (isBullet) {
      return (
        <div key={idx} style={{ display: "flex", gap: "6px", paddingLeft: "12px", marginBottom: "4px" }}>
          <span style={{ color: "#00e5c3" }}>•</span>
          <div>{displayContent}</div>
        </div>
      );
    }
    
    return (
      <div key={idx} style={{ marginBottom: "6px" }}>
        {displayContent}
      </div>
    );
  });
};

export default function AvaTab({ apiFetch, isLoggedIn, user = {} }) {
  // Steps: "resume_upload" -> "type_selection" -> "device_check" -> "loading" -> "live_call" -> "report"
  const [step, setStep] = useState("resume_upload");
  const [setupMode, setSetupMode] = useState("resume"); // "resume" or "non_resume"
  const [selectedType, setSelectedType] = useState(null);
  
  // Non-Resume Form State
  const [roleTitle, setRoleTitle] = useState("Software Engineer");
  const [roleTools, setRoleTools] = useState("Python, React, SQL, Algorithms");
  const [category, setCategory] = useState("Core CS");
  const [difficulty, setDifficulty] = useState("Medium");

  const [resumeFile, setResumeFile] = useState(null);
  const [previewResumeUrl, setPreviewResumeUrl] = useState(null);
  const [atsScore, setAtsScore] = useState(null);

  // Device check toggles & webcam stream
  const [cameraOn, setCameraOn] = useState(true);
  const [micOn, setMicOn] = useState(true);
  const videoRefDevice = useRef(null);
  const videoRefCall = useRef(null);
  const mediaStreamRef = useRef(null);

  // Voice Speaking / Speech Rec state
  const [isSpeakingAnswer, setIsSpeakingAnswer] = useState(false);
  const recognitionRef = useRef(null);

  // Loading checklist items
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const loadingSteps = [
    "Personalizing your session",
    "Setting up your interview room",
    "Connecting to the interview room",
    "Preparing your audio and video",
    "Establishing media connection",
    "Waiting for AI interviewer to join",
    "Almost there"
  ];

  // Active call state
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState("");
  const [questionNumber, setQuestionNumber] = useState(0);
  const [currentStage, setCurrentStage] = useState("Greeting & Icebreaker");
  const [answer, setAnswer] = useState("");
  const [captionText, setCaptionText] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isAvaTalking, setIsAvaTalking] = useState(false);
  const [isAvaThinking, setIsAvaThinking] = useState(false);
  const [allFeedbacks, setAllFeedbacks] = useState([]);
  const [reportData, setReportData] = useState(null);

  const currentAudioRef = useRef(null);
  const timerRef = useRef(null);

  // Initialize and attach camera stream directly
  const setupCamera = async () => {
    try {
      if (!mediaStreamRef.current) {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        mediaStreamRef.current = stream;
      }
      const stream = mediaStreamRef.current;

      if (videoRefDevice.current) {
        videoRefDevice.current.srcObject = stream;
        videoRefDevice.current.play().catch(() => {});
      }
      if (videoRefCall.current) {
        videoRefCall.current.srcObject = stream;
        videoRefCall.current.play().catch(() => {});
      }
    } catch (err) {
      console.warn("Camera setup error:", err);
    }
  };

  useEffect(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  useEffect(() => {
    if (step === "device_check" || step === "live_call") {
      setupCamera();
    }
  }, [step, cameraOn, micOn]);

  // Elapsed Timer for Live Call
  useEffect(() => {
    if (step === "live_call") {
      timerRef.current = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsedSeconds(0);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [step]);

  const formatTimer = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Step 1: Handle Resume File
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setResumeFile(file);
      setPreviewResumeUrl(URL.createObjectURL(file));
    }
  };

  const clearResume = () => {
    setResumeFile(null);
    setPreviewResumeUrl(null);
  };

  // Step 3 -> 4: Start Interview & Loading Flow
  const triggerStartInterview = async () => {
    setStep("loading");
    setLoadingStepIndex(0);

    const interval = setInterval(() => {
      setLoadingStepIndex(prev => {
        if (prev < loadingSteps.length - 1) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, 650);

    try {
      let activeSessionId = null;
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

      const resolvedUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id");
      if (setupMode === "resume" && resumeFile) {
        const formData = new FormData();
        formData.append("resume", resumeFile);
        if (resolvedUserId) formData.append("user_id", resolvedUserId);
        const token = localStorage.getItem("access_token");

        const res = await fetch(`${BACKEND_URL}/upload`, {
          method: "POST",
          headers: token ? { "Authorization": "Bearer " + token } : {},
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to upload resume");
        activeSessionId = data.session_id;
        if (data.ats_score) setAtsScore(data.ats_score);
      } else {
        const res = await apiFetch("/create-session-no-resume", {
          method: "POST",
          body: JSON.stringify({
            user_id: resolvedUserId || null,
            role: roleTitle || ((selectedType?.name || "Technical") + " Software Engineer"),
            tools: roleTools || "Algorithms, System Design, React, Python",
            experience: "1-3 Years",
            category: selectedType?.id || category || "Resume",
            difficulty: difficulty || "Medium"
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to create non-resume session");
        activeSessionId = data.session_id;
      }

      setSessionId(activeSessionId);

      const chosenCategory = selectedType?.id || (setupMode === "non_resume" ? category : "Resume");

      const startRes = await apiFetch("/start-interview", {
        method: "POST",
        body: JSON.stringify({ session_id: activeSessionId, category: chosenCategory, difficulty: difficulty || "Medium" })
      });
      const startData = await startRes.json();
      if (!startRes.ok) throw new Error(startData.error || "Failed to start interview");

      setQuestion(startData.question);
      setQuestionNumber(startData.question_number || 1);
      if (startData.stage) setCurrentStage(startData.stage);

      setTimeout(() => {
        setStep("live_call");
        playAvaSpeech(startData.question);
      }, 1200);

    } catch (err) {
      alert("Error starting interview: " + err.message);
      setStep("device_check");
    }
  };

  // Play Ava speech
  const playAvaSpeech = (text) => {
    setIsAvaTalking(true);

    // Strip markdown formatting symbols for natural vocal speech and accurate captions
    const cleanedText = (text || "")
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`[^`]*`/g, '')
      .replace(/[#*_\-~>#]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    // Set 100% accurate full subtitle caption immediately
    setCaptionText(cleanedText || text);

    const getNaturalVoice = () => {
      if (!('speechSynthesis' in window)) return null;
      const voices = window.speechSynthesis.getVoices();
      
      // Prioritize modern high-quality female natural voices
      const femaleKeywords = ["jenny", "aria", "samantha", "zira", "google us english", "female", "siri", "victoria", "karen", "serena", "online"];
      
      // 1. Exact match for popular female natural/online voices
      for (const keyword of femaleKeywords) {
        const found = voices.find(v => v.name.toLowerCase().includes(keyword) && v.lang.startsWith("en"));
        if (found) return found;
      }
      
      // 2. Any English female voice
      const anyFemale = voices.find(v => v.name.toLowerCase().includes("female") && v.lang.startsWith("en"));
      if (anyFemale) return anyFemale;
      
      // 3. Fallback to any English voice
      const anyEnglish = voices.find(v => v.lang.startsWith("en"));
      if (anyEnglish) return anyEnglish;
      
      return voices[0] || null;
    };

    const speakWithWebSpeech = () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(cleanedText || text);
        const bestVoice = getNaturalVoice();
        if (bestVoice) {
          utterance.voice = bestVoice;
        }
        utterance.lang = 'en-US';
        utterance.rate = 0.96; // Human natural cadence
        utterance.pitch = 1.03; // Warm natural vocal pitch
        utterance.onend = () => {
          setIsAvaTalking(false);
          startVoiceRecognition();
        };
        utterance.onerror = () => {
          setIsAvaTalking(false);
          startVoiceRecognition();
        };
        window.speechSynthesis.speak(utterance);
      } else {
        setIsAvaTalking(false);
        startVoiceRecognition();
      }
    };

    // If browser supports SpeechSynthesis, use WebSpeech for ultra-smooth voice!
    if ('speechSynthesis' in window) {
      speakWithWebSpeech();
      return;
    }

    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
    fetch(`${BACKEND_URL}/text-to-speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: cleanedText || text })
    })
      .then(res => {
        if (!res.ok) throw new Error("TTS endpoint returned non-200 status");
        return res.blob();
      })
      .then(blob => {
        const audio = new Audio(URL.createObjectURL(blob));
        currentAudioRef.current = audio;
        audio.play().catch(() => speakWithWebSpeech());
        audio.onended = () => {
          setIsAvaTalking(false);
          startVoiceRecognition();
        };
        audio.onerror = () => speakWithWebSpeech();
      })
      .catch(() => {
        speakWithWebSpeech();
      });
  };

  // Voice Speech Recognition (Speaking Answer)
  const startVoiceRecognition = () => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return;

    try {
      if (recognitionRef.current) recognitionRef.current.stop();
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onresult = (e) => {
        let transcript = "";
        for (let i = 0; i < e.results.length; i++) {
          transcript += e.results[i][0].transcript + " ";
        }
        setAnswer(transcript.trim());
      };

      rec.onend = () => {
        setIsSpeakingAnswer(false);
      };

      rec.start();
      recognitionRef.current = rec;
      setIsSpeakingAnswer(true);
    } catch (e) {
      console.warn("Voice speech rec start error:", e);
    }
  };

  const stopVoiceRecognition = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
    setIsSpeakingAnswer(false);
  };

  // Submit Answer & Fetch Next Question
  const submitAnswerAndNext = async () => {
    stopVoiceRecognition();
    if (!answer.trim()) return alert("Please speak your answer first.");
    setIsAvaThinking(true);
    setCaptionText("Evaluating your response...");

    try {
      const chosenCategory = selectedType?.id || (setupMode === "non_resume" ? category : "Resume");
      const res = await apiFetch("/next", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          answer: answer.trim(),
          category: chosenCategory,
          difficulty: difficulty || "Medium"
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to process answer");

      if (data.feedback) {
        setAllFeedbacks(prev => [...prev, data.feedback]);
      }
      setAnswer("");
      setIsAvaThinking(false);

      if (data.done) {
        endInterviewSession();
      } else if (data.next_question) {
        setQuestion(data.next_question);
        setQuestionNumber(data.question_number || questionNumber + 1);
        if (data.stage) setCurrentStage(data.stage);
        playAvaSpeech(data.next_question);
      }
    } catch (err) {
      alert("Error: " + err.message);
      setIsAvaThinking(false);
    }
  };

  // End Interview & Generate Report
  const endInterviewSession = async () => {
    stopVoiceRecognition();
    setIsAvaThinking(true);
    setCaptionText("Compiling your comprehensive executive evaluation report...");

    try {
      const res = await apiFetch("/end-interview", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "End interview failed");

      setReportData(data);
      setStep("report");
      setIsAvaThinking(false);

      // Poll background report if initial response is "Generating..."
      if (data.report && data.report.includes("Generating")) {
        let attempts = 0;
        const poll = setInterval(async () => {
          attempts++;
          try {
            const r = await apiFetch(`/session-report/${sessionId}`);
            const rd = await r.json();
            if (rd.final_report && !rd.final_report.includes("Generating")) {
              try {
                const parsed = JSON.parse(rd.final_report);
                setReportData(prev => ({
                  ...prev,
                  ...parsed,
                  report: rd.final_report
                }));
              } catch (e) {
                setReportData(prev => ({ ...prev, report: rd.final_report }));
              }
              clearInterval(poll);
            }
          } catch {}
          if (attempts >= 12) clearInterval(poll);
        }, 4000);
      }
    } catch (err) {
      alert("Error generating report: " + err.message);
      setIsAvaThinking(false);
    }
  };


  const downloadPDFReport = () => {
    const gc = reportData?.grade === "S" ? "#ffd700" : reportData?.grade === "A" ? "#00e5c3" : reportData?.grade === "B" ? "#00b8ff" : "#f59e0b";
    const html = `<!DOCTYPE html><html><head>
    <meta charset="UTF-8"/><title>PrepFly Executive Report - Ava</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap');
      *{box-sizing:border-box;margin:0;padding:0}body{font-family:'Plus Jakarta Sans',sans-serif;background:#070b14;color:#f0f4fd;padding:40px;line-height:1.6}
      .hdr{display:flex;justify-content:space-between;padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:28px}
      .brand{font-size:24px;font-weight:900;background:linear-gradient(135deg,#00c4a7,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
      .hero{background:linear-gradient(145deg,rgba(12,18,32,0.9),rgba(24,18,40,0.9));border:1px solid rgba(124,58,237,0.3);border-radius:20px;padding:28px;margin-bottom:28px;display:flex;gap:24px;align-items:center}
      .grade-circle{width:84px;height:84px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:900;border:4px solid ${gc};background:${gc}18;color:${gc};box-shadow:0 0 24px ${gc}33}
      .score-val{font-size:32px;font-weight:900;color:#00c4a7;margin-top:2px}
      .sec-title{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:#00c4a7;margin:28px 0 16px;border-left:3px solid #00c4a7;padding-left:10px}
      .qa-card{background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;margin-bottom:16px}
      .rpt-box{background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;font-size:14px;color:#e2e8f0;white-space:pre-wrap;line-height:1.7}
      .ftr{margin-top:40px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08);font-size:11px;color:#64748b;text-align:center}
    </style></head><body>
    <div class="hdr"><div class="brand">🚀 PrepFly Executive Evaluation (Ava)</div><div>Candidate: ${user.name||"Candidate"}<br/>Generated: ${new Date().toLocaleString()}</div></div>
    <div class="hero">
      <div class="grade-circle">${reportData?.grade || "B"}</div>
      <div>
        <div style="font-size:12px;color:#94a3b8;text-transform:uppercase;font-weight:700">Overall Rating</div>
        <div class="score-val">${reportData?.overall_score || 7.5} / 10</div>
      </div>
    </div>
    <div class="sec-title">Final Recruiter Evaluation Summary & Strengths</div>
    <div class="rpt-box">${reportData?.report || "Full technical evaluation completed successfully."}</div>
    <div class="sec-title">Question-by-Question Deep Dive</div>
    ${allFeedbacks.map((f, i) => `<div class="qa-card"><div style="color:#a78bfa;font-weight:800;margin-bottom:4px">Question ${i+1}: ${f.question||""}</div><div style="color:#00c4a7;font-weight:700">Score: ${f.score||7}/10</div><div style="margin-top:8px;font-style:italic">"${f.response||""}"</div><div style="margin-top:8px">${f.feedback||""}</div></div>`).join("")}
    <div class="ftr">Official Evaluation Conducted by Ava (Senior AI Technical Interviewer)</div>
    </body></html>`;
    const win = window.open("", "_blank");
    win.document.write(html);
    win.document.close();
    setTimeout(() => win.print(), 600);
  };

  const interviewTypes = [
    { id: "HR", name: "HR & Behavioral", desc: "Dedicated HR screening mock focusing on communication, leadership, conflict resolution, situational judgment, and STAR method responses." },
    { id: "DSA", name: "DSA & Algorithms", desc: "A focused data structures & algorithms interview designed to assess problem-solving skills." },
    { id: "SystemDesign", name: "System Design", desc: "Scalability, microservices, load balancing, database schema, and high-availability architecture." },
    { id: "Resume", name: "Resume Based", desc: "Guided conversation focused on your past experience, resume projects, and achievements." },
    { id: "Fundamentals", name: "CS Fundamentals", desc: "Core concepts: data structures, algorithms, networking, DBMS, OOPS, and OS basics." },
    { id: "MAANG", name: "MAANG / Big Tech", desc: "Rigorous algorithmic and system architecture screening inspired by top tech company rounds." }
  ];

  return (
    <div style={{ backgroundColor: "#050811", color: "#ffffff", minHeight: "100vh", padding: "28px" }}>
      <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

        {/* ── STEP 1: RESUME OR NON-RESUME INTERVIEW SETUP ── */}
        {step === "resume_upload" && (
          <div style={{ maxWidth: "800px", margin: "30px auto", background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "24px", padding: "36px" }}>
            <div style={{ textAlign: "center", marginBottom: "24px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 900, marginBottom: "8px", color: "#fff" }}>Configure Your AI Interview</h2>
              <p style={{ fontSize: "14px", color: "var(--text2)" }}>Choose between uploading your resume or setting custom non-resume topics.</p>
            </div>

            {/* Mode Switcher Tabs */}
            <div style={{ display: "flex", background: "rgba(255,255,255,0.04)", borderRadius: "14px", padding: "4px", marginBottom: "28px" }}>
              <button onClick={() => setSetupMode("resume")} style={{ flex: 1, padding: "10px", borderRadius: "10px", border: "none", background: setupMode === "resume" ? "linear-gradient(135deg,#00c4a7,#7c3aed)" : "transparent", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: "13px" }}>
                📄 Resume Interview Mode
              </button>
              <button onClick={() => setSetupMode("non_resume")} style={{ flex: 1, padding: "10px", borderRadius: "10px", border: "none", background: setupMode === "non_resume" ? "linear-gradient(135deg,#00c4a7,#7c3aed)" : "transparent", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: "13px" }}>
                ⚙️ Non-Resume / Custom Topics Mode
              </button>
            </div>

            {setupMode === "resume" ? (
              <div style={{ textAlign: "center" }}>
                {resumeFile ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "16px", padding: "16px 20px", marginBottom: "28px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span style={{ fontSize: "24px" }}>📄</span>
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff" }}>{resumeFile.name}</div>
                        <div style={{ fontSize: "11px", color: "#00c4a7" }}>{(resumeFile.size / 1024).toFixed(1)} KB · Tailoring questions to your profile</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "10px" }}>
                      {previewResumeUrl && (
                        <button onClick={() => window.open(previewResumeUrl, '_blank')} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "8px", width: "36px", height: "36px", color: "#fff", cursor: "pointer", fontSize: "16px" }} title="Preview Resume">👁️</button>
                      )}
                      <button onClick={clearResume} style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "8px", width: "36px", height: "36px", color: "#ef4444", cursor: "pointer", fontSize: "16px" }} title="Clear Resume">✕</button>
                    </div>
                  </div>
                ) : (
                  <div style={{ border: "2px dashed rgba(0,196,167,0.3)", borderRadius: "20px", padding: "36px", marginBottom: "28px", position: "relative", cursor: "pointer" }}>
                    <input type="file" accept=".pdf,.docx" onChange={handleFileUpload} style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }} />
                    <div style={{ fontSize: "40px", marginBottom: "12px" }}>☁️</div>
                    <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff" }}>Click or Drag & Drop your resume (PDF/DOCX)</div>
                    <div style={{ fontSize: "12px", color: "var(--text2)", marginTop: "4px" }}>Your resume helps us tailor every question to your experience</div>
                  </div>
                )}
              </div>
            ) : (
              /* Non-Resume Form */
              <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "28px" }}>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Target Role Title</label>
                  <input type="text" value={roleTitle} onChange={e => setRoleTitle(e.target.value)} placeholder="e.g. Senior Full Stack Software Engineer" style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }} />
                </div>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Tech Stack & Tools</label>
                  <input type="text" value={roleTools} onChange={e => setRoleTools(e.target.value)} placeholder="e.g. React, Node.js, Python, System Design" style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }} />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Category</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }}>
                      {["HR & Behavioral", "DSA", "System Design", "OOPS", "DBMS", "OS", "CN", "Core CS", "Company Specific"].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Difficulty</label>
                    <select value={difficulty} onChange={e => setDifficulty(e.target.value)} style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }}>
                      <option value="Easy">Easy</option>
                      <option value="Medium">Medium</option>
                      <option value="Hard">Hard</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div style={{ textAlign: "center", marginTop: "28px" }}>
              <button 
                onClick={() => {
                  if (setupMode === "resume" && !resumeFile) {
                    alert("Please upload your resume file (PDF/DOCX) first, or switch to Custom Topics Mode.");
                    return;
                  }
                  setStep("type_selection");
                }} 
                style={{ padding: "14px 28px", borderRadius: "14px", background: "linear-gradient(135deg, #00c4a7, #7c3aed)", border: "none", color: "#fff", fontWeight: 800, fontSize: "14px", display: "inline-flex", alignItems: "center", gap: "10px", cursor: "pointer", boxShadow: "0 8px 24px rgba(0,196,167,0.4)" }} 
                title="Continue to Track Selection"
              >
                Continue to Track Selection ➔
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: INTERVIEW TYPE SELECTION CARDS ── */}
        {step === "type_selection" && (
          <div style={{ marginTop: "24px" }}>
            <div style={{ textAlign: "center", marginBottom: "32px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>Choose Interview Track</h2>
              <p style={{ fontSize: "13px", color: "var(--text2)", marginTop: "4px" }}>Select the topic and format for your 1-on-1 AI Recruiter interview with Ava</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px" }}>
              {interviewTypes.map(t => (
                <div key={t.id} style={{ background: selectedType?.id === t.id ? "linear-gradient(145deg, rgba(12,18,32,0.95), rgba(24,18,45,0.95))" : "rgba(12,18,32,0.7)", border: selectedType?.id === t.id ? "2px solid #00c4a7" : "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between", minHeight: "240px", transition: "all 0.2s ease" }}>
                  <div>
                    <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", marginBottom: "10px" }}>{t.name}</h3>
                    <p style={{ fontSize: "12px", color: "var(--text2)", lineHeight: "1.6" }}>{t.desc}</p>
                  </div>
                  <button onClick={() => { setSelectedType(t); setStep("device_check"); }} style={{ width: "100%", padding: "12px", borderRadius: "12px", background: selectedType?.id === t.id ? "linear-gradient(135deg,#00c4a7,#7c3aed)" : "rgba(255,255,255,0.08)", border: "none", color: "#fff", fontWeight: 800, fontSize: "13px", cursor: "pointer", marginTop: "16px" }}>
                    Start {t.name} →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── STEP 3: PRE-INTERVIEW DEVICE CHECK SCREEN ── */}
        {step === "device_check" && (
          <div style={{ maxWidth: "960px", margin: "20px auto" }}>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>{selectedType.name} Interview</h2>
              <p style={{ fontSize: "13px", color: "var(--text2)", marginTop: "4px" }}>Enable and test your camera and microphone before joining.</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "28px", marginBottom: "32px" }}>
              {/* Left: Camera Preview */}
              <div style={{ background: "#000", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "20px", overflow: "hidden", position: "relative", height: "320px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video ref={videoRefDevice} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                
                {/* Floating Controls */}
                <div style={{ position: "absolute", bottom: "16px", display: "flex", gap: "12px", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)", padding: "8px 16px", borderRadius: "30px", border: "1px solid rgba(255,255,255,0.15)" }}>
                  <button onClick={() => setCameraOn(!cameraOn)} style={{ background: cameraOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}>
                    {cameraOn ? "📷" : "🚫"}
                  </button>
                  <button onClick={() => setMicOn(!micOn)} style={{ background: micOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}>
                    {micOn ? "🎙️" : "🔇"}
                  </button>
                  <button style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}>⚙️</button>
                </div>
              </div>

              {/* Right: Checklist */}
              <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff" }}>Things to know before starting</h3>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🕒</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>Expect to spend ~20 minutes</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "2px" }}>Very short interviews may not be considered complete. Please answer thoughtfully.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>✋</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>Need assistance? Just ask</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "2px" }}>Tell the AI if you need a question repeated or more time.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🔒</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>Your data is in your control</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "2px" }}>Your responses are used only to assess your candidacy and are never used to train AI models.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🌐</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>Supported browsers</div>
                    <div style={{ fontSize: "11px", color: "var(--text2)", marginTop: "2px" }}>Chrome and Safari are preferred for the best experience.</div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ textAlign: "center" }}>
              <button onClick={triggerStartInterview} style={{ padding: "14px 44px", borderRadius: "30px", background: "linear-gradient(135deg,#00c4a7,#7c3aed)", border: "none", color: "#fff", fontWeight: 900, fontSize: "16px", cursor: "pointer", boxShadow: "0 8px 24px rgba(0,196,167,0.4)" }}>
                Start interview
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 4: SESSION SETUP / LOADING OVERLAY ── */}
        {step === "loading" && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(5,8,17,0.92)", backdropFilter: "blur(16px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
            <div style={{ background: "rgba(12,18,32,0.95)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "24px", padding: "36px 44px", maxWidth: "440px", width: "100%", boxShadow: "0 24px 64px rgba(0,0,0,0.8)" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", marginBottom: "20px", textAlign: "center" }}>Setting Up Interview Room</h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {loadingSteps.map((stName, idx) => {
                  const isDone = idx < loadingStepIndex;
                  const isActive = idx === loadingStepIndex;
                  return (
                    <div key={idx} style={{ display: "flex", alignItems: "center", gap: "12px", opacity: idx <= loadingStepIndex ? 1 : 0.4 }}>
                      <div style={{ width: "24px", height: "24px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: isDone ? "rgba(0,196,167,0.2)" : isActive ? "rgba(124,58,237,0.2)" : "rgba(255,255,255,0.05)", border: isDone ? "1px solid #00c4a7" : isActive ? "1px solid #7c3aed" : "1px solid rgba(255,255,255,0.1)", color: isDone ? "#00c4a7" : "#7c3aed", fontSize: "12px", fontWeight: 800 }}>
                        {isDone ? "✓" : isActive ? "⏳" : "•"}
                      </div>
                      <span style={{ fontSize: "13px", fontWeight: isActive ? 800 : 600, color: isActive ? "#fff" : isDone ? "#00c4a7" : "var(--text2)" }}>{stName}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 5: LIVE AI INTERVIEW CALL SCREEN (50-50 SPLIT) ── */}
        {step === "live_call" && (
          <div style={{ position: "fixed", inset: 0, background: "#050811", display: "flex", flexDirection: "column", zIndex: 900, padding: "16px" }}>
            {/* Top Bar */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 16px", marginBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "20px", padding: "6px 14px", fontSize: "13px", fontWeight: 800, color: "#00c4a7" }}>
                  ⏱️ Elapsed: {formatTimer(elapsedSeconds)}
                </div>
                <div style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "20px", padding: "6px 14px", fontSize: "12px", fontWeight: 800, color: "#a78bfa" }}>
                  Stage: {currentStage}
                </div>
              </div>

              <button onClick={endInterviewSession} style={{ background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.4)", color: "#ef4444", borderRadius: "24px", padding: "8px 20px", fontWeight: 800, fontSize: "13px", cursor: "pointer" }}>
                🚪 End Interview
              </button>
            </div>

            {/* 50-50 SPLIT CONTAINER */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", flex: 1, minHeight: 0 }}>
              
              {/* LEFT 50%: CANDIDATE LIVE WEBCAM VIDEO */}
              <div style={{ background: "#000", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "24px", overflow: "hidden", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video ref={videoRefCall} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                
                <div style={{ position: "absolute", bottom: "16px", left: "16px", background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)", padding: "6px 14px", borderRadius: "20px", border: "1px solid rgba(255,255,255,0.15)", fontSize: "12px", fontWeight: 800, color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00c4a7" }}></span>
                  🎥 {user?.name ? user.name.split(' ')[0] : 'Candidate'} (You)
                </div>
              </div>

              {/* RIGHT 50%: AVA AI INTERVIEWER & VOICE SPEAKING PANEL */}
              <div style={{ background: "rgba(12,18,32,0.9)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "24px", padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center" }}>
                
                {/* Ava Concentric Waves Orb */}
                <div style={{ width: "220px", height: "220px", position: "relative", margin: "10px 0" }}>
                  <CircleWavesAvatar isTalking={isAvaTalking} isThinking={isAvaThinking} />
                </div>

                {/* Subtitles / Spoken Question */}
                <div style={{ width: "100%", textAlign: "center", padding: "16px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", minHeight: "80px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#a78bfa", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px" }}>Ava (Senior Technical Recruiter)</div>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff", lineHeight: "1.6" }}>
                    "{captionText || question || "Listening..."}"
                  </div>
                </div>

                {/* Voice Speaking Answer Area */}
                <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "10px", marginTop: "14px" }}>
                  <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                    <button onClick={isSpeakingAnswer ? stopVoiceRecognition : startVoiceRecognition} style={{ flex: 1, padding: "12px", borderRadius: "14px", background: isSpeakingAnswer ? "rgba(239,68,68,0.25)" : "rgba(124,58,237,0.2)", border: isSpeakingAnswer ? "1px solid #ef4444" : "1px solid rgba(124,58,237,0.4)", color: "#fff", fontWeight: 800, fontSize: "14px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                      {isSpeakingAnswer ? "🔴 Listening to your voice..." : "🎙️ Click to Speak Answer"}
                    </button>
                    
                    <button onClick={submitAnswerAndNext} disabled={isAvaThinking} style={{ padding: "12px 24px", borderRadius: "14px", background: "#00c4a7", border: "none", color: "#000", fontWeight: 900, fontSize: "14px", cursor: "pointer" }}>
                      {isAvaThinking ? "Evaluating..." : "Submit Spoken Answer →"}
                    </button>
                  </div>

                  <input type="text" placeholder="Spoken transcript (or type if needed)..." value={answer} onChange={e => setAnswer(e.target.value)} style={{ width: "100%", padding: "10px 14px", borderRadius: "12px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", fontSize: "12px" }} />
                </div>

              </div>

            </div>
          </div>
        )}

        {/* ── REPORT PANEL ── */}
        {step === "report" && reportData && (() => {
          const score100 = reportData.overall_score_100 || Math.round((reportData.overall_score || 7.5) * 10);
          const gInfo = getGradeInfo(score100);
          const sectionGrades = reportData.section_grades || computeSectionGrades(score100, allFeedbacks);
          const earnedBadges = reportData.badges || getBadges(score100, sectionGrades);
          const topStrengths = reportData.top_strengths || ["Excellent Communication", "Strong Technical Knowledge", "Good Leadership", "Confident Speaker", "Excellent Resume Understanding"];
          const topImprovements = reportData.top_improvements || ["Reduce filler words", "Improve DSA explanations", "Improve STAR responses", "Increase confidence", "Speak with more structure"];

          return (
            <div style={{ maxWidth: "880px", margin: "20px auto", background: "rgba(12,18,32,0.95)", border: `1px solid ${gInfo.color}44`, boxShadow: `0 0 40px ${gInfo.color}15`, borderRadius: "24px", padding: "36px", textAlign: "center" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "20px", marginBottom: "24px" }}>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Executive Candidate Evaluation</div>
                  <div style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>{gInfo.label} Candidate</div>
                  <div style={{ fontSize: "13px", color: gInfo.color, fontWeight: 800, marginTop: "4px" }}>📌 Hiring Recommendation: {gInfo.rec}</div>
                  <div style={{ fontSize: "12px", color: "#a78bfa", fontWeight: 700, marginTop: "2px" }}>Level: {gInfo.level}</div>
                </div>

                <div style={{ width: "96px", height: "96px", borderRadius: "50%", background: gInfo.bgColor, border: `4px solid ${gInfo.color}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: `0 0 24px ${gInfo.color}44`, flexShrink: 0 }}>
                  <div style={{ fontSize: "32px", fontWeight: 900, color: gInfo.color, lineHeight: 1 }}>{gInfo.grade}</div>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#fff", marginTop: "2px" }}>{score100}/100</div>
                </div>
              </div>

              {/* EARNED BADGES */}
              <div style={{ textAlign: "left", marginBottom: "20px" }}>
                <div style={{ fontSize: "11px", fontWeight: 800, color: "#94a3b8", textTransform: "uppercase", marginBottom: "8px" }}>🎖️ EARNED CANDIDATE BADGES</div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {earnedBadges.map((b, idx) => (
                    <span key={idx} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", padding: "6px 14px", borderRadius: "20px", fontSize: "12px", color: "#fff", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "6px" }}>
                      <span>{b.icon}</span> {b.name}
                    </span>
                  ))}
                </div>
              </div>

              {/* SECTION GRADES */}
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "20px", marginBottom: "24px", textAlign: "left" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#fff", marginBottom: "14px" }}>📊 Section Grades Breakdown (10 Dimensions)</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px" }}>
                  {sectionGrades.map((sec, idx) => (
                    <div key={idx} style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${sec.color}33`, borderRadius: "12px", padding: "10px", textAlign: "center" }}>
                      <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>{sec.name}</div>
                      <div style={{ fontSize: "16px", fontWeight: 900, color: sec.color, marginTop: "2px" }}>
                        {sec.score} <span style={{ fontSize: "11px", opacity: 0.8 }}>({sec.grade})</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* TOP STRENGTHS & IMPROVEMENTS */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ background: "rgba(0,196,167,0.06)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "20px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 900, color: "#00c4a7", marginBottom: "10px" }}>💪 Top 5 Strengths</h4>
                  <ul style={{ paddingLeft: "18px", margin: 0, fontSize: "12px", color: "#e2e8f0", lineHeight: "1.8" }}>
                    {topStrengths.map((str, idx) => (
                      <li key={idx}>{str}</li>
                    ))}
                  </ul>
                </div>
                <div style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "20px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 900, color: "#f59e0b", marginBottom: "10px" }}>🎯 Top 5 Focus Areas</h4>
                  <ul style={{ paddingLeft: "18px", margin: 0, fontSize: "12px", color: "#e2e8f0", lineHeight: "1.8" }}>
                    {topImprovements.map((imp, idx) => (
                      <li key={idx}>{imp}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* AI RECRUITER REPORT */}
              {reportData.report && !reportData.report.includes("Generating") && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px", textAlign: "left", color: "#e2e8f0", lineHeight: "1.7", marginBottom: "28px", fontSize: "13px" }}>
                  {renderMarkdown(reportData.report)}
                </div>
              )}


              <div style={{ display: "flex", gap: "14px", justifyContent: "center" }}>
                <button onClick={() => setStep("type_selection")} style={{ padding: "12px 24px", borderRadius: "12px", background: "rgba(255,255,255,0.1)", border: "none", color: "#fff", fontWeight: 800, cursor: "pointer" }}>Practice Another</button>
                <button onClick={downloadPDFReport} style={{ padding: "12px 28px", borderRadius: "12px", background: "linear-gradient(135deg,#00c4a7,#7c3aed)", border: "none", color: "#fff", fontWeight: 800, cursor: "pointer" }}>📄 Download PDF Report</button>
              </div>
            </div>
          );
        })()}

      </div>
    </div>
  );
}
