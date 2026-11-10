import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const STORAGE_KEY = "prepfly_adaptive_diagnostic_id";

const CANONICAL_ROLES = [
  { id: "software_development_engineer", label: "Software Engineer (SDE / SWE)", category: "Core Software" },
  { id: "ai_ml_engineer", label: "AI/ML Engineer", category: "Artificial Intelligence" },
  { id: "backend_developer", label: "Backend Developer", category: "Cloud & APIs" },
  { id: "frontend_developer", label: "Frontend Developer", category: "Web & UI" },
  { id: "full_stack_developer", label: "Full Stack Developer", category: "Full Stack" },
  { id: "data_scientist", label: "Data Scientist", category: "Analytics & Models" },
  { id: "data_engineer", label: "Data Engineer", category: "Big Data & Pipelines" },
  { id: "devops_engineer", label: "DevOps Engineer", category: "Infrastructure & CI/CD" },
];

export default function DiagnosticAssessmentModal({
  onClose,
  onCompleted,
  targetRole = "",
  experienceLevel = "Fresher"
}) {
  // Assessment Flow States: "CONFIG" | "STARTING" | "RUNNING" | "EVALUATING" | "COMPLETED"
  const [stage, setStage] = useState("CONFIG");
  const [error, setError] = useState("");

  // Configuration Fields
  const [selectedRole, setSelectedRole] = useState(targetRole || "ai_ml_engineer");
  const [customRole, setCustomRole] = useState("");
  const [company, setCompany] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [expLevel, setExpLevel] = useState(experienceLevel || "Fresher");

  // In-Session Assessment State
  const [assessmentId, setAssessmentId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [turnIndex, setTurnIndex] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [candidateAnswer, setCandidateAnswer] = useState("");
  const [submittingTurn, setSubmittingTurn] = useState(false);
  const [lastTurnFeedback, setLastTurnFeedback] = useState(null);

  // Final Evaluation Results
  const [finalScorecard, setFinalScorecard] = useState(null);

  // Check for existing in-progress session on mount
  useEffect(() => {
    checkActiveSession();
  }, []);

  const checkActiveSession = async () => {
    const savedId = sessionStorage.getItem(STORAGE_KEY);
    if (!savedId) {
      if (targetRole) {
        // Automatically start if targetRole prop is explicitly provided
        startSessionWithParams(targetRole, experienceLevel);
      }
      return;
    }

    try {
      setStage("STARTING");
      const res = await intelligenceAPI.resumeAdaptiveSession(savedId);
      if (res && res.assessment) {
        const ass = res.assessment;
        if (ass.status === "COMPLETED") {
          sessionStorage.removeItem(STORAGE_KEY);
          setStage("CONFIG");
        } else {
          setAssessmentId(ass.assessment_id);
          setCurrentQuestion(ass.current_question);
          setTurnIndex((ass.answered || 0) + 1);
          setTotalQuestions(ass.total || 10);
          setCandidateAnswer("");
          setStage("RUNNING");
        }
      } else {
        sessionStorage.removeItem(STORAGE_KEY);
        setStage("CONFIG");
      }
    } catch (_) {
      sessionStorage.removeItem(STORAGE_KEY);
      setStage("CONFIG");
    }
  };

  const startSessionWithParams = async (roleToUse, expToUse, jdText = "", targetComp = "") => {
    setStage("STARTING");
    setError("");
    try {
      const payload = {
        target_role: roleToUse === "custom" ? customRole : roleToUse,
        experience_level: expToUse,
        job_description: jdText.trim() || undefined,
        company: targetComp.trim() || undefined,
        question_budget: 10
      };

      const res = await intelligenceAPI.startAdaptiveDiagnostic(payload);
      const session = res.assessment;
      setAssessmentId(session.assessment_id);
      setCurrentQuestion(session.current_question || session.first_question);
      setTurnIndex(1);
      setTotalQuestions(session.total_questions || session.question_budget || session.progress?.total || 10);
      setCandidateAnswer("");
      sessionStorage.setItem(STORAGE_KEY, session.assessment_id);
      setStage("RUNNING");
    } catch (err) {
      setError(err.message || "Failed to launch adaptive diagnostic.");
      setStage("CONFIG");
    }
  };

  const handleStartFromConfig = () => {
    const role = selectedRole === "custom" ? customRole.trim() : selectedRole;
    if (!role) {
      setError("Please specify your target engineering role.");
      return;
    }
    startSessionWithParams(role, expLevel, jobDescription, company);
  };

  const handleSubmitTurn = async () => {
    if (!candidateAnswer.trim()) {
      setError("Please provide your technical response before submitting.");
      return;
    }
    if (!assessmentId) return;

    setSubmittingTurn(true);
    setError("");
    setLastTurnFeedback(null);

    try {
      const idempotencyKey = `${assessmentId}_turn_${turnIndex}_${Date.now()}`;
      const res = await intelligenceAPI.submitAdaptiveTurn(assessmentId, {
        turn_index: turnIndex,
        answer: candidateAnswer.trim(),
        idempotency_key: idempotencyKey
      });

      const outcome = res.result;

      if (outcome.status === "COMPLETED") {
        sessionStorage.removeItem(STORAGE_KEY);
        setFinalScorecard(outcome);
        setStage("COMPLETED");
      } else {
        // Store turn feedback briefly & advance to next question
        setLastTurnFeedback(outcome.evaluation);
        setCurrentQuestion(outcome.next_question);
        setTurnIndex(outcome.turn_index);
        setCandidateAnswer("");
        setStage("RUNNING");
      }
    } catch (err) {
      setError(err.message || "Failed to submit turn. Please retry.");
    } finally {
      setSubmittingTurn(false);
    }
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!submittingTurn) {
        handleSubmitTurn();
      }
    }
  };

  const handleFinishModal = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    if (onCompleted) {
      onCompleted(finalScorecard);
    }
    onClose();
  };

  return (
    <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="modal-card intelligence-root bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl relative text-slate-100 my-auto">
        {/* Header Bar */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
              CAT
            </div>
            <div>
              <span className="text-xs font-semibold tracking-wider uppercase text-cyan-400">
                Evidence-Based Diagnostic Engine
              </span>
              <h2 className="text-lg font-bold text-white mt-0.5">
                {stage === "CONFIG" && "Configure Role & Target Parameters"}
                {stage === "STARTING" && "Synthesizing Adaptive Assessment..."}
                {stage === "RUNNING" && `Adaptive Assessment — Question ${turnIndex} of ${totalQuestions}`}
                {stage === "COMPLETED" && "Calibrated Competency & Readiness Profile"}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={stage === "COMPLETED" ? handleFinishModal : onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg text-sm transition-colors"
            title="Close"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/50 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-center justify-between">
            <span>{error}</span>
            <button type="button" onClick={() => setError("")} className="text-red-400 font-bold ml-2">×</button>
          </div>
        )}

        {/* ── STAGE 1: CONFIGURATION SCREEN ─────────────────────────────────── */}
        {stage === "CONFIG" && (
          <div className="space-y-5">
            <p className="text-xs text-slate-300 leading-relaxed">
              PrepFly dynamically tailors assessment items to your exact engineering target.
              Select your career goal below or customize with a specific target company and job description.
            </p>

            {/* Target Role Grid */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                1. Target Engineering Role:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {CANONICAL_ROLES.map((r) => {
                  const isSelected = selectedRole === r.id;
                  return (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setSelectedRole(r.id)}
                      className={`text-left p-3 rounded-xl border text-xs transition-all ${
                        isSelected
                          ? "bg-cyan-950/40 border-cyan-500 text-white shadow-sm shadow-cyan-500/20"
                          : "bg-slate-800/40 border-slate-700/60 text-slate-300 hover:bg-slate-800/80 hover:border-slate-600"
                      }`}
                    >
                      <div className="font-semibold text-white">{r.label}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{r.category}</div>
                    </button>
                  );
                })}
              </div>

              {/* Custom Role Option */}
              <div className="mt-2.5">
                <button
                  type="button"
                  onClick={() => setSelectedRole("custom")}
                  className={`text-left w-full p-2.5 rounded-xl border text-xs transition-all ${
                    selectedRole === "custom"
                      ? "bg-cyan-950/40 border-cyan-500 text-white"
                      : "bg-slate-800/30 border-slate-700/60 text-slate-400 hover:bg-slate-800/60"
                  }`}
                >
                  <span className="font-semibold text-white">+ Custom or Specialized Role</span>
                </button>
                {selectedRole === "custom" && (
                  <input
                    type="text"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    placeholder="e.g. Computer Vision Engineer, MLOps Specialist, Embedded Firmware..."
                    className="mt-2 w-full bg-slate-950 border border-cyan-500/80 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none"
                  />
                )}
              </div>
            </div>

            {/* Experience Level & Target Company */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  2. Experience Level:
                </label>
                <select
                  value={expLevel}
                  onChange={(e) => setExpLevel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="Fresher">Fresher (0-1 yrs)</option>
                  <option value="Junior">Junior (1-3 yrs)</option>
                  <option value="Mid-Level">Mid-Level (3-5 yrs)</option>
                  <option value="Senior">Senior (5+ yrs)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  3. Target Company (Optional):
                </label>
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Google, Meta, Snowflake, Stripe..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Optional Job Description */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                4. Job Description / Requirements (Optional):
              </label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste requirements, preferred technologies, or job spec to extract exact skill weights..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Start Button */}
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleStartFromConfig}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-6 py-2.5 rounded-xl text-xs sm:text-sm transition-all shadow-md shadow-cyan-500/20"
              >
                Launch 10-Question Adaptive Diagnostic &rarr;
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE 2: LOADING / STARTING SCREEN ───────────────────────────── */}
        {stage === "STARTING" && (
          <div className="py-12 text-center text-slate-200">
            <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="text-base font-bold text-white mb-1.5">Calibrating Diagnostic Engine</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Parsing skill taxonomy, calculating requirement weights, and generating Question 1...
            </p>
          </div>
        )}

        {/* ── STAGE 3: TURN-BY-TURN ASSESSMENT COCKPIT ─────────────────────── */}
        {stage === "RUNNING" && currentQuestion && (
          <div className="space-y-4">
            {/* Top Progress & Metas */}
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold text-slate-200">
                Question {turnIndex} of {totalQuestions}
              </span>
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-300 text-[11px] font-semibold">
                  {currentQuestion.skill_name || currentQuestion.skill_id}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  currentQuestion.difficulty === "HARD" || currentQuestion.difficulty === "Advanced"
                    ? "bg-purple-950 text-purple-300 border border-purple-800"
                    : currentQuestion.difficulty === "MEDIUM" || currentQuestion.difficulty === "Intermediate"
                    ? "bg-amber-950 text-amber-300 border border-amber-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                }`}>
                  {currentQuestion.difficulty}
                </span>
              </div>
            </div>

            {/* Continuous Progress Bar */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-cyan-500 h-full transition-all duration-300"
                style={{ width: `${(turnIndex / totalQuestions) * 100}%` }}
              />
            </div>

            {/* Turn Feedback Toast (if available from previous turn) */}
            {lastTurnFeedback && (
              <div className="p-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-xs text-slate-300 flex items-center justify-between animate-fadeIn">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span>
                    {lastTurnFeedback.evaluation_status === "failed"
                      ? "Previous response recorded (evaluation pending)."
                      : "Previous question evaluated. Calibrated score recorded."}
                  </span>
                </div>
                <span className="font-bold text-cyan-400">
                  {lastTurnFeedback.evaluation_status === "failed" || lastTurnFeedback.score == null
                    ? "Pending"
                    : `${lastTurnFeedback.score}%`}
                </span>
              </div>
            )}

            {/* Question Text Box */}
            <div className="bg-slate-800/50 border border-slate-700/70 rounded-xl p-4 sm:p-5">
              <p className="text-slate-100 font-medium text-sm sm:text-base leading-relaxed whitespace-pre-line">
                {currentQuestion.question_text}
              </p>
            </div>

            {/* Candidate Response Area */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Your Technical Explanation / Code / Invariants:
                </label>
                <span className="text-[11px] text-slate-500">
                  {candidateAnswer.length} characters • Ctrl+Enter to submit
                </span>
              </div>
              <textarea
                value={candidateAnswer}
                onChange={(e) => setCandidateAnswer(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="State your conceptual principles, algorithms, asymptotic time/space complexity (Big-O), trade-offs, and edge case guards..."
                rows={7}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3.5 text-xs sm:text-sm text-slate-100 font-mono placeholder:font-sans placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-500">
                Turn {turnIndex} evaluation updates candidate skill state immediately.
              </span>
              <button
                type="button"
                disabled={submittingTurn}
                onClick={handleSubmitTurn}
                className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold px-6 py-2.5 rounded-xl text-xs sm:text-sm transition-all shadow-md shadow-cyan-500/20 flex items-center space-x-2"
              >
                {submittingTurn ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Grading with Rubric & Adapting...</span>
                  </>
                ) : (
                  <span>Submit Answer & Adapt &rarr;</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE 4: COMPLETED SCORECARD & READINESS SCREEN ─────────────── */}
        {stage === "COMPLETED" && finalScorecard && (
          <div className="space-y-6">
            {/* Scorecard Hero Banner */}
            <div className="bg-gradient-to-r from-cyan-950/40 via-slate-800/60 to-slate-900 border border-cyan-800/40 rounded-xl p-5 text-center">
              <span className="text-xs font-semibold uppercase text-cyan-400 tracking-wider">
                Demonstrated Competency
              </span>
              <div className="text-4xl font-extrabold text-white mt-1">
                {finalScorecard.overall_score !== null && finalScorecard.overall_score !== undefined
                  ? `${finalScorecard.overall_score}%`
                  : "Pending"}
              </div>
              <p className="text-xs text-slate-300 mt-2 max-w-lg mx-auto leading-relaxed">
                {finalScorecard.summary || "Your initial baseline is calibrated across all evaluated adaptive items."}
              </p>
            </div>

            {/* Metas Row: Confidence, Curriculum Coverage & Assessment Completion */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 bg-slate-800/40 border border-slate-700/60 rounded-xl text-center">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                  Measurement Confidence
                </span>
                <span className="text-lg font-bold text-white mt-0.5 block">
                  {Math.round((finalScorecard.confidence ?? 0) * 100)}%
                </span>
                <span className="text-[10px] text-slate-500">Evidence & topic diversity</span>
              </div>
              <div className="p-3.5 bg-slate-800/40 border border-slate-700/60 rounded-xl text-center">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                  Curriculum Coverage
                </span>
                <span className="text-lg font-bold text-white mt-0.5 block">
                  {finalScorecard.coverage_pct ?? 0}%
                </span>
                <span className="text-[10px] text-slate-500">
                  {finalScorecard.distinct_skills_count ?? 0} distinct skills weighted
                </span>
              </div>
              <div className="p-3.5 bg-slate-800/40 border border-slate-700/60 rounded-xl text-center">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                  Assessment Completion
                </span>
                <span className="text-lg font-bold text-white mt-0.5 block">
                  {finalScorecard.completion_pct ??
                    Math.round(
                      ((finalScorecard.progress?.answered ?? 0) /
                        Math.max(1, finalScorecard.progress?.total ?? 1)) *
                        100
                    )}%
                </span>
                <span className="text-[10px] text-slate-500">
                  {finalScorecard.evaluated_count ?? finalScorecard.progress?.answered ?? 0}/{finalScorecard.progress?.total ?? totalQuestions} valid items
                </span>
              </div>
            </div>

            {/* Action to Finish */}
            <div className="flex justify-end pt-3">
              <button
                type="button"
                onClick={handleFinishModal}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-6 py-2.5 rounded-xl text-xs sm:text-sm transition-all shadow-md shadow-cyan-500/20"
              >
                View Personalized PrepMap &rarr;
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
