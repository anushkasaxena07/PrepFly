/**
 * atsEngine.js — Frontend port of the deterministic ATS scoring engine.
 * Used for:
 *  1. Offline / demo mode in ResumeTab (logged-out users)
 *  2. Instant preview before the API call returns
 *
 * Mirrors the logic in f_backend/services/ats_engine.py
 */

// ── Skill dictionary ──────────────────────────────────────────────────────────
const SKILL_DICTIONARY = {
  languages:    ['python', 'javascript', 'java', 'c++', 'c#', 'typescript',
                 'go', 'golang', 'rust', 'php', 'ruby', 'swift', 'kotlin',
                 'scala', 'r', 'matlab', 'perl', 'bash', 'shell', 'sql'],
  frontend:     ['react', 'vue', 'angular', 'next.js', 'nuxt', 'svelte',
                 'redux', 'mobx', 'html', 'css', 'sass', 'tailwind',
                 'bootstrap', 'webpack', 'vite', 'gatsby', 'storybook',
                 'figma', 'd3.js', 'rxjs', 'pwa', 'accessibility', 'a11y',
                 'responsive design', 'graphql client'],
  backend:      ['node.js', 'express', 'fastapi', 'django', 'flask',
                 'spring boot', 'spring', 'laravel', 'rails', 'gin', 'nestjs',
                 'graphql', 'rest api', 'rest', 'grpc', 'microservices',
                 'celery', 'kafka', 'rabbitmq', 'websocket', 'oauth', 'jwt'],
  databases:    ['postgresql', 'mysql', 'mongodb', 'redis', 'dynamodb',
                 'sqlite', 'cassandra', 'elasticsearch', 'neo4j', 'supabase',
                 'firebase', 'mariadb', 'pinecone', 'weaviate', 'qdrant'],
  cloud:        ['aws', 'azure', 'gcp', 'google cloud', 'ec2', 's3', 'rds',
                 'lambda', 'ecs', 'eks', 'cloudfront', 'iam', 'vpc',
                 'azure devops', 'gke', 'cloud run', 'bigquery'],
  devops:       ['docker', 'kubernetes', 'k8s', 'terraform', 'ansible',
                 'jenkins', 'github actions', 'gitlab ci', 'ci/cd', 'helm',
                 'argocd', 'prometheus', 'grafana', 'datadog', 'nginx', 'linux'],
  ml_ai:        ['machine learning', 'deep learning', 'tensorflow', 'pytorch',
                 'keras', 'scikit-learn', 'sklearn', 'numpy', 'pandas',
                 'nlp', 'llm', 'fine-tuning', 'rag', 'langchain',
                 'hugging face', 'transformers', 'openai', 'computer vision',
                 'opencv', 'xgboost', 'lightgbm', 'mlflow', 'mlops',
                 'feature engineering', 'neural network'],
  tools:        ['git', 'github', 'gitlab', 'jira', 'confluence', 'postman',
                 'swagger', 'vim', 'vscode', 'intellij', 'datadog', 'sentry'],
  soft:         ['agile', 'scrum', 'kanban', 'leadership', 'communication',
                 'project management', 'team management', 'mentoring',
                 'code review', 'system design', 'problem solving', 'architecture'],
  data:         ['data engineering', 'spark', 'hadoop', 'airflow', 'dbt',
                 'etl', 'data pipeline', 'data warehouse', 'snowflake',
                 'tableau', 'power bi', 'looker', 'databricks'],
  mobile:       ['react native', 'flutter', 'android', 'ios', 'expo'],
  testing:      ['unit testing', 'integration testing', 'jest', 'pytest',
                 'cypress', 'selenium', 'playwright', 'tdd', 'bdd', 'qa'],
};

const ALL_SKILLS = [...new Set(Object.values(SKILL_DICTIONARY).flat())];

// ── Alias map ─────────────────────────────────────────────────────────────────
const ALIASES = {
  'node.js':          ['nodejs', 'node js', 'node'],
  'next.js':          ['nextjs', 'next js'],
  'postgresql':       ['postgres', 'pg'],
  'javascript':       ['js', 'vanillajs', 'es6'],
  'typescript':       ['ts'],
  'kubernetes':       ['k8s'],
  'python':           ['py'],
  'graphql':          ['gql'],
  'react':            ['reactjs', 'react.js', 'react js'],
  'vue':              ['vuejs', 'vue.js'],
  'angular':          ['angularjs'],
  'scikit-learn':     ['sklearn'],
  'go':               ['golang'],
  'c++':              ['cpp'],
  'c#':               ['csharp', '.net', 'dotnet'],
  'rest api':         ['restful', 'rest apis', 'api development'],
  'ci/cd':            ['continuous integration', 'continuous delivery', 'github actions', 'gitlab ci'],
  'machine learning': ['ml'],
  'deep learning':    ['dl'],
  'nlp':              ['natural language processing'],
};

// Build reverse alias map once
const REVERSE_ALIASES = {};
for (const [canonical, aliases] of Object.entries(ALIASES)) {
  for (const alias of aliases) {
    REVERSE_ALIASES[alias.toLowerCase()] = canonical.toLowerCase();
  }
}

function normalizeSkill(raw) {
  const low = raw.toLowerCase().trim();
  return REVERSE_ALIASES[low] ?? low;
}

/**
 * Extract known skills from text using word-boundary regex matching.
 * @param {string} text
 * @returns {string[]} array of canonical skill names
 */
export function extractSkills(text) {
  const lower = text.toLowerCase();
  const found = new Set();

  for (const skill of ALL_SKILLS) {
    const escaped = skill.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`, 'i');
    if (pattern.test(lower)) {
      found.add(normalizeSkill(skill));
    }
  }

  // Second pass: aliases
  for (const [alias, canonical] of Object.entries(REVERSE_ALIASES)) {
    const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`, 'i');
    if (pattern.test(lower)) {
      found.add(canonical);
    }
  }

  return [...found].sort();
}

/**
 * Extract max years of experience mentioned in text.
 * @param {string} text
 * @returns {number|null}
 */
export function extractYearsExperience(text) {
  const patterns = [
    /(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)/gi,
    /(?:experience|exp)\s*(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)/gi,
    /(\d+)\s*\+?\s*(?:years?|yrs?)/gi,
  ];
  const found = [];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const n = parseInt(match[1], 10);
      if (!isNaN(n) && n <= 50) found.push(n);
    }
  }
  return found.length ? Math.max(...found) : null;
}

const STOP_WORDS = new Set([
  'and','the','for','with','have','your','from','that','this','will','are',
  'our','you','they','all','any','can','has','not','job','role','team',
  'work','must','should','also','years','year','experience','strong','good',
  'ability','well','using','use','looking','ideal','including','based','new',
  'etc','within','across','help','build','building','make','about','into',
]);

/**
 * Core ATS match calculator — deterministic, no AI.
 * @param {string} resumeText
 * @param {string} jobDescription
 * @returns {object} full scoring result
 */
export function calculateATSMatch(resumeText, jobDescription) {
  const resumeSkills = new Set(extractSkills(resumeText));
  const jdSkills     = new Set(extractSkills(jobDescription));

  const matchedSkills = [...jdSkills].filter(s => resumeSkills.has(s)).sort();
  const missingSkills = [...jdSkills].filter(s => !resumeSkills.has(s)).sort();
  const bonusSkills   = [...resumeSkills].filter(s => !jdSkills.has(s)).sort();

  const skillMatchPct = jdSkills.size > 0
    ? Math.round((matchedSkills.length / jdSkills.size) * 100)
    : 0;

  // Keyword overlap (all meaningful words, not just skills)
  const tokenize = (text) => new Set(
    text.toLowerCase()
        .match(/\b[a-zA-Z][a-zA-Z0-9#+./\-]{2,}\b/g)
        ?.filter(w => !STOP_WORDS.has(w)) ?? []
  );
  const jdWords     = tokenize(jobDescription);
  const resumeWords = tokenize(resumeText);
  const overlap     = [...jdWords].filter(w => resumeWords.has(w));
  const keywordOverlapPct = jdWords.size > 0
    ? Math.round((overlap.length / jdWords.size) * 100)
    : 0;

  // Experience
  const resumeYears   = extractYearsExperience(resumeText);
  const requiredYears = extractYearsExperience(jobDescription);
  let experiencePct = 100;
  if (requiredYears) {
    if (resumeYears == null) {
      experiencePct = 70;
    } else if (resumeYears >= requiredYears) {
      experiencePct = 100;
    } else {
      experiencePct = Math.min(99, Math.round((resumeYears / requiredYears) * 100));
    }
  }

  // Section scores (heuristic)
  const resumeLower = resumeText.toLowerCase();
  const formatHits  = ['experience','education','skills','projects','summary',
                       'objective','certifications','achievements']
                      .filter(f => resumeLower.includes(f)).length;

  const sectionScores = {
    experience: Math.min(10, Math.max(1, Math.round(experiencePct / 10))),
    skills:     Math.min(10, Math.max(1, Math.round(skillMatchPct / 10))),
    format:     Math.min(10, Math.max(3, formatHits + 2)),
    projects:   Math.min(10, Math.max(1,
                  Math.round(keywordOverlapPct / 12) + (resumeLower.includes('project') ? 2 : 0)
                )),
  };

  // Final weighted score: 60% skills + 20% experience + 20% keyword
  const finalScore = Math.max(0, Math.min(100,
    Math.round(skillMatchPct * 0.60 + experiencePct * 0.20 + keywordOverlapPct * 0.20)
  ));

  const grade = finalScore >= 90 ? 'S'
              : finalScore >= 80 ? 'A'
              : finalScore >= 65 ? 'B'
              : finalScore >= 50 ? 'C' : 'D';

  return {
    ats_score:        finalScore,
    overall_grade:    grade,
    matched_keywords: matchedSkills.slice(0, 16),
    missing_keywords: missingSkills.slice(0, 10),
    bonus_skills:     bonusSkills.slice(0, 8),
    skill_match: {
      'Technical Skills':   skillMatchPct,
      'JD Keywords':        keywordOverlapPct,
      'Frameworks & Tools': Math.round((skillMatchPct + keywordOverlapPct) / 2),
      'Cloud & DevOps':     skillMatchPct,
      'Domain Fit':         Math.round((skillMatchPct * 0.7 + experiencePct * 0.3)),
    },
    section_scores: sectionScores,
    improvement_tips: buildTips(missingSkills, bonusSkills, finalScore, experiencePct, requiredYears, resumeYears),
    ai_summary: `Resume scores ${finalScore}/100 against this job description. ` +
                (missingSkills.length
                  ? `Key gaps: ${missingSkills.slice(0, 3).join(', ')}.`
                  : 'Skills are well aligned with the role.'),
    meta: {
      skill_match_pct:      skillMatchPct,
      keyword_overlap_pct:  keywordOverlapPct,
      experience_pct:       experiencePct,
      resume_years:         resumeYears,
      required_years:       requiredYears,
      total_jd_skills:      jdSkills.size,
      total_matched_skills: matchedSkills.length,
      engine: 'deterministic_frontend_v1',
    },
  };
}

function buildTips(missing, bonus, score, expPct, reqYears, resumeYears) {
  const tips = [];

  if (missing.length > 0) {
    tips.push(`Add ${missing.slice(0, 3).join(', ')} to your Skills section — these are explicitly required in the JD.`);
  } else {
    tips.push('Your core skills are well-matched. Focus on tailoring your bullet points to the JD language.');
  }

  if (expPct < 100 && reqYears) {
    tips.push(`Experience gap: role requires ${reqYears} yrs${resumeYears ? `, resume shows ${resumeYears}` : ' (none stated)'}. Emphasise depth and scope of past work to compensate.`);
  } else {
    tips.push("Quantify achievements: '40% latency reduction' beats 'improved performance'.");
  }

  if (bonus.length > 0) {
    tips.push(`Highlight ${bonus.slice(0, 2).join(' and ')} more prominently — these are differentiators not required by the JD.`);
  } else {
    tips.push("Mirror the JD's exact phrasing in your summary and experience bullets to pass automated screening.");
  }

  tips.push(score < 60
    ? 'ATS score is low — consider a targeted rewrite of your skills section to match this specific role.'
    : 'Strong keyword match. Ensure your resume format is ATS-friendly: avoid tables, columns, and images.');

  return tips;
}
