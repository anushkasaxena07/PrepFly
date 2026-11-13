import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  safePlayMedia,
  attachStreamToMediaElement,
  validateOAuthPostMessage,
  isAllowedOAuthOrigin,
} from '../src/utils/mediaPlayback.js';
import {
  executeResumeUploadOrRetry,
  sanitizeUserFacingError,
  RESUME_STAGE_METADATA,
} from '../src/utils/resumeWorkflow.js';
import { resolveBackendUrl } from '../src/config/apiConfig.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(__dirname, '..');

test('resume workflow reports upload progress, parsing stage progress, and completes', async () => {
  const seenStages = [];
  let pollCalls = 0;

  const mockRequestFn = async (url, opts) => {
    if (url === '/api/resume/jobs' && opts.method === 'POST') {
      return {
        ok: true,
        status: 202,
        text: async () => JSON.stringify({ job_id: 'rjob_123', status: 'queued', stage: 'queued', progress: 15 }),
      };
    }
    if (url === '/api/resume/jobs/rjob_123' && opts.method === 'GET') {
      pollCalls += 1;
      const states = [
        { status: 'parsing', stage: 'parsing', progress: 60 },
        { status: 'validating', stage: 'validating', progress: 85 },
        { status: 'completed', stage: 'completed', progress: 100, session_id: 'sess_ok', ats_score: 92 },
      ];
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify(states[Math.min(pollCalls - 1, states.length - 1)]),
      };
    }
    throw new Error(`Unexpected URL ${url}`);
  };

  const result = await executeResumeUploadOrRetry({
    file: new Blob(['%PDF-1.4 sample'], { type: 'application/pdf' }),
    userId: 'user-uuid-1',
    consentGiven: true,
    requestFn: mockRequestFn,
    sleepFn: async () => {},
    onProgress: (p) => seenStages.push(p),
  });

  assert.equal(result.ok, true);
  assert.equal(result.sessionId, 'sess_ok');
  assert.equal(result.atsScore, 92);
  assert.ok(seenStages.some((s) => s.stage === 'uploading'));
  assert.ok(seenStages.some((s) => s.stage === 'parsing' && s.parsePct === 60));
  assert.ok(seenStages.some((s) => s.stage === 'completed' && s.parsePct === 100));
});

test('resume workflow retries existing failed job via /retry without re-uploading file', async () => {
  const calls = [];
  const requestFn = async (url, opts) => {
    calls.push(`${opts.method} ${url}`);
    if (url === '/api/resume/jobs/rjob_failed_1/retry' && opts.method === 'POST') {
      return {
        ok: true,
        status: 202,
        text: async () => JSON.stringify({ job_id: 'rjob_failed_1', status: 'queued', stage: 'queued' }),
      };
    }
    if (url === '/api/resume/jobs/rjob_failed_1' && opts.method === 'GET') {
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ status: 'completed', stage: 'completed', session_id: 'sess_retried', ats_score: 88 }),
      };
    }
    throw new Error(`Unexpected call: ${url}`);
  };

  const res = await executeResumeUploadOrRetry({
    file: null,
    existingJobId: 'rjob_failed_1',
    consentGiven: true,
    requestFn,
    sleepFn: async () => {},
  });

  assert.equal(res.ok, true);
  assert.equal(res.sessionId, 'sess_retried');
  assert.equal(calls[0], 'POST /api/resume/jobs/rjob_failed_1/retry');
  assert.ok(!calls.includes('POST /api/resume/jobs'));
});

test('resume workflow preserves retryability on failure and sanitizes internal error traces', async () => {
  const sanitized = sanitizeUserFacingError('Traceback (most recent call last): PGRST204 secret leak');
  assert.ok(!sanitized.includes('Traceback'));
  assert.ok(!sanitized.includes('PGRST204'));

  const requestFn = async (url, opts) => {
    if (opts.method === 'POST') {
      return {
        ok: true,
        status: 202,
        text: async () => JSON.stringify({ job_id: 'rjob_transient', status: 'queued' }),
      };
    }
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ status: 'retryable_failed', retryable: true, error: '504 Deadline Exceeded' }),
    };
  };

  const failRes = await executeResumeUploadOrRetry({
    file: new Blob(['%PDF'], { type: 'application/pdf' }),
    consentGiven: true,
    requestFn,
    sleepFn: async () => {},
  });

  assert.equal(failRes.ok, false);
  assert.equal(failRes.retryable, true);
  assert.equal(failRes.jobId, 'rjob_transient');
  assert.ok(RESUME_STAGE_METADATA.retryable_failed.label.toLowerCase().includes('retry'));
});

test('AvaTab preserves continue-without-resume and double-click submission guards', () => {
  const avaSrc = fs.readFileSync(path.join(FRONTEND_ROOT, 'src/components/AvaTab.jsx'), 'utf8');
  assert.ok(avaSrc.includes('Continue Without Resume'));
  assert.ok(avaSrc.includes('isStartingRef.current'));
  assert.ok(avaSrc.includes('disabled={!consentGiven || isProcessingResume}'));
});

test('COOP headers and OAuth postMessage origin validation protect popup flow', () => {
  const vercelJson = JSON.parse(fs.readFileSync(path.join(FRONTEND_ROOT, 'vercel.json'), 'utf8'));
  const hdrs = vercelJson.headers[0].headers;
  const coop = hdrs.find((h) => h.key === 'Cross-Origin-Opener-Policy');
  assert.equal(coop?.value, 'same-origin-allow-popups');

  assert.equal(isAllowedOAuthOrigin('https://accounts.google.com'), true);
  assert.equal(isAllowedOAuthOrigin('https://evil-phishing.example.com'), false);

  const okEvt = validateOAuthPostMessage({ origin: 'https://accounts.google.com', data: { token: 'abc' } });
  assert.equal(okEvt.valid, true);
  const badEvt = validateOAuthPostMessage({ origin: 'https://evil.example.com', data: { token: 'abc' } });
  assert.equal(badEvt.valid, false);
});

test('safePlayMedia swallows expected AbortError cleanly without suppressing hardware errors', async () => {
  const abortErr = Object.assign(new Error('The play() request was interrupted by a new load request.'), { name: 'AbortError' });
  const fakeAbortVideo = {
    isConnected: true,
    paused: true,
    ended: false,
    play: async () => {
      throw abortErr;
    },
  };
  let unexpectedErrorCalled = false;
  const playedAbort = await safePlayMedia(fakeAbortVideo, {
    onMediaError: () => {
      unexpectedErrorCalled = true;
    },
  });
  assert.equal(playedAbort, false);
  assert.equal(unexpectedErrorCalled, false);

  // Hardware / genuine media error IS surfaced cleanly to callback
  const hwErr = Object.assign(new Error('NotSupportedError'), { name: 'NotSupportedError' });
  const fakeBadVideo = {
    isConnected: true,
    paused: true,
    ended: false,
    play: async () => {
      throw hwErr;
    },
  };
  let caughtHw = null;
  await safePlayMedia(fakeBadVideo, {
    onMediaError: (err) => {
      caughtHw = err;
    },
  });
  assert.equal(caughtHw?.name, 'NotSupportedError');

  // attachStreamToMediaElement skips redundant play() when same stream is already playing
  const sharedStream = { getVideoTracks: () => [{ enabled: true }] };
  let playCalls = 0;
  const activeVideo = {
    isConnected: true,
    srcObject: sharedStream,
    paused: false,
    ended: false,
    play: async () => {
      playCalls += 1;
    },
  };
  await attachStreamToMediaElement(activeVideo, sharedStream, { muted: true });
  assert.equal(playCalls, 0);
});

test('resolveBackendUrl defaults cleanly to production Render URL when not localhost', () => {
  assert.equal(resolveBackendUrl(), 'https://prepfly-1.onrender.com');
});

