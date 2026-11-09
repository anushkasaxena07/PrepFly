import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

export default function DiagnosticAssessmentModal({ onClose, onCompleted, targetRole, experienceLevel }) {
  const [loading, setLoading] = useState(true);
  const [assessment, setAssessment] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    initAssessment();
  }, []);

  const initAssessment = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await intelligenceAPI.startDiagnosticAssessment({
        target_role: targetRole,
        experience_level: experienceLevel
      });
      setAssessment(res.assessment);
      // Initialize answer map
      const initialAnswers = {};
      (res.assessment.questions || []).forEach((q) => {
        initialAnswers[q.id || q.question_id] = "";
      });
      setAnswers(initialAnswers);
    } catch (err) {
      setError(err.message || "Failed to start diagnostic assessment.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (val) => {
    if (!assessment) return;
    const currentQ = assessment.questions[currentIndex];
    const qid = currentQ.id || currentQ.question_id;
    setAnswers({
      ...answers,
      [qid]: val
    });
  };

  const handleFinish = () => {
    if (onCompleted) {
      onCompleted(evaluation);
    }
    onClose();
  };

  const handleSubmit = async () => {
    if (!assessment) return;
    setSubmitting(true);
    setError("");
    try {
      const assId = assessment.id || assessment.assessment_id;
      const res = await intelligenceAPI.submitAssessment(assId, answers);
      setEvaluation(res.evaluation);
    } catch (err) {
      setError(err.message || "Failed to submit assessment.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
        <div className="modal-card intelligence-root bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full text-center text-slate-200">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">Generating Adaptive Diagnostic</h3>
          <p className="text-xs text-slate-400">
            Selecting role-tailored questions across DSA, System Design, Core CS, and Interview Skills...
          </p>
        </div>
      </div>
    );
  }

  const questions = assessment?.questions || [];
  const currentQ = questions[currentIndex];
  const qid = currentQ ? (currentQ.id || currentQ.question_id) : "";
  const currentAnswer = answers[qid] || "";
  const isLast = currentIndex === questions.length - 1;

  return (
    <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="modal-card intelligence-root bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl relative text-slate-100 my-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div>
            <span className="text-xs font-semibold tracking-wider uppercase text-cyan-400">
              Diagnostic Assessment
            </span>
            <h2 className="text-xl font-bold text-white mt-0.5">
              {assessment?.title || "Baseline Competency Evaluation"}
            </h2>
          </div>
          <button
            type="button"
            onClick={evaluation ? handleFinish : onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg text-sm"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/50 border border-red-800 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Evaluation Summary View */}
        {evaluation ? (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-cyan-950/40 via-slate-800/60 to-slate-900 border border-cyan-800/40 rounded-xl p-5 text-center">
              <span className="text-xs font-semibold uppercase text-cyan-400 tracking-wider">
                Baseline Diagnostic Complete
              </span>
              <div className="text-4xl font-extrabold text-white mt-1">
                {evaluation.overall_score || 0}%
              </div>
              <p className="text-xs text-slate-300 mt-2 max-w-lg mx-auto">
                {evaluation.summary || "Your initial baseline is calibrated. Your personalized preparation roadmap has been generated."}
              </p>
            </div>

            {/* Concept Breakdown Grid */}
            <div>
              <h4 className="text-sm font-semibold text-slate-200 mb-3">
                Concept Performance Breakdown:
              </h4>
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {(evaluation.results || evaluation.evaluated_questions || []).map((r, i) => (
                  <div
                    key={i}
                    className="p-3.5 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-white">
                        {(r.skill_id || "")
                          .replace("ml_", "ML: ")
                          .replace("dl_", "Deep Learning: ")
                          .replace("genai_", "GenAI: ")
                          .replace("dsa_", "DSA: ")
                          .replace("cs_", "CS: ")
                          .replace("sys_", "System: ")
                          .replace("soft_", "Skills: ")
                          .replace(/_/g, " ")
                          .toUpperCase()}
                      </span>
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded ${r.score >= 70
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : r.score >= 50
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-red-950 text-red-400 border border-red-800"
                          }`}
                      >
                        {r.score}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{r.feedback}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-3">
              <button
                type="button"
                onClick={handleFinish}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-6 py-2.5 rounded-lg text-sm transition-all shadow-md shadow-cyan-500/20"
              >
                Go to Preparation Roadmap &rarr;
              </button>
            </div>
          </div>
        ) : (
          /* Question Runner View */
          <div className="space-y-5">
            {/* Progress indicators */}
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-medium">
                Question {currentIndex + 1} of {questions.length}
              </span>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 text-[11px] font-semibold">
                  {currentQ?.skill_name || currentQ?.skill_id}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[11px]">
                  {currentQ?.difficulty}
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-cyan-500 h-full transition-all duration-300"
                style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
              />
            </div>

            {/* Question Text */}
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4 sm:p-5">
              <p className="text-slate-100 font-medium text-sm sm:text-base leading-relaxed">
                {currentQ?.question_text}
              </p>
            </div>

            {/* Candidate Answer Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Your Technical Explanation / Code / Approach:
              </label>
              <textarea
                value={currentAnswer}
                onChange={(e) => handleAnswerChange(e.target.value)}
                placeholder="State your data structures, algorithm invariants, asymptotic time/space bounds, and key edge case considerations..."
                rows={7}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3.5 text-sm text-slate-100 font-mono placeholder:font-sans placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex(currentIndex - 1)}
                className="text-slate-400 hover:text-white disabled:opacity-30 text-sm font-medium"
              >
                &larr; Previous Question
              </button>

              {isLast ? (
                <button
                  type="button"
                  disabled={submitting || !currentAnswer.trim()}
                  onClick={handleSubmit}
                  className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold px-6 py-2.5 rounded-lg text-sm transition-all shadow-md shadow-cyan-500/20"
                >
                  {submitting ? "Grading with Rubric..." : "Submit Diagnostic Baseline &rarr;"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setCurrentIndex(currentIndex + 1)}
                  className="bg-slate-800 hover:bg-slate-700 text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition-all"
                >
                  Next Question &rarr;
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

