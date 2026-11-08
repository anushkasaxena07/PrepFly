import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import PreparationOnboarding from "./PreparationOnboarding";
import DiagnosticAssessmentModal from "./DiagnosticAssessmentModal";
import RetrievalDrillModal from "./RetrievalDrillModal";
import "./intelligence.css";

export default function RoadmapTab({ onNavigateTab }) {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [dueRevisions, setDueRevisions] = useState([]);
  const [error, setError] = useState("");

  // Modals
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showDiagnostic, setShowDiagnostic] = useState(false);
  const [activeDrillSkill, setActiveDrillSkill] = useState(null);

  // Recalculating state
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [selectedDayFilter, setSelectedDayFilter] = useState("ALL");
  const [recommendations, setRecommendations] = useState([]);
  const [activeViewMode, setActiveViewMode] = useState("SCHEDULE"); // "SCHEDULE" | "RECOMMENDATIONS"

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError("");
    try {
      // 1. Fetch profile
      const profRes = await intelligenceAPI.getProfile();
      if (!profRes.profile) {
        setShowOnboarding(true);
        setLoading(false);
        return;
      }
      setProfile(profRes.profile);

      // 2. Fetch current roadmap
      const rmRes = await intelligenceAPI.getCurrentRoadmap();
      if (!rmRes.roadmap) {
        // Prompt diagnostic assessment or generate
        setShowDiagnostic(true);
      } else {
        setRoadmap(rmRes.roadmap);
      }

      // 3. Fetch due spaced revisions
      try {
        const revRes = await intelligenceAPI.getDueRevisions();
        setDueRevisions(revRes.due_revisions || []);
      } catch (revErr) {
        console.warn("Could not fetch due revisions:", revErr);
      }

      // 4. Fetch curriculum recommendations
      try {
        const recRes = await intelligenceAPI.getRoadmapRecommendations();
        setRecommendations(recRes.data || []);
      } catch (recErr) {
        console.warn("Could not fetch recommendations:", recErr);
      }
    } catch (err) {
      setError(err.message || "Failed to load preparation roadmap.");
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    setIsRecalculating(true);
    setError("");
    try {
      await intelligenceAPI.recalculateRoadmap("Candidate requested plan rebalancing");
      const updated = await intelligenceAPI.getCurrentRoadmap();
      setRoadmap(updated.roadmap);
    } catch (err) {
      setError(err.message || "Failed to recalculate roadmap.");
    } finally {
      setIsRecalculating(false);
    }
  };

  const handleTogglePin = async (activityId, currentPinned) => {
    try {
      await intelligenceAPI.patchActivity(activityId, { is_pinned: !currentPinned });
      const updated = await intelligenceAPI.getCurrentRoadmap();
      setRoadmap(updated.roadmap);
    } catch (err) {
      setError(err.message || "Failed to pin activity.");
    }
  };

  const handleCompleteActivity = async (activityId) => {
    try {
      await intelligenceAPI.completeActivity(activityId, {
        score: 85.0,
        notes: "Completed as scheduled"
      });
      const updated = await intelligenceAPI.getCurrentRoadmap();
      setRoadmap(updated.roadmap);
      // Refresh due revisions
      const revRes = await intelligenceAPI.getDueRevisions();
      setDueRevisions(revRes.due_revisions || []);
    } catch (err) {
      setError(err.message || "Failed to mark activity complete.");
    }
  };

  const handleSkipActivity = async (activityId) => {
    try {
      await intelligenceAPI.skipActivity(activityId);
      const updated = await intelligenceAPI.getCurrentRoadmap();
      setRoadmap(updated.roadmap);
    } catch (err) {
      setError(err.message || "Failed to skip activity.");
    }
  };

  const getActivityTypeBadge = (type) => {
    const map = {
      LEARN: { bg: "bg-indigo-950/70 text-indigo-400 border-indigo-800", label: "Concept & Learn" },
      PRACTICE: { bg: "bg-cyan-950/70 text-cyan-400 border-cyan-800", label: "Practice & Drill" },
      CODING: { bg: "bg-emerald-950/70 text-emerald-400 border-emerald-800", label: "Coding Problem" },
      MOCK_INTERVIEW: { bg: "bg-purple-950/70 text-purple-400 border-purple-800", label: "Ava Mock Interview" },
      ASSESSMENT: { bg: "bg-blue-950/70 text-blue-400 border-blue-800", label: "Diagnostic Check" },
      REVISION: { bg: "bg-amber-950/70 text-amber-400 border-amber-800", label: "Spaced Retrieval" }
    };
    return map[type] || { bg: "bg-slate-800 text-slate-300 border-slate-700", label: type };
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-300">
        <div className="w-10 h-10 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading your personalized preparation engine...
      </div>
    );
  }

  const schedule = roadmap?.schedule || {};
  const dayNumbers = Object.keys(schedule).map(Number).sort((a, b) => a - b);
  const totalActivities = roadmap?.total_activities || 0;
  const completedActivities = roadmap?.completed_activities || 0;
  const completionPct = roadmap?.completion_percentage || 0;

  return (
    <div id="page-roadmap" className="page active" role="tabpanel">
      <div className="container intelligence-root space-y-6 text-slate-100 pb-12">
      {/* Modals */}
      {showOnboarding && (
        <PreparationOnboarding
          onCompleted={(newProf) => {
            setProfile(newProf);
            setShowOnboarding(false);
            setShowDiagnostic(true);
          }}
          onCancel={() => setShowOnboarding(false)}
        />
      )}

      {showDiagnostic && (
        <DiagnosticAssessmentModal
          onClose={() => {
            setShowDiagnostic(false);
            loadAllData();
          }}
          onCompleted={() => {
            setShowDiagnostic(false);
            loadAllData();
          }}
        />
      )}

      {activeDrillSkill && (
        <RetrievalDrillModal
          skillId={activeDrillSkill.skill_id}
          skillName={activeDrillSkill.skill_name}
          onClose={() => setActiveDrillSkill(null)}
          onCompleted={() => {
            setActiveDrillSkill(null);
            loadAllData();
          }}
        />
      )}

      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800/80 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center space-x-2 mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                PrepFly Intelligence
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                Roadmap v{roadmap?.current_version || roadmap?.version || 1}
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                Adaptive
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
              {profile?.target_role || "Personalized Technical Roadmap"}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1">
              Target: <strong className="text-white">{profile?.target_company || "Top Tech"}</strong>
              {profile?.target_date ? ` • Target Date: ${profile.target_date}` : ""}
              {profile?.daily_minutes ? ` • Budget: ${profile.daily_minutes} min/day` : ""}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={isRecalculating}
              onClick={handleRecalculate}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold px-4 py-2.5 rounded-xl transition-all shadow flex items-center space-x-2"
            >
              <span>{isRecalculating ? "Rebalancing..." : "↻ Recalculate Roadmap"}</span>
            </button>

            <button
              type="button"
              onClick={() => setShowDiagnostic(true)}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold px-4 py-2.5 rounded-xl transition-all shadow"
            >
              Diagnostic Assessment
            </button>

            <button
              type="button"
              onClick={() => setShowOnboarding(true)}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-md shadow-cyan-500/20"
            >
              Edit Goals
            </button>
          </div>
        </div>

        {/* Progress Bar & High-Level Stats */}
        <div className="mt-6 pt-5 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
          <div className="sm:col-span-2 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Preparation Milestone Progress</span>
              <span className="text-cyan-400 font-bold">{completionPct}% Completed</span>
            </div>
            <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full transition-all duration-500"
                style={{ width: `${Math.max(3, completionPct)}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-400">
              {completedActivities} of {totalActivities} preparation activities mastered
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3 flex items-center justify-around text-center">
            <div>
              <div className="text-base font-bold text-white">{dayNumbers.length}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Days Planned</div>
            </div>
            <div className="h-6 w-px bg-slate-700" />
            <div>
              <div className="text-base font-bold text-cyan-400">{profile?.daily_minutes || 60}m</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Daily Pace</div>
            </div>
            <div className="h-6 w-px bg-slate-700" />
            <div>
              <div className="text-base font-bold text-amber-400">{dueRevisions.length}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Due Drills</div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3.5 bg-red-950/60 border border-red-800 rounded-xl text-sm text-red-300 flex justify-between items-center">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")} className="text-xs text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Due Spaced Revision Alert Banner */}
      {dueRevisions.length > 0 && (
        <div className="bg-gradient-to-r from-amber-950/60 via-slate-900 to-amber-950/40 border border-amber-800/60 rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-0.5">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
                Spaced Revision Due Today ({dueRevisions.length})
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200">
              Retrieval practice intervals scheduled for:{" "}
              <strong>{dueRevisions.map((r) => r.skill_name).slice(0, 3).join(", ")}</strong>
            </p>
          </div>

          <button
            type="button"
            onClick={() => setActiveDrillSkill(dueRevisions[0])}
            className="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs transition-all shadow-md shadow-amber-500/20 whitespace-nowrap"
          >
            Start 5-Min Drill ({dueRevisions[0].skill_name}) &rarr;
          </button>
        </div>
      )}

      {/* View Toggle */}
      <div className="flex border-b border-slate-800 pb-3 gap-2">
        <button
          type="button"
          onClick={() => setActiveViewMode("SCHEDULE")}
          className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition ${
            activeViewMode === "SCHEDULE"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-900/40"
              : "bg-slate-900 text-slate-400 hover:text-white"
          }`}
        >
          Daily Scheduled Activities
        </button>
        <button
          type="button"
          onClick={() => setActiveViewMode("RECOMMENDATIONS")}
          className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition ${
            activeViewMode === "RECOMMENDATIONS"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-900/40"
              : "bg-slate-900 text-slate-400 hover:text-white"
          }`}
        >
          Curriculum Priority & Formula ({recommendations.length})
        </button>
      </div>

      {activeViewMode === "RECOMMENDATIONS" ? (
        /* Recommendations & Priority Formula Breakdown View */
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <span>Recommendation Engine Priority Formula</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic priority computed as:{" "}
              <code className="text-cyan-400 font-mono text-[11px]">
                0.30·SkillGap + 0.25·JobRelevance + 0.15·PrereqDepth + 0.20·Weakness + 0.10·Urgency
              </code>
            </p>
          </div>

          <div className="divide-y divide-slate-800/80">
            {recommendations.map((rec, idx) => (
              <div key={rec.skill_id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-500">#{idx + 1}</span>
                    <h3 className="font-bold text-sm text-white">{rec.name}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-slate-400 border border-slate-700">
                      {rec.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    {rec.rationale}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <div className="px-2.5 py-1 bg-slate-800/80 rounded-lg text-slate-300">
                    Gap: <span className="font-mono text-cyan-400 font-bold">{rec.components?.skill_gap}</span>
                  </div>
                  <div className="px-2.5 py-1 bg-slate-800/80 rounded-lg text-slate-300">
                    Relevance: <span className="font-mono text-indigo-400 font-bold">{rec.components?.job_relevance}</span>
                  </div>
                  <div className="px-2.5 py-1 bg-slate-800/80 rounded-lg text-slate-300">
                    Prereq: <span className="font-mono text-amber-400 font-bold">{rec.components?.prerequisite_importance}</span>
                  </div>
                  <div className="px-3 py-1 bg-cyan-950 border border-cyan-800/80 rounded-xl text-cyan-300 font-bold">
                    Score: {rec.priority_score}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Daily Schedule View */
        <>
          {/* Day Filter Pills */}
      <div className="flex items-center justify-between overflow-x-auto pb-1">
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => setSelectedDayFilter("ALL")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              selectedDayFilter === "ALL"
                ? "bg-cyan-500 text-slate-950"
                : "bg-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            All Days ({dayNumbers.length})
          </button>
          {dayNumbers.slice(0, 10).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setSelectedDayFilter(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedDayFilter === d
                  ? "bg-cyan-500 text-slate-950"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              Day {d}
            </button>
          ))}
        </div>
      </div>

      {/* Days Timeline View */}
      <div className="space-y-5">
        {dayNumbers.length === 0 ? (
          <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl">
            <h3 className="text-lg font-bold text-white mb-2">No Activities Planned Yet</h3>
            <p className="text-xs text-slate-400 mb-4">
              Take the diagnostic assessment or configure your goals to generate your daily preparation plan.
            </p>
            <button
              type="button"
              onClick={() => setShowDiagnostic(true)}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-5 py-2.5 rounded-lg text-sm"
            >
              Start Diagnostic Assessment &rarr;
            </button>
          </div>
        ) : (
          dayNumbers
            .filter((d) => selectedDayFilter === "ALL" || selectedDayFilter === d)
            .map((dayNum) => {
              const acts = schedule[dayNum] || [];
              const dayMinutes = acts.reduce((acc, a) => acc + (a.estimated_minutes || 30), 0);
              const dayCompleted = acts.filter((a) => a.status === "completed" || a.status === "COMPLETED").length;

              return (
                <div
                  key={dayNum}
                  className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4"
                >
                  {/* Day Header */}
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center font-bold text-cyan-400 text-sm">
                        {dayNum}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-white">Day {dayNum}</h3>
                        <span className="text-[11px] text-slate-400">
                          {acts[0]?.due_date ? `Scheduled for ${acts[0].due_date}` : "Scheduled study session"}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 text-xs">
                      <span className="text-slate-400">
                        {dayMinutes} min total
                      </span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300">
                        {dayCompleted} / {acts.length} Complete
                      </span>
                    </div>
                  </div>

                  {/* Activity Cards List */}
                  <div className="grid grid-cols-1 gap-3">
                    {acts.map((act) => {
                      const badge = getActivityTypeBadge(act.activity_type);
                      const isDone = act.status === "completed" || act.status === "COMPLETED";
                      const isSkipped = act.status === "skipped" || act.status === "SKIPPED";
                      const isPinned = act.is_pinned;

                      return (
                        <div
                          key={act.activity_id || act.id}
                          className={`p-4 rounded-xl border transition-all ${
                            isDone
                              ? "bg-slate-950/40 border-slate-800/80 opacity-75"
                              : isSkipped
                              ? "bg-slate-950/20 border-slate-800/50 opacity-50"
                              : "bg-slate-800/50 border-slate-700/60 hover:border-slate-600"
                          }`}
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div className="space-y-1.5 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${badge.bg}`}>
                                  {badge.label}
                                </span>
                                <span className="text-xs font-semibold text-slate-400">
                                  {act.skill_name || act.skill_id}
                                </span>
                                <span className="text-[11px] text-slate-500">
                                  &bull; {act.estimated_minutes || 30} min
                                </span>
                                {isPinned && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950/70 border border-amber-800 text-amber-300">
                                    ★ Pinned
                                  </span>
                                )}
                              </div>

                              <h4 className={`text-sm sm:text-base font-bold ${isDone ? "line-through text-slate-400" : "text-white"}`}>
                                {act.title}
                              </h4>
                              <p className="text-xs text-slate-400 leading-relaxed">
                                {act.description}
                              </p>
                              {act.recommendation_reason && (
                                <p className="text-[11px] text-cyan-400/90 italic">
                                  Why: {act.recommendation_reason}
                                </p>
                              )}
                            </div>

                            {/* Actions Right Side */}
                            <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800">
                              {/* Direct Jump CTAs */}
                              {act.activity_type === "CODING" && onNavigateTab && (
                                <button
                                  type="button"
                                  onClick={() => onNavigateTab("coding")}
                                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 underline"
                                >
                                  Solve in Sandbox &rarr;
                                </button>
                              )}
                              {act.activity_type === "MOCK_INTERVIEW" && onNavigateTab && (
                                <button
                                  type="button"
                                  onClick={() => onNavigateTab("ava")}
                                  className="text-xs font-semibold text-purple-400 hover:text-purple-300 underline"
                                >
                                  Start Ava Interview &rarr;
                                </button>
                              )}

                              {/* Action Buttons */}
                              <div className="flex items-center space-x-1.5">
                                <button
                                  type="button"
                                  title={isPinned ? "Unpin activity" : "Pin activity to preserve during adaptations"}
                                  onClick={() => handleTogglePin(act.activity_id || act.id, isPinned)}
                                  className={`p-1.5 rounded-lg text-xs transition-colors ${
                                    isPinned
                                      ? "text-amber-400 hover:bg-slate-800"
                                      : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                                  }`}
                                >
                                  {isPinned ? "★" : "☆"}
                                </button>

                                {!isDone && !isSkipped && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => handleSkipActivity(act.activity_id || act.id)}
                                      className="px-2.5 py-1 rounded-lg text-xs text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-800"
                                    >
                                      Skip
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => handleCompleteActivity(act.activity_id || act.id)}
                                      className="px-3 py-1 rounded-lg text-xs font-bold text-slate-950 bg-cyan-500 hover:bg-cyan-400 transition-all shadow-sm shadow-cyan-500/20"
                                    >
                                      Mark Done ✓
                                    </button>
                                  </>
                                )}

                                {isDone && (
                                  <span className="text-xs font-semibold text-emerald-400 flex items-center space-x-1">
                                    <span>✓ Completed</span>
                                  </span>
                                )}

                                {isSkipped && (
                                  <span className="text-xs font-semibold text-slate-500">
                                    Skipped
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
        )}
      </div>
      </>
      )}
    </div>
  </div>
  );
}

