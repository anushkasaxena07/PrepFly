import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "prepfly_ui_theme";
const VALID_THEMES = ["cosmic", "sunrise"];

const ThemeContext = createContext({
  theme: "cosmic",
  isSunrise: false,
  setTheme: () => {},
  toggleTheme: () => {},
  isTransitioning: false,
});

function readInitialTheme() {
  if (typeof window === "undefined") return "cosmic";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && VALID_THEMES.includes(saved)) return saved;
  } catch {
    // Ignore storage quota / privacy mode errors
  }
  return "cosmic";
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readInitialTheme);
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Ignore storage errors
    }
  }, [theme]);

  const applyThemeWithMagic = useCallback((nextTheme) => {
    if (!VALID_THEMES.includes(nextTheme)) return;
    if (typeof document !== "undefined") {
      document.documentElement.classList.add("pf-theme-morphing");
      setIsTransitioning(true);
      setTimeout(() => {
        document.documentElement.classList.remove("pf-theme-morphing");
        setIsTransitioning(false);
      }, 650);
    }
    setThemeState(nextTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === "sunrise" ? "cosmic" : "sunrise";
      if (typeof document !== "undefined") {
        document.documentElement.classList.add("pf-theme-morphing");
        setIsTransitioning(true);
        setTimeout(() => {
          document.documentElement.classList.remove("pf-theme-morphing");
          setIsTransitioning(false);
        }, 650);
      }
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        isSunrise: theme === "sunrise",
        setTheme: applyThemeWithMagic,
        toggleTheme,
        isTransitioning,
      }}
    >
      {isTransitioning && <div className={`pf-magic-veil pf-magic-veil-${theme}`} aria-hidden="true" />}
      {children}
    </ThemeContext.Provider>
  );
}

export function usePrepFlyTheme() {
  return useContext(ThemeContext);
}

export function ThemeToggleButton({ className = "", compact = false }) {
  const { isSunrise, toggleTheme } = usePrepFlyTheme();

  return (
    <button
      type="button"
      data-testid="theme-toggle-btn"
      onClick={toggleTheme}
      className={`pf-theme-toggle ${isSunrise ? "is-sunrise" : "is-cosmic"} ${compact ? "is-compact" : ""} ${className}`}
      title={isSunrise ? "Switch to Cosmic Violet theme" : "Switch to Alpine Sunrise Mountain theme"}
      aria-label={isSunrise ? "Switch to Cosmic Violet theme" : "Switch to Alpine Sunrise Mountain theme"}
    >
      <span className="pf-theme-toggle-orb" aria-hidden="true">
        {isSunrise ? (
          /* Cosmic Moon + Sparkle icon to switch back to Cosmic */
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            <path d="M18 4l.6 1.4L20 6l-1.4.6L18 8l-.6-1.4L16 6l1.4-.6L18 4z" fill="currentColor" stroke="none" />
          </svg>
        ) : (
          /* Warm Sunrise Sun + Mountain Peak icon */
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 18h18" />
            <path d="M5 18l5-8 4 5 3-4 4 7" />
            <circle cx="16.5" cy="7.5" r="2.5" />
          </svg>
        )}
      </span>
      {!compact && (
        <span className="pf-theme-toggle-text">
          {isSunrise ? "Cosmic Mode" : "Sunrise Peak"}
        </span>
      )}
    </button>
  );
}

