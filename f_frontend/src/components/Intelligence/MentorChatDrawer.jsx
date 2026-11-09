import React, { useState, useEffect, useRef } from "react";
import { intelligenceAPI } from "../../services/intelligenceAPI";
import "./intelligence.css";

const DEFAULT_PILLS = [
  "Explain from scratch",
  "Show real-world example",
  "Give me a harder question",
  "I have 30 mins today",
  "Prepare for tomorrow",
  "Simulate mock interview"
];

export default function MentorChatDrawer({ isOpen, onClose, activeActivity, targetRole, targetCompany }) {
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
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-black text-sm shadow-lg shadow-cyan-500/20">
              AI
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                PrepFly AI Mentor
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </h3>
              <p className="text-[11px] text-slate-400">
                {targetRole ? `${targetRole} Specialist` : "Dedicated Interview Coach"}
                {targetCompany ? ` • ${targetCompany}` : ""}
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

        {/* Active Context Banner */}
        {activeActivity && (
          <div className="px-4 py-2 bg-slate-800/60 border-b border-slate-800/80 text-[11px] text-slate-300 flex items-center justify-between">
            <span className="truncate">
              Focusing on: <strong className="text-cyan-400">{activeActivity.title}</strong>
            </span>
            <span className="text-[10px] uppercase font-bold text-slate-400 px-1.5 py-0.5 bg-slate-800 rounded">
              {activeActivity.difficulty || "Core"}
            </span>
          </div>
        )}

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs sm:text-sm">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id || m.created_at}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed whitespace-pre-line text-xs sm:text-sm ${
                      isUser
                        ? "bg-cyan-600 text-white rounded-br-xs"
                        : "bg-slate-800 border border-slate-700/60 text-slate-200 rounded-bl-xs"
                    }`}
                  >
                    {m.content}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 px-1">
                    {isUser ? "You" : "AI Mentor"}
                  </span>
                </div>
              );
            })
          )}
          {sending && (
            <div className="flex items-center gap-2 text-xs text-slate-400 p-2">
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              Thinking & synthesizing guidance...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Action Suggestion Pills */}
        <div className="px-3 py-2 border-t border-slate-800/80 bg-slate-900/60 flex flex-wrap gap-1.5">
          {pills.map((pill, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(pill)}
              disabled={sending}
              className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700 transition"
            >
              {pill}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-800 bg-slate-900">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask your mentor anything about code, system design, or interview prep..."
              disabled={sending}
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              disabled={sending || !inputValue.trim()}
              className="px-4 py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 text-black font-bold text-xs rounded-xl transition shadow-md shadow-cyan-500/20"
            >
              Send
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
