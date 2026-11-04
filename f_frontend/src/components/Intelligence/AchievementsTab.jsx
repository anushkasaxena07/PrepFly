import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

export default function AchievementsTab() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [activeCategory, setActiveCategory] = useState("ALL");
  const [claimingId, setClaimingId] = useState(null);
  const [error, setError] = useState("");
  const [claimSuccess, setClaimSuccess] = useState("");

  useEffect(() => {
    loadAchievements();
  }, []);

  const loadAchievements = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await intelligenceAPI.getAchievements();
      if (res.data) {
        setOverview(res.data);
      }
    } catch (err) {
      setError(err.message || "Failed to load achievements.");
    } finally {
      setLoading(false);
    }
  };

  const handleClaim = async (achievementId) => {
    setClaimingId(achievementId);
    setError("");
    setClaimSuccess("");
    try {
      const res = await intelligenceAPI.claimAchievement(achievementId);
      if (res.data?.status === "CLAIMED") {
        setClaimSuccess(`Awarded +${res.data.points_awarded} Points!`);
        await loadAchievements();
      }
    } catch (err) {
      setError(err.message || "Failed to claim achievement reward.");
    } finally {
      setClaimingId(null);
    }
  };

  const getBadgeCategoryStyle = (cat) => {
    const map = {
      activity: "bg-blue-950 text-blue-300 border-blue-800",
      proficiency: "bg-emerald-950 text-emerald-300 border-emerald-800",
      streak: "bg-amber-950 text-amber-300 border-amber-800",
      improvement: "bg-purple-950 text-purple-300 border-purple-800",
      mastery: "bg-rose-950 text-rose-300 border-rose-800"
    };
    return map[cat] || "bg-slate-800 text-slate-300 border-slate-700";
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-300">
        <div className="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading server-validated milestones & achievements...
      </div>
    );
  }

  const achievements = overview?.achievements || [];
  const categories = ["ALL", "activity", "proficiency", "streak", "improvement", "mastery"];
  const filtered = achievements.filter(
    (a) => activeCategory === "ALL" || a.category === activeCategory
  );

  return (
    <div id="page-achievements" className="page active" role="tabpanel">
      <div className="container intelligence-root space-y-6 text-slate-100 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
              Gamified Mastery
            </span>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
              Server-Validated
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            Achievements & Milestones
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Track your verified interview prep milestones, earn badges, and celebrate verifiable progress.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800/80 rounded-xl text-red-200 text-sm">
          {error}
        </div>
      )}

      {claimSuccess && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-800/80 rounded-xl text-emerald-200 text-sm font-semibold animate-pulse">
          🎉 {claimSuccess}
        </div>
      )}

      {/* Overview Stat Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Milestones Unlocked</span>
          <div className="text-3xl font-black text-amber-400 mt-2">
            {overview?.total_unlocked || 0} / {overview?.total_definitions || 0}
          </div>
          <span className="inline-block mt-2 text-xs text-slate-400">
            {Math.round(((overview?.total_unlocked || 0) / (overview?.total_definitions || 1)) * 100)}% Complete
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Preparation Points</span>
          <div className="text-3xl font-black text-cyan-400 mt-2">
            {overview?.total_earned_points || 0}
          </div>
          <span className="inline-block mt-2 text-xs text-slate-400">
            Out of {overview?.total_possible_points || 0} points available
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Integrity Standard</span>
          <div className="text-lg font-bold text-emerald-400 mt-3">
            Zero Duplicates
          </div>
          <span className="inline-block mt-1 text-xs text-slate-400">
            Strict transactional verification
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition ${
              activeCategory === cat
                ? "bg-amber-600 text-white shadow-md shadow-amber-900/40"
                : "bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Achievements Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((ach) => (
          <div
            key={ach.id}
            className={`p-5 rounded-2xl border transition ${
              ach.is_unlocked
                ? "bg-slate-900/90 border-amber-500/40 shadow-lg shadow-amber-950/20"
                : "bg-slate-900/40 border-slate-800/80 opacity-75"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-white text-base">{ach.name}</h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getBadgeCategoryStyle(ach.category)}`}>
                    {ach.category}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {ach.description}
                </p>
              </div>

              <div className="text-right whitespace-nowrap">
                <span className="px-2.5 py-1 rounded-xl text-xs font-black bg-amber-950/70 text-amber-300 border border-amber-800/60">
                  +{ach.reward_points} PTS
                </span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mt-4 space-y-1.5">
              <div className="flex justify-between text-[11px] text-slate-400 font-semibold">
                <span>{ach.is_unlocked ? "Completed" : "Progress"}</span>
                <span>
                  {ach.is_unlocked ? `${ach.threshold_value} / ${ach.threshold_value}` : `${ach.current_progress} / ${ach.threshold_value}`}
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    ach.is_unlocked ? "bg-gradient-to-r from-amber-500 to-yellow-400" : "bg-cyan-600"
                  }`}
                  style={{ width: `${ach.progress_percentage}%` }}
                />
              </div>
            </div>

            {/* Unlock Status / Claim Action */}
            <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
              {ach.is_unlocked ? (
                <>
                  <span className="text-emerald-400 font-semibold flex items-center space-x-1">
                    <span>✓ Unlocked</span>
                    {ach.unlocked_at && (
                      <span className="text-slate-500 text-[10px]">
                        ({new Date(ach.unlocked_at).toLocaleDateString()})
                      </span>
                    )}
                  </span>

                  {ach.reward_claimed ? (
                    <span className="text-slate-500 font-medium">Reward Claimed</span>
                  ) : (
                    <button
                      onClick={() => handleClaim(ach.id)}
                      disabled={claimingId === ach.id}
                      className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs transition shadow"
                    >
                      {claimingId === ach.id ? "Claiming..." : "Claim Reward"}
                    </button>
                  )}
                </>
              ) : (
                <span className="text-slate-500 font-medium italic">
                  In Progress ({Math.round(ach.progress_percentage)}%)
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
  );
}

