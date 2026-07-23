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


