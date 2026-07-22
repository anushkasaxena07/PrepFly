import json
from datetime import datetime
from services.ai_config import AI_INTERVIEWER
from services.grading_service import calculate_grade_info, compute_section_grades, award_badges

def generate_pdf_html_report(candidate_name, candidate_email, date_str, overall_score, grade, feedbacks, final_report_markdown, ats_score=None, structured_resume=None):
    ai_name = AI_INTERVIEWER["name"]
    
    score_100 = round(float(overall_score) * 10) if float(overall_score) <= 10 else round(float(overall_score))
    g_info = calculate_grade_info(score_100)
    gc = g_info["color"]

    section_grades = compute_section_grades(feedbacks)
    badges = award_badges(score_100, section_grades)
    
    comm_sum = tech_sum = conf_sum = proj_sum = prob_sum = 0
    valid_m = 0

    qa_blocks = []
    for i, item in enumerate(feedbacks):
        if not isinstance(item, dict): continue
        sc = item.get("score", 7)
        c = "#00e5c3" if sc >= 8 else "#00b8ff" if sc >= 6 else "#f59e0b" if sc >= 4 else "#ff4f6a"
        
        qa_blocks.append(f"""
        <div class="qa-card">
          <div class="qa-hdr">
            <span class="q-num">Question {i+1}</span>
            <span class="sc-badge" style="background:{c}18; color:{c}; border: 1px solid {c}44;">Score: {sc}/10</span>
          </div>
          <div class="q-text">{item.get('question', '')}</div>
          <div class="ans-label">Candidate Answer</div>
          <div class="ans-text">"{item.get('response', '')}"</div>
          <div class="fb-label">{ai_name}'s Evaluation & Feedback</div>
          <div class="fb-text">{item.get('feedback', '')}</div>
        </div>
        """)

    ats_badge = ""
    if ats_score:
        ats_badge = f"""<div style="background: rgba(0,196,167,0.15); border: 1px solid #00c4a7; border-radius: 12px; padding: 10px 16px; text-align: center;">
            <div style="font-size: 10px; color: #00c4a7; font-weight: 800; text-transform: uppercase;">ATS Resume Match</div>
            <div style="font-size: 20px; font-weight: 900; color: #fff;">{ats_score}%</div>
        </div>"""

    badge_html = "".join([f'<span style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:6px 14px; border-radius:20px; font-size:12px; color:#fff; font-weight:700;">{b["icon"]} {b["name"]}</span>' for b in badges])

    sec_grid_html = "".join([f'''
    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; text-align: center;">
      <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">{s["name"]}</div>
      <div style="font-size: 18px; font-weight: 900; color: {s["color"]}; margin-top: 4px;">{s["score"]} <span style="font-size: 12px; opacity:0.8;">({s["grade"]})</span></div>
    </div>
    ''' for s in section_grades])

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>PrepFly Executive Evaluation Report - {ai_name}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #070b14; color: #f0f4fd; padding: 40px; line-height: 1.6; }}
    .hdr {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 28px; }}
    .brand {{ font-size: 24px; font-weight: 900; background: linear-gradient(135deg, #00c4a7, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .meta {{ font-size: 12px; color: #94a3b8; text-align: right; line-height: 1.6; }}
    .hero {{ background: linear-gradient(145deg, rgba(12, 18, 32, 0.9), rgba(24, 18, 40, 0.9)); border: 1px solid rgba(124, 58, 237, 0.3); border-radius: 20px; padding: 28px; margin-bottom: 28px; display: flex; gap: 24px; align-items: center; }}
    .grade-circle {{ width: 94px; height: 94px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 32px; font-weight: 900; border: 4px solid {gc}; background: {g_info["bgColor"]}; color: {gc}; box-shadow: 0 0 28px {gc}44; flex-shrink: 0; }}
    .sec-title {{ font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #00c4a7; margin: 28px 0 16px; border-left: 3px solid #00c4a7; padding-left: 10px; }}
    .qa-card {{ background: rgba(12, 18, 32, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; margin-bottom: 16px; }}
    .qa-hdr {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .q-num {{ font-size: 12px; font-weight: 800; color: #a78bfa; }}
    .sc-badge {{ padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; }}
    .q-text {{ font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 12px; }}
    .ans-label {{ font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }}
    .ans-text {{ font-size: 13px; color: #cbd5e1; font-style: italic; background: rgba(0,0,0,0.2); padding: 10px 14px; border-radius: 10px; margin-bottom: 12px; line-height: 1.5; }}
    .fb-label {{ font-size: 11px; color: #00c4a7; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }}
    .fb-text {{ font-size: 13px; color: #e2e8f0; white-space: pre-wrap; line-height: 1.6; }}
    .rpt-box {{ background: rgba(12, 18, 32, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 24px; font-size: 14px; color: #e2e8f0; white-space: pre-wrap; line-height: 1.7; }}
    .ftr {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="hdr">
    <div class="brand">🚀 PrepFly Report ({ai_name})</div>
    <div class="meta">
      <strong>Candidate:</strong> {candidate_name} ({candidate_email})<br/>
      <strong>Generated:</strong> {date_str}<br/>
      <strong>Questions Evaluated:</strong> {len(qa_blocks)}
    </div>
  </div>

  <div class="hero">
    <div class="grade-circle">
      <div>{g_info["grade"]}</div>
      <div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{g_info["score"]}/100</div>
    </div>
    <div style="flex: 1;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <div style="font-size: 18px; font-weight: 900; color: #fff;">{g_info["label"]} ({g_info["level"]} Level)</div>
          <div style="font-size: 13px; color: {gc}; font-weight: 800; margin-top: 2px;">📌 Hiring Recommendation: {g_info["rec"]}</div>
        </div>
        {ats_badge}
      </div>
      
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0;">
        {badge_html}
      </div>
    </div>
  </div>

  <div class="sec-title">Section Grades Breakdown (10 Dimensions)</div>
  <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px;">
    {sec_grid_html}
  </div>

  <div class="sec-title">Question-by-Question Deep Dive</div>
  {"".join(qa_blocks)}

  <div class="sec-title">Final Recruiter Evaluation Summary & Actionable Roadmap</div>
  <div class="rpt-box">{final_report_markdown}</div>

  <div class="ftr">
    Official AI Candidate Assessment Report · Conducted by {ai_name} ({AI_INTERVIEWER['role']}) · Confidential
  </div>
</body>
</html>
"""
    return html
