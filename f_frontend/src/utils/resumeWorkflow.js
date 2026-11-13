/**
 * Resume upload, async job stage tracking, retry-without-reupload, and error sanitization helpers.
 */

export const RESUME_STAGE_METADATA = {
  uploading: { label: "Uploading resume file", uploadPct: 100, parsePct: 10 },
  queued: { label: "Upload complete — queued for processing", uploadPct: 100, parsePct: 20 },
  extracting: { label: "Extracting text from resume", uploadPct: 100, parsePct: 35 },
  parsing: { label: "AI analyzing skills & projects", uploadPct: 100, parsePct: 60 },
  validating: { label: "Validating structured resume data", uploadPct: 100, parsePct: 80 },
  persisting: { label: "Saving session & parsed profile", uploadPct: 100, parsePct: 92 },
  completed: { label: "Resume ready — starting interview", uploadPct: 100, parsePct: 100 },
  retryable_failed: { label: "AI parsing paused — retry without re-uploading", uploadPct: 100, parsePct: 100 },
  permanently_failed: { label: "Resume file could not be read", uploadPct: 100, parsePct: 100 },
  failed: { label: "Resume processing interrupted", uploadPct: 100, parsePct: 100 },
};

export function sanitizeUserFacingError(rawMsg, fallback = "Resume processing was interrupted. Please retry or continue without a resume.") {
  if (!rawMsg || typeof rawMsg !== "string") return fallback;
  const trimmed = rawMsg.trim();
  const lower = trimmed.toLowerCase();
  // Never expose raw stack traces, SQL errors, keys, or internal tokens to users
  if (
    lower.includes("traceback") ||
    lower.includes("pgrst") ||
    lower.includes("sql") ||
    lower.includes("aiza") ||
    lower.includes("secret") ||
    lower.includes("exception:")
  ) {
    return fallback;
  }
  return trimmed.slice(0, 220);
}

export function isTerminalFailureStatus(status) {
  return status === "retryable_failed" || status === "permanently_failed" || status === "failed";
}

export function isStageActive(status) {
  return ["uploading", "queued", "extracting", "parsing", "validating", "persisting", "processing"].includes(status);
}

/**
 * Coordinates resume upload / existing-job retry, stage progress callbacks, and polling
 * while preventing duplicate concurrent submissions.
 */
export async function executeResumeUploadOrRetry({
  file,
  existingJobId = null,
  existingJobToken = null,
  userId = null,
  consentGiven = true,
  requestFn,
  sleepFn = (ms) => new Promise((r) => setTimeout(r, ms)),
  onProgress = () => { },
  maxPolls = 50,
  pollIntervalMs = 1000,
}) {
  if (!consentGiven) {
    return {
      ok: false,
      retryable: false,
      step: "consent",
      error: "Affirmative privacy consent is required before starting your AI interview.",
    };
  }

  if (!file && !existingJobId) {
    return {
      ok: false,
      retryable: false,
      step: "validation",
      error: "Please select a PDF or DOCX resume file first.",
    };
  }

  const parseJsonSafe = async (res) => {
    const txt = await res.text();
    try {
      return txt ? JSON.parse(txt) : {};
    } catch {
      return {
        message: `Server returned unexpected status ${res.status}. Please retry or continue without a resume.`,
      };
    }
  };

  let res = null;
  let data = null;
  let activeJobToken = existingJobToken || null;
  const tokenHeaders = () => (activeJobToken ? { "X-Job-Token": activeJobToken } : {});

  if (existingJobId) {
    onProgress({ stage: "queued", ...RESUME_STAGE_METADATA.queued, jobId: existingJobId });
    const retryHeaders = {
      ...tokenHeaders(),
      "Idempotency-Key": `retry_${existingJobId}_${Date.now()}`,
    };
    res = await requestFn(`/api/resume/jobs/${existingJobId}/retry`, { method: "POST", headers: retryHeaders });
    data = await parseJsonSafe(res);
    // If job expired (410) or endpoint missing (404), fall back to fresh upload when file is preserved
    if ((res.status === 410 || res.status === 404) && file) {
      existingJobId = null;
    }
  }

  if (!existingJobId) {
    onProgress({ stage: "uploading", label: "Uploading resume file...", uploadPct: 40, parsePct: 0, jobId: null });
    const formData = new FormData();
    formData.append("resume", file);
    formData.append("consent", "true");
    if (userId) formData.append("user_id", userId);

    res = await requestFn("/api/resume/jobs", { method: "POST", body: formData });
    data = await parseJsonSafe(res);
    if (data && data.job_token) {
      activeJobToken = data.job_token;
    }
    if (res.status === 404) {
      res = await requestFn("/upload", { method: "POST", body: formData });
      data = await parseJsonSafe(res);
    }
  }

  if (!res.ok) {
    return {
      ok: false,
      jobId: data.job_id || existingJobId || null,
      jobToken: activeJobToken,
      retryable: data.retryable !== false,
      step: data.step || "resume_parse",
      error: sanitizeUserFacingError(data.message || data.error),
    };
  }

  if (res.status === 202 && data.job_id) {
    const jobId = data.job_id;
    const initStage = data.stage || data.status || "queued";
    const meta = RESUME_STAGE_METADATA[initStage] || RESUME_STAGE_METADATA.queued;
    onProgress({ stage: initStage, label: meta.label, uploadPct: 100, parsePct: meta.parsePct, jobId, jobToken: activeJobToken });

    for (let poll = 0; poll < maxPolls; poll++) {
      await sleepFn(pollIntervalMs);
      const pollRes = await requestFn(`/api/resume/jobs/${jobId}`, { method: "GET", headers: tokenHeaders() });
      const pollData = await parseJsonSafe(pollRes);

      if (!pollRes.ok) {
        return {
          ok: false,
          jobId,
          jobToken: activeJobToken,
          retryable: true,
          step: "resume_parse",
          error: sanitizeUserFacingError(pollData.error || pollData.message),
        };
      }

      const st = pollData.stage || pollData.status || "parsing";
      const stMeta = RESUME_STAGE_METADATA[st] || RESUME_STAGE_METADATA.parsing;
      onProgress({
        stage: st,
        label: stMeta.label,
        uploadPct: 100,
        parsePct: typeof pollData.progress === "number" ? pollData.progress : stMeta.parsePct,
        jobId,
        jobToken: activeJobToken,
      });

      if (pollData.status === "completed") {
        return {
          ok: true,
          jobId,
          jobToken: activeJobToken,
          sessionId: pollData.session_id,
          atsScore: pollData.ats_score,
          data: pollData,
        };
      }

      if (isTerminalFailureStatus(pollData.status)) {
        return {
          ok: false,
          jobId,
          jobToken: activeJobToken,
          retryable: pollData.retryable !== false && pollData.status !== "permanently_failed",
          step: "resume_parse",
          error: sanitizeUserFacingError(pollData.error || pollData.message),
        };
      }
    }

    return {
      ok: false,
      jobId,
      jobToken: activeJobToken,
      retryable: true,
      step: "resume_parse",
      error: "Resume parsing is taking longer than expected. Click Retry to continue without re-uploading.",
    };
  }

  return {
    ok: true,
    jobId: data.job_id || null,
    jobToken: activeJobToken,
    sessionId: data.session_id,
    atsScore: data.ats_score,
    data,
  };
}

