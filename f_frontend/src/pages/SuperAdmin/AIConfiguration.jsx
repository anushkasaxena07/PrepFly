import React, { useState, useEffect } from 'react';
import { getSuperAdminAIConfig, saveSuperAdminAIConfig, testSuperAdminAIProvider } from '../../services/superAdminAPI';

export default function AIConfiguration() {
  const [config, setConfig] = useState({
    gemini_api_key: '',
    openai_api_key: '',
    anthropic_api_key: '',
    deepseek_api_key: '',
    elevenlabs_api_key: '',
    primary_model: 'gemini-1.5-flash',
    fallback_model: 'gpt-4o-mini',
    voice_model: 'rachel_conversational',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 0.95,
    interview_prompt: '',
    resume_prompt: '',
    coding_prompt: '',
    report_prompt: ''
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activePromptTab, setActivePromptTab] = useState('interview');

  // Key Visibility Toggles
  const [showKeys, setShowKeys] = useState({
    gemini: false,
    openai: false,
    anthropic: false,
    deepseek: false,
    elevenlabs: false
  });

  // Testing States
  const [testingProvider, setTestingProvider] = useState(null);
  const [testResults, setTestResults] = useState({});

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const data = await getSuperAdminAIConfig();
      setConfig(prev => ({ ...prev, ...data }));
    } catch (e) {
      console.error("Error fetching AI config:", e);
    } finally {
      setLoading(false);
    }
  };

  const toggleShowKey = (provider) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleTestConnection = async (provider, apiKey, model) => {
    setTestingProvider(provider);
    try {
      const res = await testSuperAdminAIProvider({
        provider,
        api_key: apiKey,
        model
      });
      setTestResults(prev => ({
        ...prev,
        [provider]: { type: 'success', text: res.message, latency: res.latency_ms }
      }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [provider]: { type: 'error', text: err.message }
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await saveSuperAdminAIConfig(config);
      alert("✅ All LLM Credentials, Model Settings & Prompt Templates saved successfully!");
    } catch (err) {
      alert("❌ Save failed: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const insertVariable = (variable) => {
    if (activePromptTab === 'interview') {
      setConfig(prev => ({ ...prev, interview_prompt: (prev.interview_prompt || '') + ` ${variable}` }));
    } else if (activePromptTab === 'resume') {
      setConfig(prev => ({ ...prev, resume_prompt: (prev.resume_prompt || '') + ` ${variable}` }));
    } else if (activePromptTab === 'coding') {
      setConfig(prev => ({ ...prev, coding_prompt: (prev.coding_prompt || '') + ` ${variable}` }));
    } else if (activePromptTab === 'report') {
      setConfig(prev => ({ ...prev, report_prompt: (prev.report_prompt || '') + ` ${variable}` }));
    }
  };

  if (loading) {
    return (
      <div style={{ color: "#00c4a7", padding: "60px", textAlign: "center", fontWeight: 800 }}>
        ⚡ Loading enterprise LLM & Speech AI configuration...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", fontFamily: "Inter, system-ui, sans-serif" }}>
      
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "22px", fontWeight: 900, color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            🤖 Multi-Provider LLM & AI Engine Command Center
          </h2>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: "4px 0 0 0" }}>
            Manage API credentials, model routing, fallback orchestration, hyperparameters, and system prompts.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 800, background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", padding: "4px 10px", borderRadius: "20px" }}>
            🟢 Engine Status: Healthy ({config.uptime_pct || "99.98%"})
          </span>

          <button
            onClick={handleSaveConfig}
            disabled={saving}
            style={{
              background: "linear-gradient(135deg, #00c4a7, #7c4fe0)",
              border: "none",
              borderRadius: "8px",
              padding: "10px 20px",
              fontSize: "12px",
              fontWeight: 900,
              color: "#fff",
              cursor: "pointer",
              boxShadow: "0 4px 14px rgba(0,196,167,0.3)"
            }}
          >
            {saving ? "Saving Configurations..." : "💾 Save All AI Settings"}
          </button>
        </div>
      </div>

      {/* SECTION 1: MULTI-PROVIDER API KEYS & LLM MODELS */}
      <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
          🔑 Enterprise LLM API Keys & Model Routing
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
          
          {/* PROVIDER 1: GOOGLE GEMINI */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(0,196,167,0.3)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>✨</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#00c4a7" }}>Google Gemini API (Primary)</span>
              </div>
              <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(0,196,167,0.15)", color: "#00c4a7", fontWeight: 800 }}>PRIMARY ENGINE</span>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>API KEY</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showKeys.gemini ? "text" : "password"}
                  value={config.gemini_api_key || ''}
                  onChange={(e) => setConfig({ ...config, gemini_api_key: e.target.value })}
                  placeholder="AIzaSy..."
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 36px 8px 12px", fontSize: "12px", color: "#fff", fontFamily: "monospace", outline: "none" }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey('gemini')}
                  style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "14px" }}
                >
                  {showKeys.gemini ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>ACTIVE MODEL</label>
                <select
                  value={config.primary_model || 'gemini-1.5-flash'}
                  onChange={(e) => setConfig({ ...config, primary_model: e.target.value })}
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none" }}
                >
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash (Ultra Fast)</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (High Reasoning)</option>
                  <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Next Gen)</option>
                </select>
              </div>

              <button
                onClick={() => handleTestConnection('gemini', config.gemini_api_key, config.primary_model)}
                disabled={testingProvider === 'gemini'}
                style={{ background: "rgba(0,196,167,0.15)", border: "1px solid rgba(0,196,167,0.3)", color: "#00c4a7", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "7px 12px", cursor: "pointer", marginTop: "16px" }}
              >
                {testingProvider === 'gemini' ? 'Testing...' : '⚡ Test API'}
              </button>
            </div>

            {testResults.gemini && (
              <div style={{ marginTop: "10px", fontSize: "11px", padding: "8px 10px", borderRadius: "6px", background: testResults.gemini.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: testResults.gemini.type === 'success' ? '#10b981' : '#f87171' }}>
                {testResults.gemini.text}
              </div>
            )}
          </div>

          {/* PROVIDER 2: OPENAI */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(139,92,246,0.3)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>🧠</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#a78bfa" }}>OpenAI API (Secondary / Fallback)</span>
              </div>
              <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(139,92,246,0.15)", color: "#a78bfa", fontWeight: 800 }}>FALLBACK</span>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>API KEY</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showKeys.openai ? "text" : "password"}
                  value={config.openai_api_key || ''}
                  onChange={(e) => setConfig({ ...config, openai_api_key: e.target.value })}
                  placeholder="sk-proj-..."
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 36px 8px 12px", fontSize: "12px", color: "#fff", fontFamily: "monospace", outline: "none" }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey('openai')}
                  style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "14px" }}
                >
                  {showKeys.openai ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>FALLBACK MODEL</label>
                <select
                  value={config.fallback_model || 'gpt-4o-mini'}
                  onChange={(e) => setConfig({ ...config, fallback_model: e.target.value })}
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none" }}
                >
                  <option value="gpt-4o-mini">GPT-4o Mini (Cost Efficient)</option>
                  <option value="gpt-4o">GPT-4o (High Intelligence)</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                </select>
              </div>

              <button
                onClick={() => handleTestConnection('openai', config.openai_api_key, config.fallback_model)}
                disabled={testingProvider === 'openai'}
                style={{ background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)", color: "#a78bfa", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "7px 12px", cursor: "pointer", marginTop: "16px" }}
              >
                {testingProvider === 'openai' ? 'Testing...' : '⚡ Test API'}
              </button>
            </div>

            {testResults.openai && (
              <div style={{ marginTop: "10px", fontSize: "11px", padding: "8px 10px", borderRadius: "6px", background: testResults.openai.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: testResults.openai.type === 'success' ? '#10b981' : '#f87171' }}>
                {testResults.openai.text}
              </div>
            )}
          </div>

          {/* PROVIDER 3: ANTHROPIC CLAUDE */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>📜</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#f59e0b" }}>Anthropic Claude API</span>
              </div>
              <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(245,158,11,0.15)", color: "#f59e0b", fontWeight: 800 }}>OPTIONAL</span>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>API KEY</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showKeys.anthropic ? "text" : "password"}
                  value={config.anthropic_api_key || ''}
                  onChange={(e) => setConfig({ ...config, anthropic_api_key: e.target.value })}
                  placeholder="sk-ant-..."
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 36px 8px 12px", fontSize: "12px", color: "#fff", fontFamily: "monospace", outline: "none" }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey('anthropic')}
                  style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "14px" }}
                >
                  {showKeys.anthropic ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>MODEL</label>
                <select
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none" }}
                >
                  <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                  <option value="claude-3-haiku">Claude 3 Haiku</option>
                </select>
              </div>

              <button
                onClick={() => handleTestConnection('anthropic', config.anthropic_api_key, 'claude-3-5-sonnet')}
                disabled={testingProvider === 'anthropic'}
                style={{ background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "7px 12px", cursor: "pointer", marginTop: "16px" }}
              >
                {testingProvider === 'anthropic' ? 'Testing...' : '⚡ Test API'}
              </button>
            </div>

            {testResults.anthropic && (
              <div style={{ marginTop: "10px", fontSize: "11px", padding: "8px 10px", borderRadius: "6px", background: testResults.anthropic.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: testResults.anthropic.type === 'success' ? '#10b981' : '#f87171' }}>
                {testResults.anthropic.text}
              </div>
            )}
          </div>

          {/* PROVIDER 4: DEEPSEEK */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(236,72,153,0.2)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>🤖</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#ec4899" }}>DeepSeek AI API (Coding / Reasoning)</span>
              </div>
              <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(236,72,153,0.15)", color: "#ec4899", fontWeight: 800 }}>CODING</span>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>API KEY</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showKeys.deepseek ? "text" : "password"}
                  value={config.deepseek_api_key || ''}
                  onChange={(e) => setConfig({ ...config, deepseek_api_key: e.target.value })}
                  placeholder="sk-deepseek-..."
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 36px 8px 12px", fontSize: "12px", color: "#fff", fontFamily: "monospace", outline: "none" }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey('deepseek')}
                  style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "14px" }}
                >
                  {showKeys.deepseek ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>MODEL</label>
                <select
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none" }}
                >
                  <option value="deepseek-reasoner">DeepSeek R1 Reasoner</option>
                  <option value="deepseek-chat">DeepSeek Chat V3</option>
                </select>
              </div>

              <button
                onClick={() => handleTestConnection('deepseek', config.deepseek_api_key, 'deepseek-reasoner')}
                disabled={testingProvider === 'deepseek'}
                style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)", color: "#ec4899", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "7px 12px", cursor: "pointer", marginTop: "16px" }}
              >
                {testingProvider === 'deepseek' ? 'Testing...' : '⚡ Test API'}
              </button>
            </div>

            {testResults.deepseek && (
              <div style={{ marginTop: "10px", fontSize: "11px", padding: "8px 10px", borderRadius: "6px", background: testResults.deepseek.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: testResults.deepseek.type === 'success' ? '#10b981' : '#f87171' }}>
                {testResults.deepseek.text}
              </div>
            )}
          </div>

          {/* PROVIDER 5: ELEVENLABS SPEECH */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(56,189,248,0.2)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "18px" }}>🎙️</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#38bdf8" }}>ElevenLabs / WebSpeech Voice TTS</span>
              </div>
              <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(56,189,248,0.15)", color: "#38bdf8", fontWeight: 800 }}>AUDIO TTS</span>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>API KEY</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showKeys.elevenlabs ? "text" : "password"}
                  value={config.elevenlabs_api_key || ''}
                  onChange={(e) => setConfig({ ...config, elevenlabs_api_key: e.target.value })}
                  placeholder="el-..."
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 36px 8px 12px", fontSize: "12px", color: "#fff", fontFamily: "monospace", outline: "none" }}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey('elevenlabs')}
                  style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "14px" }}
                >
                  {showKeys.elevenlabs ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "10px", fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "4px" }}>VOICE PROFILE</label>
                <select
                  value={config.voice_model || 'rachel_conversational'}
                  onChange={(e) => setConfig({ ...config, voice_model: e.target.value })}
                  style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "6px 8px", fontSize: "11px", color: "#fff", outline: "none" }}
                >
                  <option value="rachel_conversational">Rachel (Human Conversational)</option>
                  <option value="adam_professional">Adam (Corporate Professional)</option>
                  <option value="webspeech_fallback">WebSpeech Browser Engine (Zero Cost)</option>
                </select>
              </div>

              <button
                onClick={() => handleTestConnection('elevenlabs', config.elevenlabs_api_key, config.voice_model)}
                disabled={testingProvider === 'elevenlabs'}
                style={{ background: "rgba(56,189,248,0.15)", border: "1px solid rgba(56,189,248,0.3)", color: "#38bdf8", borderRadius: "6px", fontSize: "11px", fontWeight: 800, padding: "7px 12px", cursor: "pointer", marginTop: "16px" }}
              >
                {testingProvider === 'elevenlabs' ? 'Testing...' : '⚡ Test API'}
              </button>
            </div>

            {testResults.elevenlabs && (
              <div style={{ marginTop: "10px", fontSize: "11px", padding: "8px 10px", borderRadius: "6px", background: testResults.elevenlabs.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: testResults.elevenlabs.type === 'success' ? '#10b981' : '#f87171' }}>
                {testResults.elevenlabs.text}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* SECTION 2: GLOBAL HYPERPARAMETERS & ORCHESTRATION */}
      <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#fff", marginBottom: "16px", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
          🎛 LLM Hyperparameters & Sampling Controls
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", fontSize: "12px" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <label style={{ fontWeight: 800, color: "#94a3b8" }}>TEMPERATURE</label>
              <span style={{ fontWeight: 900, color: "#ec4899" }}>{config.temperature}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.temperature}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              style={{ width: "100%", accentColor: "#ec4899" }}
            />
            <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>
              {config.temperature < 0.3 ? "0.0: Precise & Technical" : config.temperature < 0.8 ? "0.7: Balanced Conversational" : "1.0: Highly Creative"}
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <label style={{ fontWeight: 800, color: "#94a3b8" }}>TOP-P NUCLEUS SAMPLING</label>
              <span style={{ fontWeight: 900, color: "#00c4a7" }}>{config.top_p ?? 0.95}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={config.top_p ?? 0.95}
              onChange={(e) => setConfig({ ...config, top_p: parseFloat(e.target.value) })}
              style={{ width: "100%", accentColor: "#00c4a7" }}
            />
          </div>

          <div>
            <label style={{ fontWeight: 800, color: "#94a3b8", display: "block", marginBottom: "6px" }}>MAX GENERATION TOKENS</label>
            <input
              type="number"
              value={config.max_tokens ?? 2048}
              onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) || 2048 })}
              style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "8px 12px", color: "#fff", outline: "none" }}
            />
          </div>
        </div>
      </div>

      {/* SECTION 3: SYSTEM PROMPT ENGINEERING STUDIO */}
      <div style={{ background: "rgba(12,18,32,0.85)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "16px", padding: "24px" }}>
        
        {/* PROMPT TABS */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              onClick={() => setActivePromptTab('interview')}
              style={{
                background: activePromptTab === 'interview' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px', fontWeight: 800, padding: '8px 14px', borderRadius: '8px', cursor: 'pointer'
              }}
            >
              🎙️ AI Interviewer Persona
            </button>

            <button
              onClick={() => setActivePromptTab('resume')}
              style={{
                background: activePromptTab === 'resume' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px', fontWeight: 800, padding: '8px 14px', borderRadius: '8px', cursor: 'pointer'
              }}
            >
              📄 ATS Resume Matching
            </button>

            <button
              onClick={() => setActivePromptTab('coding')}
              style={{
                background: activePromptTab === 'coding' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px', fontWeight: 800, padding: '8px 14px', borderRadius: '8px', cursor: 'pointer'
              }}
            >
              💻 Coding Complexity Evaluator
            </button>

            <button
              onClick={() => setActivePromptTab('report')}
              style={{
                background: activePromptTab === 'report' ? 'linear-gradient(135deg, #00c4a7, #7c4fe0)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px', fontWeight: 800, padding: '8px 14px', borderRadius: '8px', cursor: 'pointer'
              }}
            >
              📊 Placement Dossier Generator
            </button>
          </div>
        </div>

        {/* VARIABLE TAG CHIPS */}
        <div style={{ marginBottom: "12px", display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: "11px", fontWeight: 800, color: "#94a3b8" }}>Click to insert variable:</span>
          {["{{candidate_name}}", "{{target_role}}", "{{department}}", "{{question_text}}", "{{resume_text}}", "{{code_submission}}"].map((v, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => insertVariable(v)}
              style={{ background: "rgba(0,196,167,0.12)", border: "1px solid rgba(0,196,167,0.3)", color: "#00c4a7", fontSize: "10px", fontWeight: 800, borderRadius: "4px", padding: "3px 8px", cursor: "pointer" }}
            >
              + {v}
            </button>
          ))}
        </div>

        {/* PROMPT TEXTAREA */}
        {activePromptTab === 'interview' && (
          <div>
            <label style={{ fontSize: "11px", fontWeight: 800, color: "#00c4a7", display: "block", marginBottom: "6px" }}>
              SYSTEM INSTRUCTIONS FOR AVA (LIVE INTERVIEWER)
            </label>
            <textarea
              rows={6}
              value={config.interview_prompt || ''}
              onChange={(e) => setConfig({ ...config, interview_prompt: e.target.value })}
              style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px", color: "#e2e8f0", fontSize: "13px", lineHeight: 1.5, fontFamily: "Inter, monospace" }}
            />
          </div>
        )}

        {activePromptTab === 'resume' && (
          <div>
            <label style={{ fontSize: "11px", fontWeight: 800, color: "#a78bfa", display: "block", marginBottom: "6px" }}>
              SYSTEM INSTRUCTIONS FOR RESUME ATS PARSING & KEYWORD EXTRACTION
            </label>
            <textarea
              rows={6}
              value={config.resume_prompt || ''}
              onChange={(e) => setConfig({ ...config, resume_prompt: e.target.value })}
              style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px", color: "#e2e8f0", fontSize: "13px", lineHeight: 1.5, fontFamily: "Inter, monospace" }}
            />
          </div>
        )}

        {activePromptTab === 'coding' && (
          <div>
            <label style={{ fontSize: "11px", fontWeight: 800, color: "#ec4899", display: "block", marginBottom: "6px" }}>
              SYSTEM INSTRUCTIONS FOR CODING SUBMISSION EVALUATION & TEST CASES
            </label>
            <textarea
              rows={6}
              value={config.coding_prompt || ''}
              onChange={(e) => setConfig({ ...config, coding_prompt: e.target.value })}
              style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px", color: "#e2e8f0", fontSize: "13px", lineHeight: 1.5, fontFamily: "Inter, monospace" }}
            />
          </div>
        )}

        {activePromptTab === 'report' && (
          <div>
            <label style={{ fontSize: "11px", fontWeight: 800, color: "#f59e0b", display: "block", marginBottom: "6px" }}>
              SYSTEM INSTRUCTIONS FOR INSTITUTIONAL DOSSIER & PLACEMENT REPORT GENERATION
            </label>
            <textarea
              rows={6}
              value={config.report_prompt || ''}
              onChange={(e) => setConfig({ ...config, report_prompt: e.target.value })}
              style={{ width: "100%", background: "#090d16", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px", color: "#e2e8f0", fontSize: "13px", lineHeight: 1.5, fontFamily: "Inter, monospace" }}
            />
          </div>
        )}

      </div>

    </div>
  );
}
