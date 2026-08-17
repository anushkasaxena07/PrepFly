/**
 * Frontend Structured Logger with Sentry Fallback Support
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
};

const CURRENT_LEVEL = import.meta.env.DEV ? LOG_LEVELS.DEBUG : LOG_LEVELS.INFO;

function formatMessage(level, message, meta) {
  const timestamp = new Date().toISOString();
  return {
    timestamp,
    level,
    message,
    ...(meta ? { meta } : {}),
  };
}

export const logger = {
  debug(message, meta) {
    if (CURRENT_LEVEL <= LOG_LEVELS.DEBUG) {
      console.debug(`[DEBUG] ${new Date().toLocaleTimeString()} - ${message}`, meta || '');
    }
  },

  info(message, meta) {
    if (CURRENT_LEVEL <= LOG_LEVELS.INFO) {
      console.info(`[INFO] ${new Date().toLocaleTimeString()} - ${message}`, meta || '');
    }
  },

  warn(message, meta) {
    if (CURRENT_LEVEL <= LOG_LEVELS.WARN) {
      console.warn(`[WARN] ${new Date().toLocaleTimeString()} - ${message}`, meta || '');
    }
  },

  error(message, error, meta) {
    if (CURRENT_LEVEL <= LOG_LEVELS.ERROR) {
      console.error(`[ERROR] ${new Date().toLocaleTimeString()} - ${message}`, error || '', meta || '');
    }

    // Capture to Sentry if globally available
    if (window.Sentry && typeof window.Sentry.captureException === 'function') {
      if (error instanceof Error) {
        window.Sentry.captureException(error, { extra: { message, ...meta } });
      } else {
        window.Sentry.captureMessage(`${message}: ${JSON.stringify(error)}`);
      }
    }
  },
};

export default logger;
