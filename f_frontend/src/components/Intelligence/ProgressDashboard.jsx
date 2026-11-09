import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

export default function ProgressDashboard({ onNavigateTab }) {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [skills, setSkills] = useState([]);
  const [insights, setInsights] = useState([]);
  const [weaknesses, setWeaknesses] = useState([]);
  const [improvementReport, setImprovementReport] = useState(null);
  const [readinessProvenance, setReadinessProvenance] = useState(null);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState("ALL");
  const [expandedPillar, setExpandedPillar] = useState(null);
  const [showProvenanceModal, setShowProvenanceModal] = useState(false);
  const [showProjectProbeModal, setShowProjectProbeModal] = useState(false);
  const [projectTitle, setProjectTitle] = useState("");
  const [projectTech, setProjectTech] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [probingQuestions, setProbingQuestions] = useState([]);
  const [probeAnswers, setProbeAnswers] = useState({});
  const [evaluatingDefense, setEvaluatingDefense] = useState(false);
  const [defenseResults, setDefenseResults] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    loadProgressData();
  }, []);

  const loadProgressData = async () => {
    setLoading(true);
    setError("");
    try {
      const [dashRes, skillRes, insightRes, weakRes, improveRes, provRes] = await Promise.allSettled([
        intelligenceAPI.getProgressDashboard(),
        intelligenceAPI.getSkillProfile(),
        intelligenceAPI.getCoachingInsights(),
        intelligenceAPI.getVerifiedWeaknesses(),
        intelligenceAPI.getImprovementAnalytics(),
        intelligenceAPI.getReadinessProvenance()
      ]);

      if (dashRes.status === "fulfilled") {
        setDashboard(dashRes.value.dashboard);
      }
      if (skillRes.status === "fulfilled") {
        setSkills(skillRes.value.skill_profiles || []);
      }
      if (insightRes.status === "fulfilled") {
        setInsights(insightRes.value.insights || []);
      }
      if (weakRes.status === "fulfilled") {
        setWeaknesses(weakRes.value.weaknesses || []);
      }
      if (improveRes.status === "fulfilled" && improveRes.value?.data) {
        setImprovementReport(improveRes.value.data);
      }
      if (provRes.status === "fulfilled") {
        setReadinessProvenance(provRes.value);
      }
    } catch (err) {
      setError(err.message || "Failed to load progress analytics.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateProjectProbes = async (e) => {
    e.preventDefault();
    if (!projectTitle.trim()) return;
    try {
      const res = await intelligenceAPI.probeProject({
        title: projectTitle,
        technologies: projectTech.split(",").map((t) => t.trim()).filter(Boolean),
        description: projectDesc
      });
      setProbingQuestions(res.questions || []);
      setDefenseResults([]);
    } catch (err) {
      alert("Failed to generate probing questions: " + err.message);
    }
  };

  const handleEvaluateDefense = async (question, answer) => {
    if (!answer.trim()) return;
    setEvaluatingDefense(true);
    try {
      const res = await intelligenceAPI.evaluateProjectDefense({
        project_title: projectTitle,
        skill_id: "sys_ml_system_design",
        question_text: question.question_text,
        response: answer
      });
      setDefenseResults((prev) => [...prev, res.evaluation]);
      loadProgressData();
    } catch (err) {
      alert("Defense evaluation error: " + err.message);
    } finally {
      setEvaluatingDefense(false);
    }
  };

  const getConfidenceBadge = (level) => {
    const map = {
      VERIFIED: "bg-emerald-950 text-emerald-300 border-emerald-800",
      HIGH: "bg-cyan-950 text-cyan-300 border-cyan-800",
      MEDIUM: "bg-blue-950 text-blue-300 border-blue-800",
      LOW: "bg-slate-800 text-slate-400 border-slate-700"
    };
    return map[level] || map.LOW;
  };

  const getTrendBadge = (trend) => {
    if (trend === "IMPROVING") {
      return <span className="text-emerald-400 font-semibold text-xs">↑ Improving</span>;
    }
    if (trend === "REGRESSING") {
      return <span className="text-red-400 font-semibold text-xs">↓ Needs Review</span>;
    }
    return <span className="text-slate-400 text-xs">→ Stable</span>;
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-300">
        <div className="w-10 h-10 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Calculating multi-source evidence-based readiness & grounded insights...
      </div>
    );
  }

  // Derive evidence-based values
  const provReadiness = readinessProvenance?.readiness;
  const pillars = readinessProvenance?.pillars || {};
  const evidenceHistory = readinessProvenance?.evidence_history || [];

  const overallReadinessScore = provReadiness?.overall_score ?? dashboard?.overall_readiness ?? 0;
  const readinessStatus = provReadiness?.readiness_status || (overallReadinessScore >= 75 ? "ESTABLISHED" : "PROVISIONAL");
  const formulaExplanation = provReadiness?.formula_breakdown || "Calibrated across verified assessment scores, coding accuracy, and task complexity.";
  const unassessedMandatory = provReadiness?.unassessed_mandatory_skills || [];
  const coverageRatio = provReadiness?.coverage_ratio || 0.5;

  const metrics = dashboard?.study_metrics || {};
  const baseline = dashboard?.baseline_comparison || {};
  const categories = ["ALL", "Data Structures and Algorithms", "System Design", "Computer Science Fundamentals", "Interview Skills"];

  const filteredSkills = skills.filter(
    (s) => activeCategoryFilter === "ALL" || s.category === activeCategoryFilter
  );

  return (
    <div id="page-analytics" className="page active" role="tabpanel">
      <div className="container intelligence-root space-y-6 text-slate-100 pb-12">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                PrepFly Intelligence
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                Evidence-Based Scoring Engine
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
              Candidate Readiness & Skill Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Strictly decoupled proficiency, confidence, and coverage calibrated from real assessments, coding challenges, and mock interviews.
            </p>
          </div>

          <div className="flex items-center space-x-2 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setShowProvenanceModal(true)}
              className="bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-700/60 text-cyan-300 text-xs font-semibold px-3.5 py-2 rounded-xl transition-all shadow-sm"
            >
              📜 View Evidence Provenance ({evidenceHistory.length})
            </button>
            <button
              type="button"
              onClick={() => setShowProjectProbeModal(true)}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold px-3.5 py-2 rounded-xl transition-all"
            >
              🛡️ Verify Project Defense
            </button>
            <button
              type="button"
              onClick={loadProgressData}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold px-3 py-2 rounded-xl transition-all"
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Statistical Trend Detection Banner */}
        {improvementReport?.trend && (
          <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
            improvementReport.trend.status === "Improving"
              ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-200"
              : improvementReport.trend.status === "Declining"
              ? "bg-rose-950/40 border-rose-800/80 text-rose-200"
              : "bg-slate-900 border-slate-800 text-slate-300"
          }`}>
            <div className="flex items-center space-x-3">
              <span className="text-xl">
                {improvementReport.trend.status === "Improving" ? "📈" : improvementReport.trend.status === "Declining" ? "📉" : "📊"}
              </span>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-sm uppercase tracking-wide">
                    Statistical Trend: {improvementReport.trend.status}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                    {improvementReport.trend.confidence} CONFIDENCE
                  </span>
                </div>
                <p className="text-xs opacity-80 mt-0.5">
                  {improvementReport.trend.status === "Improving" && `Statistically significant gain of +${improvementReport.trend.delta_points} points above your verified baseline.`}
                  {improvementReport.trend.status === "Stable" && "Performance variance is within normal margins (+/- 5%). Progress is holding stable."}
                  {improvementReport.trend.status === "Declining" && `Recent evaluations indicate a ${improvementReport.trend.delta_points} point decline. Focused drills recommended.`}
                  {improvementReport.trend.status === "Insufficient Evidence" && "Gathering evaluation checkpoints across coding, Ava mock, and diagnostic assessments."}
                </p>
              </div>
            </div>

            <div className="text-right whitespace-nowrap self-start sm:self-auto">
              <span className="text-xs font-mono font-bold">
                Slope: {improvementReport.trend.slope > 0 ? `+${improvementReport.trend.slope}` : improvementReport.trend.slope}
              </span>
            </div>
          </div>
        )}

        {/* Top Readiness & Provenance Hero Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Overall Role Readiness with Provisional vs Established Flag */}
          <div className="bg-gradient-to-br from-slate-900 via-slate-800/80 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider text-slate-400">
                <span>Overall Role Readiness</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  readinessStatus === "ESTABLISHED"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : "bg-amber-950 text-amber-300 border-amber-800"
                }`}>
                  {readinessStatus === "ESTABLISHED" ? "✓ ESTABLISHED" : "⚠ PROVISIONAL"}
                </span>
              </div>

              <div className="flex items-baseline space-x-3 mt-4">
                <span className="text-5xl font-extrabold text-white">{overallReadinessScore}%</span>
                <span className="text-xs text-slate-400">Target Role: {provReadiness?.target_role || dashboard?.target_role || "Software Engineer"}</span>
              </div>

              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden mt-3">
                <div
                  className={`h-full transition-all duration-700 ${
                    readinessStatus === "ESTABLISHED"
                      ? "bg-gradient-to-r from-cyan-500 to-emerald-400"
                      : "bg-gradient-to-r from-amber-500 to-orange-400"
                  }`}
                  style={{ width: `${Math.max(4, overallReadinessScore)}%` }}
                />
              </div>

              {/* Status Explanation & Warning */}
              <p className="text-xs text-slate-300 mt-3 leading-relaxed">
                {provReadiness?.status_explanation || "Calibrated against verified multi-source technical assessments."}
              </p>

              {unassessedMandatory.length > 0 && (
                <div className="mt-3 p-2.5 bg-amber-950/40 border border-amber-800/60 rounded-xl text-[11px] text-amber-200">
                  <span className="font-bold">Missing Mandatory Assessments: </span>
                  {unassessedMandatory.map((m) => m.skill_name).join(", ")}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-800/80 mt-4 flex items-center justify-between text-xs text-slate-400">
              <span>Evidence Coverage:</span>
              <span className="font-bold text-white">
                {Math.round(coverageRatio * 100)}% ({provReadiness?.assessed_skills_count || 0}/{provReadiness?.total_required_skills_count || 12} skills)
              </span>
            </div>
          </div>

          {/* Diagnostic Baseline Comparison */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider text-slate-400">
                <span>Diagnostic Baseline vs Latest</span>
                {baseline.has_baseline && (
                  <span className="text-emerald-400 font-bold">
                    {baseline.overall_delta >= 0 ? `+${baseline.overall_delta}%` : `${baseline.overall_delta}%`}
                  </span>
                )}
              </div>

              {baseline.has_baseline ? (
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Initial Diagnostic:</span>
                    <span className="font-bold text-slate-200">{baseline.initial_score}%</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Current Average Proficiency:</span>
                    <span className="font-bold text-cyan-400">{baseline.current_score}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-400 h-full transition-all duration-500"
                      style={{ width: `${Math.max(4, baseline.current_score || 0)}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 pt-1">
                    Calibrated across multiple evaluations since your initial assessment on{" "}
                    {baseline.initial_date ? new Date(baseline.initial_date).toLocaleDateString() : "baseline"}.
                  </p>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-400 space-y-2">
                  <p>No diagnostic baseline recorded yet.</p>
                  <button
                    type="button"
                    onClick={() => onNavigateTab && onNavigateTab("roadmap")}
                    className="text-cyan-400 hover:underline font-semibold"
                  >
                    Take Diagnostic Assessment &rarr;
                  </button>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
              <span>Completed Study Minutes:</span>
              <span className="font-bold text-white">{metrics.total_minutes_completed || 0}m</span>
            </div>
          </div>

          {/* Mathematical Provenance & Formula Breakdown */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Mathematical Provenance
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {formulaExplanation}
              </p>
              <div className="mt-4 space-y-2 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Mandatory Skills Weight:</span>
                  <span className="font-bold text-white">1.5x</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Preferred Skills Weight:</span>
                  <span className="font-bold text-white">1.0x</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Supporting Skills Weight:</span>
                  <span className="font-bold text-white">0.7x</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Recency Half-Life:</span>
                  <span className="font-bold text-white">90 Days</span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
              <span>Unassessed Penalty:</span>
              <span className="font-bold text-amber-400">
                {unassessedMandatory.length > 0 ? "Active (Coverage Gated)" : "None (100% Core Assessed)"}
              </span>
            </div>
          </div>
        </div>

        {/* 4 Competency Pillars with Decoupled Proficiency, Confidence & Coverage */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-base font-bold text-white">Competency Pillars (Subskill Aggregation)</h3>
              <p className="text-xs text-slate-400">
                Each pillar aggregates constituent subskills. If &lt;50% of subskills are evaluated, the pillar is flagged as Partially Assessed.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(pillars).map(([key, p]) => {
              const prof = p.proficiency !== null ? `${p.proficiency}%` : "Not Assessed";
              const conf = Math.round((p.confidence || 0) * 100);
              const cov = Math.round((p.coverage || 0) * 100);
              const isExpanded = expandedPillar === key;

              return (
                <div
                  key={key}
                  className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4 space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-sm text-white">
                        {p.domain_name || key.toUpperCase()}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                        p.status === "ESTABLISHED"
                          ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                          : p.status === "PARTIALLY_ASSESSED"
                          ? "bg-amber-950 text-amber-300 border-amber-800"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}>
                        {p.status || "UNASSESSED"}
                      </span>
                    </div>

                    {/* Proficiency Metric */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs text-slate-400">
                        <span>Proficiency:</span>
                        <span className="font-bold text-white">{prof}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-cyan-400 h-full"
                          style={{ width: `${Math.max(4, p.proficiency || 0)}%` }}
                        />
                      </div>
                    </div>

                    {/* Confidence Metric */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs text-slate-400">
                        <span>Confidence:</span>
                        <span className="font-bold text-white">{conf}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-400 h-full"
                          style={{ width: `${Math.max(4, conf)}%` }}
                        />
                      </div>
                    </div>

                    {/* Coverage Metric */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs text-slate-400">
                        <span>Subskill Coverage:</span>
                        <span className="font-bold text-white">{cov}% ({p.assessed_count || 0}/{p.total_subskills || 0})</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-blue-400 h-full"
                          style={{ width: `${Math.max(4, cov)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setExpandedPillar(isExpanded ? null : key)}
                    className="text-[11px] font-semibold text-cyan-400 hover:text-cyan-300 text-left pt-2 border-t border-slate-700/60"
                  >
                    {isExpanded ? "▲ Hide Subskills" : "▼ View Subskills"}
                  </button>

                  {isExpanded && p.subskills && (
                    <div className="pt-2 space-y-1.5 border-t border-slate-700/60 text-xs">
                      {p.subskills.map((sub) => (
                        <div key={sub.skill_id} className="flex justify-between py-1 border-b border-slate-800/40 text-[11px]">
                          <span className="text-slate-300 truncate pr-2">{sub.skill_name}</span>
                          <span className="font-mono font-bold text-white whitespace-nowrap">
                            {sub.proficiency !== null ? `${sub.proficiency}%` : "Not Assessed"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Strictly Verified Weaknesses Section */}
        {weaknesses.length > 0 ? (
          <div className="bg-red-950/30 border border-red-900/60 rounded-2xl p-5 space-y-3">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400 animate-pulse" />
              <h4 className="text-sm font-bold text-red-300 uppercase tracking-wider">
                Strictly Verified Skill Gaps ({weaknesses.length})
              </h4>
            </div>
            <p className="text-xs text-slate-300">
              Only skills with verified assessment scores below 60% are shown. Unassessed claims are never labeled as weaknesses.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
              {weaknesses.map((w, idx) => (
                <div key={idx} className="bg-slate-900/90 border border-red-900/40 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-white">{w.skill_name}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      w.severity === "VERIFIED_GAP"
                        ? "bg-red-950 text-red-400 border-red-800"
                        : "bg-amber-950 text-amber-400 border-amber-800"
                    }`}>
                      {w.severity} ({w.proficiency}%)
                    </span>
                  </div>

                  {w.failed_criteria && w.failed_criteria.length > 0 && (
                    <div className="text-xs text-slate-400">
                      <span className="font-semibold text-slate-300">Failed Rubrics: </span>
                      {w.failed_criteria.join(", ")}
                    </div>
                  )}

                  <div className="text-xs text-cyan-300 pt-1 flex items-center justify-between">
                    <span>💡 {w.remedial_action}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 text-center text-xs text-slate-400">
            <span className="text-emerald-400 font-bold">✓ Zero Verified Technical Gaps Detected.</span> All assessed skills currently meet the &gt;60% competency threshold.
          </div>
        )}

        {/* Grounded AI Coaching Recommendations Section */}
        {insights.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <span>⚡ Grounded AI Coaching Recommendations</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {insights.map((ins, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900/90 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 space-y-2.5 transition-all shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                        ins.priority === "HIGH"
                          ? "bg-red-950/70 text-red-400 border-red-800"
                          : ins.priority === "MEDIUM"
                          ? "bg-amber-950/70 text-amber-400 border-amber-800"
                          : "bg-emerald-950/70 text-emerald-400 border-emerald-800"
                      }`}
                    >
                      {ins.priority} Priority
                    </span>
                    <span className="text-[11px] font-semibold text-slate-400">
                      {ins.type.replace(/_/g, " ")}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-white">{ins.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{ins.message}</p>

                  {ins.action_type && (
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          if (ins.action_type === "START_REVISION" && onNavigateTab) {
                            onNavigateTab("roadmap");
                          } else if (ins.action_type === "MOCK_INTERVIEW" && onNavigateTab) {
                            onNavigateTab("ava");
                          } else if (onNavigateTab) {
                            onNavigateTab("coding");
                          }
                        }}
                        className="text-xs font-bold text-cyan-400 hover:text-cyan-300 underline"
                      >
                        Take Action: {ins.action_type.replace(/_/g, " ")} &rarr;
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Granular Skill Profiles Grid */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-white">Verified Skill Profiler</h3>
              <p className="text-xs text-slate-400">
                Proficiency and confidence decoupled across 35+ canonical skills.
              </p>
            </div>

            {/* Category Filter */}
            <div className="flex space-x-1.5 overflow-x-auto pb-1">
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setActiveCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                    activeCategoryFilter === cat
                      ? "bg-cyan-500 text-slate-950"
                      : "bg-slate-800 text-slate-400 hover:text-white"
                  }`}
                >
                  {cat === "ALL" ? "All Skills" : cat.replace("Data Structures and Algorithms", "DSA").replace("Computer Science Fundamentals", "Core CS")}
                </button>
              ))}
            </div>
          </div>

          {/* Skill Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-1">
            {filteredSkills.map((sk) => {
              const confBadge = getConfidenceBadge(sk.confidence_level);
              return (
                <div
                  key={sk.skill_id}
                  className="bg-slate-800/40 border border-slate-700/50 hover:border-slate-600 rounded-xl p-4 space-y-2.5 transition-all"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-bold text-white">{sk.name || sk.skill_id}</h4>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">
                        {sk.category}
                      </span>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${confBadge}`}>
                      {sk.confidence_level || "LOW"} CONF
                    </span>
                  </div>

                  {/* Proficiency Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Proficiency:</span>
                      <span className="font-bold text-white">
                        {sk.proficiency !== null && sk.proficiency !== undefined ? `${sk.proficiency}%` : "Not Assessed"}
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          sk.proficiency >= 75
                            ? "bg-emerald-400"
                            : sk.proficiency >= 50
                            ? "bg-cyan-400"
                            : "bg-amber-400"
                        }`}
                        style={{ width: `${Math.max(4, sk.proficiency || 0)}%` }}
                      />
                    </div>
                  </div>

                  {/* Evidence & Trend Footer */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                    <span>{sk.evidence_count || 0} Evidence Signals</span>
                    {getTrendBadge(sk.trend || sk.learning_trend)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Modal: Evidence Provenance Inspector */}
        {showProvenanceModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 my-auto">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">Verified Evidence Provenance History</h3>
                  <p className="text-xs text-slate-400">
                    Complete immutable log of all technical assessments, coding submissions, and project defenses.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowProvenanceModal(false)}
                  className="text-slate-400 hover:text-white text-sm p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
                {evidenceHistory.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-400">
                    No verified evidence items recorded yet. Take an assessment or submit code to establish evidence.
                  </div>
                ) : (
                  evidenceHistory.map((ev, i) => (
                    <div
                      key={ev.id || i}
                      className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-white">{ev.skill_id}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700 text-cyan-300 font-mono">
                            {ev.source_type}
                          </span>
                        </div>
                        <span className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                          (ev.raw_score ?? 0) >= 70 ? "bg-emerald-950 text-emerald-300" : "bg-amber-950 text-amber-300"
                        }`}>
                          Score: {ev.raw_score !== null ? `${ev.raw_score}%` : "Exposure Only"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400 text-[11px] pt-1">
                        <span>Status: {ev.validity_status} | Quality: {ev.evidence_quality || 0.8}</span>
                        <span className="font-mono text-[10px] truncate max-w-xs">Hash: {ev.provenance_hash || "n/a"}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Modal: Project Defense Probing */}
        {showProjectProbeModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 my-auto">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">Verify Project Defense Depth</h3>
                  <p className="text-xs text-slate-400">
                    Defend your project architecture to convert unverified claims into verified proficiency evidence.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowProjectProbeModal(false)}
                  className="text-slate-400 hover:text-white text-sm p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              {probingQuestions.length === 0 ? (
                <form onSubmit={handleGenerateProjectProbes} className="space-y-3 text-xs">
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Project Title</label>
                    <input
                      type="text"
                      value={projectTitle}
                      onChange={(e) => setProjectTitle(e.target.value)}
                      placeholder="e.g. Real-Time Distributed Chat Service"
                      required
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Technologies Used (comma-separated)</label>
                    <input
                      type="text"
                      value={projectTech}
                      onChange={(e) => setProjectTech(e.target.value)}
                      placeholder="e.g. Python, Redis, WebSockets, Docker, PostgreSQL"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Project Description & Architecture</label>
                    <textarea
                      rows={3}
                      value={projectDesc}
                      onChange={(e) => setProjectDesc(e.target.value)}
                      placeholder="Describe the system architecture, component boundaries, and challenges..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs"
                    >
                      Generate Architectural Probes &rarr;
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-4 text-xs">
                  <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                    {probingQuestions.map((q, idx) => (
                      <div key={q.question_id || idx} className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-cyan-400">Probe {idx + 1}: {q.focus_area}</span>
                        </div>
                        <p className="text-white text-xs leading-relaxed">{q.question_text}</p>
                        <textarea
                          rows={3}
                          value={probeAnswers[q.question_id] || ""}
                          onChange={(e) => setProbeAnswers({ ...probeAnswers, [q.question_id]: e.target.value })}
                          placeholder="Provide your technical defense detailing failure isolation, trade-offs, and invariants..."
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white text-xs"
                        />
                        <button
                          type="button"
                          disabled={evaluatingDefense}
                          onClick={() => handleEvaluateDefense(q, probeAnswers[q.question_id] || "")}
                          className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold px-3 py-1.5 rounded-lg text-xs"
                        >
                          {evaluatingDefense ? "Evaluating Defense..." : "Submit Defense Evaluation"}
                        </button>
                      </div>
                    ))}
                  </div>

                  {defenseResults.length > 0 && (
                    <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl space-y-1">
                      <span className="font-bold text-emerald-300">Defense Results Recorded:</span>
                      {defenseResults.map((r, i) => (
                        <div key={i} className="text-[11px] text-slate-300">
                          Score: {r.score}% - {r.classification}: {r.feedback}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
