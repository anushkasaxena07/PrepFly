"""
Conversational Onboarding Service for PrepFly Adaptive AI Mentor.
Parses Job Descriptions into a structured 9-category taxonomy,
collects candidate goals, target dates, experience metrics,
and orchestrates the diagnostic onboarding baseline.
"""

from typing import Dict, List, Optional, Any
import json
import uuid
import re
from datetime import datetime, timezone

from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id
from services.candidate_profile_service import CandidateProfileService
from services.assessment_service import AssessmentService
from services.ai_service import safe_invoke_llm
from local_supabase import get_supabase_client


class ConversationalOnboardingService:
    """Manages conversational onboarding, structured JD analysis, and candidate calibration."""

    @classmethod
    def parse_job_description(
        cls,
        jd_text: str,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parses raw job description text into the required 9 distinct requirement categories.
        Uses structured heuristics and LLM extraction to guarantee high fidelity.
        """
        role_label = target_role or "Software Engineer"
        company_label = target_company or "Target Company"

        if not jd_text or len(jd_text.strip()) < 20:
            # Generate sensible default categorized requirements based on role
            return cls._get_default_role_breakdown(role_label)

        system_prompt = (
            "You are an expert technical recruiting auditor. Given a job description, "
            "extract and categorize the requirements into exactly these 9 JSON arrays:\n"
            "1. mandatory_technical: core must-have requirements\n"
            "2. preferred_qualifications: nice-to-have or bonus skills\n"
            "3. programming_languages: specified languages (e.g. Python, Java, Go, TypeScript)\n"
            "4. core_cs_fundamentals: algorithms, data structures, OS, concurrency, networking\n"
            "5. frameworks_and_tools: libraries, frameworks, Docker, Kubernetes, Git, CI/CD\n"
            "6. role_specific_technologies: domain-specific tools (e.g. PyTorch, React, Kafka, Spark)\n"
            "7. system_design: scalability, microservices, distributed systems, database indexing\n"
            "8. practical_experience: production experience, project complexity, system debugging\n"
            "9. behavioral_and_culture: ownership, leadership, communication, cross-functional collaboration\n\n"
            "Return valid JSON only matching the schema:\n"
            "{\n"
            '  "mandatory_technical": ["..."],\n'
            '  "preferred_qualifications": ["..."],\n'
            '  "programming_languages": ["..."],\n'
            '  "core_cs_fundamentals": ["..."],\n'
            '  "frameworks_and_tools": ["..."],\n'
            '  "role_specific_technologies": ["..."],\n'
            '  "system_design": ["..."],\n'
            '  "practical_experience": ["..."],\n'
            '  "behavioral_and_culture": ["..."],\n'
            '  "required_years_experience": 2\n'
            "}"
        )

        user_prompt = f"Target Role: {role_label}\nTarget Company: {company_label}\n\nJob Description:\n{jd_text}"

        try:
            raw_json = safe_invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            match = re.search(r"\{[\s\S]*\}", raw_json)
            if match:
                parsed = json.loads(match.group(0))
                # Validate all 9 categories exist
                categories = [
                    "mandatory_technical", "preferred_qualifications", "programming_languages",
                    "core_cs_fundamentals", "frameworks_and_tools", "role_specific_technologies",
                    "system_design", "practical_experience", "behavioral_and_culture"
                ]
                for c in categories:
                    if c not in parsed or not isinstance(parsed[c], list):
                        parsed[c] = []
                if "required_years_experience" not in parsed:
                    parsed["required_years_experience"] = 2
                return parsed
        except Exception:
            pass

        # Fallback to taxonomy keyword matcher
        return cls._heuristic_categorization(jd_text, role_label)

    @classmethod
    def _get_default_role_breakdown(cls, role_label: str) -> Dict[str, Any]:
        """Provides curated 9-dimension requirements for common interview roles."""
        role_key = normalize_role_id(role_label)
        if "ai" in role_key or "ml" in role_key:
            return {
                "mandatory_technical": ["Supervised Machine Learning", "Deep Learning Foundations", "Model Evaluation & Metrics", "Model Deployment"],
                "preferred_qualifications": ["Experience with LLMs & RAG", "Published research or Kaggle achievements", "Distributed training with Ray or DeepSpeed"],
                "programming_languages": ["Python", "SQL", "C++"],
                "core_cs_fundamentals": ["Algorithms & Complexity Bounds", "Linear Algebra & Probability", "Concurrency in Python"],
                "frameworks_and_tools": ["PyTorch", "TensorFlow", "HuggingFace Transformers", "Docker", "Weights & Biases"],
                "role_specific_technologies": ["Vector Databases (Chroma, Pinecone)", "ONNX / TensorRT", "Feature Stores"],
                "system_design": ["Real-Time Recommendation Systems", "High-Throughput ML Inference Pipelines", "Feature Serving at Scale"],
                "practical_experience": ["Training production neural networks", "Mitigating model drift and hallucinations", "Building end-to-end data pipelines"],
                "behavioral_and_culture": ["Explaining complex math simply", "Cross-functional collaboration with product teams", "Data-driven decision making"],
                "required_years_experience": 2
            }
        return {
            "mandatory_technical": ["Data Structures & Algorithms", "Clean Object-Oriented Design", "Relational Database Queries", "RESTful API Development"],
            "preferred_qualifications": ["Cloud infrastructure experience (AWS/GCP)", "Open source contributions", "CI/CD automation"],
            "programming_languages": ["Python", "Java", "TypeScript", "SQL"],
            "core_cs_fundamentals": ["Operating Systems & Memory Isolation", "Database ACID & Indexing", "Computer Networks (HTTP/TCP)"],
            "frameworks_and_tools": ["Git", "Docker", "PostgreSQL", "Redis", "Linux CLI"],
            "role_specific_technologies": ["FastAPI / Spring Boot / Express", "ORM & Query Builders", "Message Queues (Kafka/RabbitMQ)"],
            "system_design": ["Cache-Aside & Rate Limiting", "Horizontal Scaling & Load Balancing", "Microservices Architecture"],
            "practical_experience": ["Debugging production service outages", "Writing comprehensive unit & integration tests", "Refactoring legacy code"],
            "behavioral_and_culture": ["Structured STAR problem solving", "Ownership and accountability", "Effective engineering communication"],
            "required_years_experience": 2
        }

    @classmethod
    def _heuristic_categorization(cls, jd_text: str, role_label: str) -> Dict[str, Any]:
        """Categorizes extracted taxonomy keywords when LLM is unavailable."""
        matched_skills = SkillTaxonomyService.map_text_to_skills(jd_text)
        return {
            "mandatory_technical": [s for s in matched_skills if "dsa_" in s or "sys_" in s][:4] or ["Core Programming", "Data Structures"],
            "preferred_qualifications": ["Demonstrated production system ownership", "Advanced domain specialization"],
            "programming_languages": ["Python", "Java", "SQL", "JavaScript"],
            "core_cs_fundamentals": [s for s in matched_skills if "cs_" in s] or ["Data Structures", "OS Fundamentals"],
            "frameworks_and_tools": ["Git", "Docker", "Database Querying", "REST APIs"],
            "role_specific_technologies": [s for s in matched_skills if "ml_" in s or "dl_" in s or "genai_" in s] or ["Domain Frameworks"],
            "system_design": [s for s in matched_skills if "sys_" in s] or ["System Scalability", "Caching & Architecture"],
            "practical_experience": ["Software Engineering Projects", "Code Maintenance & Unit Testing"],
            "behavioral_and_culture": ["STAR Framework", "Clear Technical Communication", "Ownership & Initiative"],
            "required_years_experience": 2
        }

    @classmethod
    def complete_onboarding(
        cls,
        user_id: str,
        onboarding_data: Dict[str, Any],
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Stores candidate onboarding selections, parses JD if supplied,
        creates/updates candidate profile, and seeds the diagnostic assessment.
        """
        client = supabase_client or get_supabase_client()

        target_company = onboarding_data.get("target_company", "Top Tech Firm").strip()
        target_role = onboarding_data.get("target_role", "Software Development Engineer").strip()
        experience_level = onboarding_data.get("experience_level", "Mid-Level").strip()
        candidate_years_experience = float(onboarding_data.get("candidate_years_experience", 1.5))
        required_years_experience = float(onboarding_data.get("required_years_experience", 2.0))
        target_date = onboarding_data.get("target_date", "30 days").strip()
        daily_minutes = int(onboarding_data.get("daily_minutes", 60))
        resume_text = onboarding_data.get("resume_text", "").strip()
        jd_text = onboarding_data.get("job_description", "").strip()

        # 1. Parse JD requirements into 9 categories
        categorized_jd = cls.parse_job_description(jd_text, target_role, target_company)

        # 2. Update Candidate Profile
        profile_data = {
            "target_role": target_role,
            "target_company": target_company,
            "experience_level": experience_level,
            "candidate_years_experience": candidate_years_experience,
            "required_years_experience": required_years_experience,
            "target_date": target_date,
            "daily_minutes": daily_minutes,
            "resume_text": resume_text,
            "job_description": jd_text,
            "categorized_requirements": categorized_jd,
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
        }
        profile = CandidateProfileService.create_or_update_profile(user_id, profile_data, client)

        # 3. Initialize Diagnostic Session for the target role
        diagnostic_session = AssessmentService.start_diagnostic_session(
            user_id=user_id,
            target_role=target_role,
            supabase_client=client
        )

        return {
            "status": "success",
            "message": "Onboarding completed successfully. Diagnostic assessment initialized.",
            "profile": profile,
            "categorized_requirements": categorized_jd,
            "diagnostic_assessment": diagnostic_session
        }
