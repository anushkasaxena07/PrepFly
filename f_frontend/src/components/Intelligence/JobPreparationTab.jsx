import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const TOP_COMPANIES = ["Google", "Amazon", "Microsoft", "Meta", "Apple", "Uber", "Netflix", "Adobe", "Stripe", "Salesforce", "Databricks"];
const ROLES = [
  "Software Engineer",
  "Backend Engineer",
  "Frontend Engineer",
  "Full Stack Engineer",
  "AI/ML Engineer",
  "Data Scientist",
  "Data Engineer",
  "DevOps Engineer",
  "Data Analyst"
];
const EXPERIENCE_LEVELS = [
  "Fresher / Entry Level (0-1 yr)",
  "Junior (1-2 yrs)",
  "Mid-Level (2-5 years)",
  "Senior (5+ years)"
];

const SAMPLE_JDS = {
  aiml: {
    title: "AI/ML Engineer",
    company: "Databricks",
    level: "Fresher / Entry Level (0-1 yr)",
    text: `Core Responsibilities:
• Model Development: Design, train, and fine-tune machine learning, deep learning, NLP, and generative AI models from scratch or using existing frameworks.
• Data Engineering: Collect, clean, preprocess, and manage large-scale datasets.
• Productionization: Deploy models into production environments, convert models into APIs, and ensure real-time scalability and low latency.
• Optimization & Monitoring: Track model performance, handle data drift, and retrain models to maintain accuracy over time.`
  },
  backend: {
    title: "Backend Engineer",
    company: "Uber",
    level: "Mid-Level (2-5 years)",
    text: `Responsibilities:
• Design and build high-throughput REST APIs and microservices.
• Optimize PostgreSQL database schemas, write efficient SQL queries, and implement Redis caching.
• Ensure system reliability, horizontal scalability, and handle production deployments using Docker.
• Collaborate with frontend and infrastructure engineers on service architecture.`
  },
  sde: {
    title: "Software Engineer",
    company: "Google",
    level: "Fresher / Entry Level (0-1 yr)",
    text: `Minimum Qualifications:
• Bachelor's degree in Computer Science or equivalent practical experience.
• Experience in software development with Python, Java, or C++.
• Strong foundation in Data Structures, Algorithms, problem solving, and computational complexity.
• Solid grasp of Operating Systems, Memory Management, and Concurrency fundamentals.`
  },
  data: {
    title: "Data Analyst",
    company: "Amazon",
    level: "Junior (1-2 yrs)",
    text: `Key Responsibilities:
• Write complex SQL queries to extract, transform, and analyze multi-terabyte datasets.
• Build automated dashboards and KPI reporting tools using Python, Pandas, and visualization libraries.
• Perform statistical hypothesis testing and present actionable business recommendations to cross-functional leaders.`
  }
};

export default function JobPreparationTab({ user, onStartInterview }) {
  const [activeTabMode, setActiveTabMode] = useState("readiness_engine"); // "readiness_engine" | "company_roadmap"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // ─── Mode A: Job Readiness Assessment Engine State ───
  const [targetCompany, setTargetCompany] = useState("Google");
  const [targetRole, setTargetRole] = useState("Software Engineer");
  const [targetExperience, setTargetExperience] = useState("Fresher / Entry Level (0-1 yr)");
  const [targetDate, setTargetDate] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  );
  const [jdText, setJdText] = useState("");

  // Assessment Report & In-session State
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [readinessReport, setReadinessReport] = useState(null);
  const [reportSection, setReportSection] = useState("overview"); // "overview" | "requirements" | "coding" | "interview" | "resume" | "assessment" | "recommendations"
  const [blueprintData, setBlueprintData] = useState(null);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [candidateResponse, setCandidateResponse] = useState("");
  const [evaluatingAttempt, setEvaluatingAttempt] = useState(false);
  const [lastAttemptEvaluation, setLastAttemptEvaluation] = useState(null);

  // ─── Mode B: Company Roadmap Schedule State (Preserved) ───
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [prepStyle, setPrepStyle] = useState("mixed");
  const [companyPlan, setCompanyPlan] = useState(null);
  const [activeDayFilter, setActiveDayFilter] = useState("ALL");

  const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";

  // Load sample JD
  const loadSampleJD = (key) => {
    const s = SAMPLE_JDS[key];
    if (s) {
      setTargetCompany(s.company);
      setTargetRole(s.title);
      setTargetExperience(s.level);
      setJdText(s.text);
    }
  };

  // Run Job Readiness Assessment
  const handleRunAssessment = async (e) => {
    if (e) e.preventDefault();
    if (!jdText.trim() || jdText.trim().length < 20) {
      setError("Please paste a job description with at least 20 characters.");
      return;
    }

    setLoading(true);
    setError("");
    setSuccessMsg("");
    setReadinessReport(null);

    try {
      const res = await intelligenceAPI.createJobReadinessAssessment({
        user_id: candidateUserId,
        raw_text: jdText,
        company: targetCompany,
        role: targetRole,
        experience_level: targetExperience,
        target_date: targetDate
      });

      if (res && res.session_id) {
        setActiveSessionId(res.session_id);
        setReadinessReport(res.data);
        setSuccessMsg("Job Readiness Assessment initialized successfully!");

        // Load blueprint questions
        const bpRes = await intelligenceAPI.getJobAssessmentBlueprint(res.session_id);
        if (bpRes && bpRes.data) {
          setBlueprintData(bpRes.data);
        }
      }
    } catch (err) {
      setError(err.message || "Failed to initialize job readiness assessment.");
    } finally {
      setLoading(false);
    }
  };

  // Submit in-session question attempt
  const handleSubmitAttempt = async () => {
    if (!candidateResponse.trim()) {
      setError("Please enter your answer or code before submitting.");
      return;
    }
    if (!blueprintData || !blueprintData.adaptive_questions || !blueprintData.adaptive_questions[activeQuestionIndex]) {
      return;
    }

    const currentQ = blueprintData.adaptive_questions[activeQuestionIndex];
    setEvaluatingAttempt(true);
    setError("");

    try {
      const res = await intelligenceAPI.submitJobAssessmentAttempt(activeSessionId, {
        user_id: candidateUserId,
        component_type: currentQ.component_type,
        canonical_skill_id: currentQ.canonical_skill_id,
        question_id: currentQ.id,
        candidate_response: candidateResponse,
        code_submission: currentQ.component_type === "coding" ? candidateResponse : null,
        time_taken_seconds: 120
      });

      if (res && res.evaluation) {
        setLastAttemptEvaluation(res.evaluation);
        if (res.updated_report) {
          setReadinessReport(res.updated_report);
        }
        setSuccessMsg(`Rubric evaluation completed! Scored ${res.evaluation.overall_score}% on ${currentQ.skill_name}.`);
        setCandidateResponse("");
        if (activeQuestionIndex < blueprintData.adaptive_questions.length - 1) {
          setActiveQuestionIndex(prev => prev + 1);
        }
      }
    } catch (err) {
      setError(err.message || "Failed to submit assessment attempt.");
    } finally {
      setEvaluatingAttempt(false);
    }
  };

  // Transfer readiness gaps to Prep tab Roadmap
  const handleTransferToPrep = async () => {
    if (!activeSessionId) return;
    setLoading(true);
    setError("");

    try {
      const res = await intelligenceAPI.transferJobReadinessToPrep(activeSessionId, {
        user_id: candidateUserId,
        daily_minutes: dailyMinutes
      });
      if (res && res.data) {
        setSuccessMsg("Readiness gaps transferred to Prep Roadmap! Generating your daily schedule...");
        // Generate plan in Mode B
        const planRes = await intelligenceAPI.generateCompanyPlan({
          user_id: candidateUserId,
          company_name: targetCompany,
          role: targetRole,
          experience_level: targetExperience,
          target_date: targetDate,
          daily_minutes: dailyMinutes,
          prep_style: "mixed",
          job_description: jdText
        });
        if (planRes && planRes.data) {
          setCompanyPlan(planRes.data);
          setActiveTabMode("company_roadmap");
        }
      }
    } catch (err) {
      setError(err.message || "Failed to transfer readiness gaps to roadmap.");
    } finally {
      setLoading(false);
    }
  };

  const getRequirementBadge = (type) => {
    switch (type) {
      case "explicit_mandatory":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">Mandatory</span>;
      case "explicit_preferred":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">Preferred</span>;
      case "responsibility_derived":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">Responsibility</span>;
      case "company_interview_pattern":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">Company Pattern</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-300">General Expectation</span>;
    }
  };

  return (
    <div className="intelligence-root min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* ─── Top Header & Mode Navigation ─── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded-full text-xs font-bold uppercase tracking-wider">
                PrepFly Candidate Diagnostic Engine
              </span>
              <span className="text-xs text-slate-500 font-mono">v2.0 Verified</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight mt-2">
              Job Readiness Assessment & Gap Engine
            </h1>
            <p className="text-xs md:text-sm text-slate-400 mt-1">
              Evidence-based diagnostic comparing job requirements against demonstrated coding, technical interviews, and resume credentials.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl">
            <button
              onClick={() => setActiveTabMode("readiness_engine")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                activeTabMode === "readiness_engine"
                  ? "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              1. Job Readiness Assessment
            </button>
            <button
              onClick={() => setActiveTabMode("company_roadmap")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                activeTabMode === "company_roadmap"
                  ? "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              2. Company Preparation Plan
            </button>
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError("")} className="text-rose-400 font-bold ml-4">✕</button>
          </div>
        )}
        {successMsg && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg("")} className="text-emerald-400 font-bold ml-4">✕</button>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB MODE 1: JOB READINESS ASSESSMENT & GAP ENGINE                         */}
        {/* ========================================================================= */}
        {activeTabMode === "readiness_engine" && (
          <div className="space-y-8">

            {/* Target Job Setup Form */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-white">Target Job & Opportunity Profile</h2>
                  <p className="text-xs text-slate-400">Specify your target company, role, and paste the job description.</p>
                </div>

                {/* Sample JD Pre-fill Buttons */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] text-slate-400 font-medium">Load Sample JD:</span>
                  <button onClick={() => loadSampleJD("sde")} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-semibold border border-slate-700">Google SDE</button>
                  <button onClick={() => loadSampleJD("aiml")} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-semibold border border-slate-700">Databricks AI/ML</button>
                  <button onClick={() => loadSampleJD("backend")} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-semibold border border-slate-700">Uber Backend</button>
                  <button onClick={() => loadSampleJD("data")} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-semibold border border-slate-700">Amazon Data</button>
                </div>
              </div>

              <form onSubmit={handleRunAssessment} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Company</label>
                    <input
                      type="text"
                      value={targetCompany}
                      onChange={(e) => setTargetCompany(e.target.value)}
                      placeholder="e.g. Google, Databricks"
                      className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Role / Job Title</label>
                    <select
                      value={targetRole}
                      onChange={(e) => setTargetRole(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    >
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Experience Level</label>
                    <select
                      value={targetExperience}
                      onChange={(e) => setTargetExperience(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                    >
                      {EXPERIENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Target Interview Date</label>
                    <input
                      type="date"
                      value={targetDate}
                      onChange={(e) => setTargetDate(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Job Description Text</label>
                  <textarea
                    rows={5}
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Paste the full job description text here..."
                    className="w-full px-3.5 py-3 bg-slate-800/90 border border-slate-700 rounded-xl text-white text-xs font-mono"
                    required
                  />
                </div>

                <div className="flex justify-end gap-3">
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition shadow-lg shadow-cyan-500/20"
                  >
                    {loading ? "Analyzing Evidence & Requirements..." : "Run Job Readiness Assessment"}
                  </button>
                </div>
              </form>
            </div>

            {/* Assessment Report Container */}
            {readinessReport && (
              <div className="space-y-6">

                {/* HERO: Readiness & Coverage Dashboard */}
                <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center">

                    {/* Overall Score / Status */}
                    <div className="md:col-span-1 border-b md:border-b-0 md:border-r border-slate-800 pb-4 md:pb-0 md:pr-6 text-center md:text-left">
                      <div className="text-xs uppercase font-extrabold tracking-wider text-slate-400 mb-1">Overall Job Readiness</div>
                      {readinessReport.section_b_overall_readiness.is_gated ? (
                        <div>
                          <div className="inline-block px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-extrabold uppercase mt-1">
                            Readiness Not Yet Established
                          </div>
                          <p className="text-[11px] text-slate-400 mt-2">
                            {readinessReport.section_b_overall_readiness.gate_reason}
                          </p>
                        </div>
                      ) : (
                        <div>
                          <div className="text-4xl md:text-5xl font-black text-cyan-400 tracking-tight">
                            {readinessReport.section_b_overall_readiness.overall_readiness}%
                          </div>
                          <span className="text-xs text-emerald-400 font-bold block mt-1">✓ Evidence-Backed Readiness</span>
                        </div>
                      )}
                    </div>

                    {/* Assessment Coverage */}
                    <div>
                      <div className="text-xs text-slate-400 font-semibold mb-1">Assessment Coverage</div>
                      <div className="text-2xl font-bold text-white mb-2">
                        {readinessReport.section_b_overall_readiness.assessment_coverage_pct}%
                      </div>
                      <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                        <div
                          className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, readinessReport.section_b_overall_readiness.assessment_coverage_pct)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 block">Min 40% required to establish readiness</span>
                    </div>

                    {/* Evidence Confidence */}
                    <div>
                      <div className="text-xs text-slate-400 font-semibold mb-1">Evidence Confidence</div>
                      <div className="text-2xl font-bold text-white mb-2">
                        {Math.round(readinessReport.section_b_overall_readiness.evidence_confidence * 100)}%
                      </div>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div
                            key={i}
                            className={`h-2 flex-1 rounded-sm ${
                              i <= Math.round(readinessReport.section_b_overall_readiness.evidence_confidence * 5)
                                ? "bg-emerald-400"
                                : "bg-slate-800"
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 block">Based on verified platform observations</span>
                    </div>

                    {/* Action: Transfer to Prep Tab */}
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={handleTransferToPrep}
                        disabled={loading}
                        className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-slate-950 font-bold rounded-xl text-xs transition shadow-lg shadow-cyan-500/20"
                      >
                        ⚡ Transfer to Prep Schedule
                      </button>
                      <button
                        onClick={() => setReportSection("assessment")}
                        className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-xs border border-slate-700 transition"
                      >
                        ✍ Take Missing Assessments
                      </button>
                    </div>

                  </div>
                </div>

                {/* 9-Section Navigation Bar */}
                <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
                  {[
                    { id: "overview", label: "A. Overview & Intel" },
                    { id: "requirements", label: "C. Requirement Breakdown" },
                    { id: "coding", label: "D. Coding Analysis" },
                    { id: "interview", label: "E. Ava Interview" },
                    { id: "resume", label: "F. Resume & Projects" },
                    { id: "assessment", label: "✍ Adaptive Assessment" },
                    { id: "recommendations", label: "I. Improvement Plan" }
                  ].map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setReportSection(s.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                        reportSection === s.id
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                          : "text-slate-400 hover:text-white bg-slate-900 border border-slate-800"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>

                {/* SECTION A: Overview & Company Interview Intelligence */}
                {reportSection === "overview" && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>🏢</span> Target Opportunity Overview
                      </h3>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                          <span className="text-slate-400">Target Company:</span>
                          <span className="font-bold text-white">{readinessReport.section_a_job_overview.company}</span>
                        </div>
                        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                          <span className="text-slate-400">Target Role:</span>
                          <span className="font-bold text-white">{readinessReport.section_a_job_overview.role}</span>
                        </div>
                        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                          <span className="text-slate-400">Experience Tier:</span>
                          <span className="font-bold text-white">{readinessReport.section_a_job_overview.experience_level}</span>
                        </div>
                        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                          <span className="text-slate-400">Target Date:</span>
                          <span className="font-bold text-cyan-400">{readinessReport.section_a_job_overview.target_date || "Open"}</span>
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 text-[11px] text-slate-300">
                        <span className="font-bold text-slate-200 block mb-1">Original Job Description Extract:</span>
                        {readinessReport.section_a_job_overview.jd_preview}
                      </div>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>📊</span> Company Interview Intelligence
                      </h3>
                      <div className="text-xs text-slate-400">
                        {readinessReport.section_a_job_overview.company_intelligence.evidence_disclosure}
                      </div>
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-slate-300 block">Expected Interview Rounds:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {readinessReport.section_a_job_overview.company_intelligence.interview_rounds.map((round, idx) => (
                            <span key={idx} className="px-2.5 py-1 rounded-md text-[11px] bg-slate-800 text-slate-200 border border-slate-700">
                              Round {idx + 1}: {round}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-2 pt-2 border-t border-slate-800">
                        <span className="text-xs font-semibold text-slate-300 block">Frequent Evaluation Topics:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {readinessReport.section_a_job_overview.company_intelligence.coding_patterns.map((p, idx) => (
                            <span key={idx} className="px-2 py-0.5 rounded text-[10px] bg-cyan-950/40 text-cyan-300 border border-cyan-800/40 font-mono">
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* SECTION C: Requirement Breakdown */}
                {reportSection === "requirements" && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-bold text-white">Extracted & Classified Job Requirements</h3>
                        <p className="text-xs text-slate-400">Every requirement is classified into 6 verified types and checked against negative guardrails.</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-400">Total: {readinessReport.section_c_requirement_analysis.total_requirements}</span>
                        <span className="text-rose-400">Mandatory: {readinessReport.section_c_requirement_analysis.mandatory_count}</span>
                        <span className="text-emerald-400">Preferred: {readinessReport.section_c_requirement_analysis.preferred_count}</span>
                      </div>
                    </div>

                    <div className="divide-y divide-slate-800/80">
                      {[
                        ...readinessReport.section_c_requirement_analysis.demonstrated_requirements.map(r => ({ ...r, status: "DEMONSTRATED" })),
                        ...readinessReport.section_c_requirement_analysis.assessed_partial_competencies.map(r => ({ ...r, status: "ASSESSED" })),
                        ...readinessReport.section_c_requirement_analysis.unassessed_requirements.map(r => ({ ...r, status: "UNASSESSED" }))
                      ].map((req, idx) => (
                        <div key={idx} className="py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-white">{req.skill_name || req.canonical_skill_id}</span>
                              {getRequirementBadge(req.requirement_type)}
                              {req.status === "DEMONSTRATED" && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">✓ Demonstrated</span>}
                              {req.status === "ASSESSED" && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">Assessed</span>}
                              {req.status === "UNASSESSED" && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">Not Assessed</span>}
                            </div>
                            <p className="text-xs text-slate-400">{req.normalized_description}</p>
                            <span className="text-[11px] text-slate-500 font-mono">Source quote: "{req.original_source_text}"</span>
                          </div>
                          <div className="text-right flex md:flex-col items-center md:items-end justify-between md:justify-center">
                            <span className="text-xs text-slate-400">Weight: {req.importance}/5.0</span>
                            <span className="text-[10px] text-slate-500">Confidence: {Math.round((req.extraction_confidence || 0.9) * 100)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* SECTION D: Coding Analysis */}
                {reportSection === "coding" && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <h3 className="text-sm font-bold text-white">Coding & Problem-Solving Assessment</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Coding Proficiency Score</span>
                        <span className="text-2xl font-bold text-cyan-400">{readinessReport.section_d_coding_analysis.coding_score}%</span>
                      </div>
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Accepted Submissions</span>
                        <span className="text-2xl font-bold text-white">{readinessReport.section_d_coding_analysis.accepted_submissions}</span>
                      </div>
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Execution Correctness</span>
                        <span className="text-2xl font-bold text-emerald-400">Verified</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-slate-300 block">Identified Boundary & Complexity Weaknesses:</span>
                      <ul className="list-disc list-inside text-xs text-slate-400 space-y-1">
                        {readinessReport.section_d_coding_analysis.weaknesses_identified.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* SECTION E: Ava Interview Analysis */}
                {reportSection === "interview" && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <h3 className="text-sm font-bold text-white">Ava AI Technical Interview Analysis</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Technical Turn Score</span>
                        <span className="text-2xl font-bold text-cyan-400">{readinessReport.section_e_technical_interview_analysis.technical_interview_score}%</span>
                      </div>
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Conceptual Understanding</span>
                        <span className="text-2xl font-bold text-white">{readinessReport.section_e_technical_interview_analysis.conceptual_understanding}%</span>
                      </div>
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Completed Mock Sessions</span>
                        <span className="text-2xl font-bold text-white">{readinessReport.section_e_technical_interview_analysis.completed_ava_sessions}</span>
                      </div>
                    </div>
                    <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/60 text-xs text-slate-300">
                      <span className="font-bold text-slate-200 block mb-1">Explanation Depth Evaluation:</span>
                      {readinessReport.section_e_technical_interview_analysis.explanation_quality}
                    </div>
                  </div>
                )}

                {/* SECTION F: Resume & Project Analysis */}
                {reportSection === "resume" && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <h3 className="text-sm font-bold text-white">Resume & Project Experience Alignment</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">ATS JD Match Score</span>
                        <span className="text-2xl font-bold text-cyan-400">{readinessReport.section_f_resume_analysis.ats_match_score}%</span>
                      </div>
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <span className="text-xs text-slate-400 block mb-1">Verified Experience Claims</span>
                        <span className="text-2xl font-bold text-white">{readinessReport.section_f_resume_analysis.verified_claims_count}</span>
                      </div>
                    </div>
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 text-xs text-slate-300">
                      <span className="font-bold text-slate-200 block mb-1">Resume Tailoring Recommendation:</span>
                      {readinessReport.section_f_resume_analysis.recommendation}
                    </div>
                  </div>
                )}

                {/* SECTION: Adaptive Assessment Runner */}
                {reportSection === "assessment" && blueprintData && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-bold text-white">Adaptive Diagnostic Assessment</h3>
                        <p className="text-xs text-slate-400">Complete targeted role-specific questions to raise your assessment coverage and establish verified readiness.</p>
                      </div>
                      <span className="text-xs text-cyan-400 font-mono">
                        Question {activeQuestionIndex + 1} of {blueprintData.adaptive_questions.length}
                      </span>
                    </div>

                    {blueprintData.adaptive_questions && blueprintData.adaptive_questions[activeQuestionIndex] && (
                      <div className="space-y-4">
                        <div className="p-5 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">
                              {blueprintData.adaptive_questions[activeQuestionIndex].component_type} • {blueprintData.adaptive_questions[activeQuestionIndex].skill_name}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                              {blueprintData.adaptive_questions[activeQuestionIndex].difficulty}
                            </span>
                          </div>
                          <p className="text-sm font-semibold text-white">
                            {blueprintData.adaptive_questions[activeQuestionIndex].question_text}
                          </p>
                          <div className="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                            <span className="font-bold text-slate-300 block mb-0.5">Objective:</span>
                            {blueprintData.adaptive_questions[activeQuestionIndex].assessment_objective}
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-300 mb-1">Your Submission (Code or Written Technical Explanation):</label>
                          <textarea
                            rows={6}
                            value={candidateResponse}
                            onChange={(e) => setCandidateResponse(e.target.value)}
                            placeholder="Type your structured solution, architectural trade-offs, or code..."
                            className="w-full px-3.5 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs font-mono"
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex gap-2">
                            {activeQuestionIndex > 0 && (
                              <button
                                onClick={() => setActiveQuestionIndex(prev => prev - 1)}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-xs transition"
                              >
                                ← Previous
                              </button>
                            )}
                            {activeQuestionIndex < blueprintData.adaptive_questions.length - 1 && (
                              <button
                                onClick={() => setActiveQuestionIndex(prev => prev + 1)}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-xs transition"
                              >
                                Next →
                              </button>
                            )}
                          </div>

                          <button
                            onClick={handleSubmitAttempt}
                            disabled={evaluatingAttempt}
                            className="px-6 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition shadow-lg shadow-cyan-500/20"
                          >
                            {evaluatingAttempt ? "Scoring against Rubrics..." : "Submit for Rubric Evaluation"}
                          </button>
                        </div>

                        {lastAttemptEvaluation && (
                          <div className="p-4 bg-slate-950/90 rounded-xl border border-cyan-500/30 text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-cyan-300">Latest Rubric Evaluation Result</span>
                              <span className="font-extrabold text-white text-sm">{lastAttemptEvaluation.overall_score}%</span>
                            </div>
                            <p className="text-slate-300">{lastAttemptEvaluation.feedback}</p>
                            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-[11px]">
                              {Object.entries(lastAttemptEvaluation.rubric_breakdown || {}).map(([k, v]) => (
                                <div key={k} className="p-2 bg-slate-900 rounded border border-slate-800">
                                  <span className="text-slate-400 block capitalize">{k.replace("_", " ")}:</span>
                                  <span className="font-bold text-white">{v}%</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* SECTION I: Actionable Improvement Plan */}
                {reportSection === "recommendations" && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-bold text-white">Targeted Job Improvement Plan</h3>
                        <p className="text-xs text-slate-400">Prioritized by requirement importance, proficiency gap, and timeline urgency.</p>
                      </div>
                      <button
                        onClick={handleTransferToPrep}
                        disabled={loading}
                        className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition"
                      >
                        ⚡ Transfer All Gaps to Roadmap
                      </button>
                    </div>

                    <div className="space-y-3">
                      {readinessReport.section_i_improvement_plan.all_recommendations.map((rec) => (
                        <div key={rec.id} className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-white">{rec.skill_name}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                rec.priority === "CRITICAL"
                                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                                  : rec.priority === "HIGH"
                                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                  : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                              }`}>
                                {rec.priority} Priority
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono">Priority Score: {rec.priority_score}</span>
                          </div>
                          <p className="text-xs text-slate-300 font-medium">{rec.problem_identified}</p>
                          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-[11px] text-slate-400 flex flex-col md:flex-row md:items-center justify-between gap-2">
                            <span><strong className="text-slate-300">Action:</strong> {rec.recommended_practice}</span>
                            <span className="text-cyan-400 font-semibold">{rec.target_competency}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB MODE 2: COMPANY-SPECIFIC PREPARATION ROADMAP                          */}
        {/* ========================================================================= */}
        {activeTabMode === "company_roadmap" && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-white">Daily Company Preparation Schedule</h2>
                <p className="text-xs text-slate-400">Personalized day-by-day roadmap targeting verified skill gaps and company interview rounds.</p>
              </div>
              <button
                onClick={() => setActiveTabMode("readiness_engine")}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold border border-slate-700 transition"
              >
                ← Return to Job Readiness
              </button>
            </div>

            {companyPlan ? (
              <div className="space-y-4">
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs text-slate-400 block">Active Target Plan</span>
                    <span className="text-lg font-bold text-cyan-400">{companyPlan.company_name} • {companyPlan.role}</span>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <div><span className="text-slate-400 block">Total Days</span><span className="font-bold text-white">{companyPlan.total_days}</span></div>
                    <div><span className="text-slate-400 block">Daily Time</span><span className="font-bold text-white">{companyPlan.daily_minutes} mins</span></div>
                  </div>
                </div>

                <div className="space-y-3">
                  {companyPlan.schedule && companyPlan.schedule.slice(0, 7).map((day) => (
                    <div key={day.day_number} className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-cyan-400 uppercase">Day {day.day_number}: {day.theme}</span>
                        <span className="text-[11px] text-slate-500 font-mono">{day.allocated_minutes} mins</span>
                      </div>
                      <div className="space-y-1.5">
                        {day.activities && day.activities.map((act, aIdx) => (
                          <div key={aIdx} className="text-xs text-slate-300 flex items-center justify-between py-1 border-t border-slate-900">
                            <span>• {act.title}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{act.activity_type}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                No active company schedule loaded. Return to the Job Readiness Assessment and click "Transfer to Prep Schedule" to generate your plan.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
