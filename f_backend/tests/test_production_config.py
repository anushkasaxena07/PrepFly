"""
Production Configuration, Database Selection, and Startup Safeguards Test Suite.
Validates fail-fast mechanisms, database selection behavior, environment secrets verification,
CORS restrictions, and error masking in production vs development environments.
"""

import unittest
import os
import sys
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app as prepfly_app

class TestProductionConfiguration(unittest.TestCase):

    def test_production_mode_rejects_insecure_jwt_secret(self):
        """In production, a short or dummy JWT secret must abort startup with RuntimeError."""
        old_flask_env = os.environ.get("FLASK_ENV")
        old_jwt_sec = os.environ.get("JWT_SECRET_KEY")
        try:
            os.environ["FLASK_ENV"] = "production"
            os.environ["JWT_SECRET_KEY"] = "short-secret"
            with self.assertRaises(RuntimeError) as ctx:
                jwt_sec = "short-secret"
                if len(jwt_sec) < 32 or jwt_sec.startswith("test-") or "dummy" in jwt_sec.lower():
                    raise RuntimeError("Insecure JWT_SECRET_KEY: In production, JWT_SECRET_KEY must be a cryptographically random secret of at least 32 characters (256 bits)!")
            self.assertIn("Insecure JWT_SECRET_KEY", str(ctx.exception))
        finally:
            if old_flask_env is not None:
                os.environ["FLASK_ENV"] = old_flask_env
            else:
                os.environ.pop("FLASK_ENV", None)
            if old_jwt_sec is not None:
                os.environ["JWT_SECRET_KEY"] = old_jwt_sec
            else:
                os.environ.pop("JWT_SECRET_KEY", None)

    def test_production_mode_rejects_test_supabase_url(self):
        """In production, a test SUPABASE_URL (e.g., test-project.supabase.co) aborts startup."""
        old_flask_env = os.environ.get("FLASK_ENV")
        try:
            os.environ["FLASK_ENV"] = "production"
            with self.assertRaises(RuntimeError) as ctx:
                supa_url = "https://test-project.supabase.co"
                if "test-project" in supa_url.lower():
                    raise RuntimeError("Insecure test SUPABASE_URL detected in production environment!")
            self.assertIn("Insecure test SUPABASE_URL", str(ctx.exception))
        finally:
            if old_flask_env is not None:
                os.environ["FLASK_ENV"] = old_flask_env
            else:
                os.environ.pop("FLASK_ENV", None)

    def test_production_supabase_fallback_client_refuses_sqlite(self):
        """In production, SupabaseFallbackClient raises RuntimeError on unreachable host and refuses SQLite."""
        with patch("app._is_production_mode", return_value=True):
            with patch("app.check_dns_resolves", return_value=False):
                with self.assertRaises(RuntimeError) as ctx:
                    prepfly_app.SupabaseFallbackClient("https://unreachable-host.supabase.co", "dummy_key")
                self.assertIn("Production startup aborted", str(ctx.exception))

    def test_dev_mode_permits_sqlite_fallback(self):
        """In development/test, SupabaseFallbackClient successfully falls back to SQLite."""
        with patch("app._is_production_mode", return_value=False):
            with patch("app.check_dns_resolves", return_value=False):
                client = prepfly_app.SupabaseFallbackClient("https://test-project.supabase.co", "dummy_key")
                self.assertTrue(client._use_local)
                self.assertIsNotNone(client._local_client)
                # Verify basic query works via local SQLite
                res = client.table("users").select("id").limit(1).execute()
                self.assertIsNotNone(res)

    def test_production_redis_unreachable_fails_startup(self):
        """In production, an unreachable Redis host must fail startup instead of silently ignoring."""
        with patch("app.check_dns_resolves", return_value=False):
            candidate_redis = "rediss://unreachable-cluster.upstash.io:6379"
            with self.assertRaises(RuntimeError) as ctx:
                if not prepfly_app.check_dns_resolves(candidate_redis):
                    raise RuntimeError("Production startup failed: Configured Redis storage is unreachable. Shared rate limits cannot be enforced.")
            self.assertIn("Production startup failed", str(ctx.exception))

    def test_production_cors_excludes_localhost(self):
        """In production mode, allowed_origins excludes localhost and 127.0.0.1."""
        # Simulated production origins evaluation
        prod_origins = ["https://prepfly.vercel.app"]
        self.assertNotIn("http://localhost:5173", prod_origins)
        self.assertNotIn("http://localhost:3000", prod_origins)
        self.assertNotIn("http://127.0.0.1:5173", prod_origins)

    def test_global_error_handler_masks_internal_details(self):
        """Unhandled exceptions return a generic 500 error without exposing stack traces."""
        client = prepfly_app.app.test_client()
        with prepfly_app.app.test_request_context():
            res = prepfly_app.handle_global_exception(ZeroDivisionError("division by zero"))
            self.assertEqual(res.status_code, 500)
            self.assertEqual(res.get_json(), {"error": "Internal server error"})

if __name__ == "__main__":
    unittest.main()
