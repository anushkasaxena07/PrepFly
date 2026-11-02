# PrepFly Unit Test Suite Package
import os

# Ensure safe dummy environment variables for CI / test runner imports if not provided by .env or host
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-for-unit-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_dummy_id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret_for_testing")
os.environ.setdefault("SMTP_EMAIL", "test@prepfly.io")
os.environ.setdefault("SMTP_PASSWORD", "test-smtp-password")
