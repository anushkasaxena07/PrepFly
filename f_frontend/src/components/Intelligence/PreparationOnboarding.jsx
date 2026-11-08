import React, { useState } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const ROLES = [
  { id: "AI/ML Engineer", label: "AI / ML Engineer", desc: "ML pipelines, deep learning, math, NLP, transformers & ML systems." },
  { id: "Data Scientist", label: "Data Scientist", desc: "Statistical modeling, classical ML, tree ensembles, SQL & experimentation." },
  { id: "Data Engineer", label: "Data Engineer", desc: "ETL pipelines, large-scale dataset management, message queues & SQL." },
  { id: "Backend Engineer", label: "Backend Engineer", desc: "Distributed systems, concurrency, databases, REST APIs & caching." },
  { id: "Frontend Engineer", label: "Frontend Engineer", desc: "React/JS, Web APIs, DOM performance & client-server architecture." },
  { id: "Full Stack Engineer", label: "Full Stack Engineer", desc: "End-to-end web architecture, databases & frontend state." },
  { id: "Software Development Engineer (General)", label: "SDE / Software Engineer", desc: "Full algorithms, data structures & system architecture." },
  { id: "DevOps Engineer", label: "DevOps / SRE Engineer", desc: "Linux/OS, networking, scalability, load balancing & fault tolerance." },
  { id: "Data Analyst", label: "Data Analyst / BI", desc: "Advanced SQL, data modeling, statistics & Python." }
];

const EXPERIENCE_LEVELS = [
  "Fresher / Entry Level (0-1 yr)",
  "Junior (1-2 yrs)",
  "Mid-Level (2-5 years)",
  "Senior (5+ years)"
];

const TIME_OPTIONS = [
  { minutes: 30, label: "30 min / day", desc: "Steady maintenance" },
  { minutes: 45, label: "45 min / day", desc: "Focused pace" },
  { minutes: 60, label: "60 min / day", desc: "Balanced standard" },
  { minutes: 90, label: "90 min / day", desc: "Accelerated preparation" },
  { minutes: 120, label: "120 min / day", desc: "Intensive sprint" }
];

const FOCUS_OPTIONS = [
  "Machine Learning & Deep Learning",
  "Math & Statistics for ML",
  "ML System Design & MLOps",
  "Data Pipelines & Engineering",
  "Data Structures & Algorithms",
  "System Design & Distributed Systems",
  "Core Computer Science",
  "Behavioral & STAR Method",
  "Object-Oriented Design",
  "Databases & SQL"
];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function PreparationOnboarding({ onCompleted, onCancel }) {
  const [step, setStep] = useState(1);
  const [targetRole, setTargetRole] = useState("AI/ML Engineer");
  const [targetCompany, setTargetCompany] = useState("Top Tech Company");
  const [daysPlanned, setDaysPlanned] = useState(9);
  const [targetDate, setTargetDate] = useState(
    new Date(Date.now() + 9 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  );
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [experienceLevel, setExperienceLevel] = useState("Mid-Level (2-5 years)");
  const [focusAreas, setFocusAreas] = useState(["Machine Learning & Deep Learning", "Math & Statistics for ML", "ML System Design & MLOps"]);
  const [studyDays, setStudyDays] = useState(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleDaysChange = (days) => {
    setDaysPlanned(days);
    const d = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
    setTargetDate(d.toISOString().split("T")[0]);
  };

  const toggleFocus = (item) => {
    if (focusAreas.includes(item)) {
      setFocusAreas(focusAreas.filter((f) => f !== item));
    } else {
      setFocusAreas([...focusAreas, item]);
    }
  };

  const toggleDay = (day) => {
    if (studyDays.includes(day)) {
      if (studyDays.length > 1) {
        setStudyDays(studyDays.filter((d) => d !== day));
      }
    } else {
      setStudyDays([...studyDays, day]);
    }
  };

  const handleFinish = async () => {
    setIsSubmitting(true);
    setError("");
    try {
      const payload = {
        target_role: targetRole,
        target_company: targetCompany,
        target_date: targetDate,
        target_interview_date: targetDate,
        days_planned: daysPlanned,
        total_days: daysPlanned,
        preparation_duration_days: daysPlanned,
        daily_minutes: dailyMinutes,
        daily_pace: dailyMinutes,
        experience_level: experienceLevel,
        focus_areas: focusAreas,
        study_days: studyDays
      };

      const res = await intelligenceAPI.initializeProfile(payload);
      if (onCompleted) {
        onCompleted(res.profile);
      }
    } catch (err) {
      setError(err.message || "Failed to initialize preparation profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 overflow-y-auto">
      <div className="modal-card intelligence-root bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl relative text-slate-100">
        {/* Progress Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div>
            <span className="text-xs font-semibold tracking-wider uppercase text-cyan-400">
              PrepFly Intelligence
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-white mt-1">
              Personalized Preparation Setup
            </h2>
          </div>
          <div className="flex items-center space-x-1.5 text-xs text-slate-400">
            <span className={step >= 1 ? "text-cyan-400 font-bold" : ""}>1. Role</span>
            <span>&bull;</span>
            <span className={step >= 2 ? "text-cyan-400 font-bold" : ""}>2. Availability</span>
            <span>&bull;</span>
            <span className={step >= 3 ? "text-cyan-400 font-bold" : ""}>3. Focus</span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/50 border border-red-800 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Step 1: Target Role & Target Company */}
        {step === 1 && (
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Select Your Target Role
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {ROLES.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setTargetRole(r.id)}
                    className={`text-left p-3.5 rounded-xl border transition-all ${
                      targetRole === r.id
                        ? "bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950/30"
                        : "bg-slate-800/60 border-slate-700/60 hover:bg-slate-800"
                    }`}
                  >
                    <div className="font-semibold text-white text-sm">{r.label}</div>
                    <div className="text-xs text-slate-400 mt-1">{r.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Company / Tier
                </label>
                <input
                  type="text"
                  value={targetCompany}
                  onChange={(e) => setTargetCompany(e.target.value)}
                  placeholder="e.g. Google, Amazon, Stripe, Startups"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Experience Level
                </label>
                <select
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                >
                  {EXPERIENCE_LEVELS.map((exp) => (
                    <option key={exp} value={exp}>
                      {exp}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-5 py-2.5 rounded-lg text-sm transition-all shadow-md shadow-cyan-500/20"
              >
                Next: Availability &rarr;
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Availability, Days Planned & Target Date */}
        {step === 2 && (
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Daily Pace (Study Availability)
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {TIME_OPTIONS.map((t) => (
                  <button
                    key={t.minutes}
                    type="button"
                    onClick={() => setDailyMinutes(t.minutes)}
                    className={`p-3 rounded-xl border text-center transition-all ${
                      dailyMinutes === t.minutes
                        ? "bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950/30"
                        : "bg-slate-800/60 border-slate-700/60 hover:bg-slate-800"
                    }`}
                  >
                    <div className="font-bold text-white text-sm">{t.label}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{t.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-slate-300">
                  Days Planned
                </label>
                <span className="text-xs font-bold text-cyan-400">
                  {daysPlanned} Days Scheduled
                </span>
              </div>
              <div className="grid grid-cols-4 gap-2 mb-3">
                {[9, 14, 30, 60].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => handleDaysChange(d)}
                    className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                      daysPlanned === d
                        ? "bg-cyan-950/50 border-cyan-500 text-cyan-300"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    {d} Days
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Interview Date
                </label>
                <input
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Active Study Days / Week
                </label>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {DAYS.map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => toggleDay(d)}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                        studyDays.includes(d)
                          ? "bg-cyan-500 text-slate-950 font-bold"
                          : "bg-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      {d.slice(0, 3)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-4">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-slate-400 hover:text-white text-sm"
              >
                &larr; Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-5 py-2.5 rounded-lg text-sm transition-all shadow-md shadow-cyan-500/20"
              >
                Next: Focus Areas &rarr;
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Focus Areas & Confirmation */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Select Your Priority Preparation Pillars
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {FOCUS_OPTIONS.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => toggleFocus(f)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-left text-sm transition-all ${
                      focusAreas.includes(f)
                        ? "bg-cyan-950/40 border-cyan-500 text-white"
                        : "bg-slate-800/60 border-slate-700/60 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    <span>{f}</span>
                    <span className="text-cyan-400 font-bold">
                      {focusAreas.includes(f) ? "✓" : "+"}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-xs text-slate-300 space-y-1.5">
              <div className="font-semibold text-white">Summary Plan:</div>
              <div>&bull; <strong>Role:</strong> {targetRole} ({experienceLevel})</div>
              <div>&bull; <strong>Target:</strong> {targetCompany} by {targetDate} ({daysPlanned} days)</div>
              <div>&bull; <strong>Cadence:</strong> {dailyMinutes} min/day across {studyDays.length} days/week</div>
            </div>

            <div className="flex justify-between items-center pt-4">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="text-slate-400 hover:text-white text-sm"
              >
                &larr; Back
              </button>
              <div className="flex space-x-3">
                {onCancel && (
                  <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 rounded-lg text-slate-400 hover:text-white text-sm"
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleFinish}
                  className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold px-6 py-2.5 rounded-lg text-sm transition-all shadow-lg shadow-cyan-500/25 flex items-center space-x-2"
                >
                  {isSubmitting ? (
                    <span>Generating Roadmap...</span>
                  ) : (
                    <span>Create Preparation Plan &rarr;</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
