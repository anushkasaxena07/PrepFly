import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const STEPS = [
  { id: 1, label: "Why This Matters", short: "Why" },
  { id: 2, label: "Core Concept", short: "Learn" },
  { id: 3, label: "Guided Practice", short: "Practice" },
  { id: 4, label: "Practical Assignment", short: "Task" },
  { id: 5, label: "Submit Solution", short: "Submit" },
  { id: 6, label: "Evaluation", short: "Review" },
  { id: 7, label: "Next Action", short: "Next" }
];

export default function LearningWorkspaceModal({
  activity,
  targetRole,
  targetCompany,
  onClose,
  onCompleted
}) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState("");

  // Step 3 Practice states (hints & answers toggle)
  const [showHint, setShowHint] = useState({});
  const [showExplanation, setShowExplanation] = useState({});

  // Step 5 Submission state
  const [submissionText, setSubmissionText] = useState("");
  const [codeSubmission, setCodeSubmission] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Step 6 & 7 Evaluation state
  const [evaluation, setEvaluation] = useState(null);

  useEffect(() => {
    fetchWorkspace();
  }, [activity]);

  const fetchWorkspace = async () => {
    if (!activity) return;
    setLoading(true);
    setError("");
    try {
      const actId = activity.id || activity.activity_id;
      const res = await intelligenceAPI.getLearningWorkspace(actId, {
        skillId: activity.skill_id,
        targetRole,
        targetCompany
      });
      setWorkspace(res.workspace);
      if (res.workspace?.assignment?.starter_code) {
        setCodeSubmission(res.workspace.assignment.starter_code);
      }
    } catch (err) {
      setError(err.message || "Failed to load learning workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!submissionText.trim() && !codeSubmission.trim()) {
      setError("Please provide a written explanation or your solution code.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const actId = activity.id || activity.activity_id;
      const res = await intelligenceAPI.submitAssignment(actId, {
        submissionText,
        codeSubmission
      });
      setEvaluation(res.evaluation);
      setCurrentStep(6);
      if (onCompleted) {
        onCompleted(res.evaluation);
      }
    } catch (err) {
      setError(err.message || "Failed to evaluate assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full text-center text-slate-200">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-1">Loading 7-Step Learning Workspace</h3>
          <p className="text-xs text-slate-400">
            Synthesizing production context, code examples, and practical assignments...
          </p>
        </div>
      </div>
    );
  }

  const learnData = workspace?.learn || {};
  const assignmentData = workspace?.assignment || {};
  const practiceItems = workspace?.practice || [];

  return (
    <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-3 sm:p-6 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-5 sm:p-7 shadow-2xl relative text-slate-100 my-auto flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                Step {currentStep} of 7 — {STEPS[currentStep - 1]?.label}
              </span>
              <span className="text-[11px] text-slate-400">
                {activity?.difficulty || "Intermediate"} • {activity?.estimated_minutes || 45} mins
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white mt-1">
              {workspace?.title || activity?.title || "Topic Learning Workspace"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg text-sm transition"
            title="Close Workspace"
          >
            ✕
          </button>
        </div>

        {/* 7-Step Horizontal Progress Bar */}
        <div className="grid grid-cols-7 gap-1 sm:gap-2 mb-5">
          {STEPS.map((s) => {
            const isActive = currentStep === s.id;
            const isCompleted = currentStep > s.id;
            return (
              <button
                key={s.id}
                onClick={() => {
                  if (s.id <= 5 || evaluation) {
                    setCurrentStep(s.id);
                  }
                }}
                disabled={s.id > 5 && !evaluation}
                className={`py-1.5 px-1 rounded-lg text-[10px] sm:text-xs font-semibold text-center transition ${
                  isActive
                    ? "bg-cyan-500 text-black shadow-lg shadow-cyan-500/30"
                    : isCompleted
                    ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/60"
                    : "bg-slate-800/60 text-slate-400 hover:text-slate-200"
                }`}
              >
                <span className="hidden sm:inline">{s.id}. </span>{s.short}
              </button>
            );
          })}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Workspace Body (Scrollable) */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 text-xs sm:text-sm">
          
          {/* ── STEP 1: WHY THIS MATTERS ── */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-cyan-950/40 via-slate-800/40 to-slate-900 border border-cyan-800/40 rounded-xl p-5">
                <h3 className="text-sm font-bold text-cyan-300 mb-2 uppercase tracking-wide">
                  Strategic Interview Importance
                </h3>
                <p className="text-slate-300 leading-relaxed whitespace-pre-line">
                  {workspace?.why_this_matters ||
                    "This topic directly targets core architectural and algorithmic evaluations prioritized by top tech interviewers."}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Target Role Fit</span>
                  <p className="text-white font-semibold mt-1">{targetRole || "Software Engineer"}</p>
                  <p className="text-slate-400 text-xs mt-1">
                    Evaluated during technical rounds to confirm foundational competence.
                  </p>
                </div>
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Target Company</span>
                  <p className="text-white font-semibold mt-1">{targetCompany || "Enterprise Engineering"}</p>
                  <p className="text-slate-400 text-xs mt-1">
                    Tests your ability to reason about production invariants and edge cases.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 2: LEARN CORE CONCEPTS ── */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wide mb-1">
                  1. Simple Definition
                </h4>
                <p className="text-slate-200 leading-relaxed">
                  {learnData.simple_definition || "Core conceptual intuition."}
                </p>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wide mb-1">
                  2. Technical Mechanism & Invariants
                </h4>
                <p className="text-slate-200 leading-relaxed whitespace-pre-line">
                  {learnData.technical_explanation || "Detailed operational mechanism."}
                </p>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wide mb-1">
                  3. Real-World Production Example
                </h4>
                <p className="text-slate-200 leading-relaxed">
                  {learnData.real_world_example || "Applied engineering architecture."}
                </p>
              </div>

              {learnData.code_example && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-emerald-400 uppercase">
                      4. Canonical Code Implementation
                    </span>
                  </div>
                  <pre className="font-mono text-xs text-slate-300 overflow-x-auto p-3 bg-slate-900 rounded-lg">
                    <code>{learnData.code_example}</code>
                  </pre>
                </div>
              )}

              {learnData.common_mistakes?.length > 0 && (
                <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wide mb-2">
                    5. Common Interview Pitfalls
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-slate-300">
                    {learnData.common_mistakes.map((m, idx) => (
                      <li key={idx}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 3: GUIDED PRACTICE ── */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <p className="text-slate-300 text-xs">
                Work through these progressive warm-up questions. Reveal hints if you get stuck, and examine the explanation before continuing to the practical assignment.
              </p>
              {practiceItems.map((p, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-cyan-400 uppercase">
                      Practice Exercise {idx + 1}
                    </span>
                  </div>
                  <p className="text-white font-medium">{p.question}</p>

                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={() => setShowHint(prev => ({ ...prev, [idx]: !prev[idx] }))}
                      className="px-2.5 py-1 text-[11px] font-semibold bg-slate-700/60 hover:bg-slate-700 text-slate-200 rounded-lg transition"
                    >
                      {showHint[idx] ? "Hide Hint" : "💡 View Hint"}
                    </button>
                    <button
                      onClick={() => setShowExplanation(prev => ({ ...prev, [idx]: !prev[idx] }))}
                      className="px-2.5 py-1 text-[11px] font-semibold bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-800/50 rounded-lg transition"
                    >
                      {showExplanation[idx] ? "Hide Answer" : "✓ View Explanation"}
                    </button>
                  </div>

                  {showHint[idx] && (
                    <div className="p-2.5 bg-amber-950/30 border border-amber-800/30 rounded-lg text-xs text-amber-200">
                      <strong>Hint:</strong> {p.hint}
                    </div>
                  )}

                  {showExplanation[idx] && (
                    <div className="p-3 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 leading-relaxed">
                      <strong>Explanation:</strong> {p.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── STEP 4: PRACTICAL ASSIGNMENT ── */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-slate-900 via-slate-800/70 to-slate-900 border border-cyan-800/40 rounded-xl p-5">
                <span className="text-[11px] font-bold uppercase text-cyan-400 tracking-wider">
                  Hands-On Technical Challenge
                </span>
                <h3 className="text-base font-bold text-white mt-1">
                  {assignmentData.prompt || "Complete the challenge specification."}
                </h3>
              </div>

              {assignmentData.deliverables && (
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase mb-2">Deliverables</h4>
                  <p className="text-slate-200">{assignmentData.deliverables}</p>
                </div>
              )}

              {assignmentData.input_output_examples?.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase mb-2">
                    Input / Output Specifications
                  </h4>
                  <div className="space-y-2">
                    {assignmentData.input_output_examples.map((ex, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 rounded-lg font-mono text-xs text-slate-300">
                        {ex}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {assignmentData.edge_cases?.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-amber-400 uppercase mb-2">
                    Mandatory Edge Cases to Handle
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-slate-300">
                    {assignmentData.edge_cases.map((ec, i) => (
                      <li key={i}>{ec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {assignmentData.rubric && (
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-cyan-400 uppercase mb-2">Evaluation Rubric</h4>
                  <div className="space-y-1 text-xs text-slate-300">
                    <p>
                      <strong className="text-emerald-400">Full Credit (100%):</strong>{" "}
                      {assignmentData.rubric.full_credit}
                    </p>
                    <p>
                      <strong className="text-amber-400">Partial Credit (60%):</strong>{" "}
                      {assignmentData.rubric.partial_credit}
                    </p>
                    <p>
                      <strong className="text-rose-400">Zero Credit:</strong>{" "}
                      {assignmentData.rubric.zero_credit}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 5: SUBMIT SOLUTION ── */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                  1. Technical Explanation & Complexity Analysis
                </label>
                <textarea
                  rows={4}
                  value={submissionText}
                  onChange={(e) => setSubmissionText(e.target.value)}
                  placeholder="State your algorithm invariants, space-time complexity bounds O(N), and edge cases considered..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                  2. Code Implementation
                </label>
                <textarea
                  rows={8}
                  value={codeSubmission}
                  onChange={(e) => setCodeSubmission(e.target.value)}
                  placeholder="Paste or write your Python / JavaScript / Java code solution here..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs sm:text-sm text-emerald-400 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
            </div>
          )}

          {/* ── STEP 6: EVALUATION RESULTS ── */}
          {currentStep === 6 && evaluation && (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-cyan-950/50 via-slate-800/70 to-slate-900 border border-cyan-800/50 rounded-xl p-5 text-center">
                <span className="text-xs font-semibold uppercase text-cyan-400 tracking-wider">
                  Assignment Evaluation Score
                </span>
                <div className="text-4xl font-extrabold text-white mt-1">
                  {evaluation.score}%
                </div>
                <div className="inline-block mt-2 px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-cyan-300 border border-cyan-800/40">
                  Status: {evaluation.status}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-emerald-400 uppercase mb-1">
                    Demonstrated Invariants
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-slate-300 text-xs">
                    {(evaluation.identified_strengths || []).map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-amber-400 uppercase mb-1">
                    Missing Concepts & Mistakes
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-slate-300 text-xs">
                    {(evaluation.missing_concepts || []).length > 0 ? (
                      evaluation.missing_concepts.map((m, idx) => (
                        <li key={idx}>{m}</li>
                      ))
                    ) : (
                      <li className="text-slate-400">No major conceptual gaps identified!</li>
                    )}
                  </ul>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase mb-1">
                  Actionable Mentor Feedback
                </h4>
                <p className="text-slate-200 leading-relaxed text-xs sm:text-sm">
                  {evaluation.actionable_feedback}
                </p>
              </div>
            </div>
          )}

          {/* ── STEP 7: NEXT ACTION ── */}
          {currentStep === 7 && evaluation && (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-emerald-950/40 via-slate-800/50 to-slate-900 border border-emerald-800/40 rounded-xl p-5 text-center">
                <span className="text-xs font-bold uppercase text-emerald-400 tracking-wider">
                  Verified Skill Calibration Updated
                </span>
                <h3 className="text-base font-bold text-white mt-1">
                  Evidence Recorded at Weight 1.2
                </h3>
                <p className="text-xs text-slate-300 mt-1 max-w-lg mx-auto">
                  Your demonstrated proficiency has been incorporated into your Candidate Intelligence Matrix.
                </p>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wide mb-2">
                  Recommended Follow-Up Path
                </h4>
                <p className="text-white font-semibold text-sm">
                  {evaluation.next_recommendation || "Proceed to the next scheduled roadmap activity."}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold rounded-lg text-xs hover:brightness-110 transition shadow-lg shadow-cyan-500/20"
                  >
                    Return to Preparation Roadmap →
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer Navigation */}
        <div className="border-t border-slate-800 pt-4 mt-4 flex items-center justify-between">
          <button
            onClick={() => setCurrentStep(prev => Math.max(1, prev - 1))}
            disabled={currentStep === 1}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition"
          >
            ← Previous Step
          </button>

          {currentStep < 5 && (
            <button
              onClick={() => setCurrentStep(prev => Math.min(5, prev + 1))}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-cyan-500 text-black hover:bg-cyan-400 transition"
            >
              Next Step →
            </button>
          )}

          {currentStep === 5 && (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-5 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-500 text-black hover:brightness-110 disabled:opacity-50 transition shadow-lg shadow-emerald-500/20"
            >
              {submitting ? "Evaluating Rubrics..." : "Submit & Evaluate →"}
            </button>
          )}

          {currentStep === 6 && (
            <button
              onClick={() => setCurrentStep(7)}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-cyan-500 text-black hover:bg-cyan-400 transition"
            >
              View Next Action →
            </button>
          )}

          {currentStep === 7 && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-slate-700 text-white hover:bg-slate-600 transition"
            >
              Close Workspace
            </button>
          )}
        </div>

      </div>
    </div>
  );
}

