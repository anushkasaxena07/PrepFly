import os
import hashlib
import json
import docx
from datetime import datetime

def get_supabase():
    import app
    return app.supabase

def extract_text_from_pdf(filepath):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        try:
            import fitz
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e2:
            print(f"PDF extraction error: {e2}")
    return text.strip()

def extract_text_from_docx(filepath):
    try:
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        print(f"docx extract error: {e}")
        return ""

def compute_text_hash(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def get_cached_resume(text_hash):
    supabase = get_supabase()
    try:
        res = supabase.table("parsed_resumes").select("*").eq("hash", text_hash).execute()
        if res and hasattr(res, "data") and res.data:
            row = res.data[0]
            s_data = row.get("structured_data")
            if isinstance(s_data, str):
                try: s_data = json.loads(s_data)
                except: s_data = {}

            m_info = row.get("missing_info")
            if isinstance(m_info, str):
                try: m_info = json.loads(m_info)
                except: m_info = []

            return {
                "id": row.get("id"),
                "raw_text": row.get("raw_text"),
                "structured_data": s_data or {},
                "ats_score": row.get("ats_score", 70),
                "missing_info": m_info or []
            }
    except Exception as e:
        print("Get cached resume notice:", e)
    return None

def save_cached_resume(text_hash, raw_text, structured_data, ats_score, missing_info):
    supabase = get_supabase()
    res_id = f"res_{text_hash[:12]}"
    try:
        supabase.table("parsed_resumes").upsert({
            "id": res_id,
            "hash": text_hash,
            "raw_text": raw_text,
            "structured_data": json.dumps(structured_data) if isinstance(structured_data, dict) else structured_data,
            "ats_score": ats_score,
            "missing_info": json.dumps(missing_info) if isinstance(missing_info, list) else missing_info,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print("Save resume cache error:", e)

def parse_resume_content(raw_text, chat_model=None):
    if chat_model is None:
        from services.gemini import get_pro_model
        chat_model = get_pro_model()
    if not raw_text or not raw_text.strip():
        return {
            "structured_data": {},
            "ats_score": 50,
            "missing_info": ["Complete Resume Content"]
        }

    text_hash = compute_text_hash(raw_text)
    cached = get_cached_resume(text_hash)
    if cached:
        print(f"[RESUME CACHE HIT] Reusing cached resume parsing for hash {text_hash[:8]}")
        return cached

    prompt = f"""Analyze the following resume text and extract structured candidate profile data.
Return ONLY valid JSON with no markdown formatting or backticks.

Resume Content:
{raw_text[:3500]}

Expected JSON Schema:
{{
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["string"],
  "projects": [{{"title": "string", "tech_stack": ["string"], "description": "string"}}],
  "experience": [{{"role": "string", "company": "string", "duration": "string", "key_achievements": ["string"]}}],
  "education": [{{"degree": "string", "institution": "string", "year": "string"}}],
  "ats_score": 75,
  "missing_info": ["string"]
}}"""

    try:
        from langchain_core.messages import HumanMessage
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(content)
        ats_score = parsed.get("ats_score", 70)
        missing_info = parsed.get("missing_info", [])
        save_cached_resume(text_hash, raw_text, parsed, ats_score, missing_info)
        return {
            "structured_data": parsed,
            "ats_score": ats_score,
            "missing_info": missing_info
        }
    except Exception as e:
        print("Parse resume AI error:", e)
        fallback_data = {
            "full_name": "Candidate",
            "skills": ["Software Engineering", "Algorithms"],
            "ats_score": 70,
            "missing_info": ["Detailed project metrics"]
        }
        save_cached_resume(text_hash, raw_text, fallback_data, 70, fallback_data["missing_info"])
        return {
            "structured_data": fallback_data,
            "ats_score": 70,
            "missing_info": fallback_data["missing_info"]
        }
