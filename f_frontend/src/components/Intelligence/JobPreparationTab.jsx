import React, { useState } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

export default function JobPreparationTab({ user, onStartInterview }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Ingestion inputs
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [rawText, setRawText] = useState("");

  // Analysis result
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedPersonality, setSelectedPersonality] = useState("professional");

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!rawText || rawText.trim().length < 20) {
      setError("Please paste a job description with at least 20 characters.");
      return;
    }

    setLoading(true);
    setError("");
    setSuccessMsg("");

    const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";

    try {
      const res = await intelligenceAPI.ingestJobDescription({
        user_id: candidateUserId,
        job_title: jobTitle,
        company: company,
        raw_text: rawText
      });
      if (res.data) {
        setAnalysisResult(res.data);
        setSuccessMsg("Job description successfully ingested and analyzed!");
      }
    } catch (err) {
      setError(err.message || "Failed to analyze job description.");
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchAva = async () => {
    if (!analysisResult?.job_profile?.id) return;
    setLoading(true);
    setError("");

    const candidateUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user_default";

    try {
      const res = await intelligenceAPI.startJobMatchedInterview(
        analysisResult.job_profile.id,
        { personality: selectedPersonality, user_id: candidateUserId }
      );
      if (res.data && onStartInterview) {
        onStartInterview(res.data);
      }
    } catch (err) {
      setError(err.message || "Failed to launch interview session.");
      setLoading(false);
    }
  };

  const gaps = analysisResult?.gap_analysis;
  const questions = analysisResult?.tailored_questions || [];
  const reqs = analysisResult?.requirements || [];

  return (
    <div id="page-jobs" className="page active" role="tabpanel">
      <div className="container intelligence-root space-y-6 text-slate-100 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
              PrepFly Intelligence
            </span>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
              Requirement-to-Skill
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            Job-Specific Preparation Engine
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Ingest target job descriptions, extract verified requirements, analyze skill gaps, and practice with tailored mock interviews.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800/80 rounded-xl text-red-200 text-sm">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-800/80 rounded-xl text-emerald-200 text-sm">
          {successMsg}
        </div>
      )}

      {/* Ingestion Form */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center space-x-2">
          <span>Target Job Ingestion</span>
        </h2>
        <form onSubmit={handleIngest} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Target Role / Job Title
              </label>
              <input
                type="text"
                placeholder="e.g. Senior Backend Engineer"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Company Name
              </label>
              <input
                type="text"
                placeholder="e.g. Stripe, Netflix, Google"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Raw Job Description Text
            </label>
            <textarea
              rows={6}
              placeholder="Paste the full job description, role requirements, and qualifications..."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              className="w-full px-4 py-3 bg-slate-800/80 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-500 leading-relaxed font-mono text-xs"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-cyan-900/30 flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Analyzing Requirements...</span>
                </>
              ) : (
                <span>Analyze Job Description</span>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Analysis Results */}
      {analysisResult && (
        <div className="space-y-6">
          {/* Top Score Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
              <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Overall Match</span>
              <div className="text-3xl font-black text-cyan-400 mt-2">
                {gaps?.overall_match_percentage || 0}%
              </div>
              <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-800 text-slate-300">
                {gaps?.readiness_verdict || "CALCULATING"}
              </span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
              <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Required Skills Match</span>
              <div className="text-3xl font-black text-emerald-400 mt-2">
                {gaps?.required_match_percentage || 0}%
              </div>
              <span className="inline-block mt-2 text-xs text-slate-400">
                Core must-have criteria
              </span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 text-center">
              <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Preferred Skills Bonus</span>
              <div className="text-3xl font-black text-indigo-400 mt-2">
                {gaps?.preferred_match_percentage || 0}%
              </div>
              <span className="inline-block mt-2 text-xs text-slate-400">
                Competitive bonus skills
              </span>
            </div>
          </div>

          {/* Critical Gaps & Aligned Skills */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Critical Gaps */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-md font-bold text-red-400 mb-3 flex items-center space-x-2">
                <span>Critical Skill Gaps ({gaps?.critical_gaps?.length || 0})</span>
              </h3>
              {(!gaps?.critical_gaps || gaps.critical_gaps.length === 0) ? (
                <p className="text-sm text-slate-400">No critical proficiency gaps found! You meet all core must-have requirements.</p>
              ) : (
                <div className="space-y-3">
                  {gaps.critical_gaps.map((gap, idx) => (
                    <div key={idx} className="p-3 bg-red-950/20 border border-red-900/40 rounded-xl flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-sm text-white">{gap.skill_name}</div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          Current: {gap.current_proficiency}% • Target: {gap.target_proficiency}%
                        </div>
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 bg-red-900/60 text-red-200 rounded-lg">
                        -{gap.deficit}% deficit
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Aligned Skills */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-md font-bold text-emerald-400 mb-3 flex items-center space-x-2">
                <span>Aligned Verified Skills ({gaps?.aligned_skills?.length || 0})</span>
              </h3>
              {(!gaps?.aligned_skills || gaps.aligned_skills.length === 0) ? (
                <p className="text-sm text-slate-400">Complete more coding challenges or assessments to verify your skills.</p>
              ) : (
                <div className="space-y-3">
                  {gaps.aligned_skills.map((al, idx) => (
                    <div key={idx} className="p-3 bg-emerald-950/20 border border-emerald-900/40 rounded-xl flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-sm text-white">{al.skill_name}</div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          Proficiency: {al.current_proficiency}%
                        </div>
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 bg-emerald-900/60 text-emerald-200 rounded-lg">
                        Verified Match
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Structured Requirements with Text Provenance */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-md font-bold text-white mb-4">
              Extracted Requirements & Provenance ({reqs.length})
            </h3>
            <div className="divide-y divide-slate-800">
              {reqs.map((req, idx) => (
                <div key={idx} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm text-white">
                        {req.normalized_skill_id.replace("_", " ").toUpperCase()}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        req.is_required ? "bg-cyan-950 text-cyan-300 border border-cyan-800" : "bg-slate-800 text-slate-400"
                      }`}>
                        {req.is_required ? "REQUIRED" : "PREFERRED"}
                      </span>
                      <span className="text-xs text-slate-500 uppercase">{req.requirement_type}</span>
                    </div>
                    <p className="text-xs text-slate-400 italic">
                      "{req.evidence_text}"
                    </p>
                  </div>
                  <span className="text-xs font-bold text-slate-300 whitespace-nowrap">
                    Weight: {req.importance_weight}x
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Tailored Questions with Quality Scores */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="text-md font-bold text-white">
                  Tailored Interview Questions ({questions.length})
                </h3>
                <p className="text-xs text-slate-400">
                  Targeted questions generated with automated Relevance, Clarity, and Depth scoring.
                </p>
              </div>

              {/* Ava Launch Action */}
              <div className="flex items-center space-x-3">
                <select
                  value={selectedPersonality}
                  onChange={(e) => setSelectedPersonality(e.target.value)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs"
                >
                  <option value="friendly">Friendly Recruiter</option>
                  <option value="professional">Professional Tech Lead</option>
                  <option value="challenging">Challenging Staff Engineer</option>
                  <option value="strict">Strict Bar Raiser</option>
                </select>

                <button
                  onClick={handleLaunchAva}
                  disabled={loading}
                  className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-xl text-xs transition shadow-lg"
                >
                  Start Job-Matched Ava Mock
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {questions.map((q, idx) => (
                <div key={idx} className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-cyan-400 uppercase">{q.category} • {q.difficulty}</span>
                    <span className="px-2 py-0.5 rounded font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                      Quality Score: {q.quality_score}/10
                    </span>
                  </div>
                  <p className="text-sm text-slate-100 font-medium leading-relaxed">
                    {q.question_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  </div>
  );
}

