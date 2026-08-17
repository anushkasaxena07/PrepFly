/**
 * Offline Draft Protection for PrepFly Student Interviews & Coding Sessions:
 * - Saves unsent interview answers and code edits locally if network drops during a session.
 * - Restores unsent work automatically when connectivity is re-established.
 */

const INTERVIEW_DRAFT_PREFIX = 'prepfly_interview_draft_';
const CODING_DRAFT_PREFIX = 'prepfly_coding_draft_';

export function saveInterviewDraft(sessionId, answerText) {
  if (!sessionId || !answerText) return;
  try {
    localStorage.setItem(`${INTERVIEW_DRAFT_PREFIX}${sessionId}`, JSON.stringify({
      answer: answerText,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.warn('Could not save interview draft locally:', e);
  }
}

export function getInterviewDraft(sessionId) {
  if (!sessionId) return null;
  try {
    const raw = localStorage.getItem(`${INTERVIEW_DRAFT_PREFIX}${sessionId}`);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function clearInterviewDraft(sessionId) {
  if (!sessionId) return;
  try {
    localStorage.removeItem(`${INTERVIEW_DRAFT_PREFIX}${sessionId}`);
  } catch (e) {
    console.warn('Could not clear interview draft:', e);
  }
}

export function saveCodingDraft(problemId, code, language) {
  if (!problemId) return;
  try {
    localStorage.setItem(`${CODING_DRAFT_PREFIX}${problemId}`, JSON.stringify({
      code,
      language,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.warn('Could not save coding draft locally:', e);
  }
}

export function getCodingDraft(problemId) {
  if (!problemId) return null;
  try {
    const raw = localStorage.getItem(`${CODING_DRAFT_PREFIX}${problemId}`);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}
