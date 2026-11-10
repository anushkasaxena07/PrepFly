import React, { useState, useEffect, useRef } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const DEFAULT_PILLS = [
  "Explain from scratch",
  "Real-world example",
  "Harder question",
  "I only have 30 mins today",
  "Prepare for tomorrow",
  "Evaluate my answer",
  "Start a mock interview"
];

export default function MentorChatDrawer({
  isOpen,
  onClose,
  activeActivity,
  targetRole = "Machine Learning Engineer",
  targetCompany = "Google",
  daysLeft = 18,
  dailyBudget = 60
}) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [pills, setPills] = useState(DEFAULT_PILLS);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      initConversation();
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const initConversation = async () => {
    setLoading(true);
    try {
      const title = activeActivity
        ? `Mentorship: ${activeActivity.title}`
        : "Interview Preparation Mentorship";
      const res = await intelligenceAPI.startMentorConversation(title);
      setConversation(res.conversation);

      const msgRes = await intelligenceAPI.getMentorMessages(res.conversation.id);
      setMessages(msgRes.messages || []);
    } catch (err) {
      console.warn("Failed to initialize mentor conversation:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputValue).trim();
    if (!text || !conversation) return;

    // Optimistically add user message
    const tempUserMsg = {
      id: "temp_" + Date.now(),
      role: "user",
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setInputValue("");
    setSending(true);

    try {
      const res = await intelligenceAPI.sendMentorMessage(
        conversation.id,
        text,
        activeActivity
      );
      if (res.message) {
        setMessages(prev => [...prev, res.message]);
      }
      if (res.suggested_pills && res.suggested_pills.length > 0) {
        setPills(res.suggested_pills);
      }
    } catch (err) {
      const errMsg = {
        id: "err_" + Date.now(),
        role: "assistant",
        content: `Could not connect to mentor: ${err.message}. Please retry.`,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs intelligence-root">
      <div className="w-full max-w-lg bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl text-slate-100 animate-slide-left">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-slate-950 text-sm shadow-lg shadow-cyan-500/20">
              AI
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                PrepFly Adaptive Mentor
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </h3>
              <p className="text-[11px] text-slate-400">
                Deterministic Invariants & Live State Mutations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg text-sm transition"
            title="Close Mentor Drawer"
          >
            ✕
          </button>
        </div>

        {/* ── CONTEXT CHIPS BAR ── */}
        <div className="px-4 py-2.5 bg-slate-950/80 border-b border-slate-800/80 flex items-center gap-2 overflow-x-auto text-[11px]">
          <span className="px-2 py-0.5 rounded-md bg-cyan-950 text-cyan-300 border border-cyan-800/50 font-semibold whitespace-nowrap">
            🎯 {targetCompany} • {targetRole}
          </span>
          <span className="px-2 py-0.5 rounded-md bg-amber-950 text-amber-300 border border-amber-800/50 font-semibold whitespace-nowrap">
            ⏳ {daysLeft} Days Left
          </span>
          <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 font-semibold whitespace-nowrap">
            ⚡ {dailyBudget}m Budget
          </span>
          {activeActivity && (
            <span className="px-2 py-0.5 rounded-md bg-purple-950 text-purple-300 border border-purple-800/50 font-semibold whitespace-nowrap">
              Active: {activeActivity.skill_name || activeActivity.skill_id}
            </span>
          )}
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading && (
            <div className="text-center py-10 text-xs text-slate-400">
              Connecting to adaptive mentor session...
            </div>
          )}

          {messages.map((m) => {
            const isUser = m.role === "user";
            let parsedPayload = null;
            try {
              if (m.context_payload) {
                parsedPayload = typeof m.context_payload === "string" ? JSON.parse(m.context_payload) : m.context_payload;
              }
            } catch {
              parsedPayload = null;
            }

            return (
              <div
                key={m.id || m.created_at}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed space-y-2 ${
                    isUser
                      ? "bg-cyan-600 text-white rounded-br-none"
                      : "bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-bl-none shadow-md"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>

                  {/* Machine Diff Alert Box */}
                  {parsedPayload?.diff && (
                    <div className="mt-2 p-2.5 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] space-y-1">
                      <div className="text-cyan-400 font-bold">Plan Diff (Trigger: {parsedPayload.trigger || "mutation"}):</div>
                      {parsedPayload.diff.added && parsedPayload.diff.added.length > 0 && (
                        <div className="text-emerald-400">+ Added: {parsedPayload.diff.added.join(", ")}</div>
                      )}
                      {parsedPayload.diff.deferred && parsedPayload.diff.deferred.length > 0 && (
                        <div className="text-amber-400">⏸ Deferred: {parsedPayload.diff.deferred.join(", ")}</div>
                      )}
                    </div>
                  )}

                  {/* Evidence Provenance Box */}
                  {parsedPayload?.evidence_id && (
                    <div className="mt-2 p-2 bg-emerald-950/60 rounded-xl border border-emerald-800/60 text-[10px] text-emerald-300 font-mono">
                      ✓ Immutable Evidence Recorded: ID #{parsedPayload.evidence_id} (Score: {parsedPayload.overall_score || 85}%)
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400/80 text-right pt-0.5">
                    {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* ── QUICK ACTION PILLS ── */}
        <div className="p-2.5 bg-slate-950/90 border-t border-slate-800 flex items-center gap-1.5 overflow-x-auto text-xs">
          {pills.map((pill, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(pill)}
              disabled={sending}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-[11px] whitespace-nowrap transition"
            >
              {pill}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !sending && handleSendMessage()}
            placeholder="Ask mentor, request 30m plan, or simulate mock..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={sending || !inputValue.trim()}
            className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 text-slate-950 font-bold px-3.5 py-2 rounded-xl text-xs transition"
          >
            {sending ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
