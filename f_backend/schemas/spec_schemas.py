"""
PrepFly Master Specification Schemas
Validates all inputs, LLM outputs, and re-planning structures strictly against Section 3, 4, 8, 10, 12.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, conint, confloat, field_validator


# ── Section 3: Skill Requirement Profile ───────────────────────────────────

class RubricCriterionSchema(BaseModel):
    id: str
    criterion: str
    points: int = Field(default=25, ge=0, le=100)

class SubskillSchema(BaseModel):
    id: str
    name: str
    rubricCriteria: List[RubricCriterionSchema] = Field(min_length=2, max_length=5)

class SkillSchema(BaseModel):
    id: str
    name: str
    pillarId: str
    tier: Literal["MANDATORY", "PREFERRED", "SUPPORTING"]
    interviewImportance: conint(ge=1, le=5)
    source: Literal["USER_PROVIDED", "WEB_SOURCED", "MODEL_INFERRED"]
    sourceUrl: Optional[str] = None
    subskills: List[SubskillSchema] = Field(min_length=1, max_length=6)

class PillarSchema(BaseModel):
    id: str
    name: str
    order: int
    skills: List[SkillSchema] = Field(default_factory=list)

class RoleProfileLLMOutputSchema(BaseModel):
    roleTitle: str
    company: str
    level: Literal["JUNIOR", "MID", "SENIOR", "STAFF"]
    pillars: List[PillarSchema] = Field(min_length=3, max_length=7)
    skills: List[SkillSchema] = Field(min_length=6, max_length=20)


# ── Section 4 & 12.2: Diagnostic Questions ──────────────────────────────────

class QuestionRubricItemSchema(BaseModel):
    id: str
    criterion: str
    points: int = Field(default=25, ge=1, le=100)

class QuestionLLMOutputSchema(BaseModel):
    prompt: str
    rubric: List[QuestionRubricItemSchema] = Field(min_length=2, max_length=5)
    modelAnswer: str
    timeLimitSec: int = Field(default=180, ge=30, le=900)
    options: Optional[List[str]] = None
    correctOptions: Optional[List[int]] = None
    testCases: Optional[List[Dict[str, Any]]] = None

    @field_validator("rubric")
    @classmethod
    def validate_rubric_sum(cls, v: List[QuestionRubricItemSchema]) -> List[QuestionRubricItemSchema]:
        total = sum(item.points for item in v)
        if total != 100:
            # Normalize to 100
            factor = 100.0 / total if total > 0 else 1.0
            for item in v:
                item.points = max(1, int(round(item.points * factor)))
            # Adjust remainder to first item
            rem = 100 - sum(item.points for item in v)
            v[0].points += rem
        return v


# ── Section 12.3: Grader Output ─────────────────────────────────────────────

class GraderItemResultSchema(BaseModel):
    rubricId: str
    result: Literal["PASS", "PARTIAL", "FAIL"]
    pointsAwarded: int = Field(ge=0, le=100)
    evidence: str = Field(default="none")

class GraderLLMOutputSchema(BaseModel):
    items: List[GraderItemResultSchema] = Field(min_length=1)
    feedbackSummary: Optional[str] = None


# ── Section 8.5 & 12.4: Day Block Content ───────────────────────────────────

class DayBlockContentSchema(BaseModel):
    keyPoints: List[str] = Field(min_length=2, max_length=6)
    commonInterviewQuestions: List[str] = Field(min_length=1, max_length=5)
    practiceTask: str
    successCriteria: str
    resources: List[str] = Field(default_factory=list)


# ── Section 8.1 & 8.7: Feasibility & Re-plan Requests ───────────────────────

class FeasibilityRequestSchema(BaseModel):
    startDate: str
    interviewDate: str
    dailyMinutes: int = Field(default=90, ge=15, le=480)
    availabilityGrid: Optional[Dict[str, int]] = None
    blackoutDates: Optional[List[str]] = None

class ReplanRequestSchema(BaseModel):
    trigger: Literal[
        "INITIAL",
        "DAILY_MINUTES_CHANGED",
        "MISSED_DAY",
        "DEADLINE_CHANGED",
        "ASSESSMENT_COMPLETED",
        "MANUAL_REBALANCE",
        "SKILL_PROFILE_EDITED"
    ]
    params: Dict[str, Any] = Field(default_factory=dict)
