import React from 'react';
import { getGradeInfo } from '../utils/gradingSystem';

export default function DashboardTab({ setActiveTab, user = {}, history = [], userStats = null }) {
  const userName = user?.full_name || user?.name || "Anushka";

  const completedSessions = (history || []).filter(s => !s.active);
  const isLoggedIn = user?._id || user?.user_id;
  const hasData = userStats ? userStats.has_data : completedSessions.length > 0;

  // 1. Total sessions
  const displayTotal = userStats?.interviews
    ? (userStats.interviews.total ?? 0)
    : (hasData ? completedSessions.length : (isLoggedIn ? 0 : 24));

  // 2. Average score
  const displayAvgScore = userStats?.interviews
    ? (userStats.interviews.avg_score != null ? userStats.interviews.avg_score.toFixed(1) : "0.0")
    : (hasData && completedSessions.length > 0
        ? (completedSessions.reduce((acc, s) => acc + (s.final_score || 0), 0) / completedSessions.length).toFixed(1)
        : (isLoggedIn ? "0.0" : "7.8"));

  // 3. Interview readiness
  const displayReadiness = userStats?.interviews
    ? (userStats.interviews.readiness ?? 0)
    : (hasData ? Math.min(100, Math.round(parseFloat(displayAvgScore || "0") * 10)) : (isLoggedIn ? 0 : 82));

  // 4. Dynamic stats
  const codingAccuracy = userStats?.coding
    ? (userStats.coding.accuracy ?? 0)
    : (hasData ? Math.min(100, Math.round(65 + ((parseFloat(displayAvgScore || "0") || 7.0) - 7.0) * 8)) : (isLoggedIn ? 0 : 73));

  const speechConfidence = userStats?.speech
    ? (userStats.speech.confidence ?? 0)
    : (hasData ? Math.min(100, Math.round(75 + ((parseFloat(displayAvgScore || "0") || 7.0) - 7.0) * 6)) : (isLoggedIn ? 0 : 87));

  // Streak & Milestone Info
  const displayStreak = userStats
    ? (userStats.streak ?? 0)
    : (hasData ? Math.min(30, completedSessions.length + 2) : (isLoggedIn ? 0 : 7));

  const gradeACount = userStats
    ? ((userStats.grade_distribution?.A || 0) + (userStats.grade_distribution?.S || 0))
    : (hasData ? completedSessions.filter(s => s.final_grade === 'A' || s.final_grade === 'S').length : (isLoggedIn ? 0 : 3));

  // Dynamic Insights calculation
  const baseInsights = [
    {
      type: "speech",
      title: "Filler words detected frequently",
      desc: 'You said "um", "uh", "like" 11 times in your last session. This signals nervousness to interviewers.',
      cta: "Practice Speech AI →",
      severity: "high",
      icon: "🎤",
      className: "insight-card sev-high ins-high"
    },
    {
      type: "resume",
      title: "Resume missing 4 JD keywords",
      desc: "Kubernetes, Terraform, GraphQL, and Docker Swarm appear in your target JD but not on your resume.",
      cta: "Update Resume →",
      severity: "med",
      icon: "📄",
      className: "insight-card sev-med ins-med"
    },
    {
      type: "coding",
      title: "Dynamic Programming up +18%",
      desc: "Your DP accuracy improved significantly. LeetCode Medium problems are now your strong suit.",
      cta: "Keep Practicing →",
      severity: "low",
      icon: "💻",
      className: "insight-card sev-low ins-low"
    }
  ];

  const latestSession = completedSessions[0];
  const latestFeedback = latestSession?.feedbacks?.[0];
  
  const insights = [];
  if (latestFeedback) {
    insights.push({
      type: "ava",
      title: "Latest Interview Performance",
      desc: `Your last mock question response scored ${latestFeedback.score}/10. Strength: "${latestFeedback.strength}". Improvement: "${latestFeedback.improvement}".`,
      cta: "Practice AI Interview →",
      severity: latestFeedback.score < 6 ? "high" : "pos",
      icon: "🤖",
      className: latestFeedback.score < 6 ? "insight-card sev-high ins-high" : "insight-card sev-pos ins-pos"
    });
  }

  if (userStats && userStats.insights) {
    userStats.insights.forEach(ins => {
      if (insights.length < 4) {
        insights.push(ins);
      }
    });
  } else {
    const defaultInsights = isLoggedIn ? [
      {
        type: "speech",
        title: "Speech AI is ready",
        desc: "Analyze filler words and confidence metrics of your speech in real-time.",
        cta: "Practice Speech AI →",
        severity: "low",
        icon: "🎤",
        className: "insight-card sev-low ins-low"
      },
      {
        type: "resume",
        title: "Resume ATS scanner ready",
        desc: "Upload a resume and job description to identify keyword matches and score resume compatibility.",
        cta: "Update Resume →",
        severity: "low",
        icon: "📄",
        className: "insight-card sev-low ins-low"
      },
      {
        type: "coding",
        title: "Coding playground is open",
        desc: "Solve standard coding questions and get automated runtime analytics and AI code reviews.",
        cta: "Resume Practice →",
        severity: "low",
        icon: "💻",
        className: "insight-card sev-low ins-low"
      }
    ] : baseInsights;

    defaultInsights.forEach(ins => {
      if (insights.length < 4) {
        insights.push(ins);
      }
    });
  }

  // Dynamic SVG Trend calculation
  const defaultChartData = [
    { final_score: 6.8, final_grade: 'B' },
    { final_score: 7.2, final_grade: 'B+' },
    { final_score: 7.9, final_grade: 'A' },
    { final_score: 8.5, final_grade: 'A' },
    { final_score: 8.9, final_grade: 'S' }
  ];
  const chartSessions = completedSessions.length > 0 
    ? [...completedSessions].reverse().slice(-12)
    : defaultChartData;
  const hasChartData = true;
  
  const chartPoints = chartSessions.map((s, index) => {
    const numPoints = chartSessions.length;
    const x = numPoints > 1 
      ? 22 + index * (520 / (numPoints - 1))
      : 22;
    const score = s.final_score || 7.5;
    const y = 136 - (score * 9.9); // scale score 0..10 to Y range 136..37
    return { x, y, score, label: `S${index + 1}${s.final_grade === 'S' ? '★' : ''}` };
  });

  const polylinePoints = chartPoints.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const fillPath = chartPoints.length > 0
    ? `M22,140 ` + chartPoints.map(p => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + ` L${chartPoints[chartPoints.length - 1].x.toFixed(1)},140 Z`
    : "";

  // Dynamic metrics
  const displayCoding = userStats ? userStats.coding.total : (hasData ? completedSessions.length : 0);
  const displaySpeech = userStats ? userStats.speech.total : (hasData ? completedSessions.length : 0);

  // Daily Goals calculation
  const goal1Pct = Math.min(100, Math.round((displayCoding / 2) * 100));
  const goal2Pct = displayTotal >= 1 ? 100 : 0;
  const goal3Pct = speechConfidence > 0 ? Math.min(100, speechConfidence) : 0;
  
  const goalsDone = (goal1Pct >= 100 ? 1 : 0) + (goal2Pct >= 100 ? 1 : 0) + (goal3Pct >= 100 ? 1 : 0);

  // Skill Radar values
  const dsaSkill = codingAccuracy;
  const readinessSkill = displayReadiness;
  const speechSkill = speechConfidence;
  const resumeSkill = userStats?.resume?.latest_score || (displayAvgScore * 10);

  const getTimeBasedGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div id="page-dashboard" className="page active" role="tabpanel">
      <div className="container">

        {/* HERO SECTION */}
        <section className="mb20" aria-label="Welcome banner">
          <div className="hero-card">
            <div className="hero-top">
              <div>
                <div className="hero-greeting">👋 {getTimeBasedGreeting()}</div>
                <h1 className="hero-name">Welcome Back, <span>{userName}</span></h1>
                <p className="hero-sub">{hasData ? `You have completed ${displayTotal} practice sessions so far. Keep practicing!` : `Your AI coach is ready. You're on a ${displayStreak}-day streak — keep it going!`}</p>
              </div>
              <div className="hero-actions">
                <button className="btn btn-primary" onClick={() => setActiveTab('ava')}>▶ Start Mock Interview</button>
                <button className="btn btn-ghost" onClick={() => setActiveTab('coding')}>💻 Resume Practice</button>
              </div>
            </div>
          </div>
        </section>

        {/* STAT CARDS */}
        <section className="mb24" aria-label="Performance statistics">
          <div className="g4 stagger">
            <div className="stat-card cyan">
              <div className="stat-icon cyan" aria-hidden="true">🎯</div>
              <div className="stat-lbl">Mock Interviews</div>
              <div className="stat-val cyan">{displayTotal}</div>
              <div className="stat-trend trend-up">↑ total sessions</div>
              <div className="sparkline" aria-hidden="true">
                <div className="spark-bar" style={{height:"30%",background:"rgba(0,240,200,0.3)"}}></div>
                <div className="spark-bar" style={{height:"45%",background:"rgba(0,240,200,0.3)"}}></div>
                <div className="spark-bar" style={{height:"60%",background:"rgba(0,240,200,0.4)"}}></div>
                <div className="spark-bar" style={{height:"75%",background:"rgba(0,240,200,0.6)"}}></div>
                <div className="spark-bar" style={{height:"90%",background:"var(--cyan)"}}></div>
              </div>
            </div>
            <div className="stat-card purple">
              <div className="stat-icon purple" aria-hidden="true">📊</div>
              <div className="stat-lbl">Avg Score</div>
              <div className="stat-val purple">{displayAvgScore}</div>
              <div className="stat-trend trend-up">↑ out of 10</div>
              <div className="sparkline" aria-hidden="true">
                <div className="spark-bar" style={{height:"50%",background:"rgba(155,109,255,0.3)"}}></div>
                <div className="spark-bar" style={{height:"65%",background:"rgba(155,109,255,0.4)"}}></div>
                <div className="spark-bar" style={{height:"80%",background:"rgba(155,109,255,0.6)"}}></div>
                <div className="spark-bar" style={{height:"95%",background:"var(--purple)"}}></div>
              </div>
            </div>
            <div className="stat-card blue">
              <div className="stat-icon blue" aria-hidden="true">💻</div>
              <div className="stat-lbl">Coding Accuracy</div>
              <div className="stat-val blue">{codingAccuracy}%</div>
              <div className="stat-trend trend-up">↑ test pass rate</div>
              <div className="sparkline" aria-hidden="true">
                <div className="spark-bar" style={{height:"40%",background:"rgba(77,159,255,0.3)"}}></div>
                <div className="spark-bar" style={{height:"55%",background:"rgba(77,159,255,0.4)"}}></div>
                <div className="spark-bar" style={{height:"70%",background:"rgba(77,159,255,0.5)"}}></div>
                <div className="spark-bar" style={{height:"85%",background:"var(--blue)"}}></div>
              </div>
            </div>
            <div className="stat-card gold">
              <div className="stat-icon gold" aria-hidden="true">🎤</div>
              <div className="stat-lbl">Speech Confidence</div>
              <div className="stat-val gold">{speechConfidence}%</div>
              <div className="stat-trend trend-up">↑ delivery score</div>
              <div className="sparkline" aria-hidden="true">
                <div className="spark-bar" style={{height:"60%",background:"rgba(255,209,102,0.3)"}}></div>
                <div className="spark-bar" style={{height:"75%",background:"rgba(255,209,102,0.5)"}}></div>
                <div className="spark-bar" style={{height:"95%",background:"var(--gold)"}}></div>
              </div>
            </div>
          </div>
        </section>

        {/* MAIN TWO-COL LAYOUT */}
        <div className="g-main">
          {/* LEFT COLUMN */}
          <div className="flex-col gap16">

            {/* AI INSIGHTS */}
            <section aria-label="AI Insights">
              <div className="sec-header mb16">
                <div className="flex items-center gap8">
                  <div className="sec-title">AI Insights</div>
                  <div className="sec-badge">{insights.length} active</div>
                </div>
                <button className="btn btn-ghost btn-xs" onClick={() => setActiveTab('analytics')}>View All</button>
              </div>
              <div className="flex-col gap8 stagger" id="insights-list">
                {insights.map((ins, idx) => (
                  <div key={idx} className={ins.className} tabIndex="0" onClick={() => setActiveTab(ins.type)} aria-label={`Insight: ${ins.title}`}>
                    <div className="insight-icon-wrap" aria-hidden="true">{ins.icon}</div>
                    <div className="insight-body">
                      <div className="insight-title">{ins.title}</div>
                      <div className="insight-desc">{ins.desc}</div>
                      <span className={`insight-cta ${ins.severity === 'high' ? 'red' : ins.severity === 'med' ? 'orange' : ins.severity === 'low' ? 'cyan' : 'green'}`}>
                        {ins.cta}
                      </span>
                    </div>
                    <span className={`sev-badge ${ins.severity === 'high' ? 'high' : ins.severity === 'med' ? 'med' : ins.severity === 'low' ? 'low' : 'pos'}`}>
                      {ins.severity.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* CONTINUE LEARNING */}
            <section aria-label="Continue Learning">
              <div className="sec-header mb16">
                <div className="sec-title">Practice Modules</div>
                <span className="sec-sub">Pick up where you left off</span>
              </div>
              <div className="flex-col gap8 stagger">
                <div className="continue-card" onClick={() => setActiveTab('coding')} tabIndex="0" role="button">
                  <div className="continue-thumb" style={{background:"rgba(77,159,255,0.1)",border:"1px solid rgba(77,159,255,0.2)"}}>💻</div>
                  <div className="continue-info">
                    <div className="continue-title">Coding Playground</div>
                    <div className="continue-meta">Solve algorithm challenges & upload question sheets</div>
                    <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(10, codingAccuracy)}%`, "--p-start":"#4d9fff", "--p-end":"#9b6dff"}}></div></div>
                  </div>
                  <div className="continue-pct" style={{color:"var(--blue)"}}>{codingAccuracy}%</div>
                  <div className="continue-arrow">›</div>
                </div>
                <div className="continue-card" onClick={() => setActiveTab('ava')} tabIndex="0" role="button">
                  <div className="continue-thumb" style={{background:"rgba(155,109,255,0.1)",border:"1px solid rgba(155,109,255,0.2)"}}>🤖</div>
                  <div className="continue-info">
                    <div className="continue-title">Ava AI Interview Coach</div>
                    <div className="continue-meta">Adaptive voice mock interview sessions</div>
                    <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(10, displayReadiness)}%`, "--p-start":"#9b6dff", "--p-end":"#00f0c8"}}></div></div>
                  </div>
                  <div className="continue-pct" style={{color:"var(--purple)"}}>{displayReadiness}%</div>
                  <div className="continue-arrow">›</div>
                </div>
                <div className="continue-card" onClick={() => setActiveTab('resume')} tabIndex="0" role="button">
                  <div className="continue-thumb" style={{background:"rgba(0,240,200,0.08)",border:"1px solid rgba(0,240,200,0.18)"}}>📄</div>
                  <div className="continue-info">
                    <div className="continue-title">Resume ATS Scanner</div>
                    <div className="continue-meta">Match resume keywords against target job descriptions</div>
                    <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(10, resumeSkill)}%`, "--p-start":"#00c4a7", "--p-end":"#00f0c8"}}></div></div>
                  </div>
                  <div className="continue-pct" style={{color:"var(--cyan)"}}>{resumeSkill}%</div>
                  <div className="continue-arrow">›</div>
                </div>
              </div>
            </section>

            {/* PERFORMANCE CHART */}
            <section className="chart-wrap" aria-label="Score trend chart">
              <div className="chart-header">
                <div>
                  <div className="sec-title" style={{marginBottom:"3px"}}>Score Trend</div>
                  <div className="sec-sub">{hasChartData ? `Last ${chartSessions.length} sessions · live score trend` : 'Complete mock sessions to view performance trend'}</div>
                </div>
              </div>
              <div className="chart-area">
                <svg className="main-chart" width="100%" viewBox="0 0 580 160" aria-label="Score trend chart" role="img">
                  <title>Score Trend</title>
                  <line x1="0" y1="20" x2="580" y2="20" stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
                  <line x1="0" y1="60" x2="580" y2="60" stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
                  <line x1="0" y1="100" x2="580" y2="100" stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
                  <line x1="0" y1="140" x2="580" y2="140" stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
                  
                  <defs>
                    <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00f0c8" stopOpacity="0.18"/>
                      <stop offset="100%" stopColor="#00f0c8" stopOpacity="0"/>
                    </linearGradient>
                  </defs>
                  
                  {hasChartData ? (
                    <>
                      <path d={fillPath} fill="url(#cyanGrad)"/>
                      <polyline points={polylinePoints} fill="none" stroke="#00f0c8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      
                      {chartPoints.map((p, idx) => (
                        <circle key={idx} cx={p.x} cy={p.y} r={idx === chartPoints.length - 1 ? 5 : 3.5} fill="var(--bg2)" stroke={idx === chartPoints.length - 1 ? "#ffd166" : "#00f0c8"} strokeWidth={idx === chartPoints.length - 1 ? 2.5 : 2}/>
                      ))}
                      
                      {chartPoints.map((p, idx) => {
                        const shouldShow = idx === 0 || idx === chartPoints.length - 1 || idx === Math.floor(chartPoints.length / 2);
                        if (!shouldShow) return null;
                        return (
                          <text key={idx} x={p.x} y={156} fontSize="8.5" fill={idx === chartPoints.length - 1 ? "#ffd166" : "#4a5a7a"} textAnchor="middle" fontFamily="Cabinet Grotesk,sans-serif">
                            {p.label}
                          </text>
                        );
                      })}
                    </>
                  ) : (
                    <text x="290" y="80" fontSize="11" fill="#4a5a7a" textAnchor="middle" fontFamily="Cabinet Grotesk,sans-serif">
                      No session data recorded yet. Start a session to view real-time score analytics.
                    </text>
                  )}
                </svg>
              </div>
            </section>

          </div>

          {/* RIGHT COLUMN */}
          <div className="flex-col gap16">

            {/* DAILY GOALS */}
            <section aria-label="Daily Goals">
              <div className="sec-header mb16">
                <div className="sec-title">Daily Goals</div>
                <span className="pill pill-cyan">{goalsDone} / 3 done</span>
              </div>
              <div className="flex-col gap8 stagger">
                <div className="goal-card">
                  <div className="goal-top">
                    <div>
                      <div className="goal-title">Solve coding challenges</div>
                      <div className="goal-desc">Target: 2 problems · Current: {displayCoding}</div>
                    </div>
                    <div className="goal-ring-wrap">
                      <div className="goal-pct-label" style={{color: goal1Pct >= 100 ? "var(--cyan)" : "var(--text2)"}}>{goal1Pct >= 100 ? "✓" : `${goal1Pct}%`}</div>
                    </div>
                  </div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${goal1Pct}%`, "--p-start":"#00c4a7", "--p-end":"#00f0c8"}}></div></div>
                </div>
                <div className="goal-card">
                  <div className="goal-top">
                    <div>
                      <div className="goal-title">Complete 1 AI Mock Session</div>
                      <div className="goal-desc">Target: 1 session · Current: {displayTotal}</div>
                    </div>
                    <div className="goal-ring-wrap">
                      <div className="goal-pct-label" style={{color: goal2Pct >= 100 ? "var(--purple)" : "var(--text2)"}}>{goal2Pct >= 100 ? "✓" : `${goal2Pct}%`}</div>
                    </div>
                  </div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${goal2Pct}%`, "--p-start":"#7c4fe0", "--p-end":"#9b6dff"}}></div></div>
                </div>
                <div className="goal-card" style={{borderColor:"rgba(255,209,102,0.18)"}}>
                  <div className="goal-top">
                    <div>
                      <div className="goal-title">Speech Confidence Goal</div>
                      <div className="goal-desc">Target: 70%+ · Current: {speechConfidence}%</div>
                    </div>
                    <div className="goal-ring-wrap">
                      <div className="goal-pct-label" style={{color:"var(--gold)",fontSize:"11px"}}>{goal3Pct}%</div>
                    </div>
                  </div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${goal3Pct}%`, "--p-start":"#f59e0b", "--p-end":"#ffd166"}}></div></div>
                </div>
              </div>
            </section>

            {/* ACTIVITY TIMELINE */}
            <section className="card" aria-label="Recent activity">
              <div className="sec-header mb16" style={{marginBottom:"12px"}}>
                <div className="sec-title">Recent Activity</div>
                <button className="btn btn-ghost btn-xs" onClick={() => setActiveTab('interviews')}>See all</button>
              </div>
              <div className="timeline" role="list">
                {completedSessions.length > 0 ? (
                  completedSessions.slice(0, 4).map((s, idx) => (
                    <div key={idx} className="tl-item" role="listitem">
                      <div className="tl-dot" style={{background:"rgba(0,240,200,0.1)",border:"1px solid rgba(0,240,200,0.25)"}}>🎯</div>
                      <div className="tl-content">
                        <div className="tl-title">Mock Interview Completed</div>
                        <div className="tl-desc">
                          {s.role || "AI Interview"} · Score {s.final_score_100 || Math.round((s.final_score || 7.5) * 10)}/100 
                          <span style={{ marginLeft: "6px", padding: "2px 8px", borderRadius: "10px", background: getGradeInfo(s.final_score_100 || (s.final_score || 7.5) * 10).bgColor, color: getGradeInfo(s.final_score_100 || (s.final_score || 7.5) * 10).color, fontWeight: 800 }}>
                            Grade {getGradeInfo(s.final_score_100 || (s.final_score || 7.5) * 10).grade}
                          </span>
                        </div>
                        <div className="tl-time">{s.created_at ? s.created_at.split('T')[0] : 'Recently'}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-muted" style={{padding: "8px 0"}}>No recent activity recorded yet. Start a practice session!</div>
                )}
              </div>
            </section>

            {/* SKILL RADAR */}
            <section className="radar-wrap" aria-label="Skill radar chart">
              <div className="sec-header mb12" style={{marginBottom:"14px"}}>
                <div className="sec-title">Skill Overview</div>
                <span className="sec-sub">Live metrics</span>
              </div>
              <div style={{display:"flex",flexDirection:"column",gap:"10px",padding:"4px 0"}}>
                <div>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:"12px",marginBottom:"4px"}}><span>Algorithms & DSA</span><span style={{color:"var(--cyan)",fontWeight:700}}>{dsaSkill}%</span></div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(5, dsaSkill)}%`, "--p-start":"#00c4a7", "--p-end":"#00f0c8"}}></div></div>
                </div>
                <div>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:"12px",marginBottom:"4px"}}><span>Interview Readiness</span><span style={{color:"var(--purple)",fontWeight:700}}>{readinessSkill}%</span></div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(5, readinessSkill)}%`, "--p-start":"#7c4fe0", "--p-end":"#9b6dff"}}></div></div>
                </div>
                <div>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:"12px",marginBottom:"4px"}}><span>Verbal Delivery</span><span style={{color:"var(--gold)",fontWeight:700}}>{speechSkill}%</span></div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(5, speechSkill)}%`, "--p-start":"#f59e0b", "--p-end":"#ffd166"}}></div></div>
                </div>
                <div>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:"12px",marginBottom:"4px"}}><span>Resume Compatibility</span><span style={{color:"var(--blue)",fontWeight:700}}>{resumeSkill}%</span></div>
                  <div className="progress-bar"><div className="progress-fill" style={{width:`${Math.max(5, resumeSkill)}%`, "--p-start":"#4d9fff", "--p-end":"#00f0c8"}}></div></div>
                </div>
              </div>
            </section>

          </div>{/* end right col */}
        </div>{/* end g-main */}
      </div>{/* end container */}
    </div>
  );
}
