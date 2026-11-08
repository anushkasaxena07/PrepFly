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
  const [activeCategoryFilter, setActiveCategoryFilter] = useState("ALL");
  const [error, setError] = useState("");

  useEffect(() => {
    loadProgressData();
  }, []);

  const loadProgressData = async () => {
    setLoading(true);
    setError("");
    try {
      const [dashRes, skillRes, insightRes, weakRes, improveRes] = await Promise.allSettled([
        intelligenceAPI.getProgressDashboard(),
        intelligenceAPI.getSkillProfile(),
        intelligenceAPI.getCoachingInsights(),
        intelligenceAPI.getCrossFeatureWeaknesses(),
        intelligenceAPI.getImprovementAnalytics()
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
    } catch (err) {
      setError(err.message || "Failed to load progress analytics.");
    } finally {
      setLoading(false);
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
        Calculating multi-source preparation readiness & grounded insights...
      </div>
    );
  }

  const readiness = dashboard?.overall_readiness || 0;
  const metrics = dashboard?.study_metrics || {};
  const dist = dashboard?.skill_distribution || {};
  const radar = dashboard?.radar_data || [];
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
              Evidence-Based
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            My Preparation & Readiness Progress
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Calibrated against real coding submissions, Ava mock interviews, diagnostic checks, and spaced repetition.
          </p>
        </div>

        <button
          type="button"
          onClick={loadProgressData}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold px-4 py-2 rounded-xl transition-all self-start sm:self-auto"
        >
          ↻ Refresh Analytics
        </button>
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

      {/* Top Readiness & Baseline Comparison Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Readiness Card */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-800/80 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider text-slate-400">
              <span>Overall Role Readiness</span>
              <span className="text-cyan-400">{dashboard?.target_role || "SDE"}</span>
            </div>
            <div className="flex items-baseline space-x-3 mt-4">
              <span className="text-5xl font-extrabold text-white">{readiness}%</span>
              <span className="text-xs text-slate-400">Target: 85%+</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-3">
              <div
                className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full transition-all duration-700"
                style={{ width: `${Math.max(4, readiness)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center pt-5 border-t border-slate-800/80 mt-5">
            <div>
              <div className="text-base font-bold text-white">{dist.mastered || 0}</div>
              <div className="text-[10px] text-emerald-400 uppercase font-semibold">Mastered</div>
            </div>
            <div>
              <div className="text-base font-bold text-white">{dist.proficient || 0}</div>
              <div className="text-[10px] text-cyan-400 uppercase font-semibold">Proficient</div>
            </div>
            <div>
              <div className="text-base font-bold text-white">{dist.needs_focus || 0}</div>
              <div className="text-[10px] text-amber-400 uppercase font-semibold">Needs Focus</div>
            </div>
          </div>
        </div>

        {/* Baseline vs Current Delta Card */}
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

        {/* 4-Dimension Competency Overview */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Competency Pillars
            </div>
            <div className="space-y-3">
              {radar.map((d, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium">
                      {d.dimension.replace("Data Structures and Algorithms", "DSA").replace("Computer Science Fundamentals", "Core CS")}
                    </span>
                    <span className="font-bold text-white">{d.score}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        d.score >= 70 ? "bg-emerald-400" : d.score >= 50 ? "bg-cyan-400" : "bg-amber-400"
                      }`}
                      style={{ width: `${Math.max(3, d.score)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
            <span>Roadmap Completion:</span>
            <span className="font-bold text-cyan-400">{metrics.completion_percentage || 0}%</span>
          </div>
        </div>
      </div>

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

      {/* Cross-Feature Weakness Alerts */}
      {weaknesses.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/60 rounded-2xl p-5 space-y-3">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400 animate-pulse" />
            <h4 className="text-sm font-bold text-red-300 uppercase tracking-wider">
              Cross-Feature Weaknesses Detected ({weaknesses.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {weaknesses.map((w, idx) => (
              <div key={idx} className="bg-slate-900/80 border border-red-900/40 rounded-xl p-3.5 space-y-1">
                <div className="font-bold text-sm text-white">{w.skill_name}</div>
                <div className="text-xs text-slate-400">
                  Flagged across multiple features:{" "}
                  {w.failing_sources.map((s) => `${s.source.replace('_', ' ')} (${s.average_score}%)`).join(", ")}
                </div>
                <div className="text-[11px] text-amber-300/90 pt-1">
                  💡 {w.remedial_recommendation}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Granular Skill Profiles Table / Grid */}
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
                    <span className="font-bold text-white">{sk.proficiency || 0}%</span>
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
    </div>
  </div>
  );
}

