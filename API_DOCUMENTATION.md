# REST API SPECIFICATION & CONTRACT ENCYCLOPEDIA — PREPFLY

**Document Version:** 2.0.0  
**Base URL:** `https://prepfly-1.onrender.com` / `http://localhost:5000`  
**Authentication:** HTTP Bearer Header (`Authorization: Bearer <JWT_TOKEN>`) and `X-User-Id`  
**Content-Type:** `application/json` (unless `multipart/form-data` for file uploads)  

---

## 1. Authentication & Security Headers

All requests to protected endpoints require:
- `Authorization: Bearer <JWT_TOKEN>` (HS256 signed with `JWT_SECRET_KEY`, contains `sub`, `user_id`, `role`, `organization_id`)
- `X-User-Id: <USER_UUID>` (Candidate client tracking identifier)

Standard error responses follow the RFC 7807 problem details specification:
```json
{
  "error": "Error classification string",
  "message": "Human-readable explanation of rejection",
  "details": null
}
```

---

## 2. Live AI Interview Simulation Engine (`/api` & Root)

### `POST /upload`
- **Description:** Uploads candidate resume, validates DPDP 2023 affirmative consent, extracts text via PyMuPDF/docx2txt, computes initial ATS compatibility score, and initializes persistent interview session.
- **Content-Type:** `multipart/form-data`
- **Request Parameters:**
  - `resume` (file, required): `.pdf` or `.docx` resume file.
  - `consent` (string, required): Must be `"true"` under DPDP Act 2023.
  - `user_id` (string, optional): Candidate user UUID.
- **Responses:**
  - `200 OK`: `{"message": "Resume uploaded successfully", "session_id": "uuid", "ats_score": 85}`
  - `400 Bad Request`: `{"error": "Affirmative consent required"}`
  - `500 Internal Server Error`: `{"error": "Failed to persist interview session"}`

### `POST /start-interview`
- **Description:** Verifies session ownership, validates active status, initializes conversational interviewer persona (Ava), generates Question 1, and transitions state to `ASKING`.
- **Rate Limit:** 10 per minute.
- **Request Body:**
  ```json
  {
    "session_id": "uuid-string",
    "role": "AI/ML Engineer",
    "category": "Machine Learning & AI",
    "difficulty": "Intermediate",
    "personality": "professional",
    "job_description": "Optional JD context"
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "message": "Interview started",
      "question": "Explain the Bias-Variance tradeoff in supervised learning.",
      "question_number": 1,
      "stage": "TECHNICAL_CORE",
      "personality": "professional",
      "total_questions": 10
    }
    ```
  - `404 Not Found`: `{"error": "Session not found or already completed"}`

### `POST /next`
- **Description:** Processes candidate response, extracts speech telemetry, evaluates concept accuracy in parallel with next-question generation, and atomically appends to session audit history.
- **Rate Limit:** 10 per minute.
- **Request Body:**
  ```json
  {
    "session_id": "uuid-string",
    "answer": "Candidate explanation or code submission...",
    "current_question": "Text of answered question",
    "question_index": 1
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "message": "Answer recorded",
      "done": false,
      "feedback": {
        "score": 8.5,
        "accuracy_score": 85,
        "feedback": "Strong explanation of bias vs variance trade-offs.",
        "live_metrics": { "wpm": 135, "clarity": 90, "filler_count": 0 }
      },
      "next_question": "How do L1 and L2 regularization prevent overfitting mathematically?",
      "question": "How do L1 and L2 regularization prevent overfitting mathematically?",
      "question_number": 2,
      "stage": "TECHNICAL_CORE",
      "total_questions": 10
    }
    ```
  - `429 Too Many Requests`: `{"error": "Concurrent request in progress for this interview session"}`

### `POST /end-interview`
- **Description:** Fast-compiles (<1ms) multi-dimensional hiring scorecard from recorded turn evaluations, persists final metrics, and deactivates session (`active = False`).
- **Request Body:** `{"session_id": "uuid-string"}`
- **Responses:**
  - `200 OK`:
    ```json
    {
      "overall_score": 82,
      "overall_score_100": 82,
      "grade": "B+",
      "hiring_recommendation": "Strong Hire",
      "executive_summary": { ... },
      "turn_evaluations": [ ... ],
      "report": "### Executive Candidate Evaluation\n..."
    }
    ```

---

## 3. Diagnostic & Roadmap Intelligence (`/api` via `routes/intelligence.py`)

### `POST /api/assessment/start`
- **Description:** Generates an adaptive diagnostic assessment session with 5 balanced questions tailored to target role and experience level.
- **Request Body:**
  ```json
  {
    "target_role": "AI/ML Engineer",
    "experience_level": "Mid-Level (2-5 years)"
  }
  ```
- **Responses:**
  - `201 Created`:
    ```json
    {
      "status": "success",
      "assessment": {
        "id": "uuid-assessment-id",
        "title": "Diagnostic Assessment — AI/ML Engineer",
        "total_questions": 5,
        "questions": [
          {
            "id": "q1",
            "skill_id": "ml_model_development",
            "question_text": "In supervised machine learning, explain...",
            "difficulty": "Intermediate"
          }
        ]
      }
    }
    ```

### `POST /api/assessment/<assessment_id>/submit`
- **Description:** Submits candidate answers for diagnostic assessment, grades responses against rubrics, writes verified evidence to `skill_evidence_registry`, and recalculates roadmap.
- **Request Body:**
  ```json
  {
    "answers": {
      "q1_id": "Candidate answer text 1...",
      "q2_id": "Candidate answer text 2..."
    }
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "status": "success",
      "evaluation": {
        "overall_score": 78.5,
        "concept_breakdown": { "ml_model_development": 85.0 },
        "results": [ ... ]
      },
      "roadmap_generated": true,
      "roadmap_id": "rm_uuid"
    }
    ```

### `GET /api/roadmap/current`
- **Description:** Retrieves candidate's active preparation plan, grouped by day number, with completion tracking and capacity allocations.
- **Responses:**
  - `200 OK`:
    ```json
    {
      "status": "success",
      "roadmap": {
        "id": "rm_uuid",
        "target_role": "AI/ML Engineer",
        "completion_percentage": 25,
        "total_activities": 16,
        "schedule": {
          "1": [ { "id": "act_1", "activity_type": "LEARN", "title": "PyTorch Tensor Operations", "estimated_minutes": 30 } ]
        }
      }
    }
    ```

### `GET /api/intelligence/readiness/provenance`
- **Description:** Returns mathematical provenance of role readiness, coverage ratio, 4 competency pillars, and chronological evidence history.
- **Responses:**
  - `200 OK`:
    ```json
    {
      "status": "success",
      "readiness": {
        "overall_score": 74.5,
        "readiness_status": "ESTABLISHED",
        "coverage_ratio": 0.85,
        "formula_breakdown": "Readiness Score (74.5%) = [Sum(Assessed Proficiency * Tier Weight) / Total Assessed Weights] * Coverage Penalty"
      },
      "pillars": {
        "dsa": { "proficiency": 80.0, "confidence": 0.85, "coverage": 0.90 },
        "cs": { "proficiency": 72.0, "confidence": 0.75, "coverage": 0.80 },
        "system_design": { "proficiency": 68.0, "confidence": 0.65, "coverage": 0.70 },
        "interview_skills": { "proficiency": 85.0, "confidence": 0.90, "coverage": 0.95 }
      },
      "evidence_history": [ ... ]
    }
    ```

---

## 4. Job Preparation & Gap Analysis (`/api/intelligence` via `routes/career_intelligence.py`)

### `POST /api/intelligence/job-prep/assessments`
- **Description:** Ingests raw Job Description text, classifies requirements across 6 canonical dimensions, aggregates existing candidate evidence, and constructs blueprint.
- **Request Body:**
  ```json
  {
    "raw_text": "Looking for a Senior ML Engineer proficient in PyTorch, Distributed Training, and RAG...",
    "company": "Databricks",
    "role": "AI/ML Engineer",
    "experience_level": "Mid-Level (2-5 years)",
    "target_date": "2026-12-15"
  }
  ```
- **Responses:**
  - `201 Created`:
    ```json
    {
      "success": true,
      "session_id": "job_sess_abc123",
      "data": {
        "section_b_overall_readiness": {
          "overall_readiness": 65,
          "assessment_coverage_pct": 70,
          "evidence_confidence": 0.75,
          "is_gated": false
        },
        "section_c_requirement_breakdown": [ ... ],
        "section_d_coding_analysis": { "coding_readiness_score": 80 }
      }
    }
    ```

