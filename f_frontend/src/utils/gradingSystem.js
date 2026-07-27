// Professional Grading System Utility for Frontend

export const GRADE_TIERS = [
  { min: 95, grade: "A+", label: "Outstanding", desc: "Ready for Top Product Companies", color: "#059669", bgColor: "rgba(5, 150, 105, 0.15)", rec: "Highly Recommended", level: "Elite" },
  { min: 90, grade: "A", label: "Excellent", desc: "Strong Candidate", color: "#22c55e", bgColor: "rgba(34, 197, 94, 0.15)", rec: "Recommended", level: "Excellent" },
  { min: 85, grade: "A-", label: "Very Good", desc: "Interview Ready", color: "#4ade80", bgColor: "rgba(74, 222, 128, 0.15)", rec: "Recommended", level: "Good" },
  { min: 80, grade: "B+", label: "Good", desc: "Minor Improvements Needed", color: "#2563eb", bgColor: "rgba(37, 99, 235, 0.15)", rec: "Recommended with Minor Improvements", level: "Good" },
  { min: 75, grade: "B", label: "Above Average", desc: "Needs More Practice", color: "#38bdf8", bgColor: "rgba(56, 189, 248, 0.15)", rec: "Recommended with Minor Improvements", level: "Average" },
  { min: 70, grade: "B-", label: "Average", desc: "Moderate Improvement Required", color: "#14b8a6", bgColor: "rgba(20, 184, 166, 0.15)", rec: "Needs Further Evaluation", level: "Average" },
  { min: 65, grade: "C+", label: "Fair", desc: "Not Yet Interview Ready", color: "#f97316", bgColor: "rgba(249, 115, 22, 0.15)", rec: "Needs Further Evaluation", level: "Below Average" },
  { min: 60, grade: "C", label: "Needs Improvement", desc: "Needs Improvement", color: "#f59e0b", bgColor: "rgba(245, 158, 11, 0.15)", rec: "Needs Significant Improvement", level: "Below Average" },
  { min: 50, grade: "D", label: "Poor Performance", desc: "Poor Performance", color: "#ef4444", bgColor: "rgba(239, 68, 68, 0.15)", rec: "Needs Significant Improvement", level: "Beginner" },
  { min: 0,  grade: "F", label: "Significant Improvement Required", desc: "Significant Improvement Required", color: "#991b1b", bgColor: "rgba(153, 27, 27, 0.15)", rec: "Not Recommended Yet", level: "Beginner" }
];

export function getGradeInfo(score100) {
  const s = Math.min(100, Math.max(0, Math.round(Number(score100) || 0)));
  for (const tier of GRADE_TIERS) {
    if (s >= tier.min) {
      return { ...tier, score: s };
    }
  }
  return { ...GRADE_TIERS[GRADE_TIERS.length - 1], score: s };
}

export function computeSectionGrades(overallScore100 = 75, rawFeedbacks = []) {
  const base100 = Math.min(100, Math.max(0, Math.round(overallScore100)));
  
  if (base100 === 0) {
    const categories = [
      "Communication", "Technical Knowledge", "Problem Solving", "Confidence",
      "Behavioral Skills", "Resume Knowledge", "Project Explanation", "Leadership",
      "Grammar", "Vocabulary"
    ];
    return categories.map(name => ({
      name,
      score: 0,
      grade: "F",
      color: "#ef4444",
      bgColor: "rgba(239, 68, 68, 0.15)",
      label: "Unevaluated / No Responses"
    }));
  }

  const rawScores = {
    "Communication": Math.min(100, Math.max(0, base100 + 4)),
    "Technical Knowledge": Math.min(100, Math.max(0, base100 + 2)),
    "Problem Solving": Math.min(100, Math.max(0, base100 - 3)),
    "Confidence": Math.min(100, Math.max(0, base100 + 5)),
    "Behavioral Skills": Math.min(100, Math.max(0, base100 - 2)),
    "Resume Knowledge": Math.min(100, Math.max(0, base100 + 3)),
    "Project Explanation": Math.min(100, Math.max(0, base100 + 6)),
    "Leadership": Math.min(100, Math.max(0, base100 - 4)),
    "Grammar": Math.min(100, Math.max(0, Math.round(base100 * 0.95))),
    "Vocabulary": Math.min(100, Math.max(0, Math.round(base100 * 0.92)))
  };

  return Object.keys(rawScores).map(name => {
    const sVal = rawScores[name];
    const gInfo = getGradeInfo(sVal);
    return {
      name,
      score: sVal,
      grade: gInfo.grade,
      color: gInfo.color,
      bgColor: gInfo.bgColor,
      label: gInfo.label
    };
  });
}

export function getBadges(overallScore100, sections = []) {
  const badges = [];
  const secDict = {};
  sections.forEach(s => { secDict[s.name] = s.score; });

  if ((secDict["Communication"] || 0) >= 88) {
    badges.push({ name: "Excellent Communicator", icon: "🗣️", desc: "Masterful clarity and articulation" });
  }
  if ((secDict["Technical Knowledge"] || 0) >= 88) {
    badges.push({ name: "Technical Expert", icon: "💻", desc: "Deep domain and engineering proficiency" });
  }
  if ((secDict["Problem Solving"] || 0) >= 88) {
    badges.push({ name: "Problem Solver", icon: "🧩", desc: "Structured and sharp analytical reasoning" });
  }
  if ((secDict["Leadership"] || 0) >= 82) {
    badges.push({ name: "Leadership Potential", icon: "👑", desc: "Strong ownership and decision-making" });
  }
  if ((secDict["Project Explanation"] || 0) >= 85) {
    badges.push({ name: "Project Specialist", icon: "🚀", desc: "Impactful project architecture walk-through" });
  }
  if ((secDict["Behavioral Skills"] || 0) >= 85) {
    badges.push({ name: "Behavioral Star", icon: "⭐", desc: "Effective STAR technique responses" });
  }
  if (overallScore100 >= 90) {
    badges.push({ name: "Quick Learner", icon: "⚡", desc: "Adaptive candidate with high learning velocity" });
    badges.push({ name: "Creative Thinker", icon: "💡", desc: "Innovative problem formulation" });
  }

  if (badges.length === 0) {
    badges.push({ name: "Promising Candidate", icon: "🌱", desc: "Solid foundation ready for growth" });
  }

  return badges;
}
