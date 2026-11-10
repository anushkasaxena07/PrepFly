import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import { CosmicHero, NavIcon } from "../ui/PrepFlyTheme";
import { usePrepFlyTheme } from "../ui/ThemeContext";
import journeyHikerImg from "../../assets/journey-hiker.jpg";
import "./intelligence.css";

export default function AchievementsTab({ onNavigateTab }) {
  const { isSunrise } = usePrepFlyTheme();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [activeCategory, setActiveCategory] = useState("ALL");
  const [claimingId, setClaimingId] = useState(null);
  const [error, setError] = useState("");
  const [claimSuccess, setClaimSuccess] = useState("");
  const [showAllBadges, setShowAllBadges] = useState(false);

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
      activity: { background: "#eef2ff", color: "#4f46e5", border: "1px solid #c7d2fe" },
      proficiency: { background: "#ecfdf5", color: "#059669", border: "1px solid #a7f3d0" },
      streak: { background: "#fffbeb", color: "#d97706", border: "1px solid #fde68a" },
      improvement: { background: "#f5f3ff", color: "#6d28d9", border: "1px solid #ddd6fe" },
      mastery: { background: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca" },
    };
    return map[cat] || { background: "#f1f5f9", color: "#475569", border: "1px solid #e2e8f0" };
  };

  const achievements = overview?.achievements || [];
  const totalUnlocked = overview?.total_unlocked || 0;
  const totalDefs = overview?.total_definitions || 0;
  const earnedPts = overview?.total_earned_points || 0;
  const possiblePts = overview?.total_possible_points || 0;
  const completePct = Math.round((totalUnlocked / Math.max(1, totalDefs)) * 100);

  const categories = [
    { id: "ALL", label: "All" },
    { id: "activity", label: "Activity" },
    { id: "proficiency", label: "Proficiency" },
    { id: "streak", label: "Streak" },
    { id: "improvement", label: "Improvement" },
    { id: "mastery", label: "Mastery" },
  ];

  const filtered = achievements.filter(
    (a) => activeCategory === "ALL" || a.category === activeCategory
  );

  // Breakdown counts derived strictly from real achievements
  const countCategory = (cat) => {
    const subset = achievements.filter((a) => a.category === cat);
    return {
      done: subset.filter((a) => a.is_unlocked).length,
      total: subset.length,
    };
  };
  const codingStat = countCategory("proficiency");
  const interviewStat = countCategory("activity");
  const masteryStat = countCategory("mastery");
  const streakStat = countCategory("streak");

  const ringRadius = 46;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringOffset = ringCircumference * (1 - Math.min(1, Math.max(0, completePct / 100)));

  return (
    <div id="page-achievements" className="page active" role="tabpanel">
      {/* ── DARK COSMIC HERO SECTION ── */}
      <CosmicHero
        badge="Your Progress"
        titleWhite="Achievements"
        titleAccent="& Milestones"
        subtitle="Track your verified interview prep milestones, earn badges, and celebrate your progress."
        cornerNote="Dream Bigger"
      >
        <div className="pf-hero-kpi">
          <div className="pf-hero-kpi-icon" style={{ color: "#fbbf24" }}>
            <NavIcon name="achievements" size={20} color="#fbbf24" />
          </div>
          <div>
            <div className="pf-hero-kpi-lbl">Milestones Unlocked</div>
            <div className="pf-hero-kpi-val">{totalUnlocked} / {totalDefs}</div>
            <div className="pf-hero-kpi-sub">{completePct}% Complete</div>
          </div>
        </div>

        <div className="pf-hero-kpi">
          <div className="pf-hero-kpi-icon" style={{ color: "#a78bfa" }}>
            <NavIcon name="layers" size={20} color="#a78bfa" />
          </div>
          <div>
            <div className="pf-hero-kpi-lbl">Preparation Points</div>
            <div className="pf-hero-kpi-val" style={{ color: "#34d399" }}>{earnedPts}</div>
            <div className="pf-hero-kpi-sub">Out of {possiblePts} points available</div>
          </div>
        </div>

        <div className="pf-hero-kpi">
          <div className="pf-hero-kpi-icon" style={{ color: "#34d399" }}>
            <NavIcon name="shield" size={20} color="#34d399" />
          </div>
          <div style={{ flex: 1 }}>
            <div className="pf-hero-kpi-lbl">Integrity Standard</div>
            <div className="pf-hero-kpi-val" style={{ fontSize: "20px", color: "#34d399" }}>
              Zero Duplicates
            </div>
            <div className="pf-hero-kpi-sub">Strict transactional verification</div>
          </div>
          <div
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "#10b981",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#052e16",
              flexShrink: 0,
            }}
          >
            <NavIcon name="check" size={14} strokeWidth={2.8} color="#ffffff" />
          </div>
        </div>
      </CosmicHero>

      {/* ── LIGHT WORKSPACE BODY CANVAS ── */}
      <main className="pf-body-surface">
        <div className="pf-body-inner intelligence-root">
          {loading ? (
            <div className="pf-card" style={{ textAlign: "center", padding: "64px 24px", color: "#64748b" }}>
              <div className="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              Loading server-validated milestones &amp; achievements...
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Filter Pill Tabs */}
              <div className="pf-filter-bar">
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setActiveCategory(cat.id)}
                    className={`pf-filter-pill ${activeCategory === cat.id ? "active" : ""}`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {error && (
                <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "12px", color: "#dc2626", fontSize: "13px", fontWeight: 600 }}>
                  {error}
                </div>
              )}

              {claimSuccess && (
                <div style={{ padding: "12px 16px", background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: "12px", color: "#059669", fontSize: "13px", fontWeight: 700 }}>
                  {claimSuccess}
                </div>
              )}

              {/* Featured Bento Row: Spotlight Banner + Progress Breakdown */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "18px" }}>
                {/* Dark Spotlight Card (adapts to Journey Hiker mountain art in Sunrise mode) */}
                {isSunrise ? (
                  <div
                    className="pf-journey-banner"
                    style={{
                      backgroundImage: `linear-gradient(90deg, rgba(44, 21, 13, 0.96) 0%, rgba(56, 28, 17, 0.88) 46%, rgba(56, 28, 17, 0.16) 100%), url(${journeyHikerImg})`,
                    }}
                  >
                    <div className="pf-journey-content">
                      <h2 className="pf-journey-title" style={{ fontSize: "24px" }}>
                        {totalUnlocked === 0
                          ? "Your journey to success starts with your first milestone!"
                          : `${totalUnlocked} of ${totalDefs} milestones unlocked — keep climbing!`}
                      </h2>
                      <button
                        type="button"
                        className="pf-journey-btn"
                        onClick={() => onNavigateTab ? onNavigateTab("ava") : null}
                      >
                        Begin Your Prep Journey →
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="pf-spotlight-dark" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "20px", flexWrap: "wrap" }}>
                    <div
                      style={{
                        width: "96px",
                        height: "96px",
                        borderRadius: "20px",
                        background: "radial-gradient(circle at 35% 30%, rgba(167,139,250,0.35), rgba(30,27,75,0.9))",
                        border: "1px solid rgba(196,181,253,0.3)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        boxShadow: "0 14px 30px rgba(109, 40, 217, 0.35)",
                      }}
                    >
                      <NavIcon name="achievements" size={44} strokeWidth={1.6} color="#e9d5ff" />
                    </div>

                    <div style={{ flex: 1, minWidth: "200px" }}>
                      <h2 className="text-white" style={{ fontSize: "20px", fontWeight: 800, lineHeight: 1.3, marginBottom: "14px", color: "#ffffff" }}>
                        {totalUnlocked === 0
                          ? "Your journey to success starts with your first milestone!"
                          : `${totalUnlocked} of ${totalDefs} milestones unlocked — keep your momentum high!`}
                      </h2>
                      <button
                        type="button"
                        onClick={() => onNavigateTab ? onNavigateTab("ava") : null}
                        style={{
                          padding: "10px 20px",
                          borderRadius: "999px",
                          border: "none",
                          background: "linear-gradient(135deg, #c4b5fd 0%, #a78bfa 100%)",
                          color: "#1e1b4b",
                          fontWeight: 800,
                          fontSize: "13px",
                          cursor: "pointer",
                        }}
                      >
                        Begin Your Prep Journey →
                      </button>
                    </div>
                  </div>
                )}

                {/* Light Progress Breakdown Donut Card */}
                <div className="pf-card">
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                    <h3 style={{ fontSize: "15px", fontWeight: 800, color: "var(--text)" }}>Your Progress Breakdown</h3>
                    <button
                      type="button"
                      onClick={() => onNavigateTab ? onNavigateTab("analytics") : null}
                      style={{ background: "none", border: "none", color: "var(--violet2)", fontSize: "12.5px", fontWeight: 700, cursor: "pointer" }}
                    >
                      View Details →
                    </button>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
                    <div style={{ position: "relative", width: "110px", height: "110px", flexShrink: 0 }}>
                      <svg width="110" height="110" viewBox="0 0 110 110">
                        <circle cx="55" cy="55" r={ringRadius} fill="none" stroke={isSunrise ? "#efe4dc" : "#e2e8f0"} strokeWidth="10" />
                        <circle
                          cx="55"
                          cy="55"
                          r={ringRadius}
                          fill="none"
                          stroke={isSunrise ? "#d46326" : "#7c3aed"}
                          strokeWidth="10"
                          strokeLinecap="round"
                          strokeDasharray={ringCircumference}
                          strokeDashoffset={ringOffset}
                          transform="rotate(-90 55 55)"
                        />
                      </svg>
                      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: "20px", fontWeight: 800, color: "var(--text)" }}>{completePct}%</span>
                        <span style={{ fontSize: "10px", color: "var(--text3)", fontWeight: 600 }}>Overall</span>
                      </div>
                    </div>

                    <div style={{ flex: 1, minWidth: "180px", display: "flex", flexDirection: "column", gap: "10px" }}>
                      {[
                        { dot: "#7c3aed", label: "Proficiency & Coding", val: `${codingStat.done} / ${codingStat.total}` },
                        { dot: "#f59e0b", label: "Activity & Interviews", val: `${interviewStat.done} / ${interviewStat.total}` },
                        { dot: "#10b981", label: "Mastery Challenges", val: `${masteryStat.done} / ${masteryStat.total}` },
                        { dot: "#94a3b8", label: "Consistency Streaks", val: `${streakStat.done} / ${streakStat.total}` },
                      ].map((row) => (
                        <div key={row.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "13px" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "8px", color: "#334155", fontWeight: 600 }}>
                            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: row.dot }} />
                            {row.label}
                          </span>
                          <span style={{ fontWeight: 800, color: "#0f172a", fontVariantNumeric: "tabular-nums" }}>{row.val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Badges Section */}
              <div className="pf-card">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "10px", flexWrap: "wrap" }}>
                    <h3 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a" }}>Badges</h3>
                    <span style={{ fontSize: "12.5px", color: "#64748b" }}>
                      Collect badges for various achievements and showcase your skills.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAllBadges((p) => !p)}
                    style={{ background: "none", border: "none", color: "#6d28d9", fontSize: "12.5px", fontWeight: 700, cursor: "pointer" }}
                  >
                    {showAllBadges ? "Show Compact" : "View All Badges →"}
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
                  {(showAllBadges ? filtered : filtered.slice(0, 8)).map((ach) => {
                    const pillStyle = getBadgeCategoryStyle(ach.category);
                    return (
                      <div
                        key={ach.id}
                        style={{
                          padding: "16px",
                          borderRadius: "14px",
                          background: ach.is_unlocked ? "#ffffff" : "#f8fafc",
                          border: ach.is_unlocked ? "1px solid #c4b5fd" : "1px solid #e2e8f0",
                          boxShadow: ach.is_unlocked ? "0 6px 18px rgba(109, 40, 217, 0.08)" : "none",
                          display: "flex",
                          flexDirection: "column",
                          gap: "10px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                          <div
                            style={{
                              width: "34px",
                              height: "34px",
                              borderRadius: "10px",
                              background: ach.is_unlocked ? "#f5f3ff" : "#e2e8f0",
                              color: ach.is_unlocked ? "#6d28d9" : "#64748b",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                            }}
                          >
                            <NavIcon name={ach.is_unlocked ? "achievements" : "lock"} size={16} />
                          </div>
                          <span style={{ ...pillStyle, fontSize: "10px", fontWeight: 800, textTransform: "uppercase", padding: "3px 8px", borderRadius: "999px" }}>
                            {ach.category}
                          </span>
                        </div>

                        <div>
                          <div style={{ fontSize: "14px", fontWeight: 800, color: "#0f172a" }}>{ach.name}</div>
                          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "3px", lineHeight: 1.45 }}>
                            {ach.description}
                          </div>
                        </div>

                        <div style={{ marginTop: "auto", paddingTop: "8px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b", fontWeight: 700, marginBottom: "5px" }}>
                            <span>+{ach.reward_points} PTS</span>
                            <span>
                              {ach.is_unlocked ? `${ach.threshold_value} / ${ach.threshold_value}` : `${ach.current_progress} / ${ach.threshold_value}`}
                            </span>
                          </div>
                          <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "999px", overflow: "hidden" }}>
                            <div
                              style={{
                                width: `${ach.progress_percentage || 0}%`,
                                height: "100%",
                                background: ach.is_unlocked ? "linear-gradient(90deg, #6d28d9, #8b5cf6)" : "#94a3b8",
                              }}
                            />
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "6px", borderTop: "1px solid #e2e8f0", fontSize: "12px" }}>
                          {ach.is_unlocked ? (
                            <>
                              <span style={{ color: "#059669", fontWeight: 700 }}>✓ Unlocked</span>
                              {ach.reward_claimed ? (
                                <span style={{ color: "#64748b", fontWeight: 600 }}>Claimed</span>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleClaim(ach.id)}
                                  disabled={claimingId === ach.id}
                                  className="btn btn-primary btn-xs"
                                >
                                  {claimingId === ach.id ? "Claiming..." : "Claim Reward"}
                                </button>
                              )}
                            </>
                          ) : (
                            <span style={{ color: "#64748b", fontWeight: 600 }}>
                              In Progress ({Math.round(ach.progress_percentage || 0)}%)
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
