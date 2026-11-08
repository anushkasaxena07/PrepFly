import React, { useState, useEffect } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

export default function RetrievalDrillModal({ skillId, skillName, onClose, onCompleted }) {
  const [drill, setDrill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState("");
  const [showRubric, setShowRubric] = useState(false);
  const [score, setScore] = useState(80);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDrill();
  }, [skillId]);

  const fetchDrill = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await intelligenceAPI.getRetrievalDrill(skillId);
      setDrill(res.drill);
    } catch (err) {
      setError(err.message || "Failed to load retrieval drill.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const res = await intelligenceAPI.submitRevisionDrill({
        skill_id: skillId,
        score: parseFloat(score),
        notes: answer
      });
      setResult(res.result);
      if (onCompleted) {
        onCompleted(res.result);
      }
    } catch (err) {
      setError(err.message || "Failed to submit revision drill.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay intelligence-root fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="modal-card intelligence-root bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 sm:p-7 shadow-2xl relative text-slate-100">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-5">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
              Spaced Retrieval Practice &bull; 5 Minutes
            </span>
            <h3 className="text-lg font-bold text-white mt-0.5">
              {skillName || drill?.skill_name || skillId}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
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

        {loading ? (
          <div className="py-12 text-center text-slate-400">
            <div className="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Loading retrieval prompt...
          </div>
        ) : result ? (
          <div className="space-y-4 text-center py-3">
            <div
              className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto text-2xl font-bold ${
                result.outcome === "ADVANCED"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-700"
                  : result.outcome === "MAINTAINED"
                  ? "bg-amber-950 text-amber-400 border border-amber-700"
                  : "bg-red-950 text-red-400 border border-red-700"
              }`}
            >
              {result.outcome === "ADVANCED" ? "✓" : "↺"}
            </div>
            <h4 className="text-lg font-bold text-white">
              {result.outcome === "ADVANCED"
                ? "Retention Interval Expanded!"
                : result.outcome === "MAINTAINED"
                ? "Recall In Interval Maintained"
                : "Remedial Refresh Scheduled"}
            </h4>
            <p className="text-xs text-slate-300 max-w-md mx-auto">
              Your memory retrieval has updated this skill to <strong>Stage {result.new_stage}</strong>.
              Next review due on {new Date(result.next_due_at).toLocaleDateString()}.
            </p>
            <div className="pt-3">
              <button
                type="button"
                onClick={onClose}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-5 py-2 rounded-lg text-sm"
              >
                Close & Return to Roadmap
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Question Card */}
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Retrieval Challenge:
              </span>
              <p className="text-slate-100 font-medium text-sm mt-1 leading-relaxed">
                {drill?.question}
              </p>
            </div>

            {/* Answer Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Your Answer / Explanation:
              </label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={4}
                placeholder="State your technical answer directly from memory before checking the rubric..."
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 focus:outline-none focus:border-amber-500 font-mono"
              />
            </div>

            {/* Rubric Reveal Toggle */}
            <div>
              <button
                type="button"
                onClick={() => setShowRubric(!showRubric)}
                className="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center space-x-1"
              >
                <span>{showRubric ? "▼ Hide Rubric & Criteria" : "▶ Reveal Rubric & Self-Grade"}</span>
              </button>

              {showRubric && (
                <div className="mt-2.5 p-3.5 bg-slate-950/70 border border-amber-900/40 rounded-xl space-y-3">
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">
                      Evaluation Criteria:
                    </span>
                    <p className="text-xs text-slate-300 mt-1">{drill?.rubric}</p>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-200 mb-1">
                      Self-Assess Your Recall Accuracy ({score}%):
                    </label>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={5}
                      value={score}
                      onChange={(e) => setScore(e.target.value)}
                      className="w-full accent-amber-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                      <span>0% (Blanked)</span>
                      <span>50% (Partial)</span>
                      <span>75% (Solid)</span>
                      <span>100% (Flawless)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Submit */}
            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-slate-400 hover:text-white text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleSubmit}
                className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold px-5 py-2 rounded-lg text-sm transition-all shadow-md shadow-amber-500/20"
              >
                {submitting ? "Updating Retention..." : "Record Drill &rarr;"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

