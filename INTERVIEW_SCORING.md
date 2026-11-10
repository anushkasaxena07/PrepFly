# PrepFly AI Interview Scoring & Verdict Specification (`formula_version = "v1"`)

All constants, weights, minimum-turn thresholds, and grade bands live centrally in [`f_backend/services/interview_scoring_config.py`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/interview_scoring_config.py). Every mathematical calculation and hiring status decision executes deterministically in [`f_backend/services/interview_scoring_service.py`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/interview_scoring_service.py); the LLM only supplies per-criterion scores paired with verified verbatim candidate quotes.

---

## 1. Per-Turn & Speech Telemetry Formulas

### 1.1 Per-Turn Score
For a candidate turn whose evaluation has `status == "ok"` and rubric criterion entries $c_i$ with weight $w_i > 0$ and score $s_i \in [0, 1]$:

$$\text{turn\_score} = \frac{\sum_i w_i \cdot \text{clamp}(s_i, 0, 1)}{\sum_i w_i}$$

Turns with evaluation status `"failed"`, `"skipped"`, or `"empty"` have `turn_score = None` (`NULL`), **never `0`**. Explicit `"I don't know"` turns receive deterministic `0.10` (`evaluator_type = "deterministic_dont_know"`).

### 1.2 Speech Delivery Metrics ([`interview_speech_service.py`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/interview_speech_service.py))
- `wpm = round((word_count / speaking_time_minutes), 1)` when `input_mode == "speech"`, `audio_duration_s >= 1.0`, and `word_count > 0`; otherwise `None` (`"Not measurable"` with explicit `missing_reason`).
- `pause_count`, `longest_pause_s`, `avg_pause_s`, `silence_ratio` require word-level timestamps (`PAUSE_GAP_THRESHOLD_S = 1.0s`); if absent, they remain `None` (`"Not measurable"`).
- **Speech Delivery Score (`[0.0, 1.0]`)**:
  - `pace_score`: `1.0` inside `115–160 WPM` (`WPM_OPTIMAL_MIN` to `WPM_OPTIMAL_MAX`); decays linearly outside `[115, 160]` floored at `0.3`.
  - `fluency_score`: $\max(0.2, 1.0 - \frac{\text{filler\_count}}{\max(1, \text{word\_count})} \times 3.0)$.
  - `turn_delivery = 0.6 * pace_score + 0.4 * fluency_score`.
  - Returns `None` if zero measurable speech turns exist.

---

## 2. Dimension Scores, Coverage & Overall Score

### 2.1 Dimension Configuration & Weights (Sum = `1.00`)

| Dimension | Weight | Critical | Delivery Signal | Contributing Rubric Criteria |
|---|---:|:---:|:---:|---|
| Technical Accuracy | `0.16` | Yes | No | `technical_accuracy`, `correctness` |
| Technical Depth | `0.14` | Yes | No | `technical_depth`, `tradeoffs`, `architecture` |
| Problem Solving | `0.14` | Yes | No | `problem_solving`, `edge_cases`, `algorithmic_thinking` |
| Communication Clarity | `0.10` | No | Yes | `clarity`, `explanation_clarity` |
| Structure & Organization | `0.10` | No | No | `structure`, `star_structure` |
| Role Relevance | `0.10` | No | No | `role_relevance`, `domain_fit` |
| Examples & Evidence | `0.08` | No | No | `examples`, `concrete_metrics` |
| Confidence & Delivery | `0.06` | No | Yes | `delivery_confidence`, `pacing` |
| Conciseness | `0.06` | No | Yes | `conciseness`, `fluency` |
| Professionalism | `0.06` | No | No | `professionalism`, `ownership` |

### 2.2 Dimension Aggregation
Over all `status == "ok"` evaluations containing at least one criterion matching the dimension:

$$\text{rubric\_mean}_d = \frac{\sum w_{d,k} \cdot s_{d,k}}{\sum w_{d,k}}$$

- If `is_delivery == True` and `speech_delivery is None`: dimension status = `"Not evaluated"`, `score = None` (excluded from overall average, **never zero-filled**).
- If `is_delivery == True` and `speech_delivery is not None`:
  $$\text{dim\_norm}_d = 0.5 \cdot \text{rubric\_mean}_d + 0.5 \cdot \text{speech\_delivery}$$
- Otherwise: $\text{dim\_norm}_d = \text{rubric\_mean}_d$.
- Dimensions with `< MIN_TURNS_PER_DIMENSION` (`2`) turns are labelled `LIMITED_EVIDENCE` (`confidence_label = "LOW_CONFIDENCE"`). Dimensions with `0` contributing turns are `score = None` (`"Not evaluated"`).

### 2.3 Overall Score & Coverage
Let $E$ be the set of evaluated dimensions (`normalized_score is not None`):

$$\text{coverage} = \frac{\sum_{d \in E} \text{weight}_d}{\sum_{d \in \text{ALL}} \text{weight}_d}, \qquad \text{overall\_score} = \frac{\sum_{d \in E} \text{weight}_d \cdot \text{dim\_norm}_d}{\sum_{d \in E} \text{weight}_d}$$

Missing or unevaluated dimensions never drag down the overall score via zero substitution.

---

## 3. Confidence, Status Rules, Grade Bands & Hiring Recommendations

### 3.1 Confidence Score (Separate from Performance Score)
- `turn_factor = min(1.0, substantive_turns / 5.0)`
- `cov_factor = clamp(coverage, 0.0, 1.0)`
- `agreement_factor = max(0.2, 1.0 - max_disagreement_delta * 0.5)` (when double-grade disagreement > `0.25` was flagged, else `1.0`)
- `confidence_score = 0.45 * turn_factor + 0.40 * cov_factor + 0.15 * agreement_factor`
- Labels: `HIGH` (`>= 0.70`), `MEDIUM` (`0.40–0.70`), `LOW` (`< 0.40`).

### 3.2 Deterministic Report Status State Machine
1. **`EVALUATION_FAILED`**: zero `ok` evaluations exist while candidate substantive turns exist (or all present evaluations have `status == "failed"`). **No grade, no recommendation.** Next action: `retry_evaluation`.
2. **`INCOMPLETE_INSUFFICIENT_DATA`**: `substantive_turns < 3` OR `total_words < 15` OR `coverage < 0.25`. **No grade, no recommendation.** Next action: `continue_interview`.
3. **`PARTIAL`**: sufficiency met and `0.25 <= coverage < 0.75` (or any substantive turn still has `status == "failed"`). Grade shown as `"Provisional (X)"`; recommendation capped at `"Needs more evidence"` or `"Leaning Hire (Provisional)"` / `"No Hire (Provisional)"`.
4. **`EVALUATED`**: `substantive_turns >= 3`, `total_words >= 15`, `coverage >= 0.75`, and no failed turns. Full grade and recommendation issued.

### 3.3 Grade Bands & Hiring Recommendation Rules
- **Grade Bands (`EVALUATED` / `PARTIAL`)**: `A >= 0.85`, `B 0.70–0.85`, `C 0.55–0.70`, `D 0.40–0.55`, `F < 0.40`.
- **Recommendation (`EVALUATED`)**:
  - `"Strong Hire"`: `overall >= 0.85` AND `min_critical_dimension >= 0.75` AND `confidence_score >= 0.70`
  - `"Hire"`: `overall >= 0.70` AND `min_critical_dimension >= 0.55`
  - `"Lean Hire"`: `overall >= 0.62`
  - `"Lean No Hire"`: `overall >= 0.50`
  - `"No Hire"`: `overall >= 0.35`
  - `"Strong Reject"`: **ONLY** allowed when `status == "EVALUATED"` AND `overall < 0.35` AND `substantive_turns >= 3` AND `confidence.label == "HIGH"`. Missing or failed data can **never** yield `Strong Reject`.

---

## 4. Worked 6-Turn Numeric Example (Verified Against `score_interview_session`)

**Inputs**:
- 6 substantive spoken turns (`t1..t6`), 30 words each (`180` words total, `80.0s` total duration, `135.0 WPM` within `115–160 WPM`, `0` fillers -> `speech_delivery_score = 1.0`).
- Turns `t1..t4`: all rubric criteria scored `0.90`.
- Turns `t5..t6`: all rubric criteria scored `0.50`.

**Intermediate & Final Output**:
- All 7 non-delivery dimensions (`rubric_mean = (4 * 0.90 + 2 * 0.50) / 6 = 0.7667` -> `76.7`, Grade `B`).
- All 3 delivery dimensions (`Communication Clarity`, `Confidence & Delivery`, `Conciseness`):
  `0.5 * 0.7667 + 0.5 * 1.0 = 0.8833` -> `88.3`, Grade `A`.
- Dimension weight sums: non-delivery weight = `0.78`, delivery weight = `0.22`, total `coverage = 1.0`.
- `overall_score = 0.78 * 0.7667 + 0.22 * 0.8833 = 0.7924` (`79.2 / 100`).
- `confidence`: `turn_factor = 1.0`, `cov_factor = 1.0`, `agreement_factor = 1.0` -> `score = 1.0` (`HIGH`).
- `report_status`: **`EVALUATED`** | `grade`: **`B`** | `recommendation`: **`Hire`**.

### Original Bug Scenario Comparison (Spoken Answers Present, Empty Evaluations)
- **Before**: `Grade = "F"`, `recommendation = "Strong Reject (No Responses Provided)"`, `WPM = 0`, `display_name = "Candidate"`.
- **After (`v1`)**: `report_status = "EVALUATION_FAILED"`, `grade = null`, `recommendation = null`, real `wpm` preserved from speech telemetry, Google profile `display_name` preserved, actionable next step = `"retry_evaluation"`.

