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
  "DevOps Engineer"
];
const EXPERIENCE_LEVELS = [
  "Fresher / Entry Level (0-1 yr)",
  "Junior (1-2 yrs)",
  "Mid-Level (2-5 years)",
  "Senior (5+ years)"
];

export default function JobPreparationTab({ user, onStartInterview }) {
  const [activeMode, setActiveMode] = useState("company_engine"); // "company_engine" | "jd_ingest"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // ── Company-Specific Engine State ──
  const [stage, setStage] = useState(1); // 1: Target Setup, 2: Candidate Readiness, 3: Company Intelligence, 4: Preview, 5: Roadmap
  const [company, setCompany] = useState("Google");
  const [role, setRole] = useState("Software Engineer");
  const [experienceLevel, setExperienceLevel] = useState("Fresher / Entry Level (0-1 yr)");
  const [targetDate, setTargetDate] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  );
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [prepStyle, setPrepStyle] = useState("mixed"); // "mixed" | "coding" | "theory" | "mock"
  const [customJD, setCustomJD] = useState("");

  // Data snapshots
  const [candidateReadiness, setCandidateReadiness] = useState(null);
  const [companyIntelligence, setCompanyIntelligence] = useState(null);
  const [gapAnalysis, setGapAnalysis] = useState(null);
  const [activePlan, setActivePlan] = useState(null);
  const [activeDayFilter, setActiveDayFilter] = useState("ALL");
  const [selectedPersonality, setSelectedPersonality] = useState("professional");

  // ── JD Ingestion Legacy State ──
  const [legacyJobTitle, setLegacyJobTitle] = useState("");
  const [legacyCompany, setLegacyCompany] = useState("");
  const [legacyRawText, setLegacyRawText] = useState("");
  const [legacyAnalysis, setLegacyAnalysis] = useState(null);

  useEffect(() => {
    // Initial fetch of candidate readiness
    loadCandidateReadiness();
  }, [role]);

  const loadCandidateReadiness = async () => {
    try {
      const res = await intelligenceAPI.getCandidateReadiness(role);
      if (res && res.data) {
        setCandidateReadiness(res.data);
      }
    } catch (e) {
      console.warn("Could not load candidate readiness:", e);
    }
  };

  const handleFetchCompanyIntelligence = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await intelligenceAPI.getCompanyIntelligence(company, role, experienceLevel);
      if (res && res.data) {
        setCompanyIntelligence(res.data);
      }
    } catch (e) {
      setError(e.message || "Failed to load company intelligence.");
    } finally {
      setLoading(false);
    }
  };

  const handleComputeGaps = async () => {
    setLoading(true);
    setError("");
    try {
      const tDate = new Date(targetDate);
      const diffDays = Math.max(1, Math.round((tDate - new Date()) / (1000 * 60 * 60 * 24)));
      const res = await intelligenceAPI.getCompanyGapAnalysis({
        company_name: company,
        role: role,
        experience_level: experienceLevel,
        days_to_deadline: diffDays
      });
      if (res && res.data) {
        setGapAnalysis(res.data);
      }
    } catch (e) {
      setError(e.message || "Failed to compute company gap analysis.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateFullPlan = async () => {
    setLoading(true);
    setError("");
    setSuccessMsg("");

    const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";

    try {
      const res = await intelligenceAPI.generateCompanyPlan({
        user_id: candidateUserId,
        company_name: company,
        role: role,
        experience_level: experienceLevel,
        target_date: targetDate,
        daily_minutes: dailyMinutes,
        prep_style: prepStyle,
        job_description: customJD
      });
      if (res && res.data) {
        setActivePlan(res.data);
        setCompanyIntelligence(res.data.company_intelligence);
        setCandidateReadiness(res.data.candidate_readiness);
        setGapAnalysis(res.data.gap_analysis);
        setSuccessMsg(`Personalized preparation plan generated for ${company}!`);
        setStage(5); // Go directly to Roadmap view
      }
    } catch (e) {
      setError(e.message || "Failed to generate preparation plan.");
    } finally {
      setLoading(false);
    }
  };

  // Launch Ava mock interview from roadmap activity or question
  const handleLaunchAvaMock = async (roundName, customPrompt) => {
    setLoading(true);
    setError("");

    const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";

    try {
      // Create session tailored to this company round
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${BACKEND_URL}/create-session-no-resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          user_id: candidateUserId,
          role: `${company} ${role}`,
          category: "Company Mock",
          difficulty: experienceLevel.includes("Senior") ? "Hard" : "Medium",
          job_description: `Target Company: ${company}\nTarget Role: ${role}\nRound Focus: ${roundName || "Company Interview Round"}\nLevel: ${experienceLevel}\n${customPrompt || ""}`,
          consent: true
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create company mock session");

      if (onStartInterview) {
        onStartInterview(data);
      }
    } catch (err) {
      setError(err.message || "Failed to launch mock interview.");
    } finally {
      setLoading(false);
    }
  };

  // Legacy JD Ingest Handler (Preserved for compatibility)
  const handleLegacyIngest = async (e) => {
    e.preventDefault();
    if (!legacyRawText || legacyRawText.trim().length < 20) {
      setError("Please paste a job description with at least 20 characters.");
      return;
    }
    setLoading(true);
    setError("");
    const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";
    try {
      const res = await intelligenceAPI.ingestJobDescription({
        user_id: candidateUserId,
        job_title: legacyJobTitle,
        company: legacyCompany,
        raw_text: legacyRawText
      });
      if (res.data) {
        setLegacyAnalysis(res.data);
        setSuccessMsg("Job description successfully analyzed!");
      }
    } catch (err) {
      setError(err.message || "Failed to analyze job description.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div id="page-jobs" className="page active" role="tabpanel">
      <div className="container intelligence-root space-y-6 text-slate-100 pb-16">
        
        {/* Header with Mode Switcher */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                PrepFly Intelligence
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                Two-Dimensional Strategy
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white mt-1">
              Company-Specific Preparation Engine
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Combines <strong>Candidate Demonstrated Readiness</strong> with <strong>Verified Company Interview Intelligence</strong> to build your targeted strategy.
            </p>
          </div>

          <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl self-start md:self-auto">
            <button
              onClick={() => setActiveMode("company_engine")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                activeMode === "company_engine"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-900/40"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              🏢 Company Strategy Engine
            </button>
            <button
              onClick={() => setActiveMode("jd_ingest")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                activeMode === "jd_ingest"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-900/40"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              📄 Raw JD Ingestion
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-950/60 border border-red-800/80 rounded-xl text-red-200 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError("")} className="text-red-400 hover:text-white">✕</button>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-950/60 border border-emerald-800/80 rounded-xl text-emerald-200 text-sm flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg("")} className="text-emerald-400 hover:text-white">✕</button>
          </div>
        )}

        {/* MODE A: INTELLIGENT COMPANY-SPECIFIC ENGINE */}
        {activeMode === "company_engine" && (
          <div className="space-y-6">
            
            {/* 6-Stage Stepper Navigation */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 bg-slate-900/90 border border-slate-800 p-2 rounded-2xl text-xs font-semibold">
              <button
                onClick={() => setStage(1)}
                className={`py-2 px-3 rounded-xl transition text-center ${
                  stage === 1 ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                1. Target Setup
              </button>
              <button
                onClick={async () => {
                  await loadCandidateReadiness();
                  setStage(2);
                }}
                className={`py-2 px-3 rounded-xl transition text-center ${
                  stage === 2 ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                2. Candidate Readiness
              </button>
              <button
                onClick={async () => {
                  if (!companyIntelligence) await handleFetchCompanyIntelligence();
                  setStage(3);
                }}
                className={`py-2 px-3 rounded-xl transition text-center ${
                  stage === 3 ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                3. Company Research
              </button>
              <button
                onClick={async () => {
                  if (!gapAnalysis) await handleComputeGaps();
                  setStage(4);
                }}
                className={`py-2 px-3 rounded-xl transition text-center ${
                  stage === 4 ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                4. Gap Analysis
              </button>
              <button
                onClick={handleGenerateFullPlan}
                className={`py-2 px-3 rounded-xl transition text-center ${
                  stage === 5 ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                5. Personalized Roadmap
              </button>
            </div>

            {/* STAGE 1: TARGET SETUP */}
            {stage === 1 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-white">Stage 1: Define Your Target & Constraints</h2>
                  <p className="text-xs text-slate-400 mt-1">Specify target company, position, experience level, and available study budget.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Target Company
                    </label>
                    <input
                      type="text"
                      list="company-list"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="e.g. Google, Amazon, Microsoft"
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    />
                    <datalist id="company-list">
                      {TOP_COMPANIES.map((c) => <option key={c} value={c} />)}
                    </datalist>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Target Role
                    </label>
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Experience Level
                    </label>
                    <select
                      value={experienceLevel}
                      onChange={(e) => setExperienceLevel(e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    >
                      {EXPERIENCE_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Target Interview Date
                    </label>
                    <input
                      type="date"
                      value={targetDate}
                      min={new Date().toISOString().split("T")[0]}
                      onChange={(e) => setTargetDate(e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Daily Study Budget (Minutes)
                    </label>
                    <select
                      value={dailyMinutes}
                      onChange={(e) => setDailyMinutes(Number(e.target.value))}
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    >
                      <option value={30}>30 min / day (Steady pace)</option>
                      <option value={45}>45 min / day (Focused pace)</option>
                      <option value={60}>60 min / day (Standard standard)</option>
                      <option value={90}>90 min / day (Accelerated pace)</option>
                      <option value={120}>120 min / day (Intensive sprint)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Preparation Focus Style
                    </label>
                    <select
                      value={prepStyle}
                      onChange={(e) => setPrepStyle(e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500"
                    >
                      <option value="mixed">Balanced (Theory + Coding + Ava Mocks)</option>
                      <option value="coding">Algorithmic & Coding Intensive</option>
                      <option value="mock">Interview Simulation & Behavioral</option>
                      <option value="theory">Systems & Core CS Fundamentals</option>
                    </select>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                  <span className="text-xs text-slate-500">
                    Next: Review your demonstrated candidate skills before matching company data.
                  </span>
                  <button
                    onClick={async () => {
                      await loadCandidateReadiness();
                      setStage(2);
                    }}
                    className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 font-bold rounded-xl text-sm text-white transition shadow-lg shadow-cyan-900/30"
                  >
                    Proceed to Candidate Analysis →
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 2: CANDIDATE READINESS ANALYSIS (DIMENSION A) */}
            {stage === 2 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <span>Dimension A: Candidate Demonstrated Readiness</span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      What you have proven across coding challenges, Ava interviews, assessments, and resume evidence.
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-slate-400">Coverage:</span>
                    <span className="px-2.5 py-1 bg-cyan-950 text-cyan-300 border border-cyan-800 rounded-lg text-xs font-bold">
                      {candidateReadiness?.assessment_coverage_pct || 0}% Catalog Assessed
                    </span>
                  </div>
                </div>

                {/* Readiness Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl text-center">
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Coding Accepted</span>
                    <div className="text-2xl font-black text-emerald-400 mt-1">
                      {candidateReadiness?.coding_readiness?.total_accepted || 0}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {candidateReadiness?.coding_readiness?.acceptance_rate_pct || 0}% acceptance rate
                    </span>
                  </div>

                  <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl text-center">
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Ava Mock Score</span>
                    <div className="text-2xl font-black text-indigo-400 mt-1">
                      {candidateReadiness?.ava_interview_readiness?.avg_score_100 || "N/A"}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {candidateReadiness?.ava_interview_readiness?.completed_interviews || 0} rounds completed
                    </span>
                  </div>

                  <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl text-center">
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Resume Alignment</span>
                    <div className="text-2xl font-black text-amber-400 mt-1">
                      {candidateReadiness?.resume_readiness?.resume_score || "N/A"}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {candidateReadiness?.resume_readiness?.extracted_skills_count || 0} claimed skills
                    </span>
                  </div>

                  <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl text-center">
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Study Habit Streak</span>
                    <div className="text-2xl font-black text-cyan-400 mt-1">
                      {candidateReadiness?.preparation_behavior?.study_streak_days || 0} Days
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {candidateReadiness?.preparation_behavior?.total_study_minutes || 0} min total study
                    </span>
                  </div>
                </div>

                {/* Demonstrated vs Confirmed Weaknesses */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-800/40 border border-slate-700 rounded-xl">
                    <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">
                      Verified Strengths ({candidateReadiness?.skills?.demonstrated_strengths?.length || 0})
                    </h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {candidateReadiness?.skills?.demonstrated_strengths?.length ? (
                        candidateReadiness.skills.demonstrated_strengths.map((s) => (
                          <div key={s.skill_id} className="flex items-center justify-between p-2 bg-slate-900/60 rounded-lg text-xs">
                            <span className="font-semibold text-slate-200">{s.name}</span>
                            <span className="text-emerald-400 font-bold">{s.proficiency}%</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 italic">No high-proficiency verified skills recorded yet.</p>
                      )}
                    </div>
                  </div>

                  <div className="p-4 bg-slate-800/40 border border-slate-700 rounded-xl">
                    <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">
                      Confirmed Weaknesses ({candidateReadiness?.skills?.confirmed_weaknesses?.length || 0})
                    </h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {candidateReadiness?.skills?.confirmed_weaknesses?.length ? (
                        candidateReadiness.skills.confirmed_weaknesses.map((s) => (
                          <div key={s.skill_id} className="flex items-center justify-between p-2 bg-slate-900/60 rounded-lg text-xs">
                            <span className="font-semibold text-slate-200">{s.name}</span>
                            <span className="text-red-400 font-bold">{s.proficiency}%</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 italic">No low-score weaknesses confirmed. Unassessed topics will be evaluated.</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                  <button onClick={() => setStage(1)} className="text-xs text-slate-400 hover:text-white">
                    ← Back to Target Setup
                  </button>
                  <button
                    onClick={async () => {
                      await handleFetchCompanyIntelligence();
                      setStage(3);
                    }}
                    className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 font-bold rounded-xl text-sm text-white transition shadow-lg shadow-cyan-900/30"
                  >
                    View Company Research (Dimension B) →
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 3: COMPANY INTERVIEW INTELLIGENCE (DIMENSION B) */}
            {stage === 3 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <span>Dimension B: {companyIntelligence?.company_name || company} Interview Intelligence</span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Empirical patterns derived from verified candidate experiences and engineering sources ({companyIntelligence?.research_period || "Recent"}).
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-1 bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-lg text-xs font-bold">
                      Confidence: {Math.round((companyIntelligence?.confidence_score || 0.8) * 100)}%
                    </span>
                    <span className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded-lg text-xs">
                      {companyIntelligence?.source_count || 12} Verified Sources
                    </span>
                  </div>
                </div>

                {/* Interview Rounds Structure */}
                <div>
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                    Expected Interview Stages for {role} ({experienceLevel})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {companyIntelligence?.round_structure?.map((r) => (
                      <div key={r.round_number} className="p-3.5 bg-slate-800/60 border border-slate-700 rounded-xl space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-cyan-400">Round {r.round_number} • {r.duration_minutes}m</span>
                          <span className="text-[10px] font-semibold text-slate-400">{r.format}</span>
                        </div>
                        <div className="text-sm font-bold text-white">{r.name}</div>
                        <p className="text-xs text-slate-400">{r.focus}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Verified Candidate Sources */}
                {companyIntelligence?.verified_sources?.length > 0 && (
                  <div className="pt-2">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                      Recent Candidate Interview Reports & Excerpts
                    </h3>
                    <div className="space-y-3">
                      {companyIntelligence.verified_sources.map((src) => (
                        <div key={src.source_id} className="p-3.5 bg-slate-800/30 border border-slate-700/80 rounded-xl space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-white">{src.title}</span>
                            <span className="text-slate-400">{src.interview_date || src.publication_date}</span>
                          </div>
                          <p className="text-xs text-slate-300 italic font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                            "{src.excerpt}"
                          </p>
                          <div className="flex items-center gap-2 text-[11px] text-slate-400">
                            <span>Reported Topics:</span>
                            {src.reported_topics?.map((t, idx) => (
                              <span key={idx} className="px-1.5 py-0.5 bg-slate-800 text-cyan-300 rounded text-[10px]">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                  <button onClick={() => setStage(2)} className="text-xs text-slate-400 hover:text-white">
                    ← Back to Candidate Readiness
                  </button>
                  <button
                    onClick={async () => {
                      await handleComputeGaps();
                      setStage(4);
                    }}
                    className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 font-bold rounded-xl text-sm text-white transition shadow-lg shadow-cyan-900/30"
                  >
                    View Gap Analysis →
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 4: GAP ANALYSIS & PREVIEW */}
            {stage === 4 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-white">Stage 4: Company-Candidate Gap Matching</h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Matching {company}'s reported competencies against your demonstrated readiness to identify high-priority target skills.
                  </p>
                </div>

                {/* Priority Summary */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 bg-red-950/30 border border-red-900/60 rounded-xl text-center">
                    <span className="text-xs uppercase font-bold text-red-300">High-Priority Weaknesses</span>
                    <div className="text-2xl font-black text-red-400 mt-1">
                      {gapAnalysis?.priority_summary?.high_priority_weakness_count || 0}
                    </div>
                    <span className="text-[11px] text-red-300/80">Crucial for {company} rounds</span>
                  </div>

                  <div className="p-4 bg-amber-950/30 border border-amber-900/60 rounded-xl text-center">
                    <span className="text-xs uppercase font-bold text-amber-300">Developing Competencies</span>
                    <div className="text-2xl font-black text-amber-400 mt-1">
                      {gapAnalysis?.priority_summary?.developing_count || 0}
                    </div>
                    <span className="text-[11px] text-amber-300/80">Need targeted revision</span>
                  </div>

                  <div className="p-4 bg-cyan-950/30 border border-cyan-900/60 rounded-xl text-center">
                    <span className="text-xs uppercase font-bold text-cyan-300">Unassessed Priority Skills</span>
                    <div className="text-2xl font-black text-cyan-400 mt-1">
                      {gapAnalysis?.priority_summary?.unassessed_company_skills_count || 0}
                    </div>
                    <span className="text-[11px] text-cyan-300/80">To be validated in roadmap</span>
                  </div>
                </div>

                {/* Top Competency Allocations */}
                <div>
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                    Top Competency Preparation Priorities
                  </h3>
                  <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                    {gapAnalysis?.gaps?.slice(0, 8).map((gap) => (
                      <div key={gap.skill_id} className="p-3 bg-slate-800/50 border border-slate-700/80 rounded-xl flex items-center justify-between">
                        <div>
                          <div className="font-bold text-sm text-white flex items-center gap-2">
                            <span>{gap.name}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              gap.classification_tier === "HIGH_PRIORITY_WEAKNESS"
                                ? "bg-red-950 text-red-300 border border-red-800"
                                : gap.classification_tier === "DEVELOPING"
                                ? "bg-amber-950 text-amber-300 border border-amber-800"
                                : "bg-slate-800 text-slate-300"
                            }`}>
                              {gap.classification_tier.replace(/_/g, " ")}
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 mt-0.5">
                            Company Relevance: {Math.round(gap.company_relevance * 100)}% • Current: {gap.candidate_proficiency}% • Rec. Study: {gap.recommended_minutes}m
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-black text-cyan-400">{gap.priority_score}</span>
                          <span className="text-[10px] text-slate-500 block">Priority Score</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                  <button onClick={() => setStage(3)} className="text-xs text-slate-400 hover:text-white">
                    ← Back to Company Research
                  </button>
                  <button
                    onClick={handleGenerateFullPlan}
                    disabled={loading}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 font-bold rounded-xl text-sm text-white transition shadow-lg shadow-emerald-900/30 flex items-center space-x-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Generating Personalized Roadmap...</span>
                      </>
                    ) : (
                      <span>Generate Personalized Plan →</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 5: PERSONALIZED DAILY ROADMAP & SCHEDULE */}
            {stage === 5 && (
              <div className="space-y-6">
                
                {/* Active Plan Overview Card */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Active Strategy</span>
                    <h2 className="text-xl font-black text-white mt-0.5">
                      {activePlan?.company_name || company} • {activePlan?.target_role || role}
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      {activePlan?.total_days || 30} Days Total • {activePlan?.daily_minutes || dailyMinutes} min/day ({activePlan?.total_study_hours || 30}h study budget) • Target Date: {activePlan?.target_date}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleGenerateFullPlan}
                      disabled={loading}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 rounded-xl transition border border-slate-700"
                    >
                      🔄 Rebalance Schedule
                    </button>
                    <button
                      onClick={() => handleLaunchAvaMock("Final Loop Simulation", "Full comprehensive final round interview simulation")}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white rounded-xl transition shadow-lg shadow-indigo-900/40"
                    >
                      🎙️ Launch Ava Mock
                    </button>
                  </div>
                </div>

                {/* Day Filter Pills */}
                {activePlan?.roadmap?.schedule && (
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
                    <button
                      onClick={() => setActiveDayFilter("ALL")}
                      className={`px-3 py-1 rounded-lg text-xs font-bold whitespace-nowrap transition ${
                        activeDayFilter === "ALL" ? "bg-cyan-600 text-white" : "bg-slate-900 text-slate-400 hover:text-white"
                      }`}
                    >
                      All Days ({activePlan.roadmap.total_activities})
                    </button>
                    {Object.keys(activePlan.roadmap.schedule).map((d) => (
                      <button
                        key={d}
                        onClick={() => setActiveDayFilter(Number(d))}
                        className={`px-3 py-1 rounded-lg text-xs font-bold whitespace-nowrap transition ${
                          activeDayFilter === Number(d) ? "bg-cyan-600 text-white" : "bg-slate-900 text-slate-400 hover:text-white"
                        }`}
                      >
                        Day {d} ({activePlan.roadmap.schedule[d].length})
                      </button>
                    ))}
                  </div>
                )}

                {/* Scheduled Daily Activities */}
                <div className="space-y-4">
                  {activePlan?.roadmap?.schedule && Object.keys(activePlan.roadmap.schedule).map((d) => {
                    const dayNum = Number(d);
                    if (activeDayFilter !== "ALL" && activeDayFilter !== dayNum) return null;
                    const dayActs = activePlan.roadmap.schedule[d];

                    return (
                      <div key={d} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                          <span className="text-xs font-black text-cyan-400 uppercase tracking-wider">
                            Day {d} Schedule
                          </span>
                          <span className="text-xs text-slate-500">
                            {dayActs.reduce((acc, curr) => acc + (curr.estimated_minutes || 30), 0)} min allocated
                          </span>
                        </div>

                        <div className="space-y-3">
                          {dayActs.map((act) => (
                            <div key={act.id} className="p-4 bg-slate-800/50 border border-slate-700/80 rounded-xl space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    act.activity_type === "MOCK_INTERVIEW"
                                      ? "bg-indigo-950 text-indigo-300 border border-indigo-800"
                                      : act.activity_type === "CODING_CHALLENGE"
                                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                      : "bg-slate-800 text-slate-300"
                                  }`}>
                                    {act.activity_type.replace(/_/g, " ")}
                                  </span>
                                  <span className="text-xs text-slate-400 font-semibold">{act.estimated_minutes} min</span>
                                </div>
                                <span className="text-[11px] font-bold text-amber-400">
                                  Priority {act.priority || 80}
                                </span>
                              </div>

                              <div className="text-sm font-bold text-white">{act.title}</div>
                              <p className="text-xs text-slate-400">{act.learning_objective || act.description}</p>

                              <div className="flex items-center justify-between pt-2 border-t border-slate-700/40 text-xs">
                                <span className="text-slate-500 text-[11px]">
                                  Criteria: {act.completion_criteria || "Complete practice drill"}
                                </span>
                                {act.activity_type === "MOCK_INTERVIEW" ? (
                                  <button
                                    onClick={() => handleLaunchAvaMock(act.title, act.learning_objective)}
                                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold"
                                  >
                                    🎙️ Start Mock
                                  </button>
                                ) : (
                                  <span className="text-slate-400 text-xs font-semibold">
                                    Status: {act.status}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Grounded Question Bank */}
                {activePlan?.tailored_question_bank?.length > 0 && (
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                    <h3 className="text-md font-bold text-white flex items-center space-x-2">
                      <span>Company Question Bank & Rubrics ({activePlan.tailored_question_bank.length})</span>
                    </h3>
                    <div className="space-y-3">
                      {activePlan.tailored_question_bank.map((q) => (
                        <div key={q.question_id} className="p-4 bg-slate-800/40 border border-slate-700 rounded-xl space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-cyan-400">{q.interview_round}</span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                              {q.source_classification}
                            </span>
                          </div>
                          <p className="text-sm font-semibold text-slate-100">{q.question_text}</p>
                          {q.suggested_answer_framework && (
                            <div className="text-xs text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                              <span className="font-bold text-slate-300 block mb-0.5">Evaluation Rubric / Framework:</span>
                              {q.suggested_answer_framework}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

          </div>
        )}

        {/* MODE B: RAW JD INGESTION (LEGACY FEATURE PRESERVED) */}
        {activeMode === "jd_ingest" && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-white">Target Job Description Ingestion</h2>
            <p className="text-xs text-slate-400">
              Paste arbitrary job descriptions to extract atomic requirements, evaluate keyword stuffing vs proof, and calculate skill gaps.
            </p>
            <form onSubmit={handleLegacyIngest} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Target Role / Job Title"
                  value={legacyJobTitle}
                  onChange={(e) => setLegacyJobTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm"
                />
                <input
                  type="text"
                  placeholder="Company Name"
                  value={legacyCompany}
                  onChange={(e) => setLegacyCompany(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm"
                />
              </div>
              <textarea
                rows={6}
                placeholder="Paste the full job description text here..."
                value={legacyRawText}
                onChange={(e) => setLegacyRawText(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-xs font-mono"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-xl text-sm transition"
                >
                  {loading ? "Analyzing..." : "Analyze Job Description"}
                </button>
              </div>
            </form>

            {legacyAnalysis && (
              <div className="pt-4 border-t border-slate-800 text-xs text-slate-300">
                <div className="font-bold text-sm text-cyan-400 mb-2">Analysis Complete!</div>
                <div>Overall Match: {legacyAnalysis.gap_analysis?.overall_match_percentage}%</div>
                <div>Extracted Requirements: {legacyAnalysis.requirements?.length || 0}</div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
