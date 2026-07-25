"""
Real ATS Engine — deterministic keyword/skill extraction and match scoring.
The LLM is only used for the written narrative (summary, suggestions).
No AI guessing of percentages or skill counts.
"""

import re
from typing import List, Dict, Tuple

# ─── Comprehensive skill dictionary ─────────────────────────────────────────
SKILL_DICTIONARY = {
    "languages":    ["python", "javascript", "java", "c++", "c#", "typescript",
                     "go", "golang", "rust", "php", "ruby", "swift", "kotlin",
                     "scala", "r", "matlab", "perl", "bash", "shell", "sql"],
    "frontend":     ["react", "vue", "angular", "next.js", "nuxt", "svelte",
                     "redux", "mobx", "html", "css", "sass", "tailwind",
                     "bootstrap", "webpack", "vite", "gatsby", "storybook",
                     "figma", "webgl", "three.js", "d3.js", "rxjs",
                     "accessibility", "a11y", "responsive design", "pwa",
                     "typescript", "javascript", "es6", "graphql client"],
    "backend":      ["node.js", "express", "fastapi", "django", "flask",
                     "spring boot", "spring", "laravel", "rails", "gin",
                     "nestjs", "graphql", "rest api", "rest", "grpc",
                     "microservices", "celery", "kafka", "rabbitmq", "message queue",
                     "websocket", "oauth", "jwt", "authentication"],
    "databases":    ["postgresql", "mysql", "mongodb", "redis", "dynamodb",
                     "sqlite", "cassandra", "elasticsearch", "neo4j",
                     "supabase", "firebase", "mariadb", "oracle", "mssql",
                     "vector database", "pinecone", "weaviate", "qdrant"],
    "cloud":        ["aws", "azure", "gcp", "google cloud", "ec2", "s3", "rds",
                     "lambda", "ecs", "eks", "cloudfront", "iam", "vpc",
                     "azure devops", "gke", "cloud run", "bigquery",
                     "cloudwatch", "sqs", "sns", "kinesis"],
    "devops":       ["docker", "kubernetes", "k8s", "terraform", "ansible",
                     "jenkins", "github actions", "gitlab ci", "ci/cd",
                     "helm", "argocd", "prometheus", "grafana", "datadog",
                     "nginx", "linux", "bash scripting", "infrastructure as code"],
    "ml_ai":        ["machine learning", "deep learning", "tensorflow", "pytorch",
                     "keras", "scikit-learn", "sklearn", "numpy", "pandas",
                     "nlp", "llm", "fine-tuning", "rag", "langchain",
                     "hugging face", "transformers", "openai", "computer vision",
                     "opencv", "xgboost", "lightgbm", "mlflow", "mlops",
                     "feature engineering", "model deployment", "statistics",
                     "linear algebra", "neural network"],
    "tools":        ["git", "github", "gitlab", "jira", "confluence",
                     "postman", "swagger", "linux", "vim", "vscode",
                     "intellij", "datadog", "sentry", "splunk", "pagerduty"],
    "soft":         ["agile", "scrum", "kanban", "leadership", "communication",
                     "project management", "team management", "mentoring",
                     "code review", "system design", "problem solving",
                     "architecture", "technical writing", "stakeholder management"],
    "security":     ["cybersecurity", "penetration testing", "owasp",
                     "vulnerability assessment", "soc", "siem", "encryption",
                     "zero trust", "api security"],
    "data":         ["data engineering", "spark", "hadoop", "airflow", "dbt",
                     "etl", "data pipeline", "data warehouse", "snowflake",
                     "dbt", "tableau", "power bi", "looker", "superset",
                     "data lake", "lakehouse", "databricks"],
    "mobile":       ["react native", "flutter", "android", "ios", "swift",
                     "kotlin", "expo", "firebase", "push notifications"],
    "testing":      ["unit testing", "integration testing", "jest", "pytest",
                     "cypress", "selenium", "playwright", "tdd", "bdd",
                     "load testing", "performance testing", "qa"],
}

# Flatten into one list for lookup
ALL_SKILLS: List[str] = list({s for group in SKILL_DICTIONARY.values() for s in group})

# ─── Alias / synonym map ────────────────────────────────────────────────────
ALIASES: Dict[str, List[str]] = {
    "node.js":          ["nodejs", "node js", "node"],
    "next.js":          ["nextjs", "next js"],
    "postgresql":       ["postgres", "pg"],
    "javascript":       ["js", "vanillajs", "es6", "es2015"],
    "typescript":       ["ts"],
    "kubernetes":       ["k8s"],
    "python":           ["py"],
    "graphql":          ["gql"],
    "react":            ["reactjs", "react.js", "react js"],
    "vue":              ["vuejs", "vue.js", "vue js"],
    "angular":          ["angularjs"],
    "scikit-learn":     ["sklearn"],
    "tensorflow":       ["tf"],
    "go":               ["golang"],
    "c++":              ["cpp", "c plus plus"],
    "c#":               ["csharp", "c sharp", "dotnet", ".net"],
    "rest api":         ["restful", "rest apis", "rest-api", "api development"],
    "ci/cd":            ["continuous integration", "continuous delivery",
                        "continuous deployment", "github actions", "gitlab ci"],
    "machine learning": ["ml"],
    "deep learning":    ["dl"],
    "natural language processing": ["nlp"],
    "large language model": ["llm", "llms"],
}


def _build_reverse_alias_map() -> Dict[str, str]:
    """Build alias → canonical mapping for fast lookup."""
    mapping: Dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            mapping[alias.lower()] = canonical.lower()
    return mapping

_REVERSE_ALIASES = _build_reverse_alias_map()


def normalize_skill(raw: str) -> str:
    """Normalize a raw token to its canonical skill name."""
    low = raw.lower().strip()
    return _REVERSE_ALIASES.get(low, low)


def extract_skills(text: str) -> List[str]:
    """
    Extract known skills from text using word-boundary regex matching.
    Handles multi-word skills (e.g. 'machine learning', 'next.js') and aliases.
    Returns deduplicated list of canonical skill names.
    """
    lower_text = text.lower()
    found: set = set()

    # First pass: check ALL_SKILLS with word-boundary regex
    for skill in ALL_SKILLS:
        # Escape regex special chars in skill name
        escaped = re.escape(skill)
        # Use word boundaries — \b doesn't work well for symbols like "." in "next.js"
        # So we use lookbehind/lookahead for non-alphanumeric chars
        pattern = r'(?<![a-z0-9])' + escaped + r'(?![a-z0-9])'
        if re.search(pattern, lower_text, re.IGNORECASE):
            canonical = normalize_skill(skill)
            found.add(canonical)

    # Second pass: check aliases (tokens like "nodejs", "k8s", "ts")
    for alias, canonical in _REVERSE_ALIASES.items():
        escaped = re.escape(alias)
        pattern = r'(?<![a-z0-9])' + escaped + r'(?![a-z0-9])'
        if re.search(pattern, lower_text, re.IGNORECASE):
            found.add(canonical)

    return sorted(found)


def extract_years_experience(text: str) -> int | None:
    """
    Extract the maximum years of experience mentioned in text.
    Handles patterns like '5 years', '3+ years experience', '7 yrs'.
    Returns None if not found.
    """
    patterns = [
        r'(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
        r'(?:experience|exp)\s*(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)',
        r'(\d+)\s*\+?\s*(?:years?|yrs?)',
    ]
    found_years = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                found_years.append(int(match.group(1)))
            except (ValueError, IndexError):
                pass
    return max(found_years) if found_years else None


def calculate_ats_match(resume_text: str, job_description: str) -> dict:
    """
    Core deterministic ATS match engine.
    Returns structured scoring data — NO LLM calls in this function.
    """
    resume_skills = set(extract_skills(resume_text))
    jd_skills = set(extract_skills(job_description))

    matched_skills = sorted(resume_skills & jd_skills)
    missing_skills = sorted(jd_skills - resume_skills)
    bonus_skills = sorted(resume_skills - jd_skills)

    # Skill match percentage
    skill_match_pct = (
        round((len(matched_skills) / len(jd_skills)) * 100)
        if jd_skills else 0
    )

    # Experience match
    resume_years = extract_years_experience(resume_text)
    required_years = extract_years_experience(job_description)
    if required_years:
        if resume_years is None:
            experience_pct = 70  # candidate didn't state experience — mild penalty
        elif resume_years >= required_years:
            experience_pct = 100
        else:
            experience_pct = min(99, round((resume_years / required_years) * 100))
    else:
        experience_pct = 100  # no requirement stated → full marks

    # Keyword overlap (ALL words, not just skills — catches project names, domain terms)
    stop_words = {
        "and", "the", "for", "with", "have", "your", "from", "that", "this",
        "will", "are", "our", "you", "they", "all", "any", "can", "has",
        "not", "job", "role", "team", "work", "must", "should", "also",
        "years", "year", "experience", "strong", "good", "ability", "well",
        "using", "use", "looking", "ideal", "including", "based", "new",
        "etc", "within", "across", "help", "build", "building", "make"
    }
    jd_words = set(
        w.lower() for w in re.findall(r'\b[a-zA-Z][a-zA-Z0-9#+./\-]{2,}\b', job_description)
        if w.lower() not in stop_words and len(w) > 2
    )
    resume_words = set(
        w.lower() for w in re.findall(r'\b[a-zA-Z][a-zA-Z0-9#+./\-]{2,}\b', resume_text)
        if w.lower() not in stop_words
    )
    keyword_overlap_pct = (
        round((len(jd_words & resume_words) / len(jd_words)) * 100)
        if jd_words else 0
    )

    # Per-category breakdown
    def category_match_pct(category_key: str) -> int:
        category_skills = set(SKILL_DICTIONARY.get(category_key, []))
        # normalize to canonical
        cat_canonical = {normalize_skill(s) for s in category_skills}
        jd_cat = jd_skills & cat_canonical
        if not jd_cat:
            return 100  # category not tested → full marks (no penalty for untested)
        resume_cat = resume_skills & cat_canonical
        matched_cat = jd_cat & resume_cat
        return round((len(matched_cat) / len(jd_cat)) * 100) if jd_cat else 100

    # Section scores (deterministic, not AI-guessed)
    # Experience: years match
    experience_section = min(10, max(1, round(experience_pct / 10)))
    # Skills: skill overlap
    skills_section = min(10, max(1, round(skill_match_pct / 10)))
    # Format: detected resume sections (heuristic)
    format_indicators = ["experience", "education", "skills", "projects",
                         "summary", "objective", "certifications", "achievements"]
    format_hits = sum(1 for fi in format_indicators if fi in resume_text.lower())
    format_section = min(10, max(3, format_hits + 2))
    # Projects: projects section detected + keyword overlap
    has_projects = "project" in resume_text.lower()
    projects_section = min(10, max(1, round(keyword_overlap_pct / 12) + (2 if has_projects else 0)))

    # Final weighted score:  60% skill match  +  20% experience  +  20% keyword overlap
    final_score = round(skill_match_pct * 0.60 + experience_pct * 0.20 + keyword_overlap_pct * 0.20)
    final_score = max(0, min(100, final_score))

    grade = ("S" if final_score >= 90 else
             "A" if final_score >= 80 else
             "B" if final_score >= 65 else
             "C" if final_score >= 50 else "D")

    # Skill match breakdown by category
    skill_match_breakdown = {
        "Technical Skills":   category_match_pct("languages"),
        "JD Keywords":        keyword_overlap_pct,
        "Frameworks & Tools": max(category_match_pct("frontend"),
                                  category_match_pct("backend"),
                                  category_match_pct("tools")),
        "Cloud & DevOps":     max(category_match_pct("cloud"),
                                  category_match_pct("devops")),
        "Domain Fit":         skill_match_pct,
    }

    return {
        "ats_score": final_score,
        "overall_grade": grade,
        "skill_match_pct": skill_match_pct,
        "keyword_overlap_pct": keyword_overlap_pct,
        "experience_pct": experience_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "bonus_skills": bonus_skills,
        "matched_keywords": matched_skills[:16],    # first 16 for display
        "missing_keywords": missing_skills[:10],    # top 10 to fix
        "skill_match": skill_match_breakdown,
        "section_scores": {
            "experience": experience_section,
            "skills": skills_section,
            "format": format_section,
            "projects": projects_section,
        },
        "resume_years": resume_years,
        "required_years": required_years,
        "total_jd_skills": len(jd_skills),
        "total_matched_skills": len(matched_skills),
        "bonus_skills_count": len(bonus_skills),
    }
