import React, { useState, useEffect, useRef } from 'react';
import { calculateSpeechMetrics } from '../utils/speechEngine';

const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={idx} style={{ height: "6px" }} />;
    
    // Clean up em-dashes and en-dashes
    let cleanLine = line
      .replace(/—/g, "-")
      .replace(/–/g, "-");

    // Headers
    if (cleanLine.startsWith("## ")) {
      const headerText = cleanLine.replace("## ", "").replace(/^[-—–\s]+/, "").trim();
      return <h2 key={idx} style={{ fontSize: "14px", fontWeight: 800, marginTop: "10px", marginBottom: "4px", color: "var(--cyan)" }}>{headerText}</h2>;
    }
    if (cleanLine.startsWith("### ")) {
      const headerText = cleanLine.replace("### ", "").replace(/^[-—–\s]+/, "").trim();
      return <h3 key={idx} style={{ fontSize: "13px", fontWeight: 700, marginTop: "8px", marginBottom: "4px", color: "#fff" }}>{headerText}</h3>;
    }

    // Check if bullet point
    let content = cleanLine;
    let isBullet = false;
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ") || trimmed.startsWith("✅ ") || trimmed.startsWith("📈 ") || trimmed.startsWith("💡 ")) {
      isBullet = true;
      if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
        content = trimmed.substring(2);
      } else {
        content = trimmed; // keep the emoji prefix like ✅, 📈, 💡
      }
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
      parts.push(<strong key={match.index} style={{ color: "var(--cyan)", fontWeight: 700 }}>{match[1]}</strong>);
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    const displayContent = parts.length > 0 ? parts : content;

    if (isBullet) {
      return (
        <div key={idx} style={{ display: "flex", gap: "6px", paddingLeft: "4px", marginBottom: "6px", alignItems: "flex-start" }}>
          {!trimmed.startsWith("✅") && !trimmed.startsWith("📈") && !trimmed.startsWith("💡") && (
            <span style={{ color: "var(--cyan)" }}>•</span>
          )}
          <span style={{ flex: 1 }}>{displayContent}</span>
        </div>
      );
    }

    return <p key={idx} style={{ margin: "0 0 6px 0" }}>{displayContent}</p>;
  });
};

export default function SpeechTab({ apiFetch, isLoggedIn, user = {} }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recStatus, setRecStatus] = useState("Click to start recording");
  const [recStatusColor, setRecStatusColor] = useState("var(--text2)");
  const [transcript, setTranscript] = useState("");
  const [metrics, setMetrics] = useState({ confidence: "—", pace: "—", fillers: "—", score: "—" });
  const [tone, setTone] = useState(null);
  const [aiFeedback, setAiFeedback] = useState("Analyze your speech to get detailed AI coaching tips.");
  
  const [waveHeights, setWaveHeights] = useState(new Array(15).fill(5));
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordStartRef = useRef(0);
  const waveIntervalRef = useRef(null);
  const durationRef = useRef(60);
  const recognitionRef = useRef(null);
  const liveSpokenTextRef = useRef("");

  // Clean up interval and speech recognition on unmount
  useEffect(() => {
    return () => {
      if (waveIntervalRef.current) clearInterval(waveIntervalRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_) {}
      }
    };
  }, []);

  const startWave = () => {
    waveIntervalRef.current = setInterval(() => {
      setWaveHeights(prev => prev.map(() => 5 + Math.floor(Math.random() * 36)));
    }, 90);
  };

  const stopWave = () => {
    if (waveIntervalRef.current) {
      clearInterval(waveIntervalRef.current);
      waveIntervalRef.current = null;
    }
    setWaveHeights(new Array(15).fill(5));
  };

  const toggleRecording = async () => {
    // ── STOP ──
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_) {}
      }
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      stopWave();
      setRecStatus("Processing recording...");
      setRecStatusColor("var(--text2)");
      return;
    }

    // ── START ──
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setRecStatus("Microphone not supported in this browser.");
      setRecStatusColor("var(--red)");
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1, sampleRate: 48000 } });
    } catch(e) {
      setRecStatus("Microphone permission denied. Please allow microphone access.");
      setRecStatusColor("var(--red)");
      return;
    }

    audioChunksRef.current = [];
    liveSpokenTextRef.current = "";
    setTranscript("🎙️ Listening... speak clearly into your microphone");
    recordStartRef.current = Date.now();

    // Start Web Speech API for real-time live transcription of spoken words
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recog = new SpeechRecognition();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = 'en-US';
        recog.onresult = (event) => {
          let currentText = "";
          for (let i = 0; i < event.results.length; i++) {
            currentText += event.results[i][0].transcript + " ";
          }
          const cleanText = currentText.trim();
          if (cleanText) {
            liveSpokenTextRef.current = cleanText;
            setTranscript(cleanText);
          }
        };
        recog.start();
        recognitionRef.current = recog;
      } catch (recErr) {
        console.warn("Live SpeechRecognition notice:", recErr);
      }
    }

    const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
      .find(t => MediaRecorder.isTypeSupported(t)) || '';

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        audioChunksRef.current.push(e.data);
      }
    };

    recorder.onstop = async () => {
      // Stop stream tracks
      stream.getTracks().forEach(track => track.stop());

      const duration = (Date.now() - recordStartRef.current) / 1000;
      durationRef.current = duration;

      if (duration < 1.2) {
        setTranscript("Recording was too short. Please speak clearly into your microphone.");
        setRecStatus("Recording too short. Please try again.");
        setRecStatusColor("var(--red)");
        return;
      }

      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });

      setRecStatus(`Recording saved (${duration.toFixed(1)}s).`);
      setRecStatusColor("var(--cyan)");

      const capturedLiveText = liveSpokenTextRef.current.trim();
      if (capturedLiveText) {
        setTranscript(capturedLiveText);
      }

      if (isLoggedIn()) {
        try {
          const formData = new FormData();
          const ext = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mp4') ? 'mp4' : 'webm';
          formData.append('file', audioBlob, `recording.${ext}`);

          const res = await apiFetch('/speech-to-text', {
            method: 'POST',
            body: formData
          });

          const data = await res.json();
          if (res.ok && data.transcript && data.transcript.trim()) {
            const serverTranscript = data.transcript.trim();
            // Use server transcript if live text was not captured, or keep user's live spoken text
            if (!capturedLiveText || serverTranscript.length > capturedLiveText.length) {
              setTranscript(serverTranscript);
            }
          }
          setRecStatus("Transcription complete. Click Analyze to get AI feedback.");
          setRecStatusColor("var(--cyan)");
        } catch(e) {
          if (capturedLiveText) {
            setTranscript(capturedLiveText);
          }
          setRecStatus("Recording ready. Click Analyze with AI for feedback.");
          setRecStatusColor("var(--cyan)");
        }
      } else {
        if (!capturedLiveText) {
          setTranscript("I believe the best approach for this problem would be to use a hash map for optimal performance.");
        }
        setRecStatus("Demo mode — click Analyze with AI for feedback.");
      }
    };

    recorder.start(250);
    setIsRecording(true);
    setRecStatus("🔴 Recording... speak clearly, then click ⏹ to stop");
    setRecStatusColor("var(--red)");
    startWave();
  };

  const analyzeTranscript = async () => {
    const rawText = transcript.trim();
    const forbidden = ['Your speech will appear', '⏳', 'Transcribing', 'Transcription failed'];
    if (!rawText || forbidden.some(s => rawText.startsWith(s))) {
      setRecStatus("Please record a transcript first.");
      setRecStatusColor("var(--red)");
      return;
    }

    setMetrics({ confidence: "...", pace: "...", fillers: "...", score: "..." });
    setAiFeedback("⏳ Analyzing with AI...");
    setTone(null);

    if (isLoggedIn()) {
      try {
        const resolvedUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id");
        const res = await apiFetch('/api/speech/analyze', {
          method: 'POST',
          body: JSON.stringify({ transcript: rawText, duration_seconds: durationRef.current, user_id: resolvedUserId })
        });
        const d = await res.json();
        if (res.ok) {
          renderSpeechResults(d);
          return;
        } else {
          throw new Error(d.detail || 'Analysis failed');
        }
      } catch(e) {
        setRecStatus("AI analysis notice: " + e.message + " — using deterministic speech engine.");
        setRecStatusColor("var(--text2)");
      }
    }

    // Demo / offline fallback using deterministic frontend speech engine
    setTimeout(() => {
      const localResult = calculateSpeechMetrics(rawText, durationRef.current);
      renderSpeechResults(localResult);
    }, 600);
  };

  const renderSpeechResults = (d) => {
    setMetrics({
      confidence: d.confidence_pct + '%',
      pace: d.wpm,
      fillers: d.filler_count,
      score: d.overall_score
    });
    setTone(d.tone || null);
    
    const feedback = d.feedback || [];
    setAiFeedback(
      feedback.length > 0 
        ? feedback.join("\n")
        : "No feedback available."
    );
    setRecStatus("Analysis complete!");
    setRecStatusColor("var(--cyan)");
  };

  const toneColors = { 
    confidence: 'var(--cyan)', 
    clarity: 'var(--blue)', 
    enthusiasm: 'var(--orange)', 
    nervousness: 'var(--red)' 
  };

  return (
    <div id="page-speech" className="page active" role="tabpanel">
      <div className="container">
        <div className="sec-header mb16">
          <div className="flex items-center gap8">
            <h1 className="sec-title" style={{fontSize:"18px"}}>Speech AI</h1>
            <span className="pill pill-cyan">Real-time STT</span>
            <span className="pill pill-purple">AI Scoring</span>
          </div>
        </div>
        <div className="g2">
          <div className="card">
            <div className="flex items-center mb16" style={{justifyContent:"space-between"}}>
              <div>
                <div style={{fontSize:"14px",fontWeight:800,marginBottom:"2px"}}>Voice Recorder</div>
                <div className="text-xs text-muted">Powered by AI speech analysis</div>
              </div>
              <button 
                id="rec-btn" 
                className={`record-btn ${isRecording ? 'record-active' : 'record-idle'}`} 
                onClick={toggleRecording} 
                aria-label={isRecording ? 'Stop recording' : 'Start recording'}
              >
                {isRecording ? '⏹' : '🎤'}
              </button>
            </div>
            <div className="waveform mb12" id="waveform" aria-hidden="true">
              {waveHeights.map((h, i) => (
                <div key={i} className="wbar" id={`w${i}`} style={{height: `${h}px`}}></div>
              ))}
            </div>
            <div id="rec-status" className="text-xs mb12" style={{textAlign:"center", color: recStatusColor}} aria-live="polite">
              {recStatus}
            </div>
            <div className="sec-sub fw7 mb8">
              Live Transcript
            </div>
            
            <textarea 
              className="transcript-area" 
              value={transcript}
              readOnly={true}
              style={{width: '100%', resize: 'vertical', border: '1px solid var(--border)', outline: 'none', background: 'rgba(255,255,255,0.02)', color: 'var(--text2)', borderRadius: '12px', padding: '14px', fontFamily: 'inherit', fontSize: '13px', lineHeight: '1.8', minHeight: '90px', cursor: 'default'}}
              placeholder={isRecording ? "Listening and transcribing your speech..." : "Your speech will appear here."}
            />
            
            <button className="btn btn-primary" style={{width:"100%",justifyContent:"center",marginTop:"14px"}} onClick={analyzeTranscript}>
              🔍 Analyze with AI
            </button>
          </div>
          
          <div className="flex-col gap12">
            <div className="card">
              <div style={{fontSize:"14px",fontWeight:800,marginBottom:"14px"}}>Speech Metrics</div>
              <div className="flex gap10 mb12">
                <div className="metric-chip"><div className="mc-val" id="metric-confidence" style={{color:"var(--cyan)"}}>{metrics.confidence}</div><div className="mc-lbl">Confidence</div></div>
                <div className="metric-chip"><div className="mc-val" id="metric-pace" style={{color:"var(--blue)"}}>{metrics.pace}</div><div className="mc-lbl">WPM</div></div>
                <div className="metric-chip"><div className="mc-val" id="metric-fillers" style={{color:"var(--orange)"}}>{metrics.fillers}</div><div className="mc-lbl">Fillers</div></div>
                <div className="metric-chip"><div className="mc-val" id="metric-score" style={{color:"var(--gold)"}}>{metrics.score}</div><div className="mc-lbl">Score</div></div>
              </div>
            </div>
            <div className="card">
              <div style={{fontSize:"14px",fontWeight:800,marginBottom:"12px"}}>Tone Analysis</div>
              <div id="tone-bars">
                {tone ? (
                  Object.keys(tone).map(k => {
                    const pct = tone[k];
                    const col = toneColors[k] || 'var(--purple)';
                    return (
                      <div key={k} className="tone-bar-row">
                        <div className="tone-lbl-row">
                          <span className="text-xs text-muted">{k.charAt(0).toUpperCase() + k.slice(1)}</span>
                          <span className="text-xs fw7" style={{color: col}}>{pct}%</span>
                        </div>
                        <div className="tone-bg">
                          <div className="tone-fg" style={{width: `${pct}%`, background: col}}></div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-sm text-muted">Run analysis to see tone breakdown</div>
                )}
              </div>
            </div>
            <div className="card" style={{flex:1}}>
              <div style={{fontSize:"14px",fontWeight:800,marginBottom:"10px"}}>AI Feedback</div>
              <div id="speech-feedback" className="text-sm" style={{color:"#b0c0d8",lineHeight:"1.7"}}>
                {renderMarkdown(aiFeedback)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
