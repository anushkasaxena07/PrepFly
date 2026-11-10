import React from "react";
import { usePrepFlyTheme } from "./ThemeContext";
import heroMountainImg from "../../assets/hero-mountain.jpg";

export function PrepFlyMark({ size = 34 }) {
  return (
    <img
      src="/prepfly-logo.png"
      alt="PrepFly"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "10px",
        objectFit: "cover",
        flexShrink: 0,
        boxShadow: "0 4px 14px rgba(15, 23, 42, 0.22)",
      }}
    />
  );
}

const ICONS = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  roadmap: (
    <>
      <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" />
      <path d="M9 3v15" />
      <path d="M15 6v15" />
    </>
  ),
  coding: (
    <>
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
      <line x1="14" y1="4" x2="10" y2="20" />
    </>
  ),
  speech: (
    <>
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </>
  ),
  resume: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </>
  ),
  ava: (
    <>
      <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6L15 21H9l-.7-6C6.3 13.7 5 11.5 5 9a7 7 0 0 1 7-7z" />
      <line x1="9.5" y1="18" x2="14.5" y2="18" />
    </>
  ),
  achievements: (
    <>
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2z" />
    </>
  ),
  interviews: (
    <>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  analytics: (
    <>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </>
  ),
  jobs: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  students: (
    <>
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </>
  ),
  qbank: (
    <>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </>
  ),
  reports: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M9 15l2 2 4-4" />
    </>
  ),
  announcements: (
    <>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </>
  ),
  support: (
    <>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </>
  ),
  organization: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
      <line x1="15" y1="8" x2="17" y2="8" />
      <line x1="15" y1="12" x2="17" y2="12" />
    </>
  ),
  subscription: (
    <>
      <path d="M2 17l3-9 5 4 2-6 2 6 5-4 3 9H2z" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.85 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </>
  ),
  payments: (
    <>
      <rect x="1" y="4" width="22" height="16" rx="2" />
      <line x1="1" y1="10" x2="23" y2="10" />
    </>
  ),
  aiconfig: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="1" x2="9" y2="4" />
      <line x1="15" y1="1" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="23" />
      <line x1="15" y1="20" x2="15" y2="23" />
    </>
  ),
  activitylogs: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  layers: (
    <>
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </>
  ),
  lock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </>
  ),
  check: (
    <>
      <polyline points="20 6 9 17 4 12" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </>
  ),
  video: (
    <>
      <rect x="2" y="6" width="14" height="12" rx="2.5" />
      <polygon points="16 10 22 7 22 17 16 14 16 10" />
    </>
  ),
};

export function NavIcon({ name, size = 16, strokeWidth = 1.75, color = "currentColor" }) {
  const path = ICONS[name] || ICONS.dashboard;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0 }}
    >
      {path}
    </svg>
  );
}

/**
 * Shared Dual-Theme Hero Header:
 * - Cosmic Violet mode: Dark galaxy gradient header transitioning into crisp cool light body.
 * - Alpine Sunrise mode: Warm porcelain editorial serif header with sunlit snow-capped mountain arch.
 */
export function CosmicHero({
  badge = "PrepFly Workspace",
  titleWhite,
  titleAccent,
  subtitle,
  cornerNote = "Dream Bigger",
  rightControls = null,
  actions = null,
  sunriseBadge = null,
  sunriseTitleLead = null,
  sunriseTitleAccent = null,
  sunriseSubtitle = null,
  ctaLabel = null,
  onCtaClick = null,
  children,
}) {
  const { isSunrise } = usePrepFlyTheme();

  if (isSunrise) {
    const eyebrow = (sunriseBadge || badge || "YOUR CAREER PREP COMPANION").toUpperCase();
    const lead = sunriseTitleLead ?? titleWhite;
    const accent = sunriseTitleAccent ?? titleAccent;
    const body = sunriseSubtitle ?? subtitle;

    return (
      <section className="pf-hero pf-hero-sunrise">
        <div className="pf-hero-sunrise-wash" aria-hidden="true" />
        <div className="pf-hero-inner pf-hero-sunrise-inner">
          <div className="pf-sunrise-grid">
            <div className="pf-sunrise-copy">
              <div className="pf-sunrise-eyebrow">{eyebrow}</div>
              <h1 className="pf-sunrise-title">
                <span>{lead}</span>
                {accent && <em className="pf-sunrise-title-italic"> {accent}</em>}
              </h1>
              {body && <p className="pf-sunrise-sub">{body}</p>}
              {(ctaLabel && onCtaClick) || actions ? (
                <div className="pf-sunrise-cta-row">
                  {ctaLabel && onCtaClick && (
                    <button
                      type="button"
                      className="pf-sunrise-cta-btn"
                      onClick={onCtaClick}
                    >
                      {ctaLabel}
                    </button>
                  )}
                  {actions}
                </div>
              ) : null}
            </div>

            <div className="pf-sunrise-art" aria-hidden="true">
              <span className="pf-sunrise-spark pf-sunrise-spark-1">✦</span>
              <span className="pf-sunrise-spark pf-sunrise-spark-2">✦</span>
              <div className="pf-mountain-arch">
                <img
                  src={heroMountainImg}
                  alt="Sunlit Alpine Mountain Peak"
                  className="pf-mountain-img"
                />
                <div className="pf-mountain-fade" />
                <svg
                  className="pf-mountain-wave"
                  viewBox="0 0 420 140"
                  fill="none"
                  preserveAspectRatio="none"
                >
                  <path
                    d="M-10 92 C 95 45, 210 128, 430 62"
                    stroke="rgba(255, 248, 240, 0.55)"
                    strokeWidth="1.5"
                  />
                  <path
                    d="M-10 108 C 110 70, 240 135, 430 85"
                    stroke="rgba(255, 248, 240, 0.30)"
                    strokeWidth="1"
                  />
                </svg>
              </div>
            </div>
          </div>

          {children && <div className="pf-hero-kpis pf-hero-kpis-sunrise">{children}</div>}
        </div>
      </section>
    );
  }

  return (
    <section className="pf-hero">
      <div className="pf-hero-glow-1" aria-hidden="true" />
      <div className="pf-hero-glow-2" aria-hidden="true" />
      <div className="pf-hero-stars" aria-hidden="true" />

      <div className="pf-hero-inner">
        <div className="pf-hero-top">
          <div className="pf-hero-pill">
            <span className="pf-hero-dot" />
            <span>{badge}</span>
          </div>

          <div className="pf-hero-right">
            {cornerNote && (
              <span className="pf-hero-note">
                {cornerNote}
              </span>
            )}
            {rightControls}
          </div>
        </div>

        <div className="pf-hero-title-row">
          <div>
            <h1 className="pf-hero-title">
              <span>{titleWhite}</span>
              {titleAccent && <span className="pf-hero-title-accent"> {titleAccent}</span>}
            </h1>
            {subtitle && <p className="pf-hero-sub">{subtitle}</p>}
          </div>
          {actions && <div className="pf-hero-actions">{actions}</div>}
        </div>

        {children && <div className="pf-hero-kpis">{children}</div>}
      </div>
    </section>
  );
}

