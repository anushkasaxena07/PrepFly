/**
 * speechEngine.js — Frontend port of the deterministic Speech Analysis Engine.
 * Used for offline / demo mode in SpeechTab.jsx.
 * Mirrors f_backend/services/speech_engine.py.
 */

const FILLER_WORDS = [
  'um', 'uh', 'er', 'ah', 'like', 'so', 'actually', 'basically',
  'you know', 'i mean', 'sort of', 'kind of', 'literally', 'honestly',
  'anyway', 'right', 'obviously', 'seriously'
];

const STOP_WORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be',
  'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'to', 'from',
  'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
  'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
  'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
  'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can',
  'will', 'just', 'should', 'now', 'i', 'you', 'he', 'she', 'it', 'we',
  'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'that', 'this'
]);

export function calculateSpeechMetrics(transcript, durationSeconds = 60) {
  const text = (transcript || '').trim();
  const words = text.match(/\b\w+\b/g) || [];
  const totalWords = words.length;
  const durSec = Math.max(5, Number(durationSeconds) || 60);
  const durMin = durSec / 60;

  // 1. WPM
  const wpm = Math.round(totalWords / durMin);

  // 2. Fillers
  const textLower = text.toLowerCase();
  let fillerCount = 0;
  const breakdown = {};

  FILLER_WORDS.forEach(filler => {
    const escaped = filler.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`\\b${escaped}\\b`, 'gi');
    const matches = textLower.match(regex);
    if (matches && matches.length > 0) {
      breakdown[filler] = matches.length;
      fillerCount += matches.length;
    }
  });

  const fillersPerMin = Math.round((fillerCount / durMin) * 10) / 10;

  // 3. Vocabulary
  const wordTokens = (textLower.match(/\b[a-z]{2,}\b/g) || []);
  const uniqueWords = new Set(wordTokens);
  const vocabDiversity = wordTokens.length > 0
    ? Math.round((uniqueWords.size / wordTokens.length) * 100)
    : 0;

  // 4. Scores
  let wpmScore = 95;
  if (wpm >= 125 && wpm <= 165) wpmScore = 95;
  else if (wpm >= 100 && wpm < 125) wpmScore = 80 + Math.round((wpm - 100) * 0.6);
  else if (wpm > 165 && wpm <= 190) wpmScore = 95 - Math.round((wpm - 165) * 0.8);
  else if (wpm < 100) wpmScore = Math.max(20, 40 + Math.round(wpm * 0.3));
  else wpmScore = Math.max(20, 70 - Math.round((wpm - 190) * 0.5));

  // Filler score: factor in filler_ratio (% of total words)
  const fillerRatio = fillerCount / Math.max(1, totalWords);
  let fillerScore = 100;
  if (fillerRatio > 0.15) {
    fillerScore = Math.max(10, Math.round(100 - (fillerRatio * 320)));
  } else {
    fillerScore = Math.max(20, Math.round(100 - (fillersPerMin * 14) - (fillerRatio * 150)));
  }

  // Vocab score adjustment for short word count
  let vocabScore = 50;
  if (totalWords < 10) {
    vocabScore = Math.min(50, Math.max(20, Math.round(vocabDiversity * 0.5)));
  } else {
    vocabScore = Math.min(100, Math.max(30, Math.round(vocabDiversity * 1.5)));
  }

  const paceScore = 88;

  const baseConfidence = (
    wpmScore * 0.30 +
    fillerScore * 0.35 +
    vocabScore * 0.20 +
    paceScore * 0.15
  );

  // Short response completeness penalty
  let confidencePct = baseConfidence;
  if (totalWords < 15) {
    const completenessFactor = Math.max(0.25, totalWords / 16.0);
    confidencePct = Math.round(baseConfidence * completenessFactor);
  } else {
    confidencePct = Math.round(baseConfidence);
  }

  const overallScore = Math.round(Math.max(1.0, Math.min(10.0, confidencePct / 10.0)) * 10) / 10;

  const tone = {
    confidence: Math.max(20, Math.min(99, confidencePct)),
    clarity: Math.max(20, Math.min(99, Math.round(fillerScore * 0.7 + wpmScore * 0.3))),
    enthusiasm: Math.max(20, Math.min(95, Math.round(wpmScore * 0.5 + vocabScore * 0.5))),
    nervousness: Math.max(5, Math.min(95, Math.round((fillerRatio * 200) + (100 - paceScore) * 0.5)))
  };

  const feedback = [];

  if (totalWords < 10) {
    feedback.push(`⚠️ Short response detected (${totalWords} words). Speak complete, detailed sentences for higher confidence scores.`);
  }

  if (wpm >= 120 && wpm <= 165) {
    feedback.push(`✅ Excellent speaking speed at ${wpm} WPM — easy to follow.`);
  } else {
    feedback.push(`✅ Vocabulary diversity ratio: ${vocabDiversity}%.`);
  }

  if (fillerCount === 0) {
    feedback.push("✅ Flawless delivery with 0 filler words detected!");
  } else {
    const listStr = Object.entries(breakdown).map(([w, c]) => `'${w}' (${c}x)`).join(", ");
    feedback.push(`⚠️ Detected ${fillerCount} filler words (${listStr}). Take silent pauses instead of fillers.`);
  }

  if (wpm < 110) {
    feedback.push(`📈 Pace is slightly slow (${wpm} WPM). Target 130–150 WPM for technical responses.`);
  } else if (wpm > 170) {
    feedback.push(`📈 Fast delivery (${wpm} WPM). Slow down slightly to emphasize key points.`);
  } else {
    feedback.push(`📈 Speaking pace is consistent at ${wpm} WPM.`);
  }

  feedback.push("💡 Tip: Take a 1-second pause before answering complex questions to organize your thoughts.");

  return {
    confidence_pct: confidencePct,
    wpm: wpm,
    filler_count: fillerCount,
    fillers_per_min: fillersPerMin,
    fillers_found: Object.keys(breakdown),
    vocabulary_diversity: vocabDiversity,
    overall_score: overallScore,
    tone: tone,
    feedback: feedback
  };
}
