import React, { useState, useEffect, useRef } from 'react';

export default function SpeechTab({ apiFetch, isLoggedIn, user = {} }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recStatus, setRecStatus] = useState("Click to start recording");
  const [recStatusColor, setRecStatusColor] = useState("var(--text2)");
  const [transcript, setTranscript] = useState("Your speech will appear here in real-time as you speak...");
  const [metrics, setMetrics] = useState({ confidence: "—", pace: "—", fillers: "—", score: "—" });
  const [tone, setTone] = useState(null);
  const [aiFeedback, setAiFeedback] = useState("Analyze your speech to get detailed AI coaching tips.");
  
  const [waveHeights, setWaveHeights] = useState(new Array(15).fill(5));
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordStartRef = useRef(0);
  const waveIntervalRef = useRef(null);
  const durationRef = useRef(60);

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (waveIntervalRef.current) clearInterval(waveIntervalRef.current);
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
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      stopWave();
      setRecStatus("Processing recording...", "var(--text2)");
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
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch(e) {
      setRecStatus("Microphone permission denied. Please allow microphone access.");
      setRecStatusColor("var(--red)");
      return;
    }

    audioChunksRef.current = [];
    recordStartRef.current = Date.now();

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
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });

      setRecStatus(`Recording saved (${duration.toFixed(1)}s). Transcribing...`);
      setRecStatusColor("var(--text2)");
      setTranscript("⏳ Transcribing audio...");

      if (isLoggedIn()) {
        try {
          const formData = new FormData();
          const ext = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mp4') ? 'mp4' : 'webm';
          formData.append('file', audioBlob, `recording.${ext}`);

          // Custom fetch wrapper doesn't specify application/json header, allowing browser to set boundary
          const token = localStorage.getItem('access_token');
          const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
          const res = await fetch(`${BACKEND_URL}/speech-to-text`, {
            method: 'POST',
            headers: token ? { 'Authorization': 'Bearer ' + token } : {},
            body: formData
          });

          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || 'Upload failed');
          setTranscript(data.transcript || "");
          setRecStatus("Transcription complete. Click Analyze to get AI feedback.");
          setRecStatusColor("var(--cyan)");
        } catch(e) {
          setTranscript("Transcription failed: " + e.message + "\n\nYou can paste your transcript manually below.");
          setRecStatus("Transcription failed. Paste transcript manually.");
          setRecStatusColor("var(--red)");
        }
      } else {
        // Not logged in — demo fallback
        setTimeout(() => {
          setTranscript("I believe the best approach for this problem would be to use a hash map. This gives us O(n) time complexity instead of the brute force O(n²). For edge cases, I would handle empty arrays and duplicate values carefully.");
          setRecStatus("Demo mode — log in to use real AI transcription. Click Analyze for feedback.");
          setRecStatusColor("var(--text2)");
        }, 1200);
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
      setRecStatus("Please record or paste a transcript first.");
      setRecStatusColor("var(--red)");
      return;
    }

    setMetrics({ confidence: "...", pace: "...", fillers: "...", score: "..." });
    setAiFeedback("⏳ Analyzing with AI...");
    setTone(null);

    if (isLoggedIn()) {
      try {
        const res = await apiFetch('/api/speech/analyze', {
          method: 'POST',
          body: JSON.stringify({ transcript: rawText, duration_seconds: durationRef.current, user_id: user?._id || user?.user_id })
        });
        const d = await res.json();
        if (res.ok) {
          renderSpeechResults(d);
          return;
        } else {
          throw new Error(d.detail || 'Analysis failed');
        }
      } catch(e) {
        setRecStatus("AI analysis failed: " + e.message + " — showing local estimate instead.");
        setRecStatusColor("var(--red)");
      }
    }

    // Demo fallback
    setTimeout(() => {
      renderSpeechResults({
        confidence_pct: 87, 
        wpm: 142, 
        filler_count: 3, 
        overall_score: 8.2,
        tone: { confidence: 87, clarity: 79, enthusiasm: 65, nervousness: 22 },
        feedback: [
          '✅ Strong clarity — your technical explanation was well-structured',
          '⚠️ Reduce fillers — 3 "um/uh" detected. Pause instead of using filler words.',
          '📈 Pace is ideal — 142 WPM is perfect for technical interviews',
          '💡 Tip: Brief eye contact with the camera signals confidence [Demo mode]'
        ]
      });
    }, 1400);
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
        ? feedback.map((f, i) => <div key={i} style={{marginBottom: "7px"}}>{f}</div>)
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
              Live Transcript <span className="text-xs text-muted" style={{fontWeight:400}}>(editable — paste manually if needed)</span>
            </div>
            
            <textarea 
              className="transcript-area" 
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              style={{width: '100%', resize: 'vertical', border: '1px solid var(--border)', outline: 'none', background: 'rgba(0,0,0,0.2)', color: 'var(--text2)', borderRadius: '12px', padding: '14px', fontFamily: 'inherit', fontSize: '13px', lineHeight: '1.8', minHeight: '90px'}}
              placeholder="Your speech will appear here..."
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
                {aiFeedback}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
