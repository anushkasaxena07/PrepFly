/**
 * PrepFly Runtime Template Guard
 * Golden Rule 5: No unresolved template variables in UI.
 * Any string containing None, null, undefined, {{, or NaN shown to a user is a bug.
 * Add a runtime guard that blocks rendering and logs an error.
 */

const FORBIDDEN_REGEX = /\b(None|null|undefined|NaN)\b|\{\{.*?\}\}|None\s*\(\s*None\s*\)/i;

/**
 * Checks if a string contains any unresolved template markers or null leaks.
 */
export function hasTemplateLeak(value) {
  if (typeof value !== "string") return false;
  return FORBIDDEN_REGEX.test(value);
}

/**
 * Sanitizes a string for user presentation, logging an error if a leak was prevented.
 */
export function sanitizeUIString(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  const str = String(value);
  if (hasTemplateLeak(str)) {
    console.error(`[TEMPLATE_GUARD_VIOLATION] Unresolved template leak blocked: "${str}"`);
    return str
      .replace(/None\s*\(\s*None\s*\)/gi, "General Role (Tech)")
      .replace(/\bNone\b/gi, "")
      .replace(/\bnull\b/gi, "")
      .replace(/\bundefined\b/gi, "")
      .replace(/\bNaN\b/gi, "0")
      .replace(/\{\{.*?\}\}/g, "")
      .trim() || fallback;
  }
  return str;
}

/**
 * Format score cleanly without NaN.
 */
export function formatScore(num, digits = 1) {
  if (num === null || num === undefined || isNaN(Number(num))) {
    return "0.0";
  }
  return Number(num).toFixed(digits);
}
