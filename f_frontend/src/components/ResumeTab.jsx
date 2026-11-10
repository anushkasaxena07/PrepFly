import React, { useState } from 'react';
import { calculateATSMatch } from '../utils/atsEngine';

const SAMPLE_JDS = {
  fullstack: `Senior Full Stack Engineer with:\n• 3+ years React/Next.js experience\n• Node.js, REST & GraphQL API design\n• AWS, Kubernetes, Docker, CI/CD\n• PostgreSQL, Redis\n• Strong frontend styling & system design`,
  ml: `Machine Learning Engineer with:\n• Strong python coding (NumPy, Pandas, PyTorch)\n• ML models training, validation, and deployment\n• NLP, LLMs, fine-tuning, retrieval augmented generation\n• MLOps (MLflow, Kubernetes)\n• Statistics, linear algebra, calculus foundations`,
  backend: `Backend Developer with SDE Core focus:\n• Python, FastAPI or Golang experience\n• Database schemas, PostgreSQL, queries optimization\n• Microservices, REST APIs, GraphQL, gRPC\n• Redis caching, Celery task queues\n• AWS EC2, S3, RDS, ECS`,
  frontend: `Frontend Developer:\n• React, Next.js, Redux or Context API\n• Modern JavaScript (ES6+), TypeScript\n• CSS Grid, Flexbox, Tailwind, responsive design\n• REST APIs consumption, WebSockets\n• Performance optimization, bundle sizes, accessibility (a11y)`
};

export default function ResumeTab({ apiFetch, isLoggedIn, user = {} }) {
  const [activeMode, setActiveMode] = useState("score"); // "score" | "improve"
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [statusColor, setStatusColor] = useState("var(--text2)");
  const [isScoring, setIsScoring] = useState(false);
  const [isImproving, setIsImproving] = useState(false);
  const [results, setResults] = useState(null);
  const [improveResults, setImproveResults] = useState(null);
  const [copied, setCopied] = useState(false);
  const [lastUploadedFile, setLastUploadedFile] = useState(null);
  const [uploadRetryable, setUploadRetryable] = useState(false);

  const fillSampleJD = (type) => {
    setJdText(SAMPLE_JDS[type] || "");
    if (type === "fullstack") setTargetRole("Senior Full Stack Engineer");
    else if (type === "ml") setTargetRole("Machine Learning Engineer");
    else if (type === "backend") setTargetRole("Senior Backend Developer");
    else if (type === "frontend") setTargetRole("Senior Frontend Developer");
  };

  const extractResumeFile = async (file) => {
    if (!file) return;
    const ext = (file.name || "").split(".").pop()?.toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      setStatusMsg("⚠️ Only PDF and DOCX resume files are supported.");
      setStatusColor("var(--orange)");
      setUploadRetryable(false);
      return;
    }
    if (file.size === 0) {
      setStatusMsg("⚠️ Uploaded file appears empty. Please select a valid resume.");
      setStatusColor("var(--orange)");
      setUploadRetryable(false);
      return;
    }
    setLastUploadedFile(file);
    setUploadRetryable(false);
    setStatusMsg("⏳ Uploading and extracting resume text...");
    setStatusColor("var(--text2)");

    try {
      const formData = new FormData();
      formData.append('resume', file);
      formData.append('consent', 'true');

      const token = localStorage.getItem('access_token');
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
      const res = typeof apiFetch === "function"
        ? await apiFetch('/api/resume/extract', { method: 'POST', body: formData })
        : await fetch(`${BACKEND_URL}/api/resume/extract`, {
            method: 'POST',
            headers: token ? { 'Authorization': 'Bearer ' + token } : {},
            body: formData
          });
      const rawText = await res.text();
      let data = {};
      try {
        data = rawText ? JSON.parse(rawText) : {};
      } catch {
        data = { error: `Server returned unexpected HTTP ${res.status}` };
      }
      if (!res.ok) throw new Error(data.message || data.detail || data.error || `Extraction failed (${res.status})`);
      
      setResumeText(data.resume_text || data.text || "");
      const pagesText = data.page_count ? ` (${data.page_count} pages)` : "";
      setStatusMsg(`✅ Resume text extracted${pagesText}. Review below and choose Score or Improve.`);
      setStatusColor("var(--cyan)");
    } catch(err) {
      setUploadRetryable(true);
      setStatusMsg("❌ Upload notice: " + err.message + " — you can retry or paste resume text directly.");
      setStatusColor("var(--orange)");
    }
  };

  const handleResumePDF = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    await extractResumeFile(file);
  };

  const scoreResume = async () => {
    if (!resumeText.trim()) {
      setStatusMsg("⚠️ Please enter or upload your resume text first.");
      setStatusColor("var(--orange)");
      return;
    }
    if (!jdText.trim()) {
      setStatusMsg("⚠️ Please enter a job description or select a target role.");
      setStatusColor("var(--orange)");
      return;
    }

    setStatusMsg("⏳ Analyzing ATS keywords and rubric scores...");
    setStatusColor("var(--text2)");
    setIsScoring(true);

    try {
      const resolvedUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id");
      const res = await apiFetch('/api/resume/score', {
        method: 'POST',
        body: JSON.stringify({ resume_text: resumeText, job_description: jdText, user_id: resolvedUserId, consent: true })
      });
      const data = await res.json();
      if (res.ok) {
        setResults(data);
        setStatusMsg("");
        setIsScoring(false);
        scrollToResults('resume-results');
        return;
      } else {
        throw new Error(data.detail || data.error || 'Scoring failed');
      }
    } catch(err) {
      console.warn("API score notice:", err);
    }

    // Deterministic fallback
    const engineResult = calculateATSMatch(resumeText, jdText);
    setTimeout(() => {
      setResults(engineResult);
      setStatusMsg('');
      setIsScoring(false);
      scrollToResults('resume-results');
    }, 600);
  };

  const improveResumeWithAI = async () => {
    if (!resumeText.trim()) {
      setStatusMsg("⚠️ Please paste or upload your resume text first.");
      setStatusColor("var(--orange)");
      return;
    }

    setStatusMsg("✨ AI is analyzing your resume against target requirements and rewriting high-impact bullet points...");
    setStatusColor("var(--purple)");
    setIsImproving(true);

    try {
      const res = await apiFetch('/api/resume/improve', {
        method: 'POST',
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jdText,
          target_role: targetRole || "Software Engineer",
          consent: true
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Resume improvement failed");

      setImproveResults(data);
      setStatusMsg("");
      setIsImproving(false);
      scrollToResults('resume-improve-results');
    } catch (err) {
      setStatusMsg("❌ AI Improvement notice: " + err.message);
      setStatusColor("var(--red)");
      setIsImproving(false);
    }
  };

  const copyToClipboard = () => {
    if (!improveResults?.full_improved_resume) return;
    navigator.clipboard.writeText(improveResults.full_improved_resume);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const downloadImprovedResume = () => {
    if (!improveResults?.full_improved_resume) return;
    const blob = new Blob([improveResults.full_improved_resume], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Enhanced_Resume_${(targetRole || 'Software_Engineer').replace(/\s+/g, '_')}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const scrollToResults = (id) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 120);
  };

  const circumference = 238.8;
  const scorePercent = results ? results.ats_score : 0;
  const strokeDashoffset = circumference * (1 - scorePercent / 100);

  const gradeLabels = { S: 'Excellent match', A: 'Strong match', B: 'Good · Room to improve', C: 'Fair match', D: 'Needs work' };
  const gradeColors = { S: 'pill-cyan', A: 'pill-cyan', B: 'pill-gold', C: 'pill-gold', D: 'pill-red' };
  const ssColors = { experience: 'var(--cyan)', skills: 'var(--blue)', format: 'var(--orange)', projects: 'var(--purple)' };
  const tipColors = ['var(--cyan)', 'var(--orange)', 'var(--blue)', 'var(--purple)'];

  return (
    <div id="page-resume" className="page active" role="tabpanel">
      <div className="container" style={{ maxWidth: "1080px", margin: "0 auto", padding: "20px 0" }}>
        
        {/* Header */}
        <div className="sec-header mb16" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: "4px" }}>PREPFLY ADVANCED RESUME SUITE</div>
            <h1 className="sec-title" style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", margin: 0 }}>Resume AI Platform</h1>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <span className="pill pill-cyan">ATS Optimizer</span>
            <span className="pill pill-purple">AI Bullet Rewriter</span>
          </div>
        </div>

        {/* ── RESUME AI MODE SELECTOR ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", background: "#eaedf6", padding: "6px", borderRadius: "16px", border: "1px solid #d5dbe9", marginBottom: "24px" }}>
          <button
            type="button"
            onClick={() => setActiveMode("score")}
            style={{
              padding: "12px 18px",
              borderRadius: "12px",
              border: activeMode === "score" ? "1px solid #6d28d9" : "1px solid transparent",
              background: activeMode === "score" ? "#ffffff" : "transparent",
              color: activeMode === "score" ? "#6d28d9" : "#475569",
              fontWeight: 800,
              fontSize: "13px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: activeMode === "score" ? "0 2px 8px rgba(109,40,217,0.12)" : "none",
              transition: "all 0.2s"
            }}
          >
            <span>Option 1: ATS Resume Score &amp; Keyword Match</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveMode("improve")}
            style={{
              padding: "12px 18px",
              borderRadius: "12px",
              border: activeMode === "improve" ? "1px solid #6d28d9" : "1px solid transparent",
              background: activeMode === "improve" ? "#ffffff" : "transparent",
              color: activeMode === "improve" ? "#6d28d9" : "#475569",
              fontWeight: 800,
              fontSize: "13px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: activeMode === "improve" ? "0 2px 8px rgba(109,40,217,0.12)" : "none",
              transition: "all 0.2s"
            }}
          >
            <span>Option 2: AI Resume Improvement &amp; Rewrite</span>
          </button>
        </div>

        {/* INPUT PANEL */}
        <div className="g2 mb20" id="resume-input-panel">
          {/* Resume text */}
          <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "20px", padding: "24px" }}>
            <div style={{ fontSize: "15px", fontWeight: 800, marginBottom: "4px", color: "#0f172a" }}>Your Current Resume</div>
            <div className="text-xs text-muted mb12">Paste your resume content below or upload your PDF file</div>
            <textarea 
              id="resume-text-input" 
              className="form-input" 
              style={{ minHeight: "240px", fontSize: "12.5px", lineHeight: "1.65", resize: "vertical", width: "100%", background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #cbd5e1", color: "#0f172a" }} 
              placeholder="Paste your full resume here...&#10;&#10;Example:&#10;John Doe · Full Stack Engineer&#10;Skills: React, Node.js, PostgreSQL, AWS, Docker&#10;Experience: 3 years at Tech Inc. — built backend APIs and user interfaces..."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px" }}>
              <label style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "7px", padding: "10px", background: "#f5f3ff", border: "1px dashed #c4b5fd", borderRadius: "10px", cursor: "pointer", fontSize: "12px", fontWeight: 700, color: "#6d28d9" }}>
                <span>Upload Resume PDF / DOCX</span>
                <input type="file" accept=".pdf,.docx" style={{ display: "none" }} onChange={handleResumePDF} />
              </label>
              <button className="btn btn-ghost btn-sm" onClick={() => setResumeText("")} style={{ borderRadius: "10px" }}>Clear</button>
            </div>
          </div>

          {/* Job description / Target Role */}
          <div className="card" style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "20px", padding: "24px" }}>
            <div style={{ fontSize: "15px", fontWeight: 800, marginBottom: "4px", color: "#0f172a" }}>Target Job Description &amp; Role</div>
            <div className="text-xs text-muted mb12">Target role title and requirements to tailor the analysis or AI rewrite</div>

            {activeMode === "improve" && (
              <div style={{ marginBottom: "12px" }}>
                <input
                  type="text"
                  placeholder="Target Role (e.g. Senior Full Stack Engineer, ML Engineer)"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f172a", fontSize: "12px" }}
                />
              </div>
            )}

            <textarea 
              id="jd-input" 
              className="form-input" 
              style={{ minHeight: activeMode === "improve" ? "190px" : "240px", fontSize: "12.5px", lineHeight: "1.65", resize: "vertical", width: "100%", background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #cbd5e1", color: "#0f172a" }} 
              placeholder="Paste the target job description here...&#10;&#10;Example:&#10;We're looking for a Senior Full Stack Engineer with:&#10;• 3+ years React/Next.js experience&#10;• Node.js, REST & GraphQL API design&#10;• AWS, Kubernetes, CI/CD automation&#10;• PostgreSQL query optimization, Redis..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />
            <div style={{ marginTop: "12px" }}>
              <div className="text-xs text-muted mb8">Or pre-fill with a common role:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('fullstack')}>Full Stack SDE</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('ml')}>ML Engineer</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('backend')}>Backend SDE</button>
                <button className="btn btn-ghost btn-xs" onClick={() => fillSampleJD('frontend')}>Frontend SDE</button>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button & Status Bar */}
        <div className="flex-col items-center gap10 mb28" style={{ textAlign: "center" }}>
          {activeMode === "score" ? (
            <button 
              className="btn btn-primary" 
              style={{ padding: "14px 36px", fontSize: "14px", borderRadius: "14px", background: "linear-gradient(135deg, #6d28d9, #7c3aed)", fontWeight: 800, cursor: isScoring ? "wait" : "pointer" }} 
              onClick={scoreResume} 
              disabled={isScoring}
            >
              {isScoring ? "Analyzing ATS Match..." : "Score & Analyze ATS Match"}
            </button>
          ) : (
            <button 
              className="btn btn-primary" 
              style={{ padding: "14px 40px", fontSize: "14px", borderRadius: "14px", background: "linear-gradient(135deg, #6d28d9, #7c3aed)", color: "#fff", fontWeight: 800, cursor: isImproving ? "wait" : "pointer" }} 
              onClick={improveResumeWithAI} 
              disabled={isImproving}
            >
              {isImproving ? "AI is Rewriting Your Resume..." : "Improve & Rewrite Resume with AI"}
            </button>
          )}

          {statusMsg && (
            <div id="resume-score-status" className="text-sm font-semibold" style={{ color: statusColor, marginTop: "8px" }}>
              {statusMsg}
              {uploadRetryable && lastUploadedFile && (
                <button
                  type="button"
                  onClick={() => extractResumeFile(lastUploadedFile)}
                  style={{ marginLeft: "10px", padding: "4px 12px", borderRadius: "8px", background: "#6d28d9", color: "#fff", border: "none", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}
                >
                  Retry Upload
                </button>
              )}
            </div>
          )}
        </div>

        {/* ── OPTION 2 RESULTS: AI RESUME IMPROVEMENT & REWRITE PANEL ── */}
        {improveResults && activeMode === "improve" && (
          <div id="resume-improve-results" style={{ display: "block", borderTop: "1px solid #e5e8f2", paddingTop: "32px", marginBottom: "40px" }} className="fade-up">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div>
                <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", letterSpacing: "1px" }}>AI RESUME TRANSFORMATION REPORT</div>
                <h3 style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", margin: "2px 0 0" }}>Enhanced Resume for {improveResults.target_role || "Target Role"}</h3>
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button 
                  type="button" 
                  onClick={copyToClipboard} 
                  style={{ background: copied ? "#059669" : "#ffffff", border: "1px solid #cbd5e1", color: copied ? "#ffffff" : "#0f172a", padding: "8px 18px", borderRadius: "10px", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}
                >
                  {copied ? "✓ Copied!" : "Copy Markdown"}
                </button>
                <button 
                  type="button" 
                  onClick={downloadImprovedResume} 
                  style={{ background: "linear-gradient(135deg, #6d28d9, #7c3aed)", border: "none", color: "#fff", padding: "8px 20px", borderRadius: "10px", fontSize: "12px", fontWeight: 800, cursor: "pointer" }}
                >
                  Download Resume (.md)
                </button>
              </div>
            </div>

            {/* ATS Score Projection Card */}
            <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "20px", padding: "24px", marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#64748b", textTransform: "uppercase" }}>PROJECTED ATS COMPATIBILITY BOOST</div>
                <div style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
                  <span style={{ color: "#dc2626", textDecoration: "line-through", marginRight: "10px" }}>{improveResults.original_ats_score}/100</span>
                  ➔ <span style={{ color: "#059669", marginLeft: "10px" }}>{improveResults.projected_ats_score}/100</span>
                  <span style={{ fontSize: "14px", fontWeight: 800, color: "#059669", marginLeft: "12px", background: "#ecfdf5", padding: "4px 10px", borderRadius: "12px", border: "1px solid #a7f3d0" }}>
                    +{improveResults.projected_ats_score - improveResults.original_ats_score}% Increase
                  </span>
                </div>
              </div>
              <div style={{ maxWidth: "450px", fontSize: "13px", color: "#475569", lineHeight: "1.6" }}>
                AI applied Google's XYZ formula, injected missing job keywords, and replaced passive verbs with quantifiable engineering accomplishments.
              </div>
            </div>

            {/* Tailored Professional Summary */}
            {improveResults.tailored_summary && (
              <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "20px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", marginBottom: "8px" }}>Tailored Professional Summary</div>
                <p style={{ fontSize: "14px", color: "#334155", lineHeight: "1.7", margin: 0 }}>{improveResults.tailored_summary}</p>
              </div>
            )}

            {/* Injected Keywords Badges */}
            {improveResults.key_injected_skills && improveResults.key_injected_skills.length > 0 && (
              <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "16px", padding: "18px 20px", marginBottom: "24px", textAlign: "left" }}>
                <div style={{ fontSize: "11px", fontWeight: 800, color: "#6d28d9", textTransform: "uppercase", marginBottom: "10px" }}>Injected High-Value ATS Keywords</div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {improveResults.key_injected_skills.map((skill, sIdx) => (
                    <span key={sIdx} style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#5b21b6", padding: "4px 12px", borderRadius: "16px", fontSize: "12px", fontWeight: 700 }}>
                      + {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Before vs After Bullet Point Comparison */}
            {improveResults.bullet_point_improvements && improveResults.bullet_point_improvements.length > 0 && (
              <div style={{ background: "#ffffff", border: "1px solid #e5e8f2", borderRadius: "20px", padding: "24px", marginBottom: "28px", textAlign: "left" }}>
                <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a", textTransform: "uppercase", marginBottom: "16px" }}>
                  High-Impact Bullet Point Rewrites (Before vs After)
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  {improveResults.bullet_point_improvements.map((b, bIdx) => (
                    <div key={bIdx} style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "16px" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "10px" }}>
                        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px", padding: "12px" }}>
                          <div style={{ fontSize: "10px", fontWeight: 800, color: "#dc2626", textTransform: "uppercase", marginBottom: "4px" }}>Original Bullet</div>
                          <div style={{ fontSize: "12.5px", color: "#475569", lineHeight: "1.5" }}>{b.original}</div>
                        </div>
                        <div style={{ background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: "10px", padding: "12px" }}>
                          <div style={{ fontSize: "10px", fontWeight: 800, color: "#059669", textTransform: "uppercase", marginBottom: "4px" }}>AI High-Impact Rewrite</div>
                          <div style={{ fontSize: "12.5px", color: "#0f172a", fontWeight: 600, lineHeight: "1.5" }}>{b.improved}</div>
                        </div>
                      </div>
                      <div style={{ fontSize: "11.5px", color: "#64748b", fontStyle: "italic", paddingLeft: "4px" }}>
                        <strong>Why it ranks higher:</strong> {b.impact_reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Complete Improved Resume Box */}
            {improveResults.full_improved_resume && (
              <div style={{ background: "#ffffff", border: "1px solid #ddd6fe", borderRadius: "20px", padding: "28px", textAlign: "left" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #e5e8f2", paddingBottom: "12px" }}>
                  <div style={{ fontSize: "14px", fontWeight: 800, color: "#6d28d9" }}>Complete Enhanced Resume (Ready to Use)</div>
                  <button type="button" onClick={copyToClipboard} style={{ background: copied ? "#059669" : "#f1f5f9", border: "1px solid #cbd5e1", color: copied ? "#fff" : "#0f172a", padding: "6px 14px", borderRadius: "8px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}>
                    {copied ? "✓ Copied!" : "Copy"}
                  </button>
                </div>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "'Courier New', Courier, monospace", fontSize: "12.5px", lineHeight: "1.7", color: "#1e293b", maxHeight: "500px", overflowY: "auto" }}>
                  {improveResults.full_improved_resume}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* ── OPTION 1 RESULTS: ATS SCORE ANALYSIS RESULTS PANEL ── */}
        {results && activeMode === "score" && (
          <div id="resume-results" style={{ display: "block", borderTop: "1px solid var(--border)", paddingTop: "24px" }} className="fade-up">
            <div className="sec-header mb16" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "15px", fontWeight: 800 }}>ATS Optimiser Analysis Results</div>
              <button className="btn btn-ghost btn-xs" onClick={() => setResults(null)}>← Clear Results</button>
            </div>

            {/* AI Summary banner */}
            {results.ai_summary && (
              <div className="card mb16" style={{ background: "rgba(0,196,167,0.07)", border: "1px solid rgba(0,196,167,0.2)", padding: "14px 18px", borderRadius: "14px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--cyan)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "5px" }}>AI Recruiter Summary</div>
                <div style={{ fontSize: "13px", lineHeight: 1.55, color: "var(--text2)" }}>{results.ai_summary}</div>
                {results.meta && (
                  <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginTop: "10px" }}>
                    <span style={{ fontSize: "11px", color: "var(--text3)" }}>⚙️ Engine: {results.meta.engine || "Hybrid ATS"}</span>
                    <span style={{ fontSize: "11px", color: "var(--text3)" }}>🎯 Skills matched: {results.meta.total_matched_skills}/{results.meta.total_jd_skills}</span>
                    {results.meta.resume_years && <span style={{ fontSize: "11px", color: "var(--text3)" }}>📅 Exp. detected: {results.meta.resume_years} yrs</span>}
                  </div>
                )}
              </div>
            )}

            <div className="g-main mb20">
              {/* Left Column: ATS Score Circle & Keyword Grid */}
              <div className="flex-col gap16">
                <div className="card flex items-center gap24" style={{ padding: "24px", flexWrap: "wrap", borderRadius: "16px" }}>
                  {/* Circular Score Ring */}
                  <div style={{ position: "relative", width: "92px", height: "92px", flexShrink: 0 }}>
                    <svg width="92" height="92" viewBox="0 0 92 92" style={{ transform: "rotate(-90deg)" }}>
                      <circle cx="46" cy="46" r="38" fill="none" stroke="#e2e8f0" strokeWidth="8"/>
                      <circle 
                        id="ats-ring-fill" 
                        cx="46" cy="46" r="38" 
                        fill="none" 
                        stroke="var(--cyan)" 
                        strokeWidth="8" 
                        strokeDasharray={circumference} 
                        strokeDashoffset={strokeDashoffset} 
                        strokeLinecap="round" 
                        style={{ transition: "stroke-dashoffset 1s ease" }}
                      />
                    </svg>
                    <div id="ats-ring-num" style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", fontSize: "22px", fontWeight: "900" }}>{results.ats_score}</div>
                  </div>
                  
                  {/* Summary & Grade */}
                  <div>
                    <div className="text-xs text-muted mb4">ATS Compatibility Index</div>
                    <div id="ats-score-display" style={{ fontSize: "28px", fontWeight: 900, color: "var(--cyan)", lineHeight: 1.1 }}>{results.ats_score}/100</div>
                    <span 
                      id="ats-grade-pill" 
                      className={`pill ${gradeColors[results.overall_grade] || 'pill-gold'}`} 
                      style={{ marginTop: "6px", display: "inline-flex" }}
                    >
                      Grade {results.overall_grade} · {gradeLabels[results.overall_grade]}
                    </span>
                  </div>
                </div>

                {/* Keyword matched vs missing grid */}
                <div className="card" style={{ borderRadius: "16px" }}>
                  <div className="sec-sub fw7 mb12">JD Keyword Analysis</div>
                  <div className="kw-grid" id="kw-grid-result">
                    {(results.matched_keywords || []).map((k, i) => (
                      <span key={`match-${i}`} className="kw kw-match">✓ {k}</span>
                    ))}
                    {(results.missing_keywords || []).map((k, i) => (
                      <span key={`miss-${i}`} className="kw kw-miss">✗ {k}</span>
                    ))}
                    {(results.bonus_skills || []).length > 0 && (
                      <>
                        <div style={{ width: "100%", fontSize: "10px", fontWeight: 700, color: "var(--purple)", letterSpacing: "0.07em", textTransform: "uppercase", marginTop: "8px", marginBottom: "2px" }}>Bonus skills (not required)</div>
                        {results.bonus_skills.map((k, i) => (
                          <span key={`bonus-${i}`} className="kw" style={{ background: "rgba(139,92,246,0.12)", border: "1px solid rgba(139,92,246,0.3)", color: "var(--purple)" }}>+ {k}</span>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Skill Match Progress Bars */}
              <div className="flex-col gap16">
                <div className="card" style={{ borderRadius: "16px" }}>
                  <div className="sec-sub fw7 mb16">Skill Relevance Checklist</div>
                  <div id="skill-match-bars" className="flex-col gap12">
                    {Object.keys(results.skill_match || {}).map(k => {
                      const pct = results.skill_match[k];
                      const col = pct >= 80 ? 'linear-gradient(90deg,var(--cyan),var(--blue))' : pct >= 50 ? 'linear-gradient(90deg,var(--orange),#d97706)' : 'linear-gradient(90deg,var(--red),#dc2626)';
                      const tc  = pct >= 80 ? 'var(--cyan)' : pct >= 50 ? 'var(--orange)' : 'var(--red)';
                      return (
                        <div key={k} className="skill-row">
                          <div className="skill-lbl">{k}</div>
                          <div className="skill-bg">
                            <div className="skill-fg" style={{ width: `${pct}%`, background: col }}></div>
                          </div>
                          <div className="skill-pct" style={{ color: tc }}>{pct}%</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Section Scores Grid */}
            {results.section_scores && (
              <>
                <div className="sec-header mb12">
                  <div className="sec-title">Section Scoring Breakdown</div>
                </div>
                <div className="g4 mb20" id="section-scores-row">
                  {Object.keys(results.section_scores).map(k => (
                    <div key={k} className="section-score">
                      <div className="ss-val" style={{ color: ssColors[k] || 'var(--cyan)' }}>{results.section_scores[k]}</div>
                      <div className="ss-lbl">{k.charAt(0).toUpperCase() + k.slice(1)}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Improvement tips list */}
            {results.improvement_tips && results.improvement_tips.length > 0 && (
              <div className="card mb24" style={{ borderRadius: "16px" }}>
                <div style={{ fontSize: "14px", fontWeight: 800, marginBottom: "12px" }}>AI Recommendations & Improvement Tips</div>
                <div className="flex-col gap8" id="improvement-tips">
                  {results.improvement_tips.map((t, i) => (
                    <div key={i} className="tip-row">
                      <span style={{ color: tipColors[i % 4] }}>→</span>
                      <span dangerouslySetInnerHTML={{ __html: t }}></span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
