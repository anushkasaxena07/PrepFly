/**
 * Shared media element playback & OAuth popup messaging helpers.
 * Handles transient browser AbortError cleanly without suppressing genuine media errors,
 * and avoids redundant load/play storms during React re-renders.
 */

export async function safePlayMedia(mediaEl, options = {}) {
  const {
    muteOnAutoplayBlock = false,
    onAutoplayBlocked = null,
    onMediaError = null,
  } = options;

  if (!mediaEl || mediaEl.isConnected === false || typeof mediaEl.play !== "function") {
    return false;
  }

  // Avoid issuing overlapping play() calls when the element is already playing.
  if (mediaEl.paused === false && mediaEl.ended === false) {
    return true;
  }

  try {
    await mediaEl.play();
    return true;
  } catch (err) {
    if (err && err.name === "AbortError") {
      // Expected when srcObject changes or component unmounts mid-play().
      return false;
    }
    if (err && err.name === "NotAllowedError") {
      if (typeof onAutoplayBlocked === "function") {
        onAutoplayBlocked(err);
      }
      if (muteOnAutoplayBlock) {
        try {
          mediaEl.muted = true;
          await mediaEl.play();
          return true;
        } catch (retryErr) {
          if (retryErr && retryErr.name === "AbortError") return false;
          if (typeof onMediaError === "function") onMediaError(retryErr);
          return false;
        }
      }
      return false;
    }
    if (typeof onMediaError === "function") {
      onMediaError(err);
    } else {
      console.warn("Media playback error:", err);
    }
    return false;
  }
}

export function attachStreamToMediaElement(mediaEl, stream, options = {}) {
  const { muted = true, ...playOptions } = options;
  if (!mediaEl || !stream) return Promise.resolve(false);

  if (typeof muted === "boolean") {
    mediaEl.muted = muted;
    if ("defaultMuted" in mediaEl) {
      mediaEl.defaultMuted = muted;
    }
  }
  if ("playsInline" in mediaEl) mediaEl.playsInline = true;
  if ("autoplay" in mediaEl) mediaEl.autoplay = true;

  const streamChanged = mediaEl.srcObject !== stream;
  if (streamChanged) {
    mediaEl.srcObject = stream;
  }

  if (stream.getVideoTracks) {
    stream.getVideoTracks().forEach((t) => {
      if (!t.enabled) t.enabled = true;
    });
  }

  // Only invoke play() if stream changed or element is paused so re-renders never cause AbortError storms.
  if (streamChanged || mediaEl.paused !== false) {
    return safePlayMedia(mediaEl, playOptions);
  }
  return Promise.resolve(true);
}

const DEFAULT_OAUTH_ORIGINS = [
  "https://accounts.google.com",
  "https://content.googleapis.com",
];

export function isAllowedOAuthOrigin(origin, extraAllowedOrigins = []) {
  if (!origin || typeof origin !== "string") return false;
  const normalized = origin.trim().replace(/\/+$/, "");
  const allowed = new Set([...DEFAULT_OAUTH_ORIGINS, ...extraAllowedOrigins.map((o) => String(o).trim().replace(/\/+$/, ""))]);
  return allowed.has(normalized);
}

export function validateOAuthPostMessage(event, extraAllowedOrigins = []) {
  if (!event || !event.origin) return { valid: false, reason: "missing_origin" };
  if (!isAllowedOAuthOrigin(event.origin, extraAllowedOrigins)) {
    return { valid: false, reason: "untrusted_origin" };
  }
  return { valid: true, data: event.data ?? null };
}

