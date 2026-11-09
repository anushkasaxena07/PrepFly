/**
 * PrepFly Intelligence API Client
 * Centralized client for Candidate Profiling, Skill Taxonomy, Diagnostic Assessments,
 * Personalized Roadmaps, Spaced Revision, and Continuous Progress Analytics.
 */

const BACKEND_URL =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:5000"
    : (import.meta.env.VITE_BACKEND_URL || "http://localhost:5000");

const getAuthHeaders = () => {
  const token =
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    localStorage.getItem("admin_access_token") ||
    "";
  const userId = resolveUserId();

  return {
    "Content-Type": "application/json",
    "X-User-Id": userId,
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

const handleResponse = async (res) => {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const data = await res.json();
      errorMsg = data.error || data.message || errorMsg;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }
  return await res.json();
};

export const resolveUserId = (explicitId) => {
  if (explicitId && typeof explicitId === "string" && explicitId !== "undefined" && explicitId !== "null" && explicitId.trim() !== "") {
    return explicitId.trim();
  }
  try {
    const rawUser = localStorage.getItem("user");
    if (rawUser) {
      const u = JSON.parse(rawUser);
      const uid = u._id || u.user_id || u.id;
      if (uid && uid !== "undefined" && uid !== "null") return String(uid);
    }
  } catch {
    // ignore
  }
  const directId = localStorage.getItem("user_id");
  if (directId && directId !== "undefined" && directId !== "null" && directId.trim() !== "") return directId.trim();
  const email = localStorage.getItem("email") || localStorage.getItem("user_email");
  if (email && email !== "undefined" && email !== "null" && email.trim() !== "") return email.trim();
  return "user_default";
};

export const intelligenceAPI = {
  // 1. Preparation Profile & Goals
  async initializeProfile(profileData) {
    const res = await fetch(`${BACKEND_URL}/api/preparation/initialize`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(profileData)
    });
    return handleResponse(res);
  },

  async getProfile() {
    const res = await fetch(`${BACKEND_URL}/api/preparation/profile`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async patchProfile(patchData) {
    const res = await fetch(`${BACKEND_URL}/api/preparation/profile`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(patchData)
    });
    return handleResponse(res);
  },

  // 2. Skill Taxonomy & Evidence
  async getTaxonomy() {
    const res = await fetch(`${BACKEND_URL}/api/skills/taxonomy`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getSkillProfile() {
    const res = await fetch(`${BACKEND_URL}/api/skills/profile`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getSkillEvidence(skillId, limit = 20) {
    const res = await fetch(`${BACKEND_URL}/api/skills/${skillId}/evidence?limit=${limit}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // 3. Diagnostic Assessment
  async startDiagnosticAssessment(data = {}) {
    const res = await fetch(`${BACKEND_URL}/api/assessment/start`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  async getAssessment(assessmentId) {
    const res = await fetch(`${BACKEND_URL}/api/assessment/${assessmentId}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async submitAssessment(assessmentId, answers) {
    const res = await fetch(`${BACKEND_URL}/api/assessment/${assessmentId}/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ answers })
    });
    return handleResponse(res);
  },

  // 4. Personalized Roadmap & Adaptation
  async generateRoadmap(forceRegenerate = false) {
    const res = await fetch(`${BACKEND_URL}/api/roadmap/generate`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ force_regenerate: forceRegenerate })
    });
    return handleResponse(res);
  },

  async getCurrentRoadmap() {
    const res = await fetch(`${BACKEND_URL}/api/roadmap/current`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async recalculateRoadmap(rationale = "User requested roadmap recalculation") {
    const res = await fetch(`${BACKEND_URL}/api/roadmap/recalculate`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ rationale })
    });
    return handleResponse(res);
  },

  async patchActivity(activityId, data) {
    const res = await fetch(`${BACKEND_URL}/api/roadmap/activities/${activityId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  async completeActivity(activityId, attemptData = {}) {
    const res = await fetch(`${BACKEND_URL}/api/activities/${activityId}/complete`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(attemptData)
    });
    return handleResponse(res);
  },

  async skipActivity(activityId) {
    const res = await fetch(`${BACKEND_URL}/api/activities/${activityId}/skip`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // 5. Spaced Revision
  async getDueRevisions() {
    const res = await fetch(`${BACKEND_URL}/api/revision/due`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getRevisionSchedules() {
    const res = await fetch(`${BACKEND_URL}/api/revision/schedules`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getRetrievalDrill(skillId) {
    const res = await fetch(`${BACKEND_URL}/api/revision/drill/${skillId}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async submitRevisionDrill(drillData) {
    const res = await fetch(`${BACKEND_URL}/api/revision/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(drillData)
    });
    return handleResponse(res);
  },

  // 6. Progress Analytics & Insights
  async getProgressDashboard() {
    const res = await fetch(`${BACKEND_URL}/api/progress/dashboard`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getCoachingInsights() {
    const res = await fetch(`${BACKEND_URL}/api/progress/insights`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getCrossFeatureWeaknesses() {
    const res = await fetch(`${BACKEND_URL}/api/progress/weaknesses`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // 7. Event Pipeline
  async emitEvent(eventType, sourceModule = "CLIENT_APP", sourceRecordId = null, payload = {}) {
    const userId = resolveUserId();
    const res = await fetch(`${BACKEND_URL}/api/intelligence/events`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        user_id: userId,
        event_type: eventType,
        source_module: sourceModule,
        source_record_id: sourceRecordId,
        payload
      })
    });
    return handleResponse(res);
  },

  // 8. Improvement Tracking & Snapshots
  async getImprovementAnalytics(userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/improvement/analytics?user_id=${uid}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async createSnapshot(userId, snapshotType = "periodic") {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/improvement/snapshot`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: uid, snapshot_type: snapshotType })
    });
    return handleResponse(res);
  },

  // 9. Recommendation vs Schedule Roadmap
  async getRoadmapRecommendations(userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/roadmap/recommendations?user_id=${uid}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getRoadmapSchedule(userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/roadmap/schedule?user_id=${uid}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async recalculateRoadmapAdaptive(userId, changeReason = "Candidate requested recalculation") {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/roadmap/recalculate`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: uid, change_reason: changeReason })
    });
    return handleResponse(res);
  },

  // 10. Job-Specific Preparation
  async ingestJobDescription(jobData) {
    const uid = resolveUserId(jobData.user_id);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/jobs/ingest`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ ...jobData, user_id: uid })
    });
    return handleResponse(res);
  },

  async getJobGaps(jobId, userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/jobs/${jobId}/gaps?user_id=${uid}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getJobQuestions(jobId) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/jobs/${jobId}/questions`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async startJobMatchedInterview(jobId, options = {}) {
    const uid = resolveUserId(options.user_id);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/jobs/${jobId}/start-interview`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        user_id: uid,
        personality: options.personality || "professional"
      })
    });
    return handleResponse(res);
  },

  // 11. Achievements & Milestones
  async getAchievements(userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/achievements?user_id=${uid}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async claimAchievement(achievementId, userId) {
    const uid = resolveUserId(userId);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/achievements/${achievementId}/claim`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: uid })
    });
    return handleResponse(res);
  },

  // 12. Intelligent Company-Specific Preparation Engine
  async getCompanyIntelligence(company, role = "Software Engineer", level = "Fresher") {
    const res = await fetch(
      `${BACKEND_URL}/api/intelligence/company/${encodeURIComponent(company)}?role=${encodeURIComponent(role)}&experience_level=${encodeURIComponent(level)}`,
      {
        method: "GET",
        headers: getAuthHeaders()
      }
    );
    return handleResponse(res);
  },

  async getCandidateReadiness(role = "Software Engineer") {
    const res = await fetch(
      `${BACKEND_URL}/api/intelligence/candidate/readiness?role=${encodeURIComponent(role)}`,
      {
        method: "GET",
        headers: getAuthHeaders()
      }
    );
    return handleResponse(res);
  },

  async getCompanyGapAnalysis(payload) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/company/gap-analysis`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(res);
  },

  async generateCompanyPlan(payload) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/company/plan`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(res);
  },

  async getCompanyPlan() {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/company/plan`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // 13. Job-Specific Readiness Assessment & Gap Engine
  async createJobReadinessAssessment(payload) {
    const uid = resolveUserId(payload.user_id);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ ...payload, user_id: uid })
    });
    return handleResponse(res);
  },

  async getJobReadinessReport(sessionId) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments/${sessionId}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getJobAssessmentBlueprint(sessionId) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments/${sessionId}/blueprint`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async submitJobAssessmentAttempt(sessionId, payload) {
    const uid = resolveUserId(payload.user_id);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments/${sessionId}/attempts`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ ...payload, user_id: uid })
    });
    return handleResponse(res);
  },

  async getJobRecommendations(sessionId) {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments/${sessionId}/recommendations`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async transferJobReadinessToPrep(sessionId, payload = {}) {
    const uid = resolveUserId(payload.user_id);
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/assessments/${sessionId}/transfer-to-prep`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ ...payload, user_id: uid })
    });
    return handleResponse(res);
  },

  async listJobAssessmentSessions() {
    const res = await fetch(`${BACKEND_URL}/api/intelligence/job-prep/sessions`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // ─── AI MENTOR & 7-STEP LEARNING WORKSPACE ─────────────────────────────
  async startMentorConversation(title) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/conversations`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ title })
    });
    return handleResponse(res);
  },

  async getMentorMessages(conversationId) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/conversations/${conversationId}/messages`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async sendMentorMessage(conversationId, message, activeActivity = null) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        message,
        active_activity: activeActivity
      })
    });
    return handleResponse(res);
  },

  async getLearningWorkspace(activityId, { skillId, targetRole, targetCompany } = {}) {
    const params = new URLSearchParams();
    if (skillId) params.append("skill_id", skillId);
    if (targetRole) params.append("target_role", targetRole);
    if (targetCompany) params.append("target_company", targetCompany);
    const qs = params.toString() ? `?${params.toString()}` : "";

    const res = await fetch(`${BACKEND_URL}/api/mentor/workspace/${activityId}${qs}`, {
      method: "GET",
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async submitAssignment(activityId, { submissionText, codeSubmission }) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/workspace/${activityId}/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        submission_text: submissionText,
        code_submission: codeSubmission
      })
    });
    return handleResponse(res);
  },

  async parseJobDescription(jobDescription, { targetRole, targetCompany } = {}) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/parse-jd`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        job_description: jobDescription,
        target_role: targetRole,
        target_company: targetCompany
      })
    });
    return handleResponse(res);
  },

  async completeOnboarding(onboardingData) {
    const res = await fetch(`${BACKEND_URL}/api/mentor/onboarding/complete`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(onboardingData)
    });
    return handleResponse(res);
  }
};

