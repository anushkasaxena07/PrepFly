-- Supabase PostgreSQL Migration Schema for InterviewAI

CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                password TEXT,
                role TEXT,
                avatar TEXT,
                google_id TEXT,
                phone TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS pending_users (
                email VARCHAR(255) PRIMARY KEY,
                name TEXT,
                password TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS otps (
                id BIGSERIAL PRIMARY KEY ,
                email TEXT,
                otp TEXT,
                expires_at TEXT,
                is_used INTEGER DEFAULT 0,
                purpose TEXT
            );

CREATE TABLE IF NOT EXISTS sqlite_sequence(name,seq);

CREATE TABLE IF NOT EXISTS otp_requests (
                id BIGSERIAL PRIMARY KEY ,
                email TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS auth_logs (
                id BIGSERIAL PRIMARY KEY ,
                email TEXT,
                auth_method TEXT,
                success INTEGER,
                ip_address TEXT,
                timestamp TEXT
            );

CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                resume_text TEXT,
                storage_path TEXT,
                question_index INTEGER,
                questions TEXT,
                responses TEXT,
                feedbacks TEXT,
                scores TEXT,
                active INTEGER DEFAULT 1,
                final_score DOUBLE PRECISION,
                final_grade TEXT,
                final_report TEXT,
                recording_path TEXT,
                created_at TEXT,
                updated_at TEXT
            , category TEXT, difficulty TEXT, stage TEXT, ats_score INTEGER, structured_resume TEXT);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id BIGSERIAL PRIMARY KEY ,
                email TEXT,
                token TEXT,
                expires_at TEXT,
                is_used INTEGER DEFAULT 0
            );

CREATE TABLE IF NOT EXISTS coding_submissions (
                id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                problem_id TEXT,
                language TEXT,
                code TEXT,
                passed INTEGER,
                total INTEGER,
                time_complexity TEXT,
                space_complexity TEXT,
                ai_review TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS speech_analyses (
                id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                transcript TEXT,
                confidence_pct DOUBLE PRECISION,
                wpm INTEGER,
                filler_count INTEGER,
                overall_score DOUBLE PRECISION,
                feedback TEXT,
                tone TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS resume_scores (
                id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                resume_text TEXT,
                job_description TEXT,
                score DOUBLE PRECISION,
                details TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS coding_problems (
                problem_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                description TEXT,
                constraints TEXT,
                examples TEXT,
                difficulty TEXT,
                category TEXT,
                starter_code TEXT,
                test_cases TEXT,
                sheet_id TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS coding_rooms (
                room_id VARCHAR(255) PRIMARY KEY,
                problem_id TEXT,
                created_by TEXT,
                current_code TEXT,
                current_lang TEXT,
                participants TEXT,
                assigned_problems TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS question_sheets (
                sheet_id VARCHAR(255) PRIMARY KEY,
                uploader_id TEXT,
                filename TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS webrtc_rooms (
                room_code VARCHAR(255) PRIMARY KEY,
                session_name TEXT,
                category TEXT,
                created_by TEXT,
                devices TEXT,
                participants TEXT,
                status TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS subscription (
                id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                plan TEXT,
                price DOUBLE PRECISION,
                status TEXT,
                payment_id TEXT,
                payment_method TEXT,
                start_date TEXT,
                expiry_date TEXT,
                auto_renew INTEGER,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS payment (
                id VARCHAR(255) PRIMARY KEY,
                user_id TEXT,
                amount DOUBLE PRECISION,
                invoice_no TEXT,
                payment_id TEXT,
                status TEXT,
                method TEXT,
                created_at TEXT
            , organization_id TEXT, razorpay_order_id TEXT, razorpay_payment_id TEXT, razorpay_signature TEXT, currency TEXT, invoice_number TEXT, payment_method TEXT);

CREATE TABLE IF NOT EXISTS admin (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                name TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS organization (
                id VARCHAR(255) PRIMARY KEY,
                name TEXT,
                type TEXT,
                logo TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                address TEXT,
                subscription_plan TEXT,
                subscription_expiry TEXT,
                status TEXT,
                created_at TEXT
            , subscription_status TEXT, trial_start TEXT, trial_end TEXT, subscription_start TEXT, current_plan TEXT, updated_at TEXT);

CREATE TABLE IF NOT EXISTS students (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                name TEXT,
                roll_number TEXT,
                department TEXT,
                semester TEXT,
                year TEXT,
                gender TEXT,
                email TEXT,
                phone TEXT,
                resume_url TEXT,
                interview_score DOUBLE PRECISION,
                coding_score DOUBLE PRECISION,
                overall_score DOUBLE PRECISION,
                subscription TEXT,
                status TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS announcements (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                message TEXT,
                target_dept TEXT,
                target_sem TEXT,
                send_email INTEGER,
                send_notif INTEGER,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS question_bank (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                category TEXT,
                difficulty TEXT,
                solution TEXT,
                description TEXT,
                starter_code TEXT,
                test_cases TEXT,
                constraints TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS admin_interviews (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                category TEXT,
                difficulty TEXT,
                questions_count INTEGER,
                student_id TEXT,
                scheduled_date TEXT,
                status TEXT,
                overall_score DOUBLE PRECISION,
                comm_score DOUBLE PRECISION,
                tech_score DOUBLE PRECISION,
                confidence_score DOUBLE PRECISION,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS admin_coding (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                duration INTEGER,
                language TEXT,
                difficulty TEXT,
                visible_tests INTEGER,
                hidden_tests INTEGER,
                status TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS super_admin (
                id VARCHAR(255) PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                avatar TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS platform_plans (
                id VARCHAR(255) PRIMARY KEY,
                plan_name TEXT,
                target_type TEXT,
                price DOUBLE PRECISION,
                duration TEXT,
                storage_limit TEXT,
                student_limit TEXT,
                ai_interviews TEXT,
                coding_tests TEXT,
                reports TEXT,
                support TEXT,
                trial_days INTEGER,
                gst_pct DOUBLE PRECISION,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS ai_configuration (
                id VARCHAR(255) PRIMARY KEY,
                gemini_api_key TEXT,
                openai_api_key TEXT,
                temperature DOUBLE PRECISION,
                max_tokens INTEGER,
                interview_prompt TEXT,
                resume_prompt TEXT,
                coding_prompt TEXT,
                speech_model TEXT,
                status TEXT,
                updated_at TEXT
            );

CREATE TABLE IF NOT EXISTS activity_logs (
                id VARCHAR(255) PRIMARY KEY,
                actor_id TEXT,
                actor_type TEXT,
                action TEXT,
                ip_address TEXT,
                details TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS support_tickets (
                id VARCHAR(255) PRIMARY KEY,
                organization_id TEXT,
                user_name TEXT,
                email TEXT,
                subject TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                assigned_to TEXT,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS platform_settings (
                id VARCHAR(255) PRIMARY KEY,
                platform_name TEXT,
                logo_url TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                timezone TEXT,
                maintenance_mode INTEGER,
                jwt_expiry_hours INTEGER,
                rate_limit_rpm INTEGER,
                updated_at TEXT
            );

CREATE TABLE IF NOT EXISTS invoice (
                id VARCHAR(255) PRIMARY KEY,
                payment_id TEXT,
                organization_id TEXT,
                invoice_number TEXT,
                amount DOUBLE PRECISION,
                gst DOUBLE PRECISION,
                created_at TEXT
            );

CREATE TABLE IF NOT EXISTS parsed_resumes (
            id VARCHAR(255) PRIMARY KEY,
            hash TEXT UNIQUE,
            raw_text TEXT,
            structured_data TEXT,
            ats_score INTEGER,
            missing_info TEXT,
            created_at TEXT
        );

CREATE TABLE IF NOT EXISTS support_conversations (
            id VARCHAR(255) PRIMARY KEY,
            organization_id TEXT,
            admin_id TEXT,
            status TEXT,
            priority TEXT,
            category TEXT,
            subject TEXT,
            created_at TEXT,
            updated_at TEXT
        );

CREATE TABLE IF NOT EXISTS support_messages (
            id VARCHAR(255) PRIMARY KEY,
            conversation_id TEXT,
            sender_role TEXT,
            sender_id TEXT,
            message TEXT,
            attachment TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT
        );

CREATE TABLE IF NOT EXISTS feedback (
            id VARCHAR(255) PRIMARY KEY,
            submitted_by TEXT,
            submitted_by_role TEXT,
            organization_id TEXT,
            subject TEXT,
            category TEXT,
            rating INTEGER DEFAULT 5,
            message TEXT,
            screenshot_url TEXT,
            status TEXT DEFAULT 'New',
            priority TEXT DEFAULT 'Medium',
            admin_notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );



-- ===========================================================================
-- PrepFly Intelligence Tables
-- ===========================================================================

CREATE TABLE IF NOT EXISTS candidate_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    target_company TEXT,
    target_role TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    target_interview_date TEXT,
    preparation_duration_days INTEGER DEFAULT 30,
    daily_study_hours DOUBLE PRECISION DEFAULT 2.0,
    preferred_study_days TEXT,
    current_skills TEXT,
    preferred_language TEXT DEFAULT 'python',
    preparation_goals TEXT,
    strengths TEXT,
    growth_areas TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    parent_skill_id TEXT,
    difficulty TEXT NOT NULL,
    description TEXT,
    learning_objectives TEXT,
    assessment_criteria TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_prerequisites (
    id BIGSERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL,
    prerequisite_skill_id VARCHAR(255) NOT NULL,
    is_mandatory INTEGER DEFAULT 1,
    UNIQUE(skill_id, prerequisite_skill_id)
);

CREATE TABLE IF NOT EXISTS role_skill_requirements (
    id BIGSERIAL PRIMARY KEY,
    role_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    importance_weight DOUBLE PRECISION DEFAULT 1.0,
    minimum_proficiency DOUBLE PRECISION DEFAULT 60.0,
    UNIQUE(role_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_skill_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    proficiency DOUBLE PRECISION DEFAULT 0.0,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    evidence_count INTEGER DEFAULT 0,
    last_assessed TEXT,
    historical_proficiency TEXT,
    learning_trend TEXT DEFAULT 'stable',
    strong_concepts TEXT,
    growth_concepts TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_evidence (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT,
    score DOUBLE PRECISION NOT NULL,
    weight DOUBLE PRECISION DEFAULT 1.0,
    demonstrated_concepts TEXT,
    missed_concepts TEXT,
    misconceptions TEXT,
    evidence_notes TEXT,
    rubric_version TEXT DEFAULT 'v1',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    assessment_type TEXT NOT NULL,
    target_role TEXT,
    status TEXT DEFAULT 'pending',
    score DOUBLE PRECISION,
    total_questions INTEGER DEFAULT 0,
    completed_questions INTEGER DEFAULT 0,
    summary TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id VARCHAR(255) PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    options TEXT,
    correct_answer TEXT,
    expected_concepts TEXT,
    rubric TEXT,
    order_index INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assessment_attempts (
    id VARCHAR(255) PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    candidate_answer TEXT,
    is_correct INTEGER,
    score DOUBLE PRECISION,
    evaluation_result TEXT,
    identified_concepts TEXT,
    missing_concepts TEXT,
    misconceptions TEXT,
    feedback TEXT,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmaps (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    target_role TEXT NOT NULL,
    target_company TEXT,
    current_version INTEGER DEFAULT 1,
    total_days INTEGER DEFAULT 30,
    total_activities INTEGER DEFAULT 0,
    completed_activities INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmap_versions (
    id VARCHAR(255) PRIMARY KEY,
    roadmap_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    change_reason TEXT NOT NULL,
    trigger_event TEXT,
    activities_snapshot TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmap_activities (
    id VARCHAR(255) PRIMARY KEY,
    roadmap_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    day_number INTEGER NOT NULL,
    order_in_day INTEGER DEFAULT 1,
    title TEXT NOT NULL,
    description TEXT,
    activity_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    estimated_minutes INTEGER DEFAULT 30,
    learning_objective TEXT,
    completion_criteria TEXT,
    priority DOUBLE PRECISION DEFAULT 1.0,
    due_date TEXT,
    status TEXT DEFAULT 'pending',
    is_pinned INTEGER DEFAULT 0,
    recommendation_reason TEXT,
    resource_payload TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_attempts (
    id VARCHAR(255) PRIMARY KEY,
    activity_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    time_spent_minutes INTEGER DEFAULT 0,
    performance_score DOUBLE PRECISION,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revision_schedules (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    interval_stage INTEGER DEFAULT 1,
    next_revision_date TEXT NOT NULL,
    last_reviewed_at TEXT,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


-- ============================================================================
-- Migration 002: Ava AI Interview Engine Schema & State Machine Architecture
-- ============================================================================

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS interview_state TEXT DEFAULT 'INITIALIZING';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS personality TEXT DEFAULT 'professional';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_map TEXT DEFAULT '{}';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS turn_count INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS interview_turns (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT,
    stage TEXT,
    candidate_response TEXT,
    intent TEXT DEFAULT 'ANSWER',
    decision TEXT DEFAULT 'NEXT_QUESTION',
    score DOUBLE PRECISION DEFAULT 0.0,
    accuracy_score INTEGER DEFAULT 0,
    evaluation_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interviewer_profiles (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    tone TEXT NOT NULL,
    formality TEXT NOT NULL,
    probing_intensity TEXT NOT NULL,
    encouragement_frequency TEXT NOT NULL,
    hint_policy TEXT NOT NULL,
    system_prompt_modifier TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS candidate_resume_claims (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    claim_type TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    provenance_section TEXT,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ===========================================================================
-- PrepFly Career Intelligence Database Migration (003_career_intelligence_schema.sql)
-- Improvement Tracking, Personalized Roadmaps, Job Preparation & Achievements
-- ===========================================================================

-- 1. Preparation Event Stream (Idempotent Event Ledger)
CREATE TABLE IF NOT EXISTS preparation_events (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    source_record_id TEXT,
    payload_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Ingested Job Target Profiles
CREATE TABLE IF NOT EXISTS job_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_title TEXT NOT NULL,
    company TEXT,
    raw_text TEXT NOT NULL,
    role_tier TEXT DEFAULT 'mid',
    target_date TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Structured Job Requirements
CREATE TABLE IF NOT EXISTS job_requirements (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    normalized_skill_id VARCHAR(255) NOT NULL,
    requirement_type TEXT NOT NULL,
    is_required INTEGER DEFAULT 1,
    importance_weight DOUBLE PRECISION DEFAULT 3.0,
    evidence_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Job Tailored Questions with Automated Quality Metrics
CREATE TABLE IF NOT EXISTS job_tailored_questions (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    requirement_id VARCHAR(255),
    question_text TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    quality_score DOUBLE PRECISION DEFAULT 8.0,
    evaluation_metrics TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Configurable Milestone and Achievement Definitions
CREATE TABLE IF NOT EXISTS achievement_definitions (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    trigger_event TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    badge_icon TEXT NOT NULL,
    reward_points INTEGER DEFAULT 50,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Server-Validated Unlocked User Achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    achievement_id VARCHAR(255) NOT NULL,
    triggering_event_id TEXT,
    unlocked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reward_claimed INTEGER DEFAULT 0,
    metadata_json TEXT,
    UNIQUE(user_id, achievement_id)
);

-- 7. Comparable Performance Snapshots
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    overall_readiness DOUBLE PRECISION NOT NULL,
    category_scores_json TEXT NOT NULL,
    sample_counts_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Fast Query Performance
CREATE INDEX IF NOT EXISTS idx_prep_events_user ON preparation_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_job_profiles_user ON job_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_job_reqs_job ON job_requirements(job_id);
CREATE INDEX IF NOT EXISTS idx_job_questions_job ON job_tailored_questions(job_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_user ON performance_snapshots(user_id, created_at);
