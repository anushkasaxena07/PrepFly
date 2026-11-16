/**
 * PREPFLY SCORING ENGINE (Section 5 & Section 6)
 * Pure deterministic mathematical functions for scoring and readiness.
 * 
 * Rules:
 * 1. The LLM writes content. Code computes numbers.
 * 2. One source of truth: all pages read identical values.
 * 3. No fake mastery: only graded evidence changes proficiency.
 * 4. Unassessed != gap: unassessed skills are never shown as weaknesses.
 */

export const RECENCY_HALF_LIFE_DAYS = 90.0;

export const DIFFICULTY_WEIGHTS = Object.freeze({
  EASY: 0.8,
  MEDIUM: 1.0,
  HARD: 1.3
});

export const TYPE_WEIGHTS = Object.freeze({
  MCQ: 0.7,
  SHORT_ANSWER: 1.0,
  SCENARIO: 1.1,
  CODE: 1.2,
  MOCK_INTERVIEW: 1.2,
  PRACTICE_ASSIGNMENT: 1.0
});

export const TIER_WEIGHTS = Object.freeze({
  MANDATORY: 1.5,
  PREFERRED: 1.0,
  SUPPORTING: 0.7
});

export const STATUS = Object.freeze({
  NOT_ASSESSED: "NOT_ASSESSED",
  LOW_EVIDENCE: "LOW_EVIDENCE",
  VERIFIED_GAP: "VERIFIED_GAP",
  DEVELOPING: "DEVELOPING",
  VERIFIED_STRONG: "VERIFIED_STRONG"
});

export const PILLAR_STATUS = Object.freeze({
  NOT_ASSESSED: "NOT_ASSESSED",
  PARTIALLY_ASSESSED: "PARTIALLY_ASSESSED",
  ASSESSED: "ASSESSED"
});

export const TREND_STATUS = Object.freeze({
  IMPROVING: "IMPROVING",
  FLAT: "FLAT",
  DECLINING: "DECLINING",
  NOT_ENOUGH_DATA: "Not enough data yet"
});

/**
 * 5.1 Evidence weighting
 * recencyWeight(e) = 0.5 ^ (ageInDays / 90)
 */
export function calculateRecencyWeight(ageInDays = 0) {
  const safeAge = Math.max(0, Number(ageInDays) || 0);
  return Math.pow(0.5, safeAge / RECENCY_HALF_LIFE_DAYS);
}

export function getDifficultyWeight(difficulty = "MEDIUM") {
  const key = String(difficulty || "MEDIUM").toUpperCase().trim();
  return DIFFICULTY_WEIGHTS[key] ?? 1.0;
}

export function getTypeWeight(evidenceType = "SHORT_ANSWER") {
  const key = String(evidenceType || "SHORT_ANSWER").toUpperCase().trim();
  return TYPE_WEIGHTS[key] ?? 1.0;
}

export function calculateEvidenceWeight(ageInDays = 0, difficulty = "MEDIUM", evidenceType = "SHORT_ANSWER") {
  return calculateRecencyWeight(ageInDays) * getDifficultyWeight(difficulty) * getTypeWeight(evidenceType);
}

/**
 * 5.2 Skill proficiency
 * P_skill = Σ(score_e × w_e) / Σ(w_e)  (only attempted evidence)
 * Returns { proficiency: number | null, sumWeights: number }
 */
export function calculateSkillProficiency(evidenceItems = []) {
  if (!Array.isArray(evidenceItems) || evidenceItems.length === 0) {
    return { proficiency: null, sumWeights: 0 };
  }

  let totalWeightedScore = 0;
  let totalWeights = 0;

  for (const item of evidenceItems) {
    if (!item || item.score === null || item.score === undefined || isNaN(Number(item.score))) {
      continue;
    }
    if (item.is_attempted === false || item.skipped === true) {
      continue;
    }

    const score = Number(item.score);
    const age = Number(item.age_in_days || 0);
    const diff = item.difficulty || "MEDIUM";
    const type = item.evidence_type || item.type || "SHORT_ANSWER";

    const w = calculateEvidenceWeight(age, diff, type);
    if (w > 0) {
      totalWeightedScore += (score * w);
      totalWeights += w;
    }
  }

  if (totalWeights <= 0) {
    return { proficiency: null, sumWeights: 0 };
  }

  return {
    proficiency: totalWeightedScore / totalWeights,
    sumWeights: totalWeights
  };
}

/**
 * 5.3 Skill confidence (how much we trust P_skill)
 * evidenceFactor  = min(1, Σ(w_e) / 3)
 * diversityFactor = min(1, distinctSubskillsTested / min(3, subskillCount))
 * C_skill = 0.7 × evidenceFactor + 0.3 × diversityFactor
 */
export function calculateSkillConfidence(sumWeights = 0, subskillsTested = 0, totalSubskillsCount = 3) {
  const evidenceFactor = Math.min(1.0, Math.max(0, Number(sumWeights) || 0) / 3.0);

  let distinctTested = 0;
  if (Array.isArray(subskillsTested) || subskillsTested instanceof Set) {
    distinctTested = new Set(subskillsTested).size;
  } else {
    distinctTested = Math.max(0, parseInt(subskillsTested, 10) || 0);
  }

  const denom = Math.min(3, Math.max(1, parseInt(totalSubskillsCount, 10) || 3));
  const diversityFactor = Math.min(1.0, distinctTested / denom);

  const cSkill = (0.7 * evidenceFactor) + (0.3 * diversityFactor);
  return Math.min(1.0, Math.max(0.0, cSkill));
}

/**
 * 5.4 Skill status
 */
export function classifySkillStatus(proficiency, confidence = 0) {
  if (proficiency === null || proficiency === undefined || isNaN(Number(proficiency))) {
    return STATUS.NOT_ASSESSED;
  }
  const conf = Number(confidence) || 0;
  if (conf < 0.4) {
    return STATUS.LOW_EVIDENCE;
  }

  const p = Number(proficiency);
  if (p < 60) {
    return STATUS.VERIFIED_GAP;
  } else if (p < 85) {
    return STATUS.DEVELOPING;
  } else {
    return STATUS.VERIFIED_STRONG;
  }
}

/**
 * 5.5 Pillar aggregation
 */
export function aggregatePillar(skills = [], pillarName = "Core Domain") {
  const totalCount = skills.length;
  const assessed = skills.filter(s => s && s.proficiency !== null && s.proficiency !== undefined);
  const assessedCount = assessed.length;
  const coverageRatio = totalCount > 0 ? assessedCount / totalCount : 0;

  if (assessedCount === 0) {
    return {
      name: pillarName,
      proficiency: null,
      assessed_count: 0,
      total_count: totalCount,
      coverage_display: `0/${totalCount}`,
      coverage_ratio: 0,
      status: PILLAR_STATUS.NOT_ASSESSED
    };
  }

  let tierWeightedSum = 0;
  let tierWeightSum = 0;

  for (const s of assessed) {
    const tKey = String(s.tier || "PREFERRED").toUpperCase().trim();
    const tw = TIER_WEIGHTS[tKey] ?? 1.0;
    tierWeightedSum += (Number(s.proficiency) * tw);
    tierWeightSum += tw;
  }

  const pillarProficiency = tierWeightSum > 0 ? tierWeightedSum / tierWeightSum : null;
  const status = coverageRatio >= 0.5 ? PILLAR_STATUS.ASSESSED : PILLAR_STATUS.PARTIALLY_ASSESSED;

  return {
    name: pillarName,
    proficiency: pillarProficiency !== null ? Number(pillarProficiency.toFixed(1)) : null,
    raw_proficiency: pillarProficiency,
    assessed_count: assessedCount,
    total_count: totalCount,
    coverage_display: `${assessedCount}/${totalCount}`,
    coverage_ratio: Number(coverageRatio.toFixed(4)),
    status
  };
}

/**
 * 5.6 Readiness (two explicit numbers, always both shown, never mixed)
 */
export function calculateReadiness(skills = []) {
  if (!Array.isArray(skills) || skills.length === 0) {
    return {
      verified_score: null,
      projected_readiness: null,
      weighted_coverage: 0,
      mandatory_coverage: 0,
      is_provisional: true,
      missing_mandatory_skills: [],
      skills_mastered_count: 0,
      skills_demonstrated_count: 0,
      assessed_skills_count: 0,
      total_skills_count: 0,
      formula_breakdown: "No evidence yet",
      readiness_label: "No evidence yet"
    };
  }

  let totalWeightAll = 0;
  let assessedWeightSum = 0;
  let assessedWeightedScore = 0;

  let mandatoryTotal = 0;
  let mandatoryAssessed = 0;
  const missingMandatoryNames = [];

  let assessedCount = 0;
  let masteredCount = 0;

  for (const s of skills) {
    const tKey = String(s.tier || "PREFERRED").toUpperCase().trim();
    const w = TIER_WEIGHTS[tKey] ?? 1.0;
    totalWeightAll += w;

    const isMandatory = (tKey === "MANDATORY");
    if (isMandatory) mandatoryTotal++;

    const prof = s.proficiency;
    const stat = s.status;

    if (prof !== null && prof !== undefined && !isNaN(Number(prof))) {
      assessedCount++;
      assessedWeightSum += w;
      assessedWeightedScore += (Number(prof) * w);
      if (isMandatory) mandatoryAssessed++;
      if (stat === STATUS.VERIFIED_STRONG) masteredCount++;
    } else {
      if (isMandatory) {
        missingMandatoryNames.push(s.name || s.skill_id || "Mandatory Skill");
      }
    }
  }

  const weightedCoverage = totalWeightAll > 0 ? assessedWeightSum / totalWeightAll : 0;
  const mandatoryCoverage = mandatoryTotal > 0 ? mandatoryAssessed / mandatoryTotal : 1.0;

  let verifiedScore = null;
  let projectedReadiness = null;

  if (assessedWeightSum > 0) {
    verifiedScore = assessedWeightedScore / assessedWeightSum;
    projectedReadiness = verifiedScore * (0.4 + 0.6 * weightedCoverage);
  }

  const isProvisional = (mandatoryCoverage < 1.0) || (weightedCoverage < 0.6);

  const formulaStr = (verifiedScore !== null && projectedReadiness !== null)
    ? `Projected Readiness = Verified Score (${verifiedScore.toFixed(1)}) × (0.4 + 0.6 × Weighted Coverage (${weightedCoverage.toFixed(2)})) = ${projectedReadiness.toFixed(1)}`
    : "No evidence yet";

  return {
    verified_score: verifiedScore !== null ? Number(verifiedScore.toFixed(1)) : null,
    raw_verified_score: verifiedScore,
    projected_readiness: projectedReadiness !== null ? Number(projectedReadiness.toFixed(1)) : null,
    raw_projected_readiness: projectedReadiness,
    weighted_coverage: Number(weightedCoverage.toFixed(4)),
    mandatory_coverage: Number(mandatoryCoverage.toFixed(4)),
    is_provisional: isProvisional,
    missing_mandatory_skills: missingMandatoryNames,
    skills_mastered_count: masteredCount,
    skills_demonstrated_count: assessedCount,
    assessed_skills_count: assessedCount,
    total_skills_count: skills.length,
    formula_breakdown: formulaStr,
    readiness_label: isProvisional ? "PROVISIONAL" : "ESTABLISHED"
  };
}

/**
 * 6. Gap Analysis
 */
export function analyzeSkillGaps(skills = []) {
  const verifiedGaps = [];
  const notAssessed = [];
  const lowEvidence = [];
  const developing = [];
  const verifiedStrong = [];

  for (const s of skills) {
    const stat = s.status;
    const p = s.proficiency;
    const name = s.name || s.skill_id || "Technical Skill";
    const tKey = String(s.tier || "PREFERRED").toUpperCase().trim();
    const w = TIER_WEIGHTS[tKey] ?? 1.0;
    const importance = Number(s.importance || 3.0);

    if (stat === STATUS.NOT_ASSESSED || p === null || p === undefined) {
      notAssessed.push({
        skill_id: s.skill_id,
        name,
        tier: tKey,
        pillar: s.pillar || "Core Technical",
        status: STATUS.NOT_ASSESSED,
        action_prompt: "Take quick assessment",
        is_weakness: false
      });
    } else if (stat === STATUS.LOW_EVIDENCE) {
      lowEvidence.push({
        skill_id: s.skill_id,
        name,
        tier: tKey,
        pillar: s.pillar || "Core Technical",
        proficiency: Number(Number(p).toFixed(1)),
        confidence: Number(Number(s.confidence || 0.2).toFixed(2)),
        status: STATUS.LOW_EVIDENCE,
        is_weakness: false,
        note: "Provisional score pending additional evidence"
      });
    } else if (stat === STATUS.VERIFIED_GAP) {
      const gapDepth = Math.max(0, 100 - Number(p));
      const priority = w * gapDepth * importance;
      const failedRubrics = s.failed_rubrics || s.failed_rubric_items || [];
      const remediation = failedRubrics.length > 0
        ? `Targeted practice on: ${failedRubrics.slice(0, 2).join("; ")}. Complete practice assignment and re-test with Ava.`
        : `Review foundational concepts in ${name}, complete 3 practice problems, then submit a targeted verification block.`;

      verifiedGaps.push({
        skill_id: s.skill_id,
        name,
        tier: tKey,
        pillar: s.pillar || "Core Technical",
        proficiency: Number(Number(p).toFixed(1)),
        confidence: Number(Number(s.confidence || 0.5).toFixed(2)),
        importance,
        priority: Number(priority.toFixed(2)),
        status: STATUS.VERIFIED_GAP,
        failed_rubric_items: failedRubrics,
        remediation_action: remediation,
        is_weakness: true
      });
    } else if (stat === STATUS.DEVELOPING) {
      developing.push({
        skill_id: s.skill_id,
        name,
        tier: tKey,
        proficiency: Number(Number(p).toFixed(1)),
        status: STATUS.DEVELOPING
      });
    } else if (stat === STATUS.VERIFIED_STRONG) {
      verifiedStrong.push({
        skill_id: s.skill_id,
        name,
        tier: tKey,
        proficiency: Number(Number(p).toFixed(1)),
        status: STATUS.VERIFIED_STRONG
      });
    }
  }

  verifiedGaps.sort((a, b) => b.priority - a.priority);

  return {
    verified_skill_gaps: verifiedGaps,
    not_yet_assessed: notAssessed,
    low_evidence_skills: lowEvidence,
    developing_skills: developing,
    verified_strong_skills: verifiedStrong,
    summary: {
      gap_count: verifiedGaps.length,
      unassessed_count: notAssessed.length,
      low_evidence_count: lowEvidence.length,
      strong_count: verifiedStrong.length
    }
  };
}
