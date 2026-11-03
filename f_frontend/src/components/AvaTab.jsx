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
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #00e5c3", animation: isTalking ? "futurWave1 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) 0s infinite" : isThinking ? "futurWave1 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) 0s infinite" : "futurWave1 5s cubic-bezier(0.1, 0.8, 0.3, 1) 0s infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #00b8ff", animation: isTalking ? "futurWave2 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) 0.55s infinite" : isThinking ? "futurWave2 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) 0.55s infinite" : "futurWave2 5s cubic-bezier(0.1, 0.8, 0.3, 1) 0.55s infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #8b5cf6", animation: isTalking ? "futurWave3 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) 1.1s infinite" : isThinking ? "futurWave3 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) 1.1s infinite" : "futurWave3 5s cubic-bezier(0.1, 0.8, 0.3, 1) 1.1s infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", width: "160px", height: "160px", borderRadius: "50%", border: "2px solid #ec4899", animation: isTalking ? "futurWave4 2.2s cubic-bezier(0.1, 0.8, 0.3, 1) 1.65s infinite" : isThinking ? "futurWave4 3.5s cubic-bezier(0.1, 0.8, 0.3, 1) 1.65s infinite" : "futurWave4 5s cubic-bezier(0.1, 0.8, 0.3, 1) 1.65s infinite", pointerEvents: "none" }} />

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

const renderEvidenceCard = (item, isStrength, idx) => {
  let rawTitle = typeof item === 'string' ? item : (item.title || "Observation");
  let rawEvidence = typeof item === 'object' ? (item.evidence || "") : "";
  
  // Extract Turn or Question label
  let turnBadge = null;
  const turnMatch = rawTitle.match(/(Turn\s*\d+|Question\s*\d+|Q\d+)/i) || rawEvidence.match(/(Turn\s*\d+|Question\s*\d+|Q\d+)/i);
  if (turnMatch) {
    turnBadge = turnMatch[1].replace(/turn/i, "Question");
  }

  // Extract quoted candidate speech if present
  let quote = null;
  let observation = rawEvidence;
  const quoteMatch = rawEvidence.match(/['"“](.*?)['"”]$/) || rawEvidence.match(/:\s*['"“](.*?)['"”]/);
  if (quoteMatch) {
    quote = quoteMatch[1];
    observation = rawEvidence.replace(quoteMatch[0], "").trim();
    if (observation.endsWith(":")) observation = observation.slice(0, -1).trim();
  }

  let cleanTitle = rawTitle;
  if (cleanTitle.includes(": '")) {
    const parts = cleanTitle.split(": '");
    cleanTitle = parts[0];
    if (!quote && parts[1]) {
      quote = parts[1].replace(/['"]+$/, "");
    }
  }

  return (
    <div key={idx} style={{
      background: isStrength ? "rgba(0,196,167,0.06)" : "rgba(245,158,11,0.06)",
      border: isStrength ? "1px solid rgba(0,196,167,0.22)" : "1px solid rgba(245,158,11,0.22)",
      borderRadius: "14px",
      padding: "14px",
      marginBottom: "12px",
      textAlign: "left"
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
        <strong style={{ color: "#fff", fontSize: "12.5px", lineHeight: "1.4", display: "flex", alignItems: "center", gap: "6px" }}>
          <span>{isStrength ? "✅" : "⚠️"}</span>
          <span>{cleanTitle}</span>
        </strong>
        {turnBadge && (
          <span style={{
            fontSize: "10px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            padding: "2px 8px",
            borderRadius: "10px",
            background: isStrength ? "rgba(0,229,195,0.15)" : "rgba(245,158,11,0.15)",
            color: isStrength ? "#00e5c3" : "#f59e0b",
            border: isStrength ? "1px solid rgba(0,229,195,0.3)" : "1px solid rgba(245,158,11,0.3)",
            whiteSpace: "nowrap"
          }}>
            {turnBadge}
          </span>
        )}
      </div>

      {observation && observation.toLowerCase() !== cleanTitle.toLowerCase() && (
        <div style={{ fontSize: "11.5px", color: "#94a3b8", marginBottom: quote ? "8px" : "0", lineHeight: "1.5" }}>
          {observation}
        </div>
      )}

      {quote && (
        <div style={{
          padding: "8px 12px",
          background: "rgba(0,0,0,0.35)",
          borderLeft: isStrength ? "3px solid #00c4a7" : "3px solid #f59e0b",
          borderRadius: "0 8px 8px 0",
          fontSize: "11px",
          color: "#cbd5e1",
          fontStyle: "italic",
          lineHeight: "1.5"
        }}>
          "{quote}"
        </div>
      )}
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
  const safeUser = user || {};
  // Steps: "resume_upload" -> "type_selection" -> "device_check" -> "loading" -> "live_call" -> "report"
  const [step, setStep] = useState("resume_upload");
  const [setupMode, setSetupMode] = useState("resume"); // "resume" or "non_resume"
  const [selectedType, setSelectedType] = useState(null);
  const [selectedEvidenceDimension, setSelectedEvidenceDimension] = useState(null);
  
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
  const [hasCameraStream, setHasCameraStream] = useState(false);
  const [cameraErrorMsg, setCameraErrorMsg] = useState("");
  const [hasMicStream, setHasMicStream] = useState(false);
  const [micErrorMsg, setMicErrorMsg] = useState("");
  const videoRefDevice = useRef(null);
  const videoRefCall = useRef(null);
  const mediaStreamRef = useRef(null);

  // Voice Speaking / Speech Rec & Audio Meter state
  const [isSpeakingAnswer, setIsSpeakingAnswer] = useState(false);
  const recognitionRef = useRef(null);
  const isListeningDesiredRef = useRef(false);
  const finalTranscriptRef = useRef("");
  const [audioLevel, setAudioLevel] = useState(0);
  const [hintText, setHintText] = useState("");
  const [isLoadingHint, setIsLoadingHint] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const audioContextRef = useRef(null);
  const audioSourceRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);

  const bindStreamToVideo = (videoEl, stream) => {
    if (!videoEl || !stream) return;
    try {
      videoEl.muted = true;
      videoEl.defaultMuted = true;
      videoEl.playsInline = true;
      videoEl.autoplay = true;
      if (videoEl.srcObject !== stream) {
        videoEl.srcObject = stream;
      }
      if (stream.getVideoTracks) {
        stream.getVideoTracks().forEach(t => {
          if (!t.enabled) t.enabled = true;
        });
      }
      const p = videoEl.play();
      if (p && typeof p.catch === "function") {
        p.catch(err => {
          console.warn("Video playback deferred/notice:", err);
        });
      }
    } catch (err) {
      console.warn("Error binding stream to video:", err);
    }
  };

  const startAudioMeter = (stream) => {
    if (!stream || stream.getAudioTracks().length === 0) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioCtx();
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }
      if (analyserRef.current) return;

      const source = ctx.createMediaStreamSource(stream);
      audioSourceRef.current = source;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      analyser.smoothingTimeConstant = 0.5;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(100, Math.round((avg / 128) * 100));
        setAudioLevel(normalized);
        animFrameRef.current = requestAnimationFrame(tick);
      };
      animFrameRef.current = requestAnimationFrame(tick);
    } catch (e) {
      console.warn("Audio meter notice:", e);
    }
  };

  const stopAudioMeter = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioSourceRef.current) {
      try { audioSourceRef.current.disconnect(); } catch {}
      audioSourceRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  };

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
  
  // Hands-Free Conversational Voice VAD
  const [isHandsFree, setIsHandsFree] = useState(true);
  const [autoSubmitCountdown, setAutoSubmitCountdown] = useState(null);
  const silenceTimerRef = useRef(null);
  const isHandsFreeRef = useRef(true);
  const isAvaTalkingRef = useRef(false);
  const isAvaThinkingRef = useRef(false);

  // Option 2: Job Description context without resume
  const [jobDescription, setJobDescription] = useState("");

  // ── PrepFly Feature: Proctoring & Eye Contact Telemetry ──
  const [eyeContactPct, setEyeContactPct] = useState(0);
  const [tabSwitches, setTabSwitches] = useState(0);

  // ── PrepFly Feature: Turn-by-Turn Audio Recording & Replay ──
  const [recordedAudios, setRecordedAudios] = useState({});
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Active accordion tab for turn-by-turn benchmark review
  const [expandedTurn, setExpandedTurn] = useState(null);

  useEffect(() => {
    isHandsFreeRef.current = isHandsFree;
  }, [isHandsFree]);

  useEffect(() => {
    isAvaTalkingRef.current = isAvaTalking;
  }, [isAvaTalking]);

  useEffect(() => {
    isAvaThinkingRef.current = isAvaThinking;
  }, [isAvaThinking]);

  const currentAudioRef = useRef(null);
  const timerRef = useRef(null);

  // Initialize and attach camera stream directly with robust device fallbacks
  const setupCamera = async (forceReacquire = false) => {
    try {
      if (forceReacquire && mediaStreamRef.current) {
        try {
          mediaStreamRef.current.getTracks().forEach(t => t.stop());
        } catch (e) {}
        mediaStreamRef.current = null;
      }

      const hasLiveVideo = mediaStreamRef.current?.getVideoTracks().some(t => t.readyState === 'live' && t.enabled);
      const hasLiveAudio = mediaStreamRef.current?.getAudioTracks().some(t => t.readyState === 'live' && t.enabled);

      if (forceReacquire || !mediaStreamRef.current || !hasLiveVideo || !hasLiveAudio) {
        let stream = null;
        let acquiredVideo = false;
        let acquiredAudio = false;

        // 1. Try combined user media with optimal camera & audio constraints
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: {
              width: { ideal: 1280, max: 1920 },
              height: { ideal: 720, max: 1080 },
              facingMode: "user"
            },
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true
            }
          });
          acquiredVideo = stream.getVideoTracks().length > 0;
          acquiredAudio = stream.getAudioTracks().length > 0;
        } catch (eBoth) {
          console.warn("Optimal getUserMedia failed, attempting basic combined:", eBoth);
          // 2. Try basic combined
          try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            acquiredVideo = stream.getVideoTracks().length > 0;
            acquiredAudio = stream.getAudioTracks().length > 0;
          } catch (eBasic) {
            console.warn("Basic combined getUserMedia failed, attempting separate requests:", eBasic);
            // 3. Try separate video
            try {
              const vStream = await navigator.mediaDevices.getUserMedia({ video: true });
              stream = vStream;
              acquiredVideo = true;
            } catch (eVid) {
              console.warn("Video only getUserMedia failed:", eVid);
              setCameraErrorMsg("Camera access unavailable. Ensure no other application (Zoom, Teams) is using your webcam, then click below.");
            }
            // 4. Try separate audio
            try {
              const aStream = await navigator.mediaDevices.getUserMedia({ audio: true });
              if (stream) {
                aStream.getAudioTracks().forEach(t => stream.addTrack(t));
              } else {
                stream = aStream;
              }
              acquiredAudio = true;
            } catch (eAud) {
              console.warn("Audio only getUserMedia failed:", eAud);
              setMicErrorMsg("Microphone access unavailable. Check browser permissions and click Reconnect Mic.");
            }
          }
        }

        if (stream) {
          mediaStreamRef.current = stream;
          const liveV = stream.getVideoTracks().some(t => t.readyState === 'live' && t.enabled);
          const liveA = stream.getAudioTracks().some(t => t.readyState === 'live' && t.enabled);
          setHasCameraStream(liveV);
          setHasMicStream(liveA);
          if (liveV) setCameraErrorMsg("");
          if (liveA) setMicErrorMsg("");
        }
      }

      const stream = mediaStreamRef.current;
      if (stream) {
        bindStreamToVideo(videoRefDevice.current, stream);
        bindStreamToVideo(videoRefCall.current, stream);
        if (stream.getAudioTracks().length > 0) {
          startAudioMeter(stream);
        }
      }
    } catch (err) {
      console.warn("Camera setup error:", err);
      setCameraErrorMsg(err.message || "Device access error");
    }
  };

  // Re-attach media stream when video elements mount or step changes
  useEffect(() => {
    if (mediaStreamRef.current) {
      const stream = mediaStreamRef.current;
      bindStreamToVideo(videoRefCall.current, stream);
      bindStreamToVideo(videoRefDevice.current, stream);
    }
  }, [step, cameraOn]);

  const showDeviceSettings = () => {
    const videoLabel = mediaStreamRef.current?.getVideoTracks()[0]?.label || "Default Camera";
    const audioLabel = mediaStreamRef.current?.getAudioTracks()[0]?.label || "Default Microphone";
    alert(`Selected Capture Devices:\n\n📷 Camera: ${videoLabel}\n🎙️ Microphone: ${audioLabel}\n\nUsing system-default selection.`);
  };

  // Restore active interview step or report from localStorage / sessionStorage on reload
  useEffect(() => {
    try {
      const saved = localStorage.getItem("prepfly_avatab_session") || sessionStorage.getItem("prepfly_avatab_session");
      if (saved) {
        const p = JSON.parse(saved);
        if (p && p.step === "report" && p.reportData) {
          setStep("report");
          setReportData(p.reportData);
          if (p.allFeedbacks) setAllFeedbacks(p.allFeedbacks);
          if (p.sessionId) setSessionId(p.sessionId);
          if (p.atsScore) setAtsScore(p.atsScore);
        }
      }
    } catch (e) {
      console.warn("Session restore notice:", e);
    }
  }, []);

  // Persist session state on change to localStorage and sessionStorage
  useEffect(() => {
    if (step && step !== "resume_upload" && step !== "loading") {
      try {
        const payload = JSON.stringify({
          step,
          selectedType,
          sessionId,
          reportData,
          allFeedbacks,
          atsScore,
          question,
          questionNumber
        });
        localStorage.setItem("prepfly_avatab_session", payload);
        sessionStorage.setItem("prepfly_avatab_session", payload);
      } catch (e) {}
    }
  }, [step, sessionId, reportData, allFeedbacks, atsScore, question, questionNumber]);

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
      setupCamera(step === "live_call");
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

  // ── Navigation guard: warn before closing/refreshing during an active interview ──
  useEffect(() => {
    const isActiveSession = step === "live_call" || step === "loading";
    if (!isActiveSession) return;

    const handleBeforeUnload = (e) => {
      e.preventDefault();
      // Modern browsers show their own message but require returnValue to be set
      e.returnValue = "Your interview is in progress. Leaving now will end your session and your progress may be lost.";
      return e.returnValue;
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [step]);



  const formatTimer = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // ── Turn Audio Recording ──
  const startAudioCapture = () => {
    try {
      if (mediaStreamRef.current && window.MediaRecorder) {
        audioChunksRef.current = [];
        const audioTracks = mediaStreamRef.current.getAudioTracks();
        if (audioTracks.length > 0) {
          const stream = new MediaStream([audioTracks[0]]);
          const mr = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '' });
          mr.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
          };
          mr.start(250);
          mediaRecorderRef.current = mr;
        }
      }
    } catch (err) {
      console.warn("Audio capture notice:", err);
    }
  };

  const stopAudioCapture = (qIndex) => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.onstop = () => {
          if (audioChunksRef.current.length > 0) {
            const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            const url = URL.createObjectURL(blob);
            setRecordedAudios(prev => ({ ...prev, [qIndex]: url }));
          }
        };
        mediaRecorderRef.current.stop();
      }
    } catch (err) {
      console.warn("Stop audio capture notice:", err);
    }
  };

  // Track window tab switches for proctoring integrity
  useEffect(() => {
    if (step === "live_call") {
      const handleVisibility = () => {
        if (document.hidden) setTabSwitches(prev => prev + 1);
      };
      document.addEventListener("visibilitychange", handleVisibility);
      return () => document.removeEventListener("visibilitychange", handleVisibility);
    }
  }, [step]);

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
    if (!consentGiven) {
      alert("Affirmative consent is required to process your voice and resume data with AI under DPDP Act 2023. Please check the consent box before starting.");
      return;
    }
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
        formData.append("consent", "true");
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
            difficulty: difficulty || "Medium",
            job_description: jobDescription || "",
            consent: true
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to create non-resume session");
        activeSessionId = data.session_id;
      }

      setSessionId(activeSessionId);

      const chosenCategory = (setupMode === "non_resume") ? (category || "Job Description") : (selectedType?.id || "Resume");
      const chosenRole = (setupMode === "non_resume" && roleTitle.trim()) ? roleTitle.trim() : (selectedType?.name || "Software Engineer");

      const startRes = await apiFetch("/start-interview", {
        method: "POST",
        body: JSON.stringify({ 
          session_id: activeSessionId, 
          category: chosenCategory, 
          role: chosenRole,
          difficulty: difficulty || "Medium",
          job_description: jobDescription || ""
        })
      });
      const startData = await startRes.json();
      if (!startRes.ok) throw new Error(startData.error || "Failed to start interview");

      setQuestion(startData.question);
      setQuestionNumber(startData.question_number || 1);
      if (startData.stage) setCurrentStage(startData.stage);

      setTimeout(() => {
        setStep("live_call");
        setupCamera(true);
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
        const found = voices.find(v => v?.name?.toLowerCase().includes(keyword) && v.lang.startsWith("en"));
        if (found) return found;
      }
      
      // 2. Any English female voice
      const anyFemale = voices.find(v => v?.name?.toLowerCase().includes("female") && v.lang.startsWith("en"));
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
        let speechSafetyTimer = null;
        const onSpeechFinish = () => {
          if (speechSafetyTimer) clearTimeout(speechSafetyTimer);
          setIsAvaTalking(false);
          startVoiceRecognition();
        };

        const wordCount = (cleanedText || text).split(/\s+/).length;
        const maxSpeechDurationMs = Math.max(3000, Math.min(25000, (wordCount / 2.2) * 1000 + 2500));
        speechSafetyTimer = setTimeout(() => {
          console.warn("SpeechSynthesis safety timeout triggered; auto-starting microphone listener.");
          onSpeechFinish();
        }, maxSpeechDurationMs);

        utterance.onend = onSpeechFinish;
        utterance.onerror = onSpeechFinish;
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

  // Voice Speech Recognition (Speaking Answer) with continuous recovery & PrepFly VAD
  const startVoiceRecognition = () => {
    isListeningDesiredRef.current = true;
    setIsSpeakingAnswer(true);

    if (mediaStreamRef.current) {
      startAudioMeter(mediaStreamRef.current);
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn("Web Speech API not available in this browser. Please type your response directly.");
      return;
    }

    // Safely abort and nullify existing instance before creating a new one
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.abort();
      } catch (err) {}
      recognitionRef.current = null;
    }

    try {
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = navigator.language || 'en-US';

      rec.onresult = (e) => {
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const chunk = e.results[i][0].transcript;
          if (e.results[i].isFinal) {
            finalTranscriptRef.current += (finalTranscriptRef.current ? " " : "") + chunk.trim();
          } else {
            interim += chunk;
          }
        }
        const currentTotal = (finalTranscriptRef.current + (interim ? " " + interim : "")).trim();
        setAnswer(currentTotal);

        // Reset silence timer whenever speech is actively streaming
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        setAutoSubmitCountdown(null);

        // PrepFly VAD: When candidate speaks meaningful words (>= 3 words) and pauses
        const words = currentTotal.split(/\s+/).filter(Boolean);
        if (isHandsFreeRef.current && words.length >= 3 && !isAvaTalkingRef.current && !isAvaThinkingRef.current) {
          setAutoSubmitCountdown(2);
          silenceTimerRef.current = setTimeout(() => {
            if (isListeningDesiredRef.current && !isAvaTalkingRef.current && !isAvaThinkingRef.current) {
              setAutoSubmitCountdown(null);
              submitAnswerAndNext(currentTotal);
            }
          }, 2100);
        }
      };

      rec.onend = () => {
        // Continuous auto-recovery: Always instantiate a NEW SpeechRecognition instance!
        if (isListeningDesiredRef.current && !isAvaTalkingRef.current && !isAvaThinkingRef.current) {
          recognitionRef.current = null;
          setTimeout(() => {
            if (isListeningDesiredRef.current && !isAvaTalkingRef.current && !isAvaThinkingRef.current) {
              startVoiceRecognition();
            }
          }, 150);
        } else {
          setIsSpeakingAnswer(false);
          stopAudioMeter();
        }
      };

      rec.onerror = (e) => {
        console.warn("Speech recognition notice:", e.error);
        if (e.error === "no-speech") {
          return;
        }
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          setMicErrorMsg("Microphone access was denied. Please allow microphone permissions in your browser.");
          setIsSpeakingAnswer(false);
          return;
        }
        if (e.error === "network" || e.error === "audio-capture") {
          console.warn("Speech recognition network/audio notice. Listener will auto-reconnect.");
        }
      };

      rec.start();
      recognitionRef.current = rec;
      setMicErrorMsg("");
    } catch (e) {
      console.warn("Voice speech rec start error:", e);
    }
  };

  const stopVoiceRecognition = () => {
    isListeningDesiredRef.current = false;
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setAutoSubmitCountdown(null);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.abort();
      } catch {}
      recognitionRef.current = null;
    }
    setIsSpeakingAnswer(false);
    stopAudioMeter();
  };

    const handleRepeatQuestion = () => {
    if (isAvaTalking || isAvaThinking) return;
    playAvaSpeech(question);
  };

  const handleRequestHint = async () => {
    if (!sessionId || isLoadingHint) return;
    setIsLoadingHint(true);
    try {
      const res = await apiFetch("/get-hint", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, eye_contact_pct: eyeContactPct, tab_switches: tabSwitches })
      });
      const data = await res.json();
      if (data.hint) {
        setHintText(data.hint);
      }
    } catch (err) {
      console.warn("Hint error:", err);
    } finally {
      setIsLoadingHint(false);
    }
  };

  // Submit Answer & Fetch Next Question (hands-free auto submit compatible)
  const submitAnswerAndNext = async (overrideAnswer = null) => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setAutoSubmitCountdown(null);

    const textToSubmit = (typeof overrideAnswer === "string" ? overrideAnswer : (answer || finalTranscriptRef.current || "")).trim();
    if (!textToSubmit) {
      if (!overrideAnswer) {
        alert("Please speak or type your answer first.");
      }
      return;
    }

    stopVoiceRecognition();
    setIsAvaThinking(true);
    setCaptionText("Evaluating your response and preparing next question...");
    setHintText("");

    try {
      const chosenCategory = (setupMode === "non_resume") ? (category || "Job Description") : (selectedType?.id || "Resume");
      const chosenRole = (setupMode === "non_resume" && roleTitle.trim()) ? roleTitle.trim() : (selectedType?.name || "Software Engineer");
      const res = await apiFetch("/next", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          answer: textToSubmit,
          category: chosenCategory,
          role: chosenRole,
          difficulty: difficulty || "Medium"
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to process answer");

      if (data.message === "Repeating question") {
        setIsAvaThinking(false);
        setCaptionText("Repeating question... Speak when ready!");
        playAvaSpeech(data.next_question);
        return;
      }

      if (data.feedback) {
        setAllFeedbacks(prev => [...prev, data.feedback]);
      }
      finalTranscriptRef.current = "";
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
      startVoiceRecognition();
    }
  };

    // End Interview & Generate Report
  const endInterviewSession = async () => {
    stopVoiceRecognition();
    setIsAvaThinking(true);
    setCaptionText("Compiling your comprehensive executive evaluation report...");

    try {
      const chosenCategory = (setupMode === "non_resume") ? (category || "Job Description") : (selectedType?.id || "Resume");
      const chosenRole = (setupMode === "non_resume" && roleTitle.trim()) ? roleTitle.trim() : (selectedType?.name || "Software Engineer");
      const res = await apiFetch("/end-interview", {
        method: "POST",
        body: JSON.stringify({ 
          session_id: sessionId, 
          role: chosenRole,
          category: chosenCategory,
          difficulty: difficulty || "Medium",
          eye_contact_pct: eyeContactPct, 
          tab_switches: tabSwitches 
        })
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
    <div class="hdr"><div class="brand">🚀 PrepFly Executive Evaluation (Ava)</div><div>Candidate: ${(safeUser?.name)||"Candidate"}<br/>Generated: ${new Date().toLocaleString()}</div></div>
    <div class="hero">
      <div class="grade-circle">${reportData?.grade || "F"}</div>
      <div>
        <div style="font-size:12px;color:#94a3b8;text-transform:uppercase;font-weight:700">Overall Rating</div>
        <div class="score-val">${reportData?.overall_score_100 ?? reportData?.overall_score ?? 0} / 100</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:4px">${reportData?.grade_label || "Candidate Evaluation"}</div>
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
    { id: "MAANG", name: "MAANG / Big Tech", duration: "45 min", desc: "A big-tech screen: your resume, technical architecture, and deep algorithmic trade-offs." },
    { id: "DSA", name: "DSA & Algorithms", duration: "20–45 min", desc: "Data structures, algorithms, complexity analysis, and live problem-solving reasoning." },
    { id: "Resume", name: "Resume Deep-Dive", duration: "20 min", desc: "Every question comes directly from your uploaded resume, past projects, and tech stack." },
    { id: "Fundamentals", name: "CS Fundamentals", duration: "15–45 min", desc: "Core computer science: Operating Systems, Computer Networks, DBMS, and OOP principles." },
    { id: "Guesstimate", name: "Guesstimate", duration: "15–30 min", desc: "Size a market or engineering volume out loud, assumption by assumption." },
    { id: "Puzzles", name: "Logic Puzzles", duration: "20 min", desc: "Classic analytical and logic puzzles, reasoned and communicated out loud." },
    { id: "SystemDesign", name: "System Design", duration: "30–45 min", desc: "Scalability, microservices, caching, database sharding, and high-availability systems." },
    { id: "HR", name: "HR & Behavioral", duration: "20 min", desc: "Culture fit, leadership, conflict resolution, and structured STAR-method storytelling." }
  ];

  return (
    <div style={{ backgroundColor: "#050811", color: "#ffffff", minHeight: "100vh", padding: "28px" }}>
      <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

        {/* ── STEP 1: RESUME OR NON-RESUME INTERVIEW SETUP ── */}
        {step === "resume_upload" && (
          <div style={{ maxWidth: "860px", margin: "30px auto", background: "rgba(12,18,32,0.9)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "24px", padding: "36px", boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "6px" }}>PREPFLY ADVANCED VOICE AI</div>
              <h2 style={{ fontSize: "28px", fontWeight: 900, marginBottom: "8px", color: "#fff" }}>Configure Your AI Interview</h2>
              <p style={{ fontSize: "14px", color: "var(--text2)", maxWidth: "560px", margin: "0 auto" }}>Choose your preferred interview setup mode below:</p>
            </div>

            {/* 2 Distinct Setup Mode Option Tabs */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", background: "rgba(255,255,255,0.03)", borderRadius: "16px", padding: "6px", marginBottom: "28px" }}>
              <button 
                type="button"
                onClick={() => setSetupMode("resume")} 
                style={{ 
                  padding: "14px", 
                  borderRadius: "12px", 
                  border: setupMode === "resume" ? "1.5px solid #00c4a7" : "1px solid transparent", 
                  background: setupMode === "resume" ? "linear-gradient(135deg, rgba(0,196,167,0.18), rgba(124,58,237,0.18))" : "transparent", 
                  color: setupMode === "resume" ? "#00c4a7" : "#94a3b8", 
                  fontWeight: 800, 
                  cursor: "pointer", 
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  transition: "all 0.2s"
                }}
              >
                <span style={{ fontSize: "18px" }}>📄</span>
                <span>Option 1: With Resume <strong>[Upload Resume]</strong></span>
              </button>

              <button 
                type="button"
                onClick={() => setSetupMode("non_resume")} 
                style={{ 
                  padding: "14px", 
                  borderRadius: "12px", 
                  border: setupMode === "non_resume" ? "1.5px solid #00c4a7" : "1px solid transparent", 
                  background: setupMode === "non_resume" ? "linear-gradient(135deg, rgba(0,196,167,0.18), rgba(124,58,237,0.18))" : "transparent", 
                  color: setupMode === "non_resume" ? "#00c4a7" : "#94a3b8", 
                  fontWeight: 800, 
                  cursor: "pointer", 
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  transition: "all 0.2s"
                }}
              >
                <span style={{ fontSize: "18px" }}>📋</span>
                <span>Option 2: Without Resume <strong>[With Job Description]</strong></span>
              </button>
            </div>

            {/* OPTION 1 CONTENT: RESUME UPLOAD */}
            {setupMode === "resume" ? (
              <div style={{ textAlign: "center" }}>
                {resumeFile ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(0,196,167,0.08)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "16px", padding: "18px 22px", marginBottom: "28px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                      <span style={{ fontSize: "28px" }}>📄</span>
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff" }}>{resumeFile?.name || 'Resume'}</div>
                        <div style={{ fontSize: "12px", color: "#00c4a7" }}>{(resumeFile.size / 1024).toFixed(1)} KB · Ava will personalize questions to your projects & experience</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "10px" }}>
                      {previewResumeUrl && (
                        <button type="button" onClick={() => window.open(previewResumeUrl, '_blank')} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "8px", width: "36px", height: "36px", color: "#fff", cursor: "pointer", fontSize: "16px" }} title="Preview Resume">👁️</button>
                      )}
                      <button type="button" onClick={clearResume} style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "8px", width: "36px", height: "36px", color: "#ef4444", cursor: "pointer", fontSize: "16px" }} title="Clear Resume">✕</button>
                    </div>
                  </div>
                ) : (
                  <div style={{ border: "2px dashed rgba(0,196,167,0.35)", borderRadius: "20px", padding: "40px 24px", marginBottom: "28px", position: "relative", cursor: "pointer", background: "rgba(0,196,167,0.02)" }}>
                    <input type="file" accept=".pdf,.docx" onChange={handleFileUpload} style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }} />
                    <div style={{ fontSize: "44px", marginBottom: "14px" }}>☁️</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#fff" }}>Click or Drag & Drop your resume (PDF or DOCX)</div>
                    <div style={{ fontSize: "13px", color: "var(--text2)", marginTop: "6px" }}>Option 1: Ava tailors every behavioral and technical question directly to your resume projects</div>
                  </div>
                )}
              </div>
            ) : (
              /* OPTION 2 CONTENT: WITHOUT RESUME (WITH JOB DESCRIPTION) */
              <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "28px", textAlign: "left" }}>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Target Role Title</label>
                  <input 
                    type="text" 
                    value={roleTitle} 
                    onChange={e => setRoleTitle(e.target.value)} 
                    placeholder="e.g. Senior Full Stack Engineer (React, Python, Microservices)" 
                    style={{ width: "100%", padding: "12px 14px", borderRadius: "10px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px" }} 
                  />
                </div>

                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                    Job Description (JD) & Key Requirements
                  </label>
                  <textarea 
                    value={jobDescription} 
                    onChange={e => setJobDescription(e.target.value)} 
                    placeholder="Paste the Job Description here (Responsibilities, Required Skills, Tech Stack, Qualifications)... Ava will tailor her questions to match this exact role!" 
                    rows={5}
                    style={{ width: "100%", padding: "12px 14px", borderRadius: "10px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px", resize: "vertical", fontFamily: "inherit" }} 
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Core Focus Category</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: "100%", padding: "11px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px" }}>
                      {["Full Stack / Generalist", "HR & Behavioral", "DSA & Algorithms", "System Design & Architecture", "OOPS & Clean Code", "DBMS & SQL", "OS & Networking", "Core CS"].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Difficulty Level</label>
                    <select value={difficulty} onChange={e => setDifficulty(e.target.value)} style={{ width: "100%", padding: "11px 14px", borderRadius: "10px", background: "#0c1220", border: "1px solid rgba(255,255,255,0.12)", color: "#fff", fontSize: "13px" }}>
                      <option value="Easy">Junior / Associate (Easy)</option>
                      <option value="Medium">Mid-Level / Standard (Medium)</option>
                      <option value="Hard">Senior / Lead (Hard)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div style={{ textAlign: "center", marginTop: "20px" }}>
              <button 
                type="button"
                onClick={() => {
                  if (setupMode === "resume" && !resumeFile) {
                    alert("Please upload your resume file (PDF/DOCX) first, or switch to Option 2: Without Resume [With Job Description].");
                    return;
                  }
                  if (setupMode === "non_resume") {
                    if (!roleTitle.trim()) {
                      alert("Please specify your Target Job Role (e.g. HR Manager, Python Developer).");
                      return;
                    }
                    if (!jobDescription.trim()) {
                      alert("Please provide the Job Description or key skill requirements.");
                      return;
                    }
                    setStep("device_check");
                    return;
                  }
                  setStep("type_selection");
                }} 
                style={{ padding: "14px 32px", borderRadius: "14px", background: "linear-gradient(135deg, #00c4a7, #7c3aed)", border: "none", color: "#fff", fontWeight: 800, fontSize: "14px", display: "inline-flex", alignItems: "center", gap: "10px", cursor: "pointer", boxShadow: "0 8px 24px rgba(0,196,167,0.4)" }} 
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
              <h2 style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>{selectedType?.name || (setupMode === "non_resume" ? roleTitle : "AI Mock")} Interview</h2>
              <p style={{ fontSize: "13px", color: "var(--text2)", marginTop: "4px" }}>Enable and test your camera and microphone before joining.</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "28px", marginBottom: "32px" }}>
              {/* Left: Camera Preview */}
              <div style={{ background: "#000", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "20px", overflow: "hidden", position: "relative", height: "320px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video
                  ref={(el) => {
                    videoRefDevice.current = el;
                    if (el && mediaStreamRef.current) {
                      bindStreamToVideo(el, mediaStreamRef.current);
                    }
                  }}
                  autoPlay
                  playsInline
                  muted
                  onLoadedMetadata={(e) => {
                    e.target.muted = true;
                    e.target.play().catch(() => {});
                  }}
                  style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)", display: (cameraOn && hasCameraStream) ? "block" : "none" }}
                />
                
                {!cameraOn && (
                  <div style={{ position: "absolute", inset: 0, background: "#0c1220", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: "64px", height: "64px", borderRadius: "50%", background: "linear-gradient(135deg, #00f0c8, #7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", fontWeight: 800, marginBottom: "12px" }}>
                      {safeUser?.name ? safeUser.name.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2) : "ME"}
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff" }}>Camera Muted</div>
                  </div>
                )}

                {cameraOn && (!hasCameraStream || cameraErrorMsg) && (
                  <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, #0b1120 0%, #050811 100%)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "20px", textAlign: "center", zIndex: 5 }}>
                    <div style={{ width: "52px", height: "52px", borderRadius: "50%", background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", marginBottom: "12px" }}>
                      📷
                    </div>
                    <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "6px" }}>Webcam Access Required</div>
                    <div style={{ fontSize: "12px", color: "#94a3b8", maxWidth: "260px", marginBottom: "14px", lineHeight: "1.4" }}>
                      {cameraErrorMsg || "Camera stream is inactive. Please allow browser camera and microphone permissions."}
                    </div>
                    <button
                      type="button"
                      onClick={() => setupCamera(true)}
                      style={{ padding: "8px 18px", borderRadius: "20px", background: "linear-gradient(135deg, #00c4a7, #00e5c3)", border: "none", color: "#050811", fontWeight: 800, fontSize: "12px", cursor: "pointer", boxShadow: "0 0 15px rgba(0,196,167,0.3)", display: "flex", alignItems: "center", gap: "6px" }}
                    >
                      <span>📹</span>
                      <span>Allow Camera & Mic</span>
                    </button>
                  </div>
                )}
                
                {/* Floating Controls */}
                <div style={{ position: "absolute", bottom: "16px", display: "flex", gap: "12px", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)", padding: "8px 16px", borderRadius: "30px", border: "1px solid rgba(255,255,255,0.15)", zIndex: 10 }}>
                  <button 
                    type="button"
                    onClick={() => {
                      const next = !cameraOn;
                      setCameraOn(next);
                      if (next) {
                        setupCamera(true);
                      } else {
                        if (mediaStreamRef.current) {
                          mediaStreamRef.current.getVideoTracks().forEach(t => t.enabled = false);
                        }
                      }
                    }} 
                    style={{ background: cameraOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}
                    title={cameraOn ? "Mute Camera" : "Unmute Camera"}
                  >
                    {cameraOn ? "📷" : "🚫"}
                  </button>
                  <button 
                    type="button"
                    onClick={() => {
                      const next = !micOn;
                      setMicOn(next);
                      if (next) {
                        const liveA = mediaStreamRef.current?.getAudioTracks().some(t => t.readyState === 'live');
                        if (!liveA) {
                          setupCamera(true);
                        } else {
                          mediaStreamRef.current.getAudioTracks().forEach(t => t.enabled = true);
                        }
                      } else {
                        if (mediaStreamRef.current) {
                          mediaStreamRef.current.getAudioTracks().forEach(t => t.enabled = false);
                        }
                      }
                    }} 
                    style={{ background: micOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}
                    title={micOn ? "Mute Microphone" : "Unmute Microphone"}
                  >
                    {micOn ? "🎙️" : "🔇"}
                  </button>
                  <button 
                    type="button"
                    onClick={showDeviceSettings} 
                    style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "50%", width: "40px", height: "40px", color: "#fff", cursor: "pointer" }}
                    title="Device Settings"
                  >
                    ⚙️
                  </button>
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

                {/* Explicit Affirmative Consent Card (DPDP Act 2023 / Privacy Compliance) */}
                <div style={{
                  background: "rgba(0,196,167,0.08)",
                  border: "1px solid rgba(0,196,167,0.3)",
                  borderRadius: "14px",
                  padding: "14px 16px",
                  marginTop: "6px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "10px",
                  textAlign: "left"
                }}>
                  <input
                    type="checkbox"
                    id="affirmative-consent-checkbox"
                    checked={consentGiven}
                    onChange={(e) => setConsentGiven(e.target.checked)}
                    style={{
                      marginTop: "3px",
                      width: "18px",
                      height: "18px",
                      accentColor: "#00c4a7",
                      cursor: "pointer"
                    }}
                  />
                  <label htmlFor="affirmative-consent-checkbox" style={{ fontSize: "11px", color: "#e2e8f0", lineHeight: "1.5", cursor: "pointer" }}>
                    <strong style={{ color: "#fff" }}>Affirmative Privacy & AI Consent (DPDP Act 2023):</strong> I explicitly consent to the recording and real-time processing of my voice, interview responses, and resume by PrepFly's AI interviewer (Ava) solely for candidate evaluation and scoring. I understand my data is confidential, is never used to train foundation models, and can be deleted upon request via my profile dashboard.
                  </label>
                </div>
              </div>
            </div>

            <div style={{ textAlign: "center", marginTop: "16px" }}>
              <button
                type="button"
                onClick={triggerStartInterview}
                disabled={!consentGiven}
                style={{
                  padding: "14px 44px",
                  borderRadius: "30px",
                  background: consentGiven
                    ? "linear-gradient(135deg,#00c4a7,#7c3aed)"
                    : "rgba(255,255,255,0.12)",
                  border: "none",
                  color: consentGiven ? "#fff" : "rgba(255,255,255,0.4)",
                  fontWeight: 900,
                  fontSize: "16px",
                  cursor: consentGiven ? "pointer" : "not-allowed",
                  boxShadow: consentGiven ? "0 8px 24px rgba(0,196,167,0.4)" : "none",
                  transition: "all 0.2s"
                }}
              >
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
                  ⏱️ {formatTimer(elapsedSeconds)} / 15:00
                </div>
                <div style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "20px", padding: "6px 14px", fontSize: "12px", fontWeight: 800, color: "#a78bfa" }}>
                  Stage: {currentStage}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>


                <button onClick={endInterviewSession} style={{ background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.4)", color: "#ef4444", borderRadius: "24px", padding: "8px 20px", fontWeight: 800, fontSize: "13px", cursor: "pointer" }}>
                  🚪 End Interview & Evaluate
                </button>
              </div>
            </div>

            {/* SPLIT CONTAINER: 50-50 OR WITH CODE EDITOR */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", flex: 1, minHeight: 0 }}>
              
              {/* LEFT 50%: CANDIDATE LIVE WEBCAM VIDEO */}
              <div style={{ background: "#000", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "24px", overflow: "hidden", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video
                  ref={(el) => {
                    videoRefCall.current = el;
                    if (el && mediaStreamRef.current) {
                      bindStreamToVideo(el, mediaStreamRef.current);
                    }
                  }}
                  autoPlay
                  playsInline
                  muted
                  onLoadedMetadata={(e) => {
                    e.target.muted = true;
                    e.target.play().catch(() => {});
                  }}
                  style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)", display: (cameraOn && hasCameraStream) ? "block" : "none" }}
                />
                
                {!cameraOn && (
                  <div style={{ position: "absolute", inset: 0, background: "#0c1220", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: "64px", height: "64px", borderRadius: "50%", background: "linear-gradient(135deg, #00f0c8, #7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", fontWeight: 800, marginBottom: "12px" }}>
                      {safeUser?.name ? safeUser.name.split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2) : "ME"}
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff" }}>Camera Muted</div>
                  </div>
                )}

                {cameraOn && (!hasCameraStream || cameraErrorMsg) && (
                  <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, #0b1120 0%, #050811 100%)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "24px", textAlign: "center", zIndex: 5 }}>
                    <div style={{ width: "56px", height: "56px", borderRadius: "50%", background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", marginBottom: "12px" }}>
                      📷
                    </div>
                    <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "6px" }}>Webcam Access Required</div>
                    <div style={{ fontSize: "12px", color: "#94a3b8", maxWidth: "280px", marginBottom: "16px", lineHeight: "1.4" }}>
                      {cameraErrorMsg || "Camera stream is inactive. Please allow browser camera and microphone permissions."}
                    </div>
                    <button
                      type="button"
                      onClick={() => setupCamera(true)}
                      style={{ padding: "9px 20px", borderRadius: "20px", background: "linear-gradient(135deg, #00c4a7, #00e5c3)", border: "none", color: "#050811", fontWeight: 800, fontSize: "12px", cursor: "pointer", boxShadow: "0 0 15px rgba(0,196,167,0.3)", display: "flex", alignItems: "center", gap: "6px" }}
                    >
                      <span>📹</span>
                      <span>Allow Camera & Mic</span>
                    </button>
                  </div>
                )}
                
                <div style={{ position: "absolute", bottom: "16px", left: "16px", background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)", padding: "6px 14px", borderRadius: "20px", border: "1px solid rgba(255,255,255,0.15)", fontSize: "12px", fontWeight: 800, color: "#fff", display: "flex", alignItems: "center", gap: "8px", zIndex: 10 }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: (cameraOn && hasCameraStream) ? "#00c4a7" : "#ef4444" }}></span>
                  🎥 {safeUser?.name ? safeUser.name.split(' ')[0] : 'Candidate'} (You)
                </div>

                {/* Floating Media Controls Overlay */}
                <div style={{ position: "absolute", bottom: "16px", right: "16px", display: "flex", gap: "10px", background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)", padding: "6px 12px", borderRadius: "30px", border: "1px solid rgba(255,255,255,0.15)", zIndex: 10 }}>
                  <button 
                    type="button"
                    onClick={() => {
                      const next = !cameraOn;
                      setCameraOn(next);
                      if (next) {
                        const liveV = mediaStreamRef.current?.getVideoTracks().some(t => t.readyState === 'live');
                        if (!liveV) {
                          setupCamera(true);
                        } else {
                          mediaStreamRef.current.getVideoTracks().forEach(t => t.enabled = true);
                        }
                      } else {
                        if (mediaStreamRef.current) {
                          mediaStreamRef.current.getVideoTracks().forEach(t => t.enabled = false);
                        }
                      }
                    }} 
                    style={{ background: cameraOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "32px", height: "32px", color: "#fff", cursor: "pointer", fontSize: "12px", display: "flex", alignItems: "center", justifyContent: "center" }}
                    title={cameraOn ? "Mute Camera" : "Unmute Camera"}
                  >
                    {cameraOn ? "📷" : "🚫"}
                  </button>
                  <button 
                    type="button"
                    onClick={() => {
                      const next = !micOn;
                      setMicOn(next);
                      if (next) {
                        const liveA = mediaStreamRef.current?.getAudioTracks().some(t => t.readyState === 'live');
                        if (!liveA) {
                          setupCamera(true);
                        } else {
                          mediaStreamRef.current.getAudioTracks().forEach(t => t.enabled = true);
                        }
                        startVoiceRecognition();
                      } else {
                        if (mediaStreamRef.current) {
                          mediaStreamRef.current.getAudioTracks().forEach(t => t.enabled = false);
                        }
                        stopVoiceRecognition();
                      }
                    }} 
                    style={{ background: micOn ? "rgba(0,196,167,0.2)" : "rgba(239,68,68,0.2)", border: "none", borderRadius: "50%", width: "32px", height: "32px", color: "#fff", cursor: "pointer", fontSize: "12px", display: "flex", alignItems: "center", justifyContent: "center" }}
                    title={micOn ? "Mute Microphone" : "Unmute Microphone"}
                  >
                    {micOn ? "🎙️" : "🔇"}
                  </button>
                </div>
              </div>

              {/* RIGHT 50%: AVA AI INTERVIEWER & VOICE SPEAKING PANEL */}
              <div style={{ background: "rgba(12,18,32,0.92)", border: "1px solid rgba(124,58,237,0.35)", borderRadius: "24px", padding: "22px", display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center", backdropFilter: "blur(12px)", boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}>
                
                {/* Real-time Status Badge */}
                <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button
                      type="button"
                      onClick={() => setIsHandsFree(!isHandsFree)}
                      style={{
                        background: isHandsFree ? "rgba(0,196,167,0.18)" : "rgba(255,255,255,0.08)",
                        border: isHandsFree ? "1px solid rgba(0,196,167,0.4)" : "1px solid rgba(255,255,255,0.15)",
                        color: isHandsFree ? "#00c4a7" : "#94a3b8",
                        padding: "4px 12px",
                        borderRadius: "20px",
                        fontSize: "11px",
                        fontWeight: 800,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px"
                      }}
                      title="Hands-free Voice: Automatically submits and listens when you pause speaking"
                    >
                      <span>{isHandsFree ? "⚡ Hands-Free VAD: ON" : "✋ Hands-Free: OFF"}</span>
                    </button>
                    <span style={{ fontSize: "11px", fontWeight: 800, padding: "4px 12px", borderRadius: "16px", background: isAvaTalking ? "rgba(0,196,167,0.2)" : isSpeakingAnswer ? "rgba(16,185,129,0.2)" : isAvaThinking ? "rgba(124,58,237,0.25)" : "rgba(255,255,255,0.08)", color: isAvaTalking ? "#00c4a7" : isSpeakingAnswer ? "#10b981" : isAvaThinking ? "#a78bfa" : "#94a3b8", border: isAvaTalking ? "1px solid rgba(0,196,167,0.4)" : isSpeakingAnswer ? "1px solid rgba(16,185,129,0.4)" : "1px solid rgba(255,255,255,0.1)" }}>
                      {isAvaTalking ? "🗣️ Ava Speaking" : isSpeakingAnswer ? "🎙️ Ava Listening" : isAvaThinking ? "⚡ Analyzing Response" : "Standby"}
                    </span>
                  </div>

                  {/* Active soundwave bars for microphone */}
                  {isSpeakingAnswer && (
                    <div style={{ display: "flex", alignItems: "center", gap: "3px", height: "18px" }}>
                      {[0.35, 0.65, 1.0, 0.75, 0.45, 0.3].map((factor, idx) => (
                        <div key={idx} style={{
                          width: "3px",
                          borderRadius: "3px",
                          background: "linear-gradient(to top, #00c4a7, #10b981)",
                          height: `${Math.max(5, Math.min(18, 5 + (audioLevel * factor * 0.25)))}px`,
                          transition: "height 0.08s ease"
                        }} />
                      ))}
                      <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 700, marginLeft: "4px" }}>Mic Live</span>
                    </div>
                  )}
                </div>

                {/* Ava Concentric Waves Orb */}
                <div style={{ width: "200px", height: "200px", position: "relative", margin: "6px 0" }}>
                  <CircleWavesAvatar isTalking={isAvaTalking} isThinking={isAvaThinking} />
                </div>

                {/* Spoken Question & Prompt Card */}
                <div style={{ width: "100%", padding: "14px 18px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", minHeight: "75px", display: "flex", flexDirection: "column", justifyContent: "center", textAlign: "center" }}>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#a78bfa", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px" }}>
                    Ava · Question {questionNumber} of 10 (~15 min)
                  </div>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff", lineHeight: "1.5" }}>
                    "{captionText || question || "Listening..."}"
                  </div>

                  {/* Interactive Quick Actions (Repeat & Hint) */}
                  <div style={{ display: "flex", justifyContent: "center", gap: "10px", marginTop: "10px" }}>
                    <button
                      type="button"
                      onClick={handleRepeatQuestion}
                      disabled={isAvaTalking || isAvaThinking}
                      style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "14px", padding: "4px 12px", color: "#e2e8f0", fontSize: "11px", fontWeight: 700, cursor: "pointer", transition: "all 0.2s" }}
                      title="Replay Ava's audio for this question"
                    >
                      🔄 Repeat Question
                    </button>
                    <button
                      type="button"
                      onClick={handleRequestHint}
                      disabled={isLoadingHint || isAvaTalking || isAvaThinking}
                      style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: "14px", padding: "4px 12px", color: "#fbbf24", fontSize: "11px", fontWeight: 700, cursor: "pointer", transition: "all 0.2s" }}
                      title="Ask Ava for a hint"
                    >
                      {isLoadingHint ? "Fetching Hint..." : "💡 Need a Hint"}
                    </button>
                  </div>

                  {/* Hint Pill if available */}
                  {hintText && (
                    <div style={{ marginTop: "10px", padding: "8px 12px", background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: "12px", fontSize: "12px", color: "#fef3c7", textAlign: "left", lineHeight: "1.4" }}>
                      <strong style={{ color: "#fbbf24" }}>💡 Ava's Tip:</strong> {hintText}
                    </div>
                  )}
                </div>

                {/* Spoken Answer & Response Area */}
                <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                  {autoSubmitCountdown !== null && (
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 14px",
                      borderRadius: "12px",
                      background: "rgba(0,196,167,0.15)",
                      border: "1px solid rgba(0,196,167,0.4)",
                      fontSize: "12px",
                      color: "#00e5c3",
                      fontWeight: 700,
                      animation: "coreGlowPulse 1.2s ease-in-out infinite"
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00e5c3" }}></span>
                        <span>🎙️ Answer captured · Ava answering in 2s (pause)...</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => submitAnswerAndNext(answer)}
                        style={{
                          background: "#00c4a7",
                          color: "#050811",
                          border: "none",
                          borderRadius: "8px",
                          padding: "3px 12px",
                          fontWeight: 800,
                          fontSize: "11px",
                          cursor: "pointer"
                        }}
                      >
                        Send Now →
                      </button>
                    </div>
                  )}
                  <textarea
                    rows={3}
                    placeholder="Speak your answer naturally (transcription appears here in real-time). You can also edit or type directly..."
                    value={answer}
                    onChange={e => {
                      setAnswer(e.target.value);
                      finalTranscriptRef.current = e.target.value;
                    }}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "14px",
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      color: "#fff",
                      fontSize: "13px",
                      fontFamily: "inherit",
                      lineHeight: "1.5",
                      resize: "none",
                      outline: "none"
                    }}
                  />

                  <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                    <button
                      type="button"
                      onClick={isSpeakingAnswer ? stopVoiceRecognition : startVoiceRecognition}
                      style={{
                        flex: 1,
                        padding: "11px 16px",
                        borderRadius: "14px",
                        background: isSpeakingAnswer ? "rgba(239,68,68,0.2)" : "rgba(124,58,237,0.2)",
                        border: isSpeakingAnswer ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(124,58,237,0.5)",
                        color: "#fff",
                        fontWeight: 800,
                        fontSize: "13px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        transition: "all 0.2s"
                      }}
                    >
                      {isSpeakingAnswer ? "⏸️ Pause Voice Mic" : "🎙️ Resume Voice Mic"}
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        stopVoiceRecognition();
                        setupCamera(true);
                        setTimeout(() => {
                          startVoiceRecognition();
                        }, 350);
                      }}
                      style={{
                        padding: "11px 16px",
                        borderRadius: "14px",
                        background: "rgba(255,255,255,0.06)",
                        border: "1px solid rgba(255,255,255,0.15)",
                        color: "#cbd5e1",
                        fontWeight: 700,
                        fontSize: "12.5px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        transition: "all 0.2s"
                      }}
                      title="Restart microphone capture and permissions"
                    >
                      🔄 Reconnect Mic
                    </button>
                    
                    <button
                      type="button"
                      onClick={submitAnswerAndNext}
                      disabled={isAvaThinking}
                      style={{
                        padding: "11px 22px",
                        borderRadius: "14px",
                        background: "linear-gradient(135deg, #00c4a7 0%, #00e5c3 100%)",
                        border: "none",
                        color: "#050811",
                        fontWeight: 900,
                        fontSize: "13px",
                        cursor: "pointer",
                        boxShadow: "0 0 20px rgba(0,196,167,0.4)",
                        transition: "all 0.2s"
                      }}
                    >
                      {isAvaThinking ? "Evaluating..." : "Submit Answer →"}
                    </button>
                  </div>
                </div>

              </div>
              </div>
          </div>
        )}

        {/* ── REPORT PANEL ── */}
        {step === "report" && reportData && (() => {
          const answeredCount = reportData.answered_questions_count !== undefined 
            ? Number(reportData.answered_questions_count) 
            : (allFeedbacks ? allFeedbacks.length : 0);

          let rawScore = 0;
          if (reportData.overall_score_100 !== undefined && reportData.overall_score_100 !== null) {
            rawScore = Number(reportData.overall_score_100);
          } else if (reportData.overall_score !== undefined && reportData.overall_score !== null) {
            rawScore = Number(reportData.overall_score);
          }
          if (rawScore > 100) {
            rawScore = rawScore / 10;
          }

          let score100 = Math.min(100, Math.max(0, Math.round(rawScore)));

          // PrepFly Proration Guard:
          // If candidate answered < 5 questions and score is not yet prorated, prorate by completion rate.
          // For early exit (e.g. 1 question), maximum possible score is 10/100.
          if (answeredCount === 0) {
            score100 = 0;
          } else if (answeredCount < 5 && score100 > (answeredCount * 10)) {
            score100 = Math.min(100, Math.max(0, Math.round(score100 * (answeredCount / 10))));
          }

          const allZero = reportData.section_grades && reportData.section_grades.length > 0 && reportData.section_grades.every(s => s.score === 0);
          if (answeredCount === 0 || allZero) {
            score100 = 0;
          }

          // PrepFly Standardized Hiring Tiers
          let gInfo;
          if (score100 === 0 || answeredCount === 0) {
            gInfo = {
              grade: "F",
              label: "Unevaluated / No Responses",
              desc: "No responses attempted during interview",
              color: "#ef4444",
              bgColor: "rgba(239, 68, 68, 0.15)",
              rec: "Strong Reject (No Responses Provided)",
              level: "Beginner / Not Attempted",
              score: 0
            };
          } else if (answeredCount < 3) {
            // Early exit after only 1-2 questions (e.g. candidate gave only 1 answer)
            gInfo = {
              grade: "F",
              label: "Incomplete / Early Exit",
              desc: `Only ${answeredCount} of 10 questions answered`,
              color: "#ef4444",
              bgColor: "rgba(239, 68, 68, 0.15)",
              rec: `Strong Reject (Incomplete — only ${answeredCount} of 10 questions answered)`,
              level: "Incomplete Session",
              score: score100
            };
          } else if (answeredCount < 5) {
            // Preliminary evaluation (3-4 questions)
            const rawG = getGradeInfo(score100);
            gInfo = {
              ...rawG,
              grade: rawG.grade.startsWith("A") || rawG.grade.startsWith("B") ? "D" : rawG.grade,
              label: "Preliminary Assessment",
              color: "#f59e0b",
              bgColor: "rgba(245, 158, 11, 0.15)",
              rec: "Preliminary Evaluation (Requires ≥ 5 answered questions)",
              level: "Preliminary Evaluation",
              score: score100
            };
          } else {
            // Full evaluation (5+ questions)
            gInfo = reportData.grade && reportData.grade_color ? {
              grade: reportData.grade,
              label: reportData.grade_label || "Evaluated Candidate",
              color: reportData.grade_color,
              bgColor: `${reportData.grade_color}22`,
              rec: reportData.hiring_recommendation || reportData.recommendation || "Evaluated",
              level: reportData.performance_level || "Standard Candidate",
              score: score100
            } : getGradeInfo(score100);
          }

          const sectionGrades = reportData.section_grades || computeSectionGrades(score100, allFeedbacks);
          const earnedBadges = (score100 === 0 || answeredCount < 5) ? [] : (reportData.badges || getBadges(score100, sectionGrades));
          const isEarlyExit = answeredCount < 3 && answeredCount > 0;
          const isPrelim = answeredCount < 5 && answeredCount >= 3;
          const confidence = score100 === 0 ? "None" : (reportData.confidence || (answeredCount < 3 ? "Low" : (answeredCount < 5 ? "Medium" : "High")));
          const recText = gInfo.rec || reportData.hiring_recommendation || reportData.recommendation;

          const hasNoResponses = answeredCount === 0 || score100 === 0;

          const topStrengths = hasNoResponses
            ? ["None identified: No responses provided during interview. Complete at least 5 questions to demonstrate strengths."]
            : (isEarlyExit 
                ? ["Preliminary observation: Complete more technical/behavioral questions to demonstrate strengths."] 
                : (reportData.top_strengths || ["Clear Communication", "Technical Understanding", "Structured Approach"]));

          const topImprovements = hasNoResponses
            ? ["Candidate did not speak or answer any questions. Speak into the microphone or submit answers to get evaluated."]
            : (isEarlyExit 
                ? [`Completed only ${answeredCount} of 10 questions. Ensure you complete the full interview to evaluate all 10 core dimensions.`] 
                : (reportData.top_improvements || ["Provide deeper technical details", "Use STAR technique for behavioral questions", "Structure answers with clear outcomes"]));

          return (
            <div style={{ maxWidth: "880px", margin: "20px auto", background: "rgba(12,18,32,0.95)", border: `1px solid ${gInfo.color}44`, boxShadow: `0 0 40px ${gInfo.color}15`, borderRadius: "24px", padding: "36px", textAlign: "center" }}>
              
              {/* INCOMPLETE / PRELIMINARY CONFIDENCE BANNER */}
              {(isEarlyExit || isPrelim) && (
                <div style={{ 
                  background: isEarlyExit ? "rgba(239, 68, 68, 0.1)" : "rgba(245, 158, 11, 0.1)", 
                  border: `1px solid ${isEarlyExit ? "rgba(239, 68, 68, 0.3)" : "rgba(245, 158, 11, 0.3)"}`, 
                  borderRadius: "16px", 
                  padding: "14px 20px", 
                  marginBottom: "20px", 
                  textAlign: "left", 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center" 
                }}>
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 800, color: isEarlyExit ? "#ef4444" : "#f59e0b", textTransform: "uppercase" }}>
                      {isEarlyExit ? "⚠️ Incomplete Interview (Early Exit)" : "⚠️ Preliminary Evaluation"}
                    </div>
                    <div style={{ fontSize: "13px", color: "#e2e8f0", marginTop: "2px" }}>
                      Questions Answered: <strong>{answeredCount} / 10</strong> · {isEarlyExit ? "At least 5 questions required for hiring assessment. Session marked incomplete." : "Complete at least 5 questions for a full hiring recommendation."}
                    </div>
                  </div>
                  <span style={{ 
                    background: isEarlyExit ? "#ef444422" : "#f59e0b22", 
                    color: isEarlyExit ? "#ef4444" : "#f59e0b", 
                    fontSize: "11px", 
                    fontWeight: 900, 
                    padding: "4px 12px", 
                    borderRadius: "20px", 
                    border: `1px solid ${isEarlyExit ? "#ef444444" : "#f59e0b44"}` 
                  }}>
                    Confidence: {confidence}
                  </span>
                </div>
              )}

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "20px", marginBottom: "24px" }}>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Executive Candidate Evaluation</div>
                  <div style={{ fontSize: "24px", fontWeight: 900, color: "#fff" }}>
                    {isEarlyExit ? "Incomplete Assessment" : (isPrelim ? "Preliminary Assessment" : `${gInfo.label} Candidate`)}
                  </div>
                  <div style={{ fontSize: "13px", color: gInfo.color, fontWeight: 800, marginTop: "4px" }}>📌 Hiring Recommendation: {gInfo.rec || recText}</div>
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
                <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#fff", marginBottom: "4px" }}>📊 Section Grades Breakdown (10 Dimensions)</h4>
                <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "14px" }}>Click on any dimension card below to view detailed FAANG-style behavioral evidence.</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px" }}>
                  {sectionGrades.map((sec, idx) => {
                    const isSelected = selectedEvidenceDimension?.name === sec.name;
                    const isNotAssessed = sec.score === null || sec.score === undefined || sec.grade === "N/A";
                    return (
                      <div 
                        key={idx} 
                        onClick={() => setSelectedEvidenceDimension(isSelected ? null : sec)}
                        style={{ 
                          background: isSelected ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)", 
                          border: isSelected ? `2.5px solid ${sec.color}` : `1px solid ${isNotAssessed ? "#475569" : sec.color}33`, 
                          borderRadius: "12px", 
                          padding: "10px", 
                          textAlign: "center",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          transform: isSelected ? "scale(1.03)" : "none",
                          opacity: isNotAssessed ? 0.75 : 1
                        }}
                      >
                        <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>{sec.name}</div>
                        <div style={{ fontSize: "15px", fontWeight: 900, color: isNotAssessed ? "#94a3b8" : sec.color, marginTop: "2px" }}>
                          {isNotAssessed ? "Not Evaluated" : `${sec.score} (${sec.grade})`}
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
                        🔍 Evidence Log: {selectedEvidenceDimension?.name || 'Evidence'} ({selectedEvidenceDimension.score !== undefined ? `${selectedEvidenceDimension.score}/100` : "N/A"})
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


              {/* ── PREPFLY SPEECH & DELIVERY TELEMETRY DASHBOARD ── */}
              {(() => {
                const isSpeechAbsent = hasNoResponses || !reportData.speech_metrics || (reportData.speech_metrics.total_words === 0 && (reportData.speech_metrics.wpm === 0 || !reportData.speech_metrics.wpm));

                const sm = isSpeechAbsent ? {
                  wpm: 0,
                  pacing_label: "No Speech Detected",
                  pacing_color: "#94a3b8",
                  total_words: 0,
                  filler_count: 0,
                  filler_breakdown: {},
                  vocabulary_diversity_pct: 0
                } : (reportData.speech_metrics || {
                  wpm: 0,
                  pacing_label: "Not Evaluated",
                  pacing_color: "#94a3b8",
                  total_words: 0,
                  filler_count: 0,
                  filler_breakdown: {},
                  vocabulary_diversity_pct: 0
                });

                const eyePct = hasNoResponses ? 0 : (reportData.eye_contact_pct !== undefined ? reportData.eye_contact_pct : (eyeContactPct || 0));
                const tabCount = reportData.tab_switches !== undefined ? reportData.tab_switches : (tabSwitches || 0);

                return (
                  <div style={{
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(0,196,167,0.25)",
                    borderRadius: "20px",
                    padding: "20px",
                    marginBottom: "24px",
                    textAlign: "left"
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                      <div>
                        <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#fff", margin: 0 }}>
                          🎙️ Speech & Communication Delivery Dashboard
                        </h4>
                        <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                          Deterministic telemetry: speaking pace, filler word frequency, lexical diversity, and engagement.
                        </div>
                      </div>
                      <span style={{ background: "rgba(0,196,167,0.15)", color: "#00c4a7", fontSize: "11px", fontWeight: 800, padding: "4px 12px", borderRadius: "16px", border: "1px solid rgba(0,196,167,0.3)" }}>
                        FAANG Metric Suite
                      </span>
                    </div>

                    {/* Notice if no speech was detected */}
                    {isSpeechAbsent && (
                      <div style={{
                        background: "rgba(239, 68, 68, 0.08)",
                        border: "1px solid rgba(239, 68, 68, 0.25)",
                        borderRadius: "12px",
                        padding: "10px 14px",
                        marginBottom: "16px",
                        fontSize: "12px",
                        color: "#fca5a5",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px"
                      }}>
                        <span>⚠️</span>
                        <span><strong>No Verbal Responses Recorded:</strong> Candidate did not speak during this interview. Spoken answers are required to calculate speaking pace, filler words, and lexical range.</span>
                      </div>
                    )}

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                      {/* WPM Pacing Card */}
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "14px", padding: "14px" }}>
                        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Speaking Pace</div>
                        <div style={{ fontSize: "22px", fontWeight: 900, color: isSpeechAbsent ? "#94a3b8" : "#fff", marginTop: "4px" }}>
                          {isSpeechAbsent ? 0 : sm.wpm} <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 600 }}>WPM</span>
                        </div>
                        <div style={{ fontSize: "11px", fontWeight: 800, color: isSpeechAbsent ? "#94a3b8" : (sm.pacing_color || "#10b981"), marginTop: "2px" }}>
                          ● {isSpeechAbsent ? "No Speech Detected" : (sm.pacing_label || "Optimal (130-155 WPM)")}
                        </div>
                      </div>

                      {/* Filler Words Card */}
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "14px", padding: "14px" }}>
                        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Filler Words</div>
                        <div style={{ fontSize: "22px", fontWeight: 900, color: isSpeechAbsent ? "#94a3b8" : (sm.filler_count > 6 ? "#f59e0b" : "#10b981"), marginTop: "4px" }}>
                          {isSpeechAbsent ? 0 : sm.filler_count} <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 600 }}>detected</span>
                        </div>
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "6px" }}>
                          {isSpeechAbsent ? (
                            <span style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>No speech recorded</span>
                          ) : Object.keys(sm.filler_breakdown || {}).length > 0 ? (
                            Object.entries(sm.filler_breakdown).slice(0, 4).map(([w, c], idx) => (
                              <span key={idx} style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b", fontSize: "10px", fontWeight: 700, padding: "2px 6px", borderRadius: "8px" }}>
                                {w}: {c}
                              </span>
                            ))
                          ) : (
                            <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 700 }}>Clean articulation</span>
                          )}
                        </div>
                      </div>

                      {/* Lexical Diversity */}
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "14px", padding: "14px" }}>
                        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Vocabulary Richness</div>
                        <div style={{ fontSize: "22px", fontWeight: 900, color: isSpeechAbsent ? "#94a3b8" : "#38bdf8", marginTop: "4px" }}>
                          {isSpeechAbsent ? 0 : (sm.vocabulary_diversity_pct || 0)}%
                        </div>
                        <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                          {isSpeechAbsent ? "No responses evaluated" : "Technical lexical range"}
                        </div>
                      </div>

                      {/* Eye Contact & Proctoring Integrity */}
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "14px", padding: "14px" }}>
                        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>Visual & Focus Integrity</div>
                        <div style={{ fontSize: "22px", fontWeight: 900, color: hasNoResponses ? "#94a3b8" : (eyePct >= 80 ? "#10b981" : "#f59e0b"), marginTop: "4px" }}>
                          {hasNoResponses ? "N/A" : `${eyePct}%`} <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 600 }}>{hasNoResponses ? "" : "Eye Contact"}</span>
                        </div>
                        <div style={{ fontSize: "11px", color: hasNoResponses ? "#94a3b8" : (tabCount === 0 ? "#10b981" : "#f59e0b"), marginTop: "2px", fontWeight: 700 }}>
                          {hasNoResponses ? "Session Incomplete / Not Evaluated" : (tabCount === 0 ? "✓ 100% Window Focus (0 Tab Switches)" : `⚠️ ${tabCount} Tab Switch(es) Detected`)}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* ── QUESTION-BY-QUESTION DEEP DIVE WITH STAFF BENCHMARKS ── */}
              {reportData.turn_evaluations && reportData.turn_evaluations.length > 0 && (
                <div style={{
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(124,58,237,0.3)",
                  borderRadius: "20px",
                  padding: "20px",
                  marginBottom: "24px",
                  textAlign: "left"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <div>
                      <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#fff", margin: 0 }}>
                        📋 Question-by-Question Deep Dive & Staff Benchmark Answers
                      </h4>
                      <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                        Compare your spoken response against top-tier Staff / Senior Engineer model answers and review recorded audio.
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {reportData.turn_evaluations.map((turn, tIdx) => {
                      const isExpanded = expandedTurn === tIdx;
                      const audioSrc = recordedAudios[turn.question_number];

                      return (
                        <div
                          key={tIdx}
                          style={{
                            background: "rgba(255,255,255,0.03)",
                            border: isExpanded ? "1px solid #7c3aed" : "1px solid rgba(255,255,255,0.08)",
                            borderRadius: "14px",
                            padding: "14px 18px",
                            transition: "all 0.2s"
                          }}
                        >
                          {/* Accordion Header */}
                          <div
                            onClick={() => setExpandedTurn(isExpanded ? null : tIdx)}
                            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, paddingRight: "10px" }}>
                              <span style={{
                                background: "rgba(124,58,237,0.2)",
                                color: "#a78bfa",
                                fontSize: "11px",
                                fontWeight: 800,
                                padding: "2px 8px",
                                borderRadius: "8px",
                                border: "1px solid rgba(124,58,237,0.3)"
                              }}>
                                Q{turn.question_number}
                              </span>
                              <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff", lineHeight: "1.4" }}>
                                {turn.question}
                              </span>
                            </div>

                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                              <span style={{
                                background: `${turn.grade_color || '#10b981'}22`,
                                color: turn.grade_color || "#10b981",
                                fontSize: "11px",
                                fontWeight: 800,
                                padding: "2px 8px",
                                borderRadius: "8px",
                                border: `1px solid ${turn.grade_color || '#10b981'}44`
                              }}>
                                {turn.score}/100 ({turn.grade})
                              </span>
                              <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                                {isExpanded ? "▲" : "▼"}
                              </span>
                            </div>
                          </div>

                          {/* Expanded Content */}
                          {isExpanded && (
                            <div style={{ marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "14px", display: "flex", flexDirection: "column", gap: "14px" }}>
                              {/* Audio Replay if captured */}
                              {audioSrc && (
                                <div style={{ background: "rgba(0,196,167,0.06)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "12px", padding: "10px 14px", display: "flex", alignItems: "center", gap: "12px" }}>
                                  <span style={{ fontSize: "12px", fontWeight: 800, color: "#00c4a7" }}>▶ Audio Replay:</span>
                                  <audio controls src={audioSrc} style={{ flex: 1, height: "32px" }} />
                                </div>
                              )}

                              {/* Your Answer */}
                              <div>
                                <div style={{ fontSize: "11px", fontWeight: 800, color: "#38bdf8", textTransform: "uppercase", marginBottom: "4px" }}>
                                  Candidate Spoken Answer
                                </div>
                                <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "10px 14px", fontSize: "12px", color: "#cbd5e1", fontStyle: "italic", lineHeight: "1.6" }}>
                                  "{turn.candidate_answer}"
                                </div>
                              </div>

                              {/* Staff Benchmark Model Answer */}
                              {turn.benchmark && (
                                <div style={{ background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.25)", borderRadius: "12px", padding: "14px" }}>
                                  <div style={{ fontSize: "12px", fontWeight: 900, color: "#c084fc", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span>🎯</span> Staff/Senior Engineer Model Answer Benchmark
                                  </div>
                                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#e2e8f0", lineHeight: "1.7" }}>
                                    {turn.benchmark.key_principles && turn.benchmark.key_principles.map((p, pIdx) => (
                                      <li key={pIdx} style={{ marginBottom: "4px" }}>{p}</li>
                                    ))}
                                  </ul>
                                  {turn.benchmark.staff_takeaway && (
                                    <div style={{ marginTop: "8px", fontSize: "11px", color: "#cbd5e1", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "8px" }}>
                                      <strong style={{ color: "#a78bfa" }}>What Top Interviewers Look For:</strong> {turn.benchmark.staff_takeaway}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* TOP STRENGTHS & IMPROVEMENTS */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ background: "rgba(0,196,167,0.04)", border: "1px solid rgba(0,196,167,0.2)", borderRadius: "20px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 900, color: "#00c4a7", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>💪</span> Top Strengths
                  </h4>
                  <div>
                    {hasNoResponses ? (
                      <div style={{ padding: "12px", color: "#94a3b8", fontSize: "12px", fontStyle: "italic", lineHeight: "1.5" }}>
                        No strengths identified. Candidate did not provide any spoken or written responses during the interview.
                      </div>
                    ) : (reportData.strengths && reportData.strengths.length > 0 && typeof reportData.strengths[0] === 'object' ? (
                      reportData.strengths.map((str, idx) => renderEvidenceCard(str, true, idx))
                    ) : (
                      topStrengths.map((str, idx) => renderEvidenceCard(str, true, idx))
                    ))}
                  </div>
                </div>
                <div style={{ background: "rgba(245,158,11,0.04)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "20px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 900, color: "#f59e0b", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>🎯</span> Focus Areas & Weaknesses
                  </h4>
                  <div>
                    {reportData.weaknesses && reportData.weaknesses.length > 0 && typeof reportData.weaknesses[0] === 'object' ? (
                      reportData.weaknesses.map((imp, idx) => renderEvidenceCard(imp, false, idx))
                    ) : (
                      topImprovements.map((imp, idx) => renderEvidenceCard(imp, false, idx))
                    )}
                  </div>
                </div>
              </div>

              {/* AI RECRUITER REPORT */}
              {reportData.report && !reportData.report.includes("Generating") && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "20px", textAlign: "left", color: "#e2e8f0", lineHeight: "1.7", marginBottom: "28px", fontSize: "13px" }}>
                  {renderMarkdown(reportData.report)}
                </div>
              )}


              <div style={{ display: "flex", gap: "14px", justifyContent: "center" }}>
                <button onClick={() => { try { sessionStorage.removeItem("prepfly_avatab_session"); } catch (_) {} setStep("resume_upload"); setReportData(null); setAllFeedbacks([]); setSessionId(null); }} style={{ padding: "12px 24px", borderRadius: "12px", background: "rgba(255,255,255,0.1)", border: "none", color: "#fff", fontWeight: 800, cursor: "pointer" }}>Practice Another</button>
                <button onClick={downloadPDFReport} style={{ padding: "12px 28px", borderRadius: "12px", background: "linear-gradient(135deg,#00c4a7,#7c3aed)", border: "none", color: "#fff", fontWeight: 800, cursor: "pointer" }}>📄 Download PDF Report</button>
              </div>
            </div>
          );
        })()}

      </div>
    </div>
  );
}
