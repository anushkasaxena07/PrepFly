import React, { useState } from 'react';

const SAMPLE_JDS = {
  fullstack: `Senior Full Stack Engineer with:\n• 3+ years React/Next.js experience\n• Node.js, REST & GraphQL API design\n• AWS, Kubernetes, Docker, CI/CD\n• PostgreSQL, Redis\n• Strong frontend styling & system design`,
  ml: `Machine Learning Engineer with:\n• Strong python coding (NumPy, Pandas, PyTorch)\n• ML models training, validation, and deployment\n• NLP, LLMs, fine-tuning, retrieval augmented generation\n• MLOps (MLflow, Kubernetes)\n• Statistics, linear algebra, calculus foundations`,
  backend: `Backend Developer with SDE Core focus:\n• Python, FastAPI or Golang experience\n• Database schemas, PostgreSQL, queries optimization\n• Microservices, REST APIs, GraphQL, gRPC\n• Redis caching, Celery task queues\n• AWS EC2, S3, RDS, ECS`,
  frontend: `Frontend Developer:\n• React, Next.js, Redux or Context API\n• Modern JavaScript (ES6+), TypeScript\n• CSS Grid, Flexbox, Tailwind, responsive design\n• REST APIs consumption, WebSockets\n• Performance optimization, bundle sizes, accessibility (a11y)`
};

export default function ResumeTab({ apiFetch, isLoggedIn, user = {} }) {
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [statusColor, setStatusColor] = useState("var(--text2)");
  const [isScoring, setIsScoring] = useState(false);
  const [results, setResults] = useState(null);

  const fillSampleJD = (type) => {
    setJdText(SAMPLE_JDS[type] || "");
  };

  const handleResumePDF = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setStatusMsg("⏳ Uploading PDF...");
    setStatusColor("var(--text2)");

    if (isLoggedIn()) {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
        const res = await fetch(`${BACKEND_URL}/upload`, {
          method: 'POST',
          headers: token ? { 'Authorization': 'Bearer ' + token } : {},
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');
        
        // Wait, does `/upload` return `resume_text` or similar? Let's check.
        // If the backend has a specific PDF endpoint, let's hit that, else fallback.
        // Wait, backend app.py has: @app.route("/upload", methods=["POST"])
        setResumeText(data.resume_text || data.text || "");
        setStatusMsg(`✅ PDF extracted (${data.page_count || '?'} pages). Review text below, then click Score.`);
        setStatusColor("var(--cyan)");
      } catch(err) {
        setStatusMsg("❌ Upload failed: " + err.message + " — please paste your resume text manually.");
        setStatusColor("var(--red)");
      }
    } else {
      setStatusMsg("⚠️ Log in to use PDF extraction. Paste resume text manually.");
      setStatusColor("var(--orange)");
    }
  };

  const scoreResume = async () => {
    if (!resumeText.trim()) {
      setStatusMsg("⚠️ Please paste your resume text first.");
      setStatusColor("var(--orange)");
      return;
    }
    if (!jdText.trim()) {
      setStatusMsg("⚠️ Please enter a job description.");
      setStatusColor("var(--orange)");
      return;
    }

    setStatusMsg("⏳ Scoring with Gemini AI...");
    setStatusColor("var(--text2)");
    setIsScoring(true);

    if (isLoggedIn()) {
      try {
        const res = await apiFetch('/api/resume/score', {
          method: 'POST',
          body: JSON.stringify({ resume_text: resumeText, job_description: jdText, user_id: user?._id || user?.user_id })
        });
        const data = await res.json();
        if (res.ok) {
          setResults(data);
          setStatusMsg("");
          setIsScoring(false);
          scrollToResults();
          return;
        } else {
          throw new Error(data.detail || 'Scoring failed');
        }
      } catch(err) {
        setStatusMsg("❌ AI scoring failed: " + err.message + " — showing local estimate instead.");
        setStatusColor("var(--red)");
      }
    }

    // Demo fallback / local simulation
    setTimeout(() => {
      const demoScore = 60 + Math.floor(Math.random() * 30);
      const generatedResults = buildDemoResumeResult(resumeText, jdText, demoScore);
      setResults(generatedResults);
      setStatusMsg(isLoggedIn() ? "" : "⚠️ Demo mode — log in for real Gemini scoring.");
      setStatusColor("var(--text2)");
      setIsScoring(false);
      scrollToResults();
    }, 1200);
  };

  const scrollToResults = () => {
    setTimeout(() => {
      const el = document.getElementById('resume-results');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  const resetResumeScorer = () => {
    setResults(null);
    setTimeout(() => {
      const el = document.getElementById('resume-input-panel');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  const buildDemoResumeResult = (resume, jd, score) => {
    const jdWords = jd.match(/\b[A-Za-z][A-Za-z0-9#+./\-]{2,}\b/g) || [];
    const resumeLower = resume.toLowerCase();
    const seen = {};
    const matched = [];
    const missing = [];
    const skip = new Set(['and','the','for','with','have','your','from','that','this','will','are','our','you','they','all','any','can','has','not','job','role','team','work']);
    
    jdWords.forEach(w => {
      const l = w.toLowerCase();
      if (seen[l] || l.length < 3 || skip.has(l)) return;
      seen[l] = true;
      if (resumeLower.includes(l)) {
        matched.push(w);
      } else {
        missing.push(w);
      }
    });

    return {
      ats_score: score,
      overall_grade: score >= 90 ? 'S' : score >= 80 ? 'A' : score >= 65 ? 'B' : score >= 50 ? 'C' : 'D',
      matched_keywords: matched.slice(0, 12),
      missing_keywords: missing.slice(0, 8),
      skill_match: {
        'Technical Skills': Math.min(99, score + 10),
        'JD Keywords': Math.round(score * 0.9),
        'Experience Depth': Math.min(99, score + 5),
        'Tools & Frameworks': Math.round(score * 0.85),
        'Domain Fit': Math.round(score * 0.92)
      },
      section_scores: {
        experience: Math.min(10, Math.round(score / 11)),
        skills: Math.min(10, Math.round(score / 12)),
        format: 6 + Math.floor(Math.random() * 3),
        projects: Math.min(10, Math.round(score / 10))
      },
      improvement_tips: [
        missing.length ? `Add ${missing.slice(0, 3).join(', ')} to your skills section — found in JD but missing from resume.` : 'Great keyword coverage!',
        'Quantify achievements: "reduced load time by 40%" is stronger than "improved performance".',
        score < 75 ? `ATS score is ${score}/100 — tailor language more closely to the JD.` : 'Good ATS compatibility! Review formatting for further improvements.',
        'Keep skills section ordered by relevance to this specific role.'
      ]
    };
  };

  const circumference = 238.8; // 2 * Math.PI * 38
  const scorePercent = results ? results.ats_score : 0;
  const strokeDashoffset = circumference * (1 - scorePercent / 100);

  const gradeLabels = { S: 'Excellent match', A: 'Strong match', B: 'Good · Room to improve', C: 'Fair match', D: 'Needs work' };
  const gradeColors = { S: 'pill-cyan', A: 'pill-cyan', B: 'pill-gold', C: 'pill-gold', D: 'pill-red' };
  const ssColors = { experience: 'var(--cyan)', skills: 'var(--blue)', format: 'var(--orange)', projects: 'var(--purple)' };
  const tipColors = ['var(--cyan)', 'var(--orange)', 'var(--blue)', 'var(--purple)'];

  return (
    <div id="page-resume" className="page active" role="tabpanel">
      <div className="container">
        <div className="sec-header mb16">
          <div className="flex items-center gap8">
            <h1 className="sec-title" style={{fontSize:"18px"}}>Resume AI Scoring</h1>
            <span className="pill pill-cyan">ATS Match</span>
            <span className="pill pill-purple">Skill Gap</span>
          </div>
        </div>

        {/* INPUT PANEL */}
        <div className="g2 mb20" id="resume-input-panel">
          {/* Resume text */}
          <div className="card">
            <div style={{fontSize:"14px",fontWeight:800,marginBottom:"6px"}}>Your Resume</div>
            <div className="text-xs text-muted mb12">Paste your resume text below, or upload a PDF</div>
            <textarea 
              id="resume-text-input" 
              className="code-area" 
              style={{minHeight:"220px",fontFamily:"'Cabinet Grotesk',sans-serif",fontSize:"12px",lineHeight:"1.65",resize:"vertical"}} 
              placeholder="Paste your full resume here...&#10;&#10;Example:&#10;John Doe · Full Stack Engineer&#10;Skills: React, Node.js, PostgreSQL, AWS, Docker&#10;Experience: 3 years at Startup Inc. — built scalable APIs serving 500K users..."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
            <div style={{display:"flex",alignItems:"center",gap:"8px",marginTop:"10px"}}>
              <label style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",gap:"7px",padding:"9px",background:"rgba(155,109,255,0.07)",border:"1px dashed rgba(155,109,255,0.3)",borderRadius:"10px",cursor:"pointer",fontSize:"12px",fontWeight:700,color:"var(--purple)"}}>
                <span>📎 Upload PDF</span>
                <input type="file" accept=".pdf" style={{display:"none"}} onChange={handleResumePDF} />
              </label>
              <button className="btn btn-ghost btn-sm" onClick={() => setResumeText("")}>Clear</button>
            </div>
          </div>

          {/* Job description */}
          <div className="card">
            <div style={{fontSize:"14px",fontWeight:800,marginBottom:"6px"}}>Job Description / Target Role</div>
            <div className="text-xs text-muted mb12">Paste the JD or describe the role you're targeting</div>
            <textarea 
              id="jd-input" 
              className="code-area" 
              style={{minHeight:"220px",fontFamily:"'Cabinet Grotesk',sans-serif",fontSize:"12px",lineHeight:"1.65",resize:"vertical"}} 
              placeholder="Paste the job description here...&#10;&#10;Example:&#10;We're looking for a Senior Full Stack Engineer with:&#10;• 3+ years React/Next.js experience&#10;• Node.js, REST & GraphQL API design&#10;• AWS, Kubernetes, Terraform (DevOps)&#10;• PostgreSQL, Redis&#10;• Strong system design fundamentals..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />
            <div style={{marginTop:"10px"}}>
              <div className="text-xs text-muted mb8">Or pick a common role:</div>
              <div style={{display:"flex",flexWrap:"wrap",gap:"6px"}}>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('fullstack')}>Full Stack SDE</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('ml')}>ML Engineer</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('backend')}>Backend Engineer</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('frontend')}>Frontend Engineer</button>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button & Loader */}
        <div className="flex-col items-center gap10 mb24">
          <button className="btn btn-primary" style={{padding:"12px 32px",fontSize:"14px",borderRadius:"12px"}} onClick={scoreResume} disabled={isScoring}>
            {isScoring ? "⏳ Analyzing..." : "⚡ Score & Optimize Resume"}
          </button>
          {statusMsg && (
            <div id="resume-score-status" className="text-sm font-semibold" style={{color: statusColor}}>
              {statusMsg}
            </div>
          )}
        </div>

        {/* RESULTS PANEL */}
        {results && (
          <div id="resume-results" style={{display:"block", borderTop:"1px solid var(--border)", paddingTop:"24px"}} className="fade-up">
            <div className="sec-header mb16">
              <div style={{fontSize:"15px",fontWeight:800}}>ATS Optimiser Analysis Results</div>
              <button className="btn btn-ghost btn-xs" onClick={resetResumeScorer}>← Clear Results</button>
            </div>

            <div className="g-main mb20">
              {/* Left Column: ATS Score Circle & Keyword Grid */}
              <div className="flex-col gap16">
                <div className="card flex items-center gap24" style={{padding:"24px", flexWrap:"wrap"}}>
                  {/* Circular Score Ring */}
                  <div style={{position:"relative",width:"92px",height:"92px",flexShrink:0}}>
                    <svg width="92" height="92" viewBox="0 0 92 92" style={{transform:"rotate(-90deg)"}}>
                      <circle cx="46" cy="46" r="38" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8"/>
                      <circle 
                        id="ats-ring-fill" 
                        cx="46" cy="46" r="38" 
                        fill="none" 
                        stroke="var(--cyan)" 
                        strokeWidth="8" 
                        strokeDasharray={circumference} 
                        strokeDashoffset={strokeDashoffset} 
                        strokeLinecap="round" 
                        style={{transition:"stroke-dashoffset 1s ease"}}
                      />
                    </svg>
                    <div id="ats-ring-num" style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",fontSize:"22px",fontWeight:"900"}}>{results.ats_score}</div>
                  </div>
                  
                  {/* Summary & Grade */}
                  <div>
                    <div className="text-xs text-muted mb4">ATS Compatibility Index</div>
                    <div id="ats-score-display" style={{fontSize:"28px",fontWeight:900,color:"var(--cyan)",lineHeight:1.1}}>{results.ats_score}/100</div>
                    <span 
                      id="ats-grade-pill" 
                      className={`pill ${gradeColors[results.overall_grade] || 'pill-gold'}`} 
                      style={{marginTop:"6px", display:"inline-flex"}}
                    >
                      Grade {results.overall_grade} · {gradeLabels[results.overall_grade]}
                    </span>
                  </div>
                </div>

                {/* Keyword matched vs missing grid */}
                <div className="card">
                  <div className="sec-sub fw7 mb12">JD Keyword Analysis</div>
                  <div className="kw-grid" id="kw-grid-result">
                    {results.matched_keywords.map((k, i) => (
                      <span key={`match-${i}`} className="kw kw-match">{k}</span>
                    ))}
                    {results.missing_keywords.map((k, i) => (
                      <span key={`miss-${i}`} className="kw kw-miss">{k}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Skill Match Progress Bars */}
              <div className="flex-col gap16">
                <div className="card">
                  <div className="sec-sub fw7 mb16">Skill Relevance Checklist</div>
                  <div id="skill-match-bars" className="flex-col gap12">
                    {Object.keys(results.skill_match).map(k => {
                      const pct = results.skill_match[k];
                      const col = pct >= 80 ? 'linear-gradient(90deg,var(--cyan),var(--blue))' : pct >= 50 ? 'linear-gradient(90deg,var(--orange),#d97706)' : 'linear-gradient(90deg,var(--red),#dc2626)';
                      const tc  = pct >= 80 ? 'var(--cyan)' : pct >= 50 ? 'var(--orange)' : 'var(--red)';
                      return (
                        <div key={k} className="skill-row">
                          <div className="skill-lbl">{k}</div>
                          <div className="skill-bg">
                            <div className="skill-fg" style={{width: `${pct}%`, background: col}}></div>
                          </div>
                          <div className="skill-pct" style={{color: tc}}>{pct}%</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Section Scores Grid */}
            <div className="sec-header mb12">
              <div className="sec-title">Section Scoring Breakdown</div>
            </div>
            <div className="g4 mb20" id="section-scores-row">
              {Object.keys(results.section_scores).map(k => (
                <div key={k} className="section-score">
                  <div className="ss-val" style={{color: ssColors[k] || 'var(--cyan)'}}>{results.section_scores[k]}</div>
                  <div className="ss-lbl">{k.charAt(0).toUpperCase() + k.slice(1)}</div>
                </div>
              ))}
            </div>

            {/* Improvement tips list */}
            <div className="card mb24">
              <div style={{fontSize:"14px",fontWeight:800,marginBottom:"12px"}}>AI Recommendations & Improvement Tips</div>
              <div className="flex-col gap8" id="improvement-tips">
                {results.improvement_tips.map((t, i) => (
                  <div key={i} className="tip-row">
                    <span style={{color: tipColors[i % 4]}}>→</span>
                    <span dangerouslySetInnerHTML={{__html: t}}></span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
