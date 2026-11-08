"""
Resume Intelligence Service: Extracts structured candidate profiles with strict provenance,
grounds interview questions in verified resume facts, and protects against AI hallucinations.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Canonical technology and framework taxonomies
KNOWN_LANGUAGES = {"python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "sql", "html", "css"}
LANGUAGE_CANONICAL = {
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "c++": "C++",
    "c#": "C#",
    "php": "PHP"
}
KNOWN_FRAMEWORKS = {"react", "angular", "vue", "next.js", "node.js", "express", "flask", "django", "fastapi", "spring boot", "asp.net", "tensorflow", "pytorch", "keras", "opencv", "yolo"}
KNOWN_DATABASES = {"postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra", "sqlite", "dynamodb", "elasticsearch"}
KNOWN_TOOLS = {"docker", "kubernetes", "aws", "gcp", "azure", "git", "github", "linux", "terraform", "kafka", "rabbitmq"}


class ResumeIntelligenceService:
    """Extracts structured profiles, records verified claims with provenance, and prevents AI hallucinations."""

    @staticmethod
    def extract_structured_candidate_profile(raw_resume_text: str) -> Dict[str, Any]:
        """
        Parses raw resume text into a normalized candidate profile with exact text provenance.
        Extracts verified skills, projects, experience, and education.
        """
        if not raw_resume_text or not raw_resume_text.strip():
            return {
                "skills": [],
                "languages": [],
                "frameworks": [],
                "databases": [],
                "tools": [],
                "projects": [],
                "experience_years_estimated": 1.0,
                "verified_claims": []
            }

        text_lower = raw_resume_text.lower()
        extracted_languages = []
        extracted_frameworks = []
        extracted_databases = []
        extracted_tools = []
        claims = []

        # 1. Extract Languages
        for lang in sorted(KNOWN_LANGUAGES, key=len, reverse=True):
            pattern = r'\b' + re.escape(lang) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                extracted_languages.append(LANGUAGE_CANONICAL.get(lang, lang.capitalize()))
                start, end = match.span()
                snippet = raw_resume_text[max(0, start - 25):min(len(raw_resume_text), end + 25)].strip()
                claims.append({
                    "type": "SKILL",
                    "claim": lang,
                    "section_provenance": snippet,
                    "confidence": 1.0
                })

        # 2. Extract Frameworks & Libraries
        for fw in sorted(KNOWN_FRAMEWORKS, key=len, reverse=True):
            pattern = r'\b' + re.escape(fw) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                extracted_frameworks.append(fw.title())
                start, end = match.span()
                snippet = raw_resume_text[max(0, start - 25):min(len(raw_resume_text), end + 25)].strip()
                claims.append({
                    "type": "FRAMEWORK",
                    "claim": fw,
                    "section_provenance": snippet,
                    "confidence": 1.0
                })

        # 3. Extract Databases
        for db in sorted(KNOWN_DATABASES, key=len, reverse=True):
            pattern = r'\b' + re.escape(db) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                extracted_databases.append(db.title())
                start, end = match.span()
                snippet = raw_resume_text[max(0, start - 25):min(len(raw_resume_text), end + 25)].strip()
                claims.append({
                    "type": "DATABASE",
                    "claim": db,
                    "section_provenance": snippet,
                    "confidence": 1.0
                })

        # 4. Extract Cloud & DevOps Tools
        for tool in sorted(KNOWN_TOOLS, key=len, reverse=True):
            pattern = r'\b' + re.escape(tool) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                extracted_tools.append(tool.title())
                start, end = match.span()
                snippet = raw_resume_text[max(0, start - 25):min(len(raw_resume_text), end + 25)].strip()
                claims.append({
                    "type": "TOOL",
                    "claim": tool,
                    "section_provenance": snippet,
                    "confidence": 1.0
                })

        # 5. Extract Projects
        projects = []
        lines = raw_resume_text.split("\n")
        in_project_section = False
        current_project: Optional[Dict[str, Any]] = None

        for line in lines:
            trimmed = line.strip()
            lower = trimmed.lower()
            if any(h in lower for h in ["projects", "personal projects", "academic projects", "key projects"]):
                in_project_section = True
                continue
            if in_project_section and any(h in lower for h in ["education", "experience", "work history", "certifications", "skills"]):
                if current_project:
                    projects.append(current_project)
                    current_project = None
                in_project_section = False
                continue

            if in_project_section and trimmed:
                # Detect project title line (e.g., "Traffic Management System | Python, OpenCV" or bullet)
                if not current_project or (len(trimmed) < 60 and not trimmed.startswith(("-", "•", "*")) and any(sep in trimmed for sep in ["|", "-", ":", "–"])):
                    if current_project:
                        projects.append(current_project)
                    parts = re.split(r'[|\-–:]', trimmed)
                    p_title = parts[0].strip()
                    p_tech = [t.strip() for t in parts[1:] if t.strip()] if len(parts) > 1 else []
                    current_project = {
                        "title": p_title,
                        "technologies": p_tech,
                        "description": "",
                        "raw_lines": [trimmed]
                    }
                    claims.append({
                        "type": "PROJECT",
                        "claim": p_title,
                        "section_provenance": trimmed,
                        "confidence": 1.0
                    })
                elif current_project:
                    current_project["raw_lines"].append(trimmed)
                    current_project["description"] += " " + trimmed.lstrip("-•* ")

        if current_project:
            projects.append(current_project)

        # Estimate years of experience
        exp_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience', text_lower)
        estimated_exp = 1.0
        if exp_matches:
            try:
                estimated_exp = float(max(int(m) for m in exp_matches))
            except Exception:
                estimated_exp = 1.0

        all_skills = list(dict.fromkeys(extracted_languages + extracted_frameworks + extracted_databases + extracted_tools))

        return {
            "skills": all_skills,
            "languages": extracted_languages,
            "frameworks": extracted_frameworks,
            "databases": extracted_databases,
            "tools": extracted_tools,
            "projects": projects[:5],
            "experience_years_estimated": estimated_exp,
            "verified_claims": claims
        }

    @staticmethod
    def persist_verified_claims(supabase_client, session_id: str, verified_claims: List[Dict[str, Any]]) -> int:
        """Persists verified resume claims into candidate_resume_claims table."""
        count = 0
        for idx, claim in enumerate(verified_claims):
            rec = {
                "id": f"claim_{session_id}_{idx}_{int(datetime.now(timezone.utc).timestamp())}",
                "session_id": session_id,
                "claim_type": claim.get("type", "SKILL"),
                "claim_text": claim.get("claim", ""),
                "provenance_section": claim.get("section_provenance", "")[:300],
                "confidence": float(claim.get("confidence", 1.0)),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            try:
                supabase_client.table("candidate_resume_claims").insert(rec).execute()
                count += 1
            except Exception as e:
                logger.warning(f"Could not persist claim {idx} for session {session_id}: {e}")
        return count

    @staticmethod
    def build_grounded_resume_context(structured_profile: Dict[str, Any]) -> str:
        """
        Builds a compact, strictly verifiable resume context prompt block.
        Ensures the AI knows what was explicitly claimed versus what is unestablished.
        """
        skills_str = ", ".join(structured_profile.get("skills", [])) or "None listed"
        projects = structured_profile.get("projects", [])
        proj_lines = []
        for p in projects:
            title = p.get("title", "")
            desc = p.get("description", "").strip()[:180]
            proj_lines.append(f"- Project: {title}\n  Claimed Scope: {desc if desc else 'General implementation'}")
        projects_str = "\n".join(proj_lines) if proj_lines else "None listed"

        return f"""═══════════════════════════════
VERIFIED RESUME CLAIMS (PROVENANCE-BOUNDED)
═══════════════════════════════
- Explicitly Claimed Skills: {skills_str}
- Verified Projects:
{projects_str}

CRITICAL ANTI-HALLUCINATION INSTRUCTION:
1. You may ask the candidate to explain their architecture, implementation challenges, or design trade-offs regarding these verified projects.
2. DO NOT invent specific metrics, third-party libraries, or technology versions (e.g. YOLOv8, React 19) unless explicitly stated above.
3. If asking about a project, ground your question strictly in the candidate's claimed scope."""

    @staticmethod
    def detect_question_hallucination(question_text: str, structured_profile: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates whether a generated question hallucinates specific tools or frameworks
        not present in the candidate's verified profile.
        Returns (is_clean, reason).
        """
        q_lower = question_text.lower()
        verified_skills_lower = {s.lower() for s in structured_profile.get("skills", [])}

        # Check for ungrounded specific tech mentions
        all_known_tech = KNOWN_LANGUAGES | KNOWN_FRAMEWORKS | KNOWN_DATABASES | KNOWN_TOOLS
        mentioned_tech = []
        for tech in all_known_tech:
            if re.search(r'\b' + re.escape(tech) + r'\b', q_lower):
                mentioned_tech.append(tech)

        ungrounded = [t for t in mentioned_tech if t not in verified_skills_lower]
        # If question asserts candidate used an ungrounded technology as a fact (e.g. "In your React project...")
        for un_t in ungrounded:
            if re.search(r'(your|using|built with|implemented in)\s+' + re.escape(un_t), q_lower):
                return False, f"Question falsely asserts candidate used '{un_t}' which is not in verified claims."

        return True, "Question is properly grounded."
