import React, { useState, useEffect, useRef } from 'react';
import AI_INTERVIEWER, { INTERVIEWER_PERSONALITIES, getInterviewerPersonality } from '../config/aiInterviewerConfig';

const STATUS_META = {
  EVALUATED: {
    badge: "Evaluated",
    color: "#059669",
    bg: "#ecfdf5",
    border: "#a7f3d0",
  },
  PARTIAL: {
    badge: "Partial Evidence",
    color: "#d97706",
    bg: "#fffbeb",
    border: "#fde68a",
  },
  INCOMPLETE_INSUFFICIENT_DATA: {
    badge: "Incomplete · Insufficient Data",
    color: "#475569",
    bg: "#f1f5f9",
    border: "#cbd5e1",
  },
  EVALUATION_FAILED: {
    badge: "Evaluation Pending Retry",
    color: "#4f46e5",
    bg: "#eef2ff",
    border: "#c7d2fe",
  },
};

const formatDurationDisplay = (seconds) => {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) {
    return "Not measurable";
  }
  const s = Math.max(0, Math.round(Number(seconds)));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return m > 0 ? `${m}m ${rem}s` : `${rem}s`;
};

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
      background: isStrength ? "#ecfdf5" : "#fffbeb",
      border: isStrength ? "1px solid #a7f3d0" : "1px solid #fde68a",
      borderRadius: "14px",
      padding: "14px",
      marginBottom: "12px",
      textAlign: "left"
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
        <strong style={{ color: "#0f172a", fontSize: "12.5px", lineHeight: "1.4", display: "flex", alignItems: "center", gap: "6px" }}>
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
            background: isStrength ? "#d1fae5" : "#fef3c7",
            color: isStrength ? "#065f46" : "#92400e",
            border: isStrength ? "1px solid #6ee7b7" : "1px solid #fcd34d",
            whiteSpace: "nowrap"
          }}>
            {turnBadge}
          </span>
        )}
      </div>

      {observation && observation.toLowerCase() !== cleanTitle.toLowerCase() && (
        <div style={{ fontSize: "11.5px", color: "#475569", marginBottom: quote ? "8px" : "0", lineHeight: "1.5" }}>
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
  const [selectedPersonality, setSelectedPersonality] = useState("professional");
  const [useTextInput, setUseTextInput] = useState(false);
  
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
  const isEndingRef = useRef(false);
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

  // Phase 6: Capture telemetry, error/retry states, transcript preview & evidence drawer
  const [inputMode, setInputMode] = useState("speech"); // "speech" | "typed"
  const [sttConfidence, setSttConfidence] = useState(null);
  const [confirmedEdit, setConfirmedEdit] = useState(false);
  const [reviewNotice, setReviewNotice] = useState("");
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [setupError, setSetupError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [evaluatingTurns, setEvaluatingTurns] = useState([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState(null);
  const [retryEvalState, setRetryEvalState] = useState({ loading: false, error: null });
  const [emailState, setEmailState] = useState({ sending: false, sent: false, error: null });
  const [customNameDraft, setCustomNameDraft] = useState("");
  const [nameSaving, setNameSaving] = useState(false);
  const [evidenceDrawer, setEvidenceDrawer] = useState(null);

  const turnStartIsoRef = useRef(null);
  const speechStartMsRef = useRef(null);
  const speechConfsRef = useRef([]);
  const turnInputModeRef = useRef("speech");
  const turnIdemKeyRef = useRef(null);

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

  // Restore active interview step or report from localStorage / sessionStorage & backend persistence on reload
  useEffect(() => {
    try {
      const saved = localStorage.getItem("prepfly_avatab_session") || sessionStorage.getItem("prepfly_avatab_session");
      if (saved) {
        const p = JSON.parse(saved);
        if (p && p.sessionId && p.step === "report") {
          setSessionId(p.sessionId);
          setStep("report");
          if (p.reportData) setReportData(p.reportData);
          if (p.allFeedbacks) setAllFeedbacks(p.allFeedbacks);
          if (p.atsScore) setAtsScore(p.atsScore);
          // Rehydrate latest persisted report from DB
          setReportLoading(true);
          apiFetch(`/interview/${p.sessionId}/report`)
            .then(async (r) => {
              const d = await r.json();
              if (r.ok) {
                setReportData(d);
                setReportError(null);
              } else {
                setReportError(d.error || "Could not load saved report.");
              }
            })
            .catch((err) => setReportError(err.message || "Network error loading report."))
            .finally(() => setReportLoading(false));
        } else if (p && p.sessionId && p.step === "live_call") {
          setSessionId(p.sessionId);
          setStep("live_call");
          if (p.question) setQuestion(p.question);
          if (p.questionNumber) setQuestionNumber(p.questionNumber);
          apiFetch(`/interview/${p.sessionId}/state`)
            .then(async (r) => {
              if (!r.ok) return;
              const st = await r.json();
              if (st.current_question) setQuestion(st.current_question);
              const candTurns = (st.turns || []).filter((t) => t.speaker === "candidate");
              if (candTurns.length > 0) {
                setAllFeedbacks(candTurns);
                setQuestionNumber(candTurns.length + 1);
              }
              turnStartIsoRef.current = new Date().toISOString();
            })
            .catch(() => {});
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
  const triggerStartInterview = async (overrideSetupMode = null) => {
    if (!consentGiven) {
      setSetupError({
        message: "Affirmative privacy consent is required before starting your AI interview.",
        retryable: false,
        step: "consent",
      });
      return;
    }
    const activeMode = (typeof overrideSetupMode === "string" ? overrideSetupMode : null) || setupMode;
    setSetupError(null);
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
      if (activeMode === "resume" && resumeFile) {
        const formData = new FormData();
        formData.append("resume", resumeFile);
        formData.append("consent", "true");
        if (resolvedUserId) formData.append("user_id", resolvedUserId);

        const res = typeof apiFetch === "function"
          ? await apiFetch("/upload", { method: "POST", body: formData })
          : await fetch(`${BACKEND_URL}/upload`, {
              method: "POST",
              headers: localStorage.getItem("access_token") ? { "Authorization": "Bearer " + localStorage.getItem("access_token") } : {},
              body: formData
            });
        const data = await res.json();
        if (!res.ok) {
          clearInterval(interval);
          setSetupError({
            message: data.message || data.error || "Resume parsing failed temporarily.",
            retryable: data.retryable !== false,
            step: data.step || "resume_parse",
          });
          setStep("resume_upload");
          return;
        }
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
        if (!res.ok) {
          clearInterval(interval);
          setSetupError({
            message: data.message || data.error || "Failed to initialize interview session.",
            retryable: true,
            step: "session_create",
          });
          setStep("device_check");
          return;
        }
        activeSessionId = data.session_id;
      }

      if (!activeSessionId) {
        throw new Error("Interview session could not be established. Please retry.");
      }

      setSessionId(activeSessionId);

      const chosenCategory = (activeMode === "non_resume") ? (category || "Job Description") : (selectedType?.id || "Resume");
      const chosenRole = (activeMode === "non_resume" && roleTitle.trim()) ? roleTitle.trim() : (selectedType?.name || "Software Engineer");

      let startRes = await apiFetch("/start-interview", {
        method: "POST",
        body: JSON.stringify({
          session_id: activeSessionId,
          category: chosenCategory,
          role: chosenRole,
          difficulty: difficulty || "Medium",
          personality: selectedPersonality || "professional",
          job_description: jobDescription || "",
          idempotency_key: `start_${activeSessionId}`
        })
      });

      const startData = await startRes.json();
      if (!startRes.ok) {
        clearInterval(interval);
        setSetupError({
          message: startData.message || startData.error || "Failed to start interview.",
          retryable: true,
          step: "start_interview",
        });
        setStep("device_check");
        return;
      }

      clearInterval(interval);
      isEndingRef.current = false;
      setQuestion(startData.question);
      setQuestionNumber(startData.question_number || 1);
      if (startData.stage) setCurrentStage(startData.stage);
      turnStartIsoRef.current = new Date().toISOString();
      speechStartMsRef.current = null;
      speechConfsRef.current = [];
      setConfirmedEdit(false);
      setReviewNotice("");

      setTimeout(() => {
        setStep("live_call");
        setupCamera(true);
        playAvaSpeech(startData.question);
      }, 900);

    } catch (err) {
      clearInterval(interval);
      setSetupError({
        message: err.message || "Unexpected error starting interview.",
        retryable: true,
        step: "start_interview",
      });
      setStep("device_check");
    }
  };

  // Play Ava speech
  const playAvaSpeech = (text) => {
    if (isEndingRef.current) {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      setIsAvaTalking(false);
      return;
    }
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
      if (isEndingRef.current) {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        setIsAvaTalking(false);
        return;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        if (isEndingRef.current) return;
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
          if (!isEndingRef.current) {
            startVoiceRecognition();
          }
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
        if (!isEndingRef.current) {
          startVoiceRecognition();
        }
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

  // Voice Speech Recognition (Speaking Answer) with continuous recovery, telemetry & PrepFly VAD
  const startVoiceRecognition = () => {
    isListeningDesiredRef.current = true;
    setIsSpeakingAnswer(true);
    setInputMode("speech");
    turnInputModeRef.current = "speech";
    if (!turnStartIsoRef.current) {
      turnStartIsoRef.current = new Date().toISOString();
    }
    if (!speechStartMsRef.current) {
      speechStartMsRef.current = Date.now();
    }

    if (mediaStreamRef.current) {
      startAudioMeter(mediaStreamRef.current);
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      setMicErrorMsg("Speech-to-text is unavailable in this browser. Switched to Typed Response mode (all content dimensions are still evaluated).");
      setIsSpeakingAnswer(false);
      setInputMode("typed");
      turnInputModeRef.current = "typed";
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
        let latestChunk = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const alt = e.results[i][0];
          const chunk = alt.transcript;
          latestChunk = chunk;
          if (e.results[i].isFinal) {
            finalTranscriptRef.current += (finalTranscriptRef.current ? " " : "") + chunk.trim();
            if (typeof alt.confidence === "number" && alt.confidence > 0) {
              speechConfsRef.current.push(alt.confidence);
              const avgConf = speechConfsRef.current.reduce((a, b) => a + b, 0) / speechConfsRef.current.length;
              setSttConfidence(Number(avgConf.toFixed(3)));
            }
          } else {
            interim += chunk;
          }
        }
        // Barge-in Interruption: When candidate speaks while Ava is talking, interrupt playback
        if (isAvaTalkingRef.current && (interim || latestChunk)) {
          if ('speechSynthesis' in window) window.speechSynthesis.cancel();
          if (currentAudioRef.current) {
            try { currentAudioRef.current.pause(); } catch {}
          }
          setIsAvaTalking(false);
          isAvaTalkingRef.current = false;
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
        if (isHandsFreeRef.current && words.length >= 3 && !isAvaTalkingRef.current && !isAvaThinkingRef.current && !reviewNotice) {
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
          setMicErrorMsg("Microphone permission was denied. Switched to Typed Response mode so you can continue cleanly.");
          setIsSpeakingAnswer(false);
          setInputMode("typed");
          turnInputModeRef.current = "typed";
          isListeningDesiredRef.current = false;
          return;
        }
        if (e.error === "network" || e.error === "audio-capture") {
          setMicErrorMsg("Microphone audio/STT had a brief interruption. You can type or edit your answer directly below.");
        }
      };

      rec.start();
      recognitionRef.current = rec;
      setMicErrorMsg("");
    } catch (e) {
      console.warn("Voice speech rec start error:", e);
      setInputMode("typed");
      turnInputModeRef.current = "typed";
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

  // Submit Answer & Fetch Next Question (hands-free auto submit compatible + capture telemetry)
  const submitAnswerAndNext = async (overrideAnswer = null) => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setAutoSubmitCountdown(null);
    setSubmitError(null);

    const textToSubmit = (typeof overrideAnswer === "string" ? overrideAnswer : (answer || finalTranscriptRef.current || "")).trim();
    if (!textToSubmit) {
      if (!overrideAnswer) {
        setSubmitError("Please speak or type your answer before submitting.");
      }
      return;
    }

    stopVoiceRecognition();
    setIsAvaThinking(true);
    setCaptionText("Saving your response and preparing next question...");
    setHintText("");

    const endedIso = new Date().toISOString();
    const startedIso = turnStartIsoRef.current || endedIso;
    const isSpeechMode = turnInputModeRef.current === "speech";
    const measuredDurationSec = isSpeechMode && speechStartMsRef.current
      ? Math.max(0.5, Number(((Date.now() - speechStartMsRef.current) / 1000).toFixed(2)))
      : null;

    try {
      const chosenCategory = (setupMode === "non_resume") ? (category || "Job Description") : (selectedType?.id || "Resume");
      const chosenRole = (setupMode === "non_resume" && roleTitle.trim()) ? roleTitle.trim() : (selectedType?.name || "Software Engineer");
      if (!turnIdemKeyRef.current) {
        turnIdemKeyRef.current = `turn_${sessionId}_${questionNumber}_${Date.now()}`;
      }
      const res = await apiFetch("/next", {
        method: "POST",
        headers: { "X-Idempotency-Key": turnIdemKeyRef.current },
        body: JSON.stringify({
          session_id: sessionId,
          idempotency_key: turnIdemKeyRef.current,
          answer: textToSubmit,
          category: chosenCategory,
          role: chosenRole,
          difficulty: difficulty || "Medium",
          input_mode: isSpeechMode ? "speech" : "typed",
          stt_engine: isSpeechMode ? "web_speech_api" : null,
          stt_confidence: isSpeechMode ? sttConfidence : null,
          audio_duration_s: measuredDurationSec,
          started_at: startedIso,
          ended_at: endedIso,
          confirmed_edit: Boolean(confirmedEdit),
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.degraded_message || data.error || "Failed to process answer");

      if (data.requires_review) {
        setIsAvaThinking(false);
        setReviewNotice(data.message || "Low speech confidence detected. Review or edit your transcript below before submitting.");
        setConfirmedEdit(true);
        return;
      }

      if (data.message === "Repeating question") {
        setIsAvaThinking(false);
        setCaptionText("Repeating question... Speak when ready!");
        playAvaSpeech(data.next_question);
        return;
      }

      if (data.feedback || data.turn_id) {
        setAllFeedbacks(prev => [...prev, {
          ...(data.feedback || {}),
          turn_id: data.turn_id,
          question,
          response: textToSubmit,
          status: data.turn_status || "ok",
        }]);
      }
      finalTranscriptRef.current = "";
      speechStartMsRef.current = null;
      speechConfsRef.current = [];
      turnIdemKeyRef.current = null;
      turnStartIsoRef.current = new Date().toISOString();
      setSttConfidence(null);
      setConfirmedEdit(false);
      setReviewNotice("");
      setAnswer("");
      setIsAvaThinking(false);

      if (data.audio_cutoff || data.done) {
        isEndingRef.current = true;
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
        setIsAvaTalking(false);
        endInterviewSession(true);
        return;
      } else if (data.next_question) {
        setQuestion(data.next_question);
        setQuestionNumber(data.question_number || questionNumber + 1);
        if (data.stage) setCurrentStage(data.stage);
        playAvaSpeech(data.next_question);
      }
    } catch (err) {
      setSubmitError(err.message || "Could not submit your response. Your draft is preserved below.");
      setIsAvaThinking(false);
    }
  };

  // End Interview & Generate Report (with confirmation warning if < 3 substantive answers)
  const handleRequestEndInterview = () => {
    const answeredSoFar = allFeedbacks.length;
    if (answeredSoFar < 3) {
      setShowEndConfirm(true);
      return;
    }
    endInterviewSession(true);
  };

  const endInterviewSession = async (confirmedEarly = false) => {
    setShowEndConfirm(false);
    isEndingRef.current = true;
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsAvaTalking(false);
    stopVoiceRecognition();
    setIsAvaThinking(true);
    setReportLoading(true);
    setReportError(null);

    // Initialize visible per-turn evaluation progress list
    const initialTurnProgress = (allFeedbacks || []).map((f, idx) => ({
      turn: idx + 1,
      label: f.question ? f.question.slice(0, 48) : `Response ${idx + 1}`,
      status: "retrying",
    }));
    setEvaluatingTurns(initialTurnProgress);
    setCaptionText("Evaluating your answers against structured rubrics...");

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
          tab_switches: tabSwitches,
          confirmed_early: Boolean(confirmedEarly),
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "End interview failed");

      const revStatus = (data.question_reviews || []).map((q, idx) => ({
        turn: idx + 1,
        label: q.question ? q.question.slice(0, 48) : `Response ${idx + 1}`,
        status: q.evaluation_status === "ok" ? "ok" : (q.evaluation_status === "failed" ? "failed" : "ok"),
      }));
      if (revStatus.length > 0) setEvaluatingTurns(revStatus);

      setReportData(data);
      setStep("report");
      setIsAvaThinking(false);
      setReportLoading(false);
    } catch (err) {
      setReportError(err.message || "Error generating report.");
      setIsAvaThinking(false);
      setReportLoading(false);
    }
  };

  const retryFailedEvaluations = async () => {
    if (!sessionId || retryEvalState.loading) return;
    setRetryEvalState({ loading: true, error: null });
    try {
      const res = await apiFetch(`/interview/${sessionId}/retry-evaluations`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setRetryEvalState({ loading: false, error: data.message || data.error || "Evaluation service temporarily unavailable." });
      } else {
        setRetryEvalState({ loading: false, error: null });
      }
      const repRes = await apiFetch(`/interview/${sessionId}/report`);
      if (repRes.ok) {
        const repJson = await repRes.json();
        setReportData(repJson);
      }
    } catch (err) {
      setRetryEvalState({ loading: false, error: err.message || "Retry request failed." });
    }
  };

  const sendReportByEmail = async () => {
    if (!sessionId || emailState.sending) return;
    setEmailState({ sending: true, sent: false, error: null });
    try {
      const res = await apiFetch(`/interview/${sessionId}/email-report`, {
        method: "POST",
        body: JSON.stringify({ email: safeUser?.email || "" }),
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        setEmailState({ sending: false, sent: false, error: data.error || "Failed to send email." });
        return;
      }
      setEmailState({ sending: false, sent: true, error: null });
    } catch (err) {
      setEmailState({ sending: false, sent: false, error: err.message || "Network error sending email." });
    }
  };

  const saveCustomDisplayName = async () => {
    const trimmed = customNameDraft.trim();
    if (!trimmed || !sessionId || nameSaving) return;
    setNameSaving(true);
    try {
      const res = await apiFetch(`/interview/${sessionId}/display-name`, {
        method: "POST",
        body: JSON.stringify({ display_name: trimmed }),
      });
      const data = await res.json();
      if (res.ok) {
        setReportData(data);
        setCustomNameDraft("");
      }
    } catch {}
    setNameSaving(false);
  };

  const downloadPDFReport = () => {
    if (!reportData) return;
    const hdr = reportData.header || {};
    const status = reportData.report_status || "INCOMPLETE_INSUFFICIENT_DATA";
    const statusInfo = STATUS_META[status] || STATUS_META.INCOMPLETE_INSUFFICIENT_DATA;
    const candidateDisplay = hdr.candidate_name || reportData.candidate_name || safeUser?.name || "Candidate";
    const canShowScore = status === "EVALUATED" || status === "PARTIAL";
    const scoreStr = canShowScore && reportData.overall_score_100 !== null && reportData.overall_score_100 !== undefined
      ? `${reportData.overall_score_100} / 100`
      : "Not Scored";
    const gradeStr = canShowScore && reportData.grade ? reportData.grade : "—";
    const recStr = canShowScore && (reportData.recommendation || reportData.hiring_recommendation)
      ? (reportData.recommendation || reportData.hiring_recommendation)
      : reportData.status_reason || statusInfo.badge;
    const dimsHtml = (reportData.dimensions || reportData.section_grades || []).map((d) => {
      const val = d.score !== null && d.score !== undefined ? `${d.score}/100 (${d.grade || ""})` : "Not Evaluated";
      return `<div class="dim-row"><span>${d.name}</span><span>${val}</span></div>`;
    }).join("");
    const reviewsHtml = (reportData.question_reviews || []).map((q, i) =>
      `<div class="qa-card">
        <div style="color:#a78bfa;font-weight:800;margin-bottom:4px">Q${q.question_number || i + 1}: ${q.question || ""}${q.is_small_talk ? " (Small Talk · Excluded from scoring)" : ""}</div>
        <div style="color:#00c4a7;font-weight:700">${q.score_100 !== null && q.score_100 !== undefined ? `Score: ${q.score_100}/100` : `Status: ${q.evaluation_status || q.turn_status}`}</div>
        <div style="margin-top:8px;font-style:italic">"${q.candidate_answer || ""}"</div>
        ${q.improved_answer ? `<div style="margin-top:8px;color:#cbd5e1"><strong>Model Benchmark:</strong> ${q.improved_answer}</div>` : ""}
      </div>`
    ).join("");

    const html = `<!DOCTYPE html><html><head>
    <meta charset="UTF-8"/><title>PrepFly Interview Report - ${candidateDisplay}</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap');
      *{box-sizing:border-box;margin:0;padding:0}body{font-family:'Plus Jakarta Sans',sans-serif;background:#070b14;color:#f0f4fd;padding:40px;line-height:1.6}
      .hdr{display:flex;justify-content:space-between;padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:28px}
      .brand{font-size:24px;font-weight:900;background:linear-gradient(135deg,#00c4a7,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
      .hero{background:rgba(12,18,32,0.9);border:1px solid ${statusInfo.border};border-radius:20px;padding:28px;margin-bottom:28px;display:flex;gap:24px;align-items:center}
      .grade-circle{min-width:84px;height:84px;padding:0 14px;border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:900;border:2px solid ${statusInfo.color};background:${statusInfo.bg};color:${statusInfo.color}}
      .score-val{font-size:28px;font-weight:900;color:#00c4a7;margin-top:2px}
      .sec-title{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:#00c4a7;margin:24px 0 12px;border-left:3px solid #00c4a7;padding-left:10px}
      .dim-row{display:flex;justify-content:space-between;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06);font-size:13px}
      .qa-card{background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;margin-bottom:16px}
      .rpt-box{background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;font-size:14px;color:#e2e8f0;white-space:pre-wrap;line-height:1.7}
      .ftr{margin-top:40px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08);font-size:11px;color:#64748b;text-align:center}
    </style></head><body>
    <div class="hdr"><div class="brand">PrepFly Interview Report</div><div>Candidate: ${candidateDisplay}<br/>Role: ${hdr.role || "Software Engineer"} (${hdr.level || "Mid"})<br/>Status: ${statusInfo.badge}<br/>Generated: ${new Date().toLocaleString()}</div></div>
    <div class="hero">
      <div class="grade-circle">${gradeStr}</div>
      <div>
        <div style="font-size:12px;color:#94a3b8;text-transform:uppercase;font-weight:700">${statusInfo.badge}</div>
        <div class="score-val">${scoreStr}</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:4px">${recStr}</div>
      </div>
    </div>
    <div class="sec-title">Summary</div>
    <div class="rpt-box">${(reportData.narrative && reportData.narrative.text) || reportData.report || reportData.status_reason || ""}</div>
    <div class="sec-title">10 Dimensions</div>
    ${dimsHtml}
    <div class="sec-title">Question-by-Question Review</div>
    ${reviewsHtml}
    <div class="ftr">Evidence-Grounded Report generated from persisted interview turns (Formula ${reportData.formula_version || "v1"})</div>
    </body></html>`;
    const win = window.open("", "_blank");
    if (win) {
      win.document.write(html);
      win.document.close();
      setTimeout(() => win.print(), 600);
    }
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

  const isLiveRoomStep = step === "loading" || step === "live_call";

  return (
    <div style={{
      backgroundColor: isLiveRoomStep ? "#090c1a" : "transparent",
      color: isLiveRoomStep ? "#ffffff" : "#0f172a",
      minHeight: isLiveRoomStep ? "calc(100vh - 120px)" : "auto",
      borderRadius: isLiveRoomStep ? "20px" : "0",
      padding: isLiveRoomStep ? "24px" : "4px 0 28px"
    }}>
      <div style={{ maxWidth: "1080px", margin: "0 auto" }}>

        {/* ── STEP 1: RESUME OR NON-RESUME INTERVIEW SETUP ── */}
        {step === "resume_upload" && (
          <div style={{ maxWidth: "860px", margin: "8px auto", background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "22px", padding: "36px", boxShadow: "0 4px 20px rgba(15,23,42,0.04)" }}>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "6px" }}>PREPFLY ADVANCED VOICE AI</div>
              <h2 style={{ fontSize: "26px", fontWeight: 800, marginBottom: "8px", color: "#0f172a" }}>Configure Your AI Interview</h2>
              <p style={{ fontSize: "14px", color: "#64748b", maxWidth: "560px", margin: "0 auto" }}>Choose your preferred interview setup mode below:</p>
            </div>

            {setupError && (
              <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "14px", padding: "14px 18px", marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                <div style={{ fontSize: "13px", color: "#991b1b", textAlign: "left" }}>
                  <strong style={{ color: "#dc2626" }}>Upload / Parse Interrupted:</strong> {setupError.message}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  {setupError.retryable && resumeFile && (
                    <button type="button" onClick={() => triggerStartInterview("resume")} style={{ padding: "8px 14px", borderRadius: "10px", background: "#6d28d9", color: "#ffffff", border: "none", fontWeight: 800, fontSize: "12px", cursor: "pointer" }}>
                      Retry Resume Parse
                    </button>
                  )}
                  <button type="button" onClick={() => { setSetupError(null); setSetupMode("non_resume"); setResumeFile(null); }} style={{ padding: "8px 14px", borderRadius: "10px", background: "#ffffff", color: "#0f172a", border: "1px solid #cbd5e1", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}>
                    Continue Without Resume
                  </button>
                </div>
              </div>
            )}

            {/* 2 Distinct Setup Mode Option Tabs */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", background: "#eaedf6", borderRadius: "14px", padding: "6px", marginBottom: "26px" }}>
              <button 
                type="button"
                onClick={() => setSetupMode("resume")} 
                style={{ 
                  padding: "13px", 
                  borderRadius: "10px", 
                  border: setupMode === "resume" ? "1px solid #6d28d9" : "1px solid transparent", 
                  background: setupMode === "resume" ? "#ffffff" : "transparent", 
                  color: setupMode === "resume" ? "#6d28d9" : "#475569", 
                  fontWeight: 800, 
                  cursor: "pointer", 
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  boxShadow: setupMode === "resume" ? "0 2px 8px rgba(109,40,217,0.12)" : "none",
                  transition: "all 0.2s"
                }}
              >
                <span>Option 1: With Resume <strong>[Upload Resume]</strong></span>
              </button>

              <button 
                type="button"
                onClick={() => setSetupMode("non_resume")} 
                style={{ 
                  padding: "13px", 
                  borderRadius: "10px", 
                  border: setupMode === "non_resume" ? "1px solid #6d28d9" : "1px solid transparent", 
                  background: setupMode === "non_resume" ? "#ffffff" : "transparent", 
                  color: setupMode === "non_resume" ? "#6d28d9" : "#475569", 
                  fontWeight: 800, 
                  cursor: "pointer", 
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  boxShadow: setupMode === "non_resume" ? "0 2px 8px rgba(109,40,217,0.12)" : "none",
                  transition: "all 0.2s"
                }}
              >
                <span>Option 2: Without Resume <strong>[With Job Description]</strong></span>
              </button>
            </div>

            {/* OPTION 1 CONTENT: RESUME UPLOAD */}
            {setupMode === "resume" ? (
              <div style={{ textAlign: "center" }}>
                {resumeFile ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#f5f3ff", border: "1px solid #c4b5fd", borderRadius: "16px", padding: "18px 22px", marginBottom: "28px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                      <span style={{ fontSize: "26px" }}>📄</span>
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a" }}>{resumeFile?.name || 'Resume'}</div>
                        <div style={{ fontSize: "12px", color: "#6d28d9" }}>{(resumeFile.size / 1024).toFixed(1)} KB · Ava will personalize questions to your projects & experience</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "10px" }}>
                      {previewResumeUrl && (
                        <button type="button" onClick={() => window.open(previewResumeUrl, '_blank')} style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "8px", width: "36px", height: "36px", color: "#0f172a", cursor: "pointer", fontSize: "16px" }} title="Preview Resume">👁️</button>
                      )}
                      <button type="button" onClick={clearResume} style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", width: "36px", height: "36px", color: "#dc2626", cursor: "pointer", fontSize: "16px" }} title="Clear Resume">✕</button>
                    </div>
                  </div>
                ) : (
                  <div style={{ border: "2px dashed #c4b5fd", borderRadius: "18px", padding: "40px 24px", marginBottom: "28px", position: "relative", cursor: "pointer", background: "#faf8ff" }}>
                    <input type="file" accept=".pdf,.docx" onChange={handleFileUpload} style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }} />
                    <div style={{ fontSize: "38px", marginBottom: "12px" }}>☁️</div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>Click or Drag &amp; Drop your resume (PDF or DOCX)</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "6px" }}>Option 1: Ava tailors every behavioral and technical question directly to your resume projects</div>
                  </div>
                )}
              </div>
            ) : (
              /* OPTION 2 CONTENT: WITHOUT RESUME (WITH JOB DESCRIPTION) */
              <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "28px", textAlign: "left" }}>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Target Role Title</label>
                  <input 
                    type="text" 
                    value={roleTitle} 
                    onChange={e => setRoleTitle(e.target.value)} 
                    placeholder="e.g. Senior Full Stack Engineer (React, Python, Microservices)" 
                    style={{ width: "100%", padding: "12px 14px", borderRadius: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "13px" }} 
                  />
                </div>

                <div>
                  <label style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                    Job Description (JD) &amp; Key Requirements
                  </label>
                  <textarea 
                    value={jobDescription} 
                    onChange={e => setJobDescription(e.target.value)} 
                    placeholder="Paste the Job Description here (Responsibilities, Required Skills, Tech Stack, Qualifications)... Ava will tailor her questions to match this exact role!" 
                    rows={5}
                    style={{ width: "100%", padding: "12px 14px", borderRadius: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "13px", resize: "vertical", fontFamily: "inherit" }} 
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Core Focus Category</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: "100%", padding: "11px 14px", borderRadius: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "13px" }}>
                      {["Full Stack / Generalist", "HR & Behavioral", "DSA & Algorithms", "System Design & Architecture", "OOPS & Clean Code", "DBMS & SQL", "OS & Networking", "Core CS"].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Difficulty Level</label>
                    <select value={difficulty} onChange={e => setDifficulty(e.target.value)} style={{ width: "100%", padding: "11px 14px", borderRadius: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "13px" }}>
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
                style={{ padding: "13px 32px", borderRadius: "12px", background: "linear-gradient(135deg, #6d28d9, #7c3aed)", border: "none", color: "#fff", fontWeight: 800, fontSize: "14px", display: "inline-flex", alignItems: "center", gap: "10px", cursor: "pointer", boxShadow: "0 6px 20px rgba(109,40,217,0.28)" }} 
                title="Continue to Track Selection"
              >
                Continue to Track Selection ➔
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: INTERVIEW TYPE SELECTION CARDS ── */}
        {step === "type_selection" && (
          <div style={{ marginTop: "12px" }}>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a" }}>Choose Interview Track</h2>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>Select the topic and format for your 1-on-1 AI Recruiter interview with Ava</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "18px" }}>
              {interviewTypes.map(t => (
                <div key={t.id} style={{ background: "#ffffff", border: selectedType?.id === t.id ? "2px solid #6d28d9" : "1px solid #e5e8f2", borderRadius: "18px", padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between", minHeight: "220px", boxShadow: "0 2px 12px rgba(15,23,42,0.04)", transition: "all 0.2s ease" }}>
                  <div>
                    <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", marginBottom: "10px" }}>{t.name}</h3>
                    <p style={{ fontSize: "13px", color: "#475569", lineHeight: "1.6" }}>{t.desc}</p>
                  </div>
                  <button onClick={() => { setSelectedType(t); setStep("device_check"); }} style={{ width: "100%", padding: "12px", borderRadius: "12px", background: "linear-gradient(135deg,#6d28d9,#7c3aed)", border: "none", color: "#fff", fontWeight: 800, fontSize: "13px", cursor: "pointer", marginTop: "16px" }}>
                    Start {t.name} →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── STEP 3: PRE-INTERVIEW DEVICE CHECK SCREEN ── */}
        {step === "device_check" && (
          <div style={{ maxWidth: "960px", margin: "10px auto", background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "22px", padding: "30px" }}>
            <div style={{ textAlign: "center", marginBottom: "24px" }}>
              <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a" }}>{selectedType?.name || (setupMode === "non_resume" ? roleTitle : "AI Mock")} Interview</h2>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>Enable and test your camera and microphone before joining.</p>
            </div>

            {setupError && (
              <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "16px", padding: "14px 18px", marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                <div style={{ fontSize: "13px", color: "#991b1b" }}>
                  <strong style={{ color: "#7f1d1d" }}>Session Error:</strong> {setupError.message}
                </div>
                {setupError.retryable && (
                  <button type="button" onClick={() => triggerStartInterview()} style={{ padding: "8px 16px", borderRadius: "10px", background: "var(--violet)", color: "#ffffff", border: "none", fontWeight: 800, fontSize: "12px", cursor: "pointer" }}>
                    Retry Start Interview
                  </button>
                )}
              </div>
            )}

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
              <div style={{ background: "#f8fafc", border: "1px solid #e5e8f2", borderRadius: "20px", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a" }}>Things to know before starting</h3>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🕒</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>Expect to spend ~20 minutes</div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Very short interviews may not be considered complete. Please answer thoughtfully.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>✋</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>Need assistance? Just ask</div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Tell the AI if you need a question repeated or more time.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🔒</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>Your data is in your control</div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Your responses are used only to assess your candidacy and are never used to train AI models.</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "20px" }}>🌐</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>Supported browsers</div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Chrome and Safari are preferred for the best experience.</div>
                  </div>
                </div>

                {/* Interviewer Personality Selection */}
                <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "16px", textAlign: "left" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <div style={{ fontSize: "12px", fontWeight: 800, color: "#0f172a", textTransform: "uppercase", letterSpacing: "0.5px" }}>Interviewer Personality</div>
                    <span style={{ fontSize: "11px", color: "#6d28d9", fontWeight: 700 }}>Rubric score remains objective</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "8px" }}>
                    {INTERVIEWER_PERSONALITIES.map(p => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setSelectedPersonality(p.id)}
                        style={{
                          padding: "8px 6px",
                          borderRadius: "10px",
                          border: selectedPersonality === p.id ? "1.5px solid #6d28d9" : "1px solid #e2e8f0",
                          background: selectedPersonality === p.id ? "#f5f3ff" : "#f8fafc",
                          color: selectedPersonality === p.id ? "#6d28d9" : "#475569",
                          cursor: "pointer",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          gap: "3px",
                          textAlign: "center"
                        }}
                      >
                        <span style={{ fontSize: "11px", fontWeight: 800 }}>{p.name.replace(" Ava", "")}</span>
                        <span style={{ fontSize: "9px", color: "#64748b" }}>{p.badge}</span>
                      </button>
                    ))}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "8px" }}>
                    {getInterviewerPersonality(selectedPersonality).description}
                  </div>
                  {getInterviewerPersonality(selectedPersonality).sampleLine && (
                    <div style={{ fontSize: "11px", color: "#5b21b6", marginTop: "6px", fontStyle: "italic", background: "#f5f3ff", padding: "6px 10px", borderRadius: "8px", borderLeft: "2px solid #7c3aed" }}>
                      Spoken Tone Preview: "{getInterviewerPersonality(selectedPersonality).sampleLine}"
                    </div>
                  )}
                </div>

                {/* Explicit Affirmative Consent Card (DPDP Act 2023 / Privacy Compliance) */}
                <div style={{
                  background: "#f5f3ff",
                  border: "1px solid #ddd6fe",
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
                      accentColor: "#6d28d9",
                      cursor: "pointer"
                    }}
                  />
                  <label htmlFor="affirmative-consent-checkbox" style={{ fontSize: "11px", color: "#334155", lineHeight: "1.5", cursor: "pointer" }}>
                    <strong style={{ color: "#0f172a" }}>Affirmative Privacy &amp; AI Consent (DPDP Act 2023):</strong> I explicitly consent to the recording and real-time processing of my voice, interview responses, and resume by PrepFly's AI interviewer (Ava) solely for candidate evaluation and scoring. I understand my data is confidential, is never used to train foundation models, and can be deleted upon request via my profile dashboard.
                  </label>
                </div>
              </div>
            </div>

            <div style={{ textAlign: "center", marginTop: "16px" }}>
              <button
                type="button"
                onClick={() => triggerStartInterview()}
                disabled={!consentGiven}
                style={{
                  padding: "14px 44px",
                  borderRadius: "30px",
                  background: consentGiven
                    ? "linear-gradient(135deg,#6d28d9,#7c3aed)"
                    : "#e2e8f0",
                  border: "none",
                  color: consentGiven ? "#ffffff" : "#94a3b8",
                  fontWeight: 800,
                  fontSize: "15px",
                  cursor: consentGiven ? "pointer" : "not-allowed",
                  boxShadow: consentGiven ? "0 8px 24px rgba(109,40,217,0.3)" : "none",
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
                <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>
                  Answered: {allFeedbacks.length}
                </span>
                <button onClick={handleRequestEndInterview} style={{ background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.4)", color: "#ef4444", borderRadius: "24px", padding: "8px 20px", fontWeight: 800, fontSize: "13px", cursor: "pointer" }}>
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

                {/* Spoken Answer & Transcript Preview Area */}
                <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                  {/* Live Transcript Preview Header + Mode Switch */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                        Transcript Preview (Editable Before Submit)
                      </span>
                      <span style={{ background: inputMode === "speech" ? "rgba(0,196,167,0.14)" : "rgba(148,163,184,0.15)", color: inputMode === "speech" ? "#00c4a7" : "#cbd5e1", padding: "2px 8px", borderRadius: "10px", fontWeight: 700 }}>
                        {inputMode === "speech" ? "Voice Capture" : "Typed Mode"}
                      </span>
                      {sttConfidence !== null && inputMode === "speech" && (
                        <span style={{ color: sttConfidence < 0.55 ? "#f59e0b" : "#94a3b8", fontWeight: 700 }}>
                          STT {Math.round(sttConfidence * 100)}%
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ color: "#94a3b8" }}>{answer.trim() ? answer.trim().split(/\s+/).length : 0} words</span>
                      <button
                        type="button"
                        onClick={() => {
                          if (inputMode === "speech") {
                            stopVoiceRecognition();
                            setInputMode("typed");
                            turnInputModeRef.current = "typed";
                          } else {
                            setInputMode("speech");
                            turnInputModeRef.current = "speech";
                            startVoiceRecognition();
                          }
                        }}
                        style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)", color: "#cbd5e1", borderRadius: "8px", padding: "2px 8px", fontSize: "10.5px", fontWeight: 700, cursor: "pointer" }}
                      >
                        {inputMode === "speech" ? "Switch to Typing" : "Use Voice"}
                      </button>
                    </div>
                  </div>

                  {micErrorMsg && (
                    <div style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.35)", borderRadius: "10px", padding: "8px 12px", fontSize: "11.5px", color: "#fde68a", textAlign: "left" }}>
                      {micErrorMsg}
                    </div>
                  )}

                  {reviewNotice && (
                    <div style={{ background: "rgba(124,58,237,0.16)", border: "1px solid rgba(124,58,237,0.45)", borderRadius: "10px", padding: "8px 12px", fontSize: "12px", color: "#e9d5ff", textAlign: "left", fontWeight: 700 }}>
                      {reviewNotice}
                    </div>
                  )}

                  {submitError && (
                    <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.35)", borderRadius: "10px", padding: "8px 12px", fontSize: "11.5px", color: "#fca5a5", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>{submitError}</span>
                      <button type="button" onClick={() => submitAnswerAndNext(answer)} style={{ background: "#ef4444", color: "#fff", border: "none", borderRadius: "8px", padding: "3px 10px", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                        Retry Submit
                      </button>
                    </div>
                  )}

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
                        <span>🎙️ Answer captured · Review transcript or click Send Now...</span>
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
                    placeholder={inputMode === "typed" ? "Type your technical or behavioral response directly here..." : "Speak your answer naturally — live transcript appears here so you can review or edit before submitting..."}
                    value={answer}
                    onChange={e => {
                      setAnswer(e.target.value);
                      finalTranscriptRef.current = e.target.value;
                      if (!isSpeakingAnswer) {
                        setInputMode("typed");
                        turnInputModeRef.current = "typed";
                      } else {
                        setConfirmedEdit(true);
                      }
                    }}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "14px",
                      background: reviewNotice ? "rgba(124,58,237,0.08)" : "rgba(255,255,255,0.04)",
                      border: reviewNotice ? "1.5px solid #a78bfa" : "1px solid rgba(255,255,255,0.12)",
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
                      onClick={() => submitAnswerAndNext()}
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
                      {isAvaThinking ? "Saving..." : (reviewNotice ? "Confirm & Submit Transcript →" : "Submit Answer →")}
                    </button>
                  </div>
                </div>

              </div>
              </div>

            {/* Early Exit Confirmation Modal */}
            {showEndConfirm && (
              <div style={{ position: "fixed", inset: 0, background: "rgba(5,8,17,0.84)", backdropFilter: "blur(10px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100 }}>
                <div style={{ maxWidth: "460px", width: "92%", background: "#0c1220", border: "1px solid rgba(245,158,11,0.4)", borderRadius: "20px", padding: "28px", textAlign: "left", boxShadow: "0 20px 60px rgba(0,0,0,0.75)" }}>
                  <div style={{ fontSize: "13px", fontWeight: 800, color: "#f59e0b", textTransform: "uppercase", marginBottom: "6px" }}>
                    Early Exit Notice
                  </div>
                  <h3 style={{ fontSize: "18px", fontWeight: 900, color: "#fff", marginBottom: "10px" }}>
                    End interview before minimum coverage?
                  </h3>
                  <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: "1.6", marginBottom: "18px" }}>
                    You have submitted <strong>{allFeedbacks.length}</strong> response(s) so far (at least <strong>3 substantive answers</strong> are needed for a full grade &amp; recommendation). If you end now, your saved answers are preserved and the report will be marked <strong>Incomplete · Insufficient Data</strong> until you continue.
                  </p>
                  <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                    <button type="button" onClick={() => setShowEndConfirm(false)} style={{ padding: "10px 18px", borderRadius: "12px", background: "linear-gradient(135deg,#00c4a7,#00e5c3)", border: "none", color: "#050811", fontWeight: 800, fontSize: "13px", cursor: "pointer" }}>
                      Keep Answering
                    </button>
                    <button type="button" onClick={() => endInterviewSession(true)} style={{ padding: "10px 18px", borderRadius: "12px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", fontWeight: 700, fontSize: "13px", cursor: "pointer" }}>
                      End &amp; Save Progress
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Evaluating Answers Progress Overlay */}
            {reportLoading && (
              <div style={{ position: "fixed", inset: 0, background: "rgba(5,8,17,0.92)", backdropFilter: "blur(14px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1150 }}>
                <div style={{ maxWidth: "480px", width: "92%", background: "#0c1220", border: "1px solid rgba(0,196,167,0.35)", borderRadius: "22px", padding: "30px", textAlign: "left" }}>
                  <div style={{ fontSize: "12px", fontWeight: 800, color: "#00c4a7", textTransform: "uppercase", marginBottom: "6px" }}>Rubric Evaluation Engine</div>
                  <h3 style={{ fontSize: "20px", fontWeight: 900, color: "#fff", marginBottom: "14px" }}>Evaluating your answers...</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "14px" }}>
                    {evaluatingTurns.length > 0 ? evaluatingTurns.map((et, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderRadius: "10px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", fontSize: "12px" }}>
                        <span style={{ color: "#e2e8f0" }}>Turn {et.turn}: {et.label}</span>
                        <span style={{ fontWeight: 800, color: et.status === "ok" ? "#00c4a7" : et.status === "failed" ? "#f87171" : "#f59e0b", textTransform: "uppercase", fontSize: "10.5px" }}>
                          {et.status}
                        </span>
                      </div>
                    )) : (
                      <div style={{ fontSize: "13px", color: "#94a3b8" }}>Reconstructing evidence from persisted turns...</div>
                    )}
                  </div>
                  {reportError && (
                    <div style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.35)", borderRadius: "12px", padding: "10px 14px", fontSize: "12px", color: "#fca5a5", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>{reportError}</span>
                      <button type="button" onClick={() => endInterviewSession(true)} style={{ background: "#00c4a7", color: "#050811", border: "none", borderRadius: "8px", padding: "5px 12px", fontWeight: 800, cursor: "pointer" }}>
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── REPORT LOADING SKELETON / ERROR RETRY STATE ── */}
        {step === "report" && !reportData && (
          <div style={{ maxWidth: "900px", margin: "20px auto", background: "rgba(12,18,32,0.96)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "24px", padding: "36px", textAlign: "left" }}>
            {reportError ? (
              <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.35)", borderRadius: "16px", padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 800, color: "#fca5a5" }}>Could not load interview report</div>
                  <div style={{ fontSize: "12px", color: "#cbd5e1", marginTop: "4px" }}>{reportError}</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (!sessionId) return;
                    setReportLoading(true);
                    setReportError(null);
                    apiFetch(`/interview/${sessionId}/report`)
                      .then(async (r) => {
                        const d = await r.json();
                        if (r.ok) setReportData(d);
                        else setReportError(d.error || "Could not load saved report.");
                      })
                      .catch((err) => setReportError(err.message || "Network error."))
                      .finally(() => setReportLoading(false));
                  }}
                  style={{ padding: "8px 16px", borderRadius: "10px", background: "#00c4a7", color: "#050811", border: "none", fontWeight: 800, cursor: "pointer" }}
                >
                  Retry Load
                </button>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: "14px", fontWeight: 800, color: "#00c4a7", marginBottom: "14px" }}>Loading evidence-grounded report...</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px" }}>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <div key={n} style={{ height: "64px", borderRadius: "12px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── REPORT PANEL (STRICTLY EVIDENCE-GROUNDED, NO HARDCODED TEMPLATES) ── */}
        {step === "report" && reportData && (() => {
          const status = reportData.report_status || "INCOMPLETE_INSUFFICIENT_DATA";
          const statusInfo = STATUS_META[status] || STATUS_META.INCOMPLETE_INSUFFICIENT_DATA;
          const hdr = reportData.header || {};
          const candidateName = hdr.candidate_name || reportData.candidate_name || safeUser?.name || "Candidate";
          const needsNamePrompt = Boolean(hdr.needs_name_prompt || reportData.display_name_source === "fallback");
          const canShowScore = status === "EVALUATED" || status === "PARTIAL";
          const overall100 = canShowScore ? reportData.overall_score_100 : null;
          const displayGrade = canShowScore ? reportData.grade : null;
          const displayRec = canShowScore ? (reportData.recommendation || reportData.hiring_recommendation) : null;
          const coveragePct = reportData.coverage !== undefined && reportData.coverage !== null ? Math.round(Number(reportData.coverage) * 100) : 0;
          const confLabel = (reportData.confidence && (reportData.confidence.label || reportData.confidence.level)) || "NONE";
          const dims = reportData.dimensions || reportData.section_grades || [];
          const unassessed = reportData.not_assessed_yet || [];
          const sm = reportData.speech_metrics || {};
          const isWpmNull = sm.wpm === null || sm.wpm === undefined;
          const qReviews = reportData.question_reviews || reportData.turn_evaluations || [];
          const strengths = Array.isArray(reportData.strengths) ? reportData.strengths : [];
          const weaknesses = Array.isArray(reportData.weaknesses) ? reportData.weaknesses : [];
          const recurringTags = Array.isArray(reportData.recurring_misconceptions) ? reportData.recurring_misconceptions : [];
          const roadmapLinks = Array.isArray(reportData.roadmap_evidence_links) ? reportData.roadmap_evidence_links : [];
          const reviewsByTurnId = {};
          qReviews.forEach((qr) => {
            if (qr && qr.turn_id) reviewsByTurnId[qr.turn_id] = qr;
          });

          const resetSessionToSetup = () => {
            try {
              localStorage.removeItem("prepfly_avatab_session");
              sessionStorage.removeItem("prepfly_avatab_session");
            } catch (_) {}
            isEndingRef.current = false;
            setStep("resume_upload");
            setReportData(null);
            setAllFeedbacks([]);
            setSessionId(null);
            setEvidenceDrawer(null);
            setSetupError(null);
          };

          const openOverallEvidenceDrawer = () => {
            setEvidenceDrawer({
              title: "Overall Score & Coverage Evidence",
              scoreLabel: overall100 !== null && overall100 !== undefined ? `${overall100}/100 (${displayGrade || ""})` : statusInfo.badge,
              subtitle: `Formula ${reportData.formula_version || "v1"} · Coverage ${coveragePct}% · Confidence ${confLabel}`,
              formulaInputs: {
                formula_version: reportData.formula_version || "v1",
                evaluated_dimensions: dims.filter(d => d.score !== null && d.score !== undefined).length,
                total_dimensions: dims.length || 10,
                coverage: `${coveragePct}%`,
                substantive_turns: reportData.answered_questions_count ?? 0,
                confidence: confLabel,
              },
              items: dims.filter(d => Array.isArray(d.evidence) && d.evidence.length > 0).flatMap(d => d.evidence.map(ev => ({ ...ev, dimension: d.name }))),
            });
          };

          const openDimensionDrawer = (sec) => {
            const firstTurnId = Array.isArray(sec.contributing_turns) && sec.contributing_turns.length > 0 ? sec.contributing_turns[0] : null;
            const linkedRev = firstTurnId ? reviewsByTurnId[firstTurnId] : null;
            setEvidenceDrawer({
              title: sec.name,
              scoreLabel: sec.score !== null && sec.score !== undefined ? `${sec.score}/100 (${sec.grade || ""})` : "Not Evaluated",
              subtitle: `${sec.status === "LIMITED_EVIDENCE" ? "Limited Evidence · " : ""}Weight ${Math.round((sec.weight || 0) * 100)}% · ${sec.turn_count || 0} turn(s)`,
              formulaInputs: {
                ...(sec.formula_inputs || {}),
                evaluator_type: (linkedRev && linkedRev.evaluator_type) || "gemini_rubric_v1",
                prompt_id: (linkedRev && linkedRev.prompt_id) || "interview_rubric_grader",
                prompt_version: (linkedRev && linkedRev.prompt_version) || "v1.0",
                model_used: (linkedRev && linkedRev.model_used) || "recorded_per_turn",
              },
              items: Array.isArray(sec.evidence) ? sec.evidence : [],
              missingReason: sec.reason || null,
            });
          };

          return (
            <div style={{ maxWidth: "920px", margin: "8px auto", background: "#ffffff", border: `1px solid ${statusInfo.border}`, boxShadow: "0 6px 28px rgba(15,23,42,0.06)", borderRadius: "22px", padding: "34px", textAlign: "center", color: "#0f172a" }}>
              {reportLoading && (
                <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "12px", padding: "10px 14px", marginBottom: "16px", fontSize: "12px", color: "#6d28d9", fontWeight: 700 }}>
                  Syncing latest report state from persisted database records...
                </div>
              )}

              {/* Add your name banner ONLY when identity fell back to "Candidate" */}
              {needsNamePrompt && (
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "12px 16px", marginBottom: "18px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", flexWrap: "wrap", textAlign: "left" }}>
                  <div style={{ fontSize: "12.5px", color: "#334155" }}>
                    <strong>Add your name:</strong> No profile or resume name was found on this session.
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <input
                      type="text"
                      value={customNameDraft}
                      onChange={(e) => setCustomNameDraft(e.target.value)}
                      placeholder="Enter your full name"
                      style={{ padding: "6px 10px", borderRadius: "8px", background: "#ffffff", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "12px" }}
                    />
                    <button type="button" onClick={saveCustomDisplayName} disabled={nameSaving || !customNameDraft.trim()} style={{ padding: "6px 14px", borderRadius: "8px", background: "#6d28d9", color: "#ffffff", border: "none", fontWeight: 800, fontSize: "12px", cursor: "pointer" }}>
                      {nameSaving ? "Saving..." : "Save Name"}
                    </button>
                  </div>
                </div>
              )}

              {/* NON-ALARMING STATUS BANNER FOR NON-EVALUATED REPORTS */}
              {status !== "EVALUATED" && (
                <div style={{
                  background: statusInfo.bg,
                  border: `1px solid ${statusInfo.border}`,
                  borderRadius: "16px",
                  padding: "16px 20px",
                  marginBottom: "22px",
                  textAlign: "left",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "14px",
                  flexWrap: "wrap",
                }}>
                  <div style={{ flex: 1, minWidth: "240px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 900, color: statusInfo.color, textTransform: "uppercase", letterSpacing: "0.8px" }}>
                      {statusInfo.badge}
                    </div>
                    <div style={{ fontSize: "13px", color: "#334155", marginTop: "4px", lineHeight: "1.5" }}>
                      {reportData.status_reason || "More evidence is required before issuing a full evaluation."}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    {status === "EVALUATION_FAILED" && (
                      <button
                        type="button"
                        onClick={retryFailedEvaluations}
                        disabled={retryEvalState.loading}
                        style={{ padding: "9px 16px", borderRadius: "10px", background: "#6d28d9", color: "#ffffff", border: "none", fontWeight: 800, fontSize: "12px", cursor: "pointer" }}
                      >
                        {retryEvalState.loading ? "Retrying Evaluation..." : "Retry Evaluation"}
                      </button>
                    )}
                    {(status === "INCOMPLETE_INSUFFICIENT_DATA" || status === "PARTIAL") && (
                      <button
                        type="button"
                        onClick={() => {
                          isEndingRef.current = false;
                          setStep("live_call");
                        }}
                        style={{ padding: "9px 16px", borderRadius: "10px", background: "#6d28d9", color: "#ffffff", border: "none", fontWeight: 800, fontSize: "12px", cursor: "pointer" }}
                      >
                        Continue Interview →
                      </button>
                    )}
                  </div>
                </div>
              )}

              {retryEvalState.error && (
                <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "12px", padding: "10px 14px", marginBottom: "16px", fontSize: "12px", color: "#dc2626", textAlign: "left" }}>
                  Retry notice: {retryEvalState.error}
                </div>
              )}

              {/* REPORT HEADER */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #e5e8f2", paddingBottom: "22px", marginBottom: "24px", gap: "16px", flexWrap: "wrap" }}>
                <div style={{ textAlign: "left" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>
                      {hdr.role || "Software Engineer"} · {hdr.level || "Mid"}
                    </span>
                    <span style={{ fontSize: "10px", fontWeight: 800, padding: "2px 10px", borderRadius: "12px", background: statusInfo.bg, color: statusInfo.color, border: `1px solid ${statusInfo.border}` }}>
                      {statusInfo.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: "26px", fontWeight: 800, color: "#0f172a" }}>
                    {candidateName}
                  </div>
                  <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                    Date: {hdr.date ? new Date(hdr.date).toLocaleDateString() : "Today"} · Measured Speech Time: <span style={{ color: hdr.duration_s ? "#0f172a" : "#64748b", fontWeight: 600 }}>{formatDurationDisplay(hdr.duration_s)}</span> · Coverage: {coveragePct}%
                  </div>
                  {displayRec ? (
                    <div style={{ fontSize: "13px", color: statusInfo.color, fontWeight: 800, marginTop: "6px" }}>
                      Hiring Recommendation: {displayRec} · Confidence: {confLabel}
                    </div>
                  ) : (
                    <div style={{ fontSize: "12.5px", color: "#64748b", fontWeight: 700, marginTop: "6px" }}>
                      No grade or hiring verdict issued while status is {statusInfo.badge}.
                    </div>
                  )}
                </div>

                {/* Clickable Score Circle */}
                {canShowScore ? (
                  <button
                    type="button"
                    onClick={openOverallEvidenceDrawer}
                    title="Click to inspect formula inputs & evidence"
                    style={{ minWidth: "106px", height: "106px", padding: "0 14px", borderRadius: "50%", background: statusInfo.bg, border: `3px solid ${statusInfo.color}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}
                  >
                    <div style={{ fontSize: displayGrade && displayGrade.length > 3 ? "14px" : "28px", fontWeight: 800, color: statusInfo.color, lineHeight: 1.1 }}>{displayGrade}</div>
                    <div style={{ fontSize: "12px", fontWeight: 800, color: "#0f172a", marginTop: "3px" }}>{overall100}/100</div>
                    <div style={{ fontSize: "9px", color: "#64748b", marginTop: "2px" }}>Evidence ↗</div>
                  </button>
                ) : (
                  <div style={{ minWidth: "106px", height: "106px", padding: "0 12px", borderRadius: "50%", background: "#f1f5f9", border: "2px dashed #94a3b8", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <div style={{ fontSize: "13px", fontWeight: 800, color: "#475569" }}>Not Scored</div>
                    <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>{coveragePct}% cov</div>
                  </div>
                )}
              </div>

              {/* SECTION GRADES (10 DIMENSIONS) */}
              <div style={{ background: "#f8fafc", border: "1px solid #e5e8f2", borderRadius: "18px", padding: "20px", marginBottom: "24px", textAlign: "left" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a", marginBottom: "4px" }}>Section Grades Breakdown (10 Dimensions)</h4>
                <p style={{ fontSize: "11.5px", color: "#64748b", marginBottom: "14px" }}>Click any dimension card to open the Evidence Drawer (turn citations, quoted snippets, prompt version, formula inputs).</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "10px" }}>
                  {dims.map((sec, idx) => {
                    const isNotAssessed = sec.score === null || sec.score === undefined || sec.status === "Not evaluated";
                    const cardColor = isNotAssessed ? "#64748b" : (sec.color === "#00c4a7" ? "#059669" : (sec.color || "#6d28d9"));
                    return (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => openDimensionDrawer(sec)}
                        style={{
                          background: "#ffffff",
                          border: `1px solid ${isNotAssessed ? "#e2e8f0" : `${cardColor}44`}`,
                          borderRadius: "12px",
                          padding: "12px 10px",
                          textAlign: "center",
                          cursor: "pointer",
                          color: "#0f172a",
                        }}
                      >
                        <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>{sec.name}</div>
                        <div style={{ fontSize: "15px", fontWeight: 800, color: cardColor, marginTop: "4px" }}>
                          {isNotAssessed ? "Not evaluated" : `${sec.score} (${sec.grade})`}
                        </div>
                        <div style={{ fontSize: "9.5px", color: "#64748b", marginTop: "4px" }}>
                          {isNotAssessed ? "Excluded from average" : (sec.status === "LIMITED_EVIDENCE" ? "Limited evidence ↗" : `${sec.turn_count || 0} turn(s) ↗`)}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* NOT ASSESSED YET LIST */}
              {unassessed.length > 0 && (
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "16px 20px", marginBottom: "24px", textAlign: "left" }}>
                  <div style={{ fontSize: "12px", fontWeight: 800, color: "#475569", textTransform: "uppercase", marginBottom: "8px" }}>
                    Not Assessed Yet ({unassessed.length} dimension{unassessed.length === 1 ? "" : "s"} — never counted as weaknesses or zero)
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {unassessed.map((dName, i) => (
                      <span key={i} style={{ background: "#e2e8f0", color: "#334155", fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "10px" }}>
                        {dName}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* SPEECH & COMMUNICATION TELEMETRY DASHBOARD */}
              <div style={{ background: "#f8fafc", border: "1px solid #ddd6fe", borderRadius: "18px", padding: "20px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "8px" }}>
                  <div>
                    <h4 style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a", margin: 0 }}>Speech &amp; Communication Telemetry</h4>
                    <div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
                      Computed strictly from captured speech duration and transcript words. Unmeasured signals show &quot;Not measurable&quot;.
                    </div>
                  </div>
                  <span style={{ background: "#ede9fe", color: "#5b21b6", fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "12px" }}>
                    Words: {sm.total_words ?? 0}
                  </span>
                </div>

                {sm.missing_reason && (
                  <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "10px 14px", marginBottom: "14px", fontSize: "12px", color: "#475569" }}>
                    <strong style={{ color: "#0f172a" }}>Telemetry Notice:</strong> {sm.missing_reason}
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: "12px" }}>
                  <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "14px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Speaking Pace</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: isWpmNull ? "#64748b" : "#0f172a", marginTop: "4px" }}>
                      {sm.wpm_display || (isWpmNull ? "Not measurable" : `${sm.wpm} WPM`)}
                    </div>
                  </div>
                  <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "14px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Filler Words</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: sm.filler_count === null || sm.filler_count === undefined ? "#64748b" : "#059669", marginTop: "4px" }}>
                      {sm.filler_count_display || "Not measurable"}
                    </div>
                    {sm.filler_breakdown && Object.keys(sm.filler_breakdown).length > 0 && (
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "6px" }}>
                        {Object.entries(sm.filler_breakdown).map(([fw, fc], idx) => (
                          <span key={idx} style={{ background: "#fffbeb", color: "#b45309", border: "1px solid #fde68a", fontSize: "10px", padding: "2px 6px", borderRadius: "6px", fontWeight: 700 }}>
                            {fw}: {fc}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "14px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Pauses</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: sm.pause_count === null || sm.pause_count === undefined ? "#64748b" : "#0f172a", marginTop: "4px" }}>
                      {sm.pause_count_display || "Not measurable"}
                    </div>
                  </div>
                  <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "14px", padding: "14px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Speaking Duration</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: sm.speaking_time_s ? "#6d28d9" : "#64748b", marginTop: "4px" }}>
                      {sm.speaking_time_display || "Not measurable"}
                    </div>
                  </div>
                </div>

                {Array.isArray(sm.tips) && sm.tips.length > 0 && (
                  <ul style={{ margin: "12px 0 0", paddingLeft: "18px", fontSize: "12px", color: "#475569", lineHeight: "1.6" }}>
                    {sm.tips.map((tip, i) => <li key={i}>{tip}</li>)}
                  </ul>
                )}
              </div>

              {/* TOP STRENGTHS & WEAKNESSES (CITED QUOTES ONLY) */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ background: "#ffffff", border: "1px solid #a7f3d0", borderRadius: "18px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 800, color: "#059669", marginBottom: "12px" }}>Evidence-Backed Strengths</h4>
                  {strengths.length > 0 ? strengths.map((str, idx) => renderEvidenceCard(str, true, idx)) : (
                    <div style={{ padding: "10px", color: "#64748b", fontSize: "12px", lineHeight: "1.5" }}>
                      {reportData.strengths_empty_message || `Not enough strong evidence yet (dimension coverage: ${coveragePct}%).`}
                    </div>
                  )}
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #fde68a", borderRadius: "18px", padding: "18px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: 800, color: "#d97706", marginBottom: "12px" }}>Focus Areas &amp; Weaknesses</h4>
                  {recurringTags.length > 0 && (
                    <div style={{ marginBottom: "10px", display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      {recurringTags.map((rt, i) => (
                        <span key={i} style={{ background: "#fffbeb", color: "#b45309", border: "1px solid #fde68a", fontSize: "10.5px", fontWeight: 800, padding: "3px 8px", borderRadius: "8px" }}>
                          Recurring ({rt.count} turns): {rt.tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {weaknesses.length > 0 ? weaknesses.map((imp, idx) => renderEvidenceCard(imp, false, idx)) : (
                    <div style={{ padding: "10px", color: "#64748b", fontSize: "12px", lineHeight: "1.5" }}>
                      No evaluated criteria fell below the weakness threshold.
                    </div>
                  )}
                </div>
              </div>

              {/* QUESTION-BY-QUESTION REVIEW */}
              {qReviews.length > 0 && (
                <div style={{ background: "#f8fafc", border: "1px solid #e5e8f2", borderRadius: "18px", padding: "20px", marginBottom: "24px", textAlign: "left" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a", marginBottom: "12px" }}>Question-by-Question Review (From Persisted Turns)</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {qReviews.map((turn, tIdx) => {
                      const isExpanded = expandedTurn === tIdx;
                      const audioSrc = recordedAudios[turn.question_number];
                      const hasTurnScore = turn.score_100 !== null && turn.score_100 !== undefined && !turn.is_small_talk;
                      return (
                        <div key={tIdx} style={{ background: "#ffffff", border: isExpanded ? "1px solid #7c3aed" : "1px solid #e2e8f0", borderRadius: "14px", padding: "14px 16px" }}>
                          <div onClick={() => setExpandedTurn(isExpanded ? null : tIdx)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", gap: "10px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1 }}>
                              <span style={{ background: "#ede9fe", color: "#5b21b6", fontSize: "11px", fontWeight: 800, padding: "2px 8px", borderRadius: "8px" }}>
                                Q{turn.question_number || tIdx + 1}
                              </span>
                              <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>{turn.question || "Interview Question"}</span>
                              {turn.is_small_talk && (
                                <span style={{ background: "#f1f5f9", color: "#475569", fontSize: "10px", fontWeight: 700, padding: "2px 7px", borderRadius: "8px" }}>
                                  Small Talk · Excluded from scoring
                                </span>
                              )}
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ fontSize: "11px", fontWeight: 800, padding: "2px 8px", borderRadius: "8px", background: hasTurnScore ? "#ecfdf5" : "#f1f5f9", color: hasTurnScore ? "#059669" : "#64748b" }}>
                                {hasTurnScore ? `${turn.score_100}/100` : (turn.evaluation_status === "failed" ? "Eval Failed" : "Not Scored")}
                              </span>
                              <span style={{ fontSize: "12px", color: "#64748b" }}>{isExpanded ? "▲" : "▼"}</span>
                            </div>
                          </div>
                          {isExpanded && (
                            <div style={{ marginTop: "12px", borderTop: "1px solid #e5e8f2", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
                              {audioSrc && (
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                  <span style={{ color: "#6d28d9", fontWeight: 800 }}>▶ Audio Replay:</span>
                                  <audio controls src={audioSrc} style={{ flex: 1, height: "30px" }} />
                                </div>
                              )}
                              <div>
                                <div style={{ color: "#4f46e5", fontWeight: 800, marginBottom: "4px" }}>Candidate Transcript ({turn.input_mode || "typed"})</div>
                                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "8px 12px", borderRadius: "8px", color: "#334155", fontStyle: "italic" }}>
                                  &quot;{turn.candidate_answer}&quot;
                                </div>
                              </div>
                              {Array.isArray(turn.criteria) && turn.criteria.length > 0 && (
                                <div>
                                  <div style={{ color: "#6d28d9", fontWeight: 800, marginBottom: "4px" }}>Rubric Criteria Evidence ({turn.prompt_id || "rubric"} {turn.prompt_version || ""})</div>
                                  {turn.criteria.map((c, ci) => (
                                    <div key={ci} style={{ padding: "4px 8px", borderLeft: "2px solid #7c3aed", marginBottom: "4px", color: "#0f172a" }}>
                                      <strong>{c.criterion}</strong>: {Math.round((c.score || 0) * 100)}/100 — &quot;{c.quoted_justification}&quot;
                                    </div>
                                  ))}
                                </div>
                              )}
                              {turn.improved_answer && (
                                <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "10px", padding: "10px 12px", color: "#1e1b4b" }}>
                                  <strong style={{ color: "#5b21b6" }}>Model Answer Guidance:</strong> {turn.improved_answer}
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

              {/* FINAL NARRATIVE SUMMARY */}
              {(reportData.narrative?.text || reportData.report) && (
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "20px", textAlign: "left", color: "#1e293b", lineHeight: "1.7", marginBottom: "20px", fontSize: "13px" }}>
                  {renderMarkdown(reportData.narrative?.text || reportData.report)}
                </div>
              )}

              {/* ROADMAP SKILL LINKS (PROMPT 1 SYNC) */}
              {roadmapLinks.length > 0 && (
                <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "14px", padding: "12px 16px", marginBottom: "20px", textAlign: "left" }}>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", marginBottom: "6px" }}>Updated Prep Roadmap Evidence</div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {roadmapLinks.map((rl, idx) => (
                      <span key={idx} style={{ background: "#ffffff", border: "1px solid #ddd6fe", color: "#4c1d95", fontSize: "11px", fontWeight: 700, padding: "4px 10px", borderRadius: "10px" }}>
                        {rl.skill_id} (Turn linked)
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* EMAIL REPORT ERROR/SUCCESS FEEDBACK */}
              {emailState.error && (
                <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px", padding: "10px 14px", marginBottom: "14px", fontSize: "12px", color: "#dc2626", textAlign: "left" }}>
                  Email delivery failed: {emailState.error}
                </div>
              )}
              {emailState.sent && (
                <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: "10px", padding: "10px 14px", marginBottom: "14px", fontSize: "12px", color: "#059669", textAlign: "left" }}>
                  Report sent successfully via HTTP email provider.
                </div>
              )}

              <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
                <button type="button" onClick={resetSessionToSetup} style={{ padding: "12px 22px", borderRadius: "12px", background: "#f1f5f9", border: "1px solid #cbd5e1", color: "#0f172a", fontWeight: 800, cursor: "pointer" }}>
                  Practice Another
                </button>
                <button type="button" onClick={downloadPDFReport} style={{ padding: "12px 24px", borderRadius: "12px", background: "linear-gradient(135deg,#6d28d9,#7c3aed)", border: "none", color: "#fff", fontWeight: 800, cursor: "pointer", boxShadow: "0 4px 14px rgba(109,40,217,0.28)" }}>
                  📄 Download PDF Report
                </button>
                <button type="button" onClick={sendReportByEmail} disabled={emailState.sending} style={{ padding: "12px 20px", borderRadius: "12px", background: "#ffffff", border: "1px solid #cbd5e1", color: "#0f172a", fontWeight: 700, cursor: "pointer" }}>
                  {emailState.sending ? "Sending Email..." : "✉️ Email Report"}
                </button>
              </div>

              {/* CLICK-TO-INSPECT EVIDENCE DRAWER MODAL */}
              {evidenceDrawer && (
                <div style={{ position: "fixed", inset: 0, background: "rgba(11,14,26,0.65)", backdropFilter: "blur(6px)", display: "flex", justifyContent: "flex-end", zIndex: 1200 }} onClick={() => setEvidenceDrawer(null)}>
                  <div onClick={(e) => e.stopPropagation()} style={{ width: "440px", maxWidth: "94vw", height: "100%", background: "#ffffff", borderLeft: "1px solid #e2e8f0", padding: "26px", overflowY: "auto", textAlign: "left", boxShadow: "-20px 0 50px rgba(15,23,42,0.22)", color: "#0f172a" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px" }}>
                      <div>
                        <div style={{ fontSize: "10.5px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase" }}>Evidence Drawer</div>
                        <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#0f172a", marginTop: "2px" }}>{evidenceDrawer.title}</h3>
                        <div style={{ fontSize: "13px", fontWeight: 800, color: "#334155", marginTop: "2px" }}>{evidenceDrawer.scoreLabel}</div>
                        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>{evidenceDrawer.subtitle}</div>
                      </div>
                      <button type="button" onClick={() => setEvidenceDrawer(null)} style={{ background: "#f1f5f9", border: "1px solid #e2e8f0", color: "#0f172a", borderRadius: "8px", width: "32px", height: "32px", cursor: "pointer", fontWeight: 800 }}>
                        ✕
                      </button>
                    </div>

                    {evidenceDrawer.missingReason && (
                      <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "10px 12px", fontSize: "12px", color: "#475569", marginBottom: "14px" }}>
                        Excluded from overall calculation ({evidenceDrawer.missingReason}).
                      </div>
                    )}

                    <div style={{ background: "#f8fafc", border: "1px solid #e5e8f2", borderRadius: "12px", padding: "12px", marginBottom: "16px" }}>
                      <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", marginBottom: "8px" }}>Formula Inputs &amp; Provenance</div>
                      <div style={{ fontSize: "11.5px", color: "#334155", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                        {Object.entries(evidenceDrawer.formulaInputs || {}).map(([k, v]) => (
                          <div key={k} style={{ background: "#ffffff", border: "1px solid #e2e8f0", padding: "6px 8px", borderRadius: "8px" }}>
                            <div style={{ fontSize: "9.5px", color: "#64748b", textTransform: "uppercase" }}>{k.replace(/_/g, " ")}</div>
                            <div style={{ fontWeight: 700, color: "#0f172a", wordBreak: "break-word" }}>{Array.isArray(v) ? v.join(", ") : String(v ?? "null")}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", marginBottom: "8px" }}>
                      Cited Turn Quotes ({(evidenceDrawer.items || []).length})
                    </div>
                    {(evidenceDrawer.items || []).length > 0 ? evidenceDrawer.items.map((ev, idx) => (
                      <div key={idx} style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "12px", marginBottom: "10px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                          <strong style={{ color: "#0f172a" }}>{ev.criterion}{ev.dimension ? ` · ${ev.dimension}` : ""}</strong>
                          <span style={{ color: "#059669", fontWeight: 800 }}>{Math.round((ev.score || 0) * 100)}/100</span>
                        </div>
                        <div style={{ fontSize: "10.5px", color: "#64748b", marginBottom: "6px" }}>Turn ID: {ev.turn_id}</div>
                        <div style={{ fontSize: "12px", color: "#334155", fontStyle: "italic", borderLeft: "2px solid #7c3aed", paddingLeft: "8px" }}>
                          &quot;{ev.quote}&quot;
                        </div>
                      </div>
                    )) : (
                      <div style={{ fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
                        No evaluated turns contributed to this dimension yet.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })()}

      </div>
    </div>
  );
}
