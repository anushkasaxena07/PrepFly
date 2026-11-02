import unittest
import os
import sys
import hashlib
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.resume_service import (
    compute_text_hash,
    parse_resume_content,
    get_cached_resume,
    save_cached_resume
)

class TestResumeService(unittest.TestCase):
    """Unit tests for Resume hashing, parsing fallbacks, and caching mechanisms."""

    def test_compute_text_hash_consistency(self):
        """SHA256 text hash should be consistent, whitespace-trimmed, and 64 hex characters."""
        text = "  Senior Full Stack Software Engineer with React & Python.  "
        expected = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        self.assertEqual(compute_text_hash(text), expected)
        self.assertEqual(len(compute_text_hash(text)), 64)

    def test_parse_resume_content_empty_text(self):
        """Empty or blank resume text should return safe fallback dictionary with 50 ATS score."""
        result = parse_resume_content("", chat_model=None)
        self.assertEqual(result["ats_score"], 50)
        self.assertEqual(result["structured_data"], {})
        self.assertIn("Complete Resume Content", result["missing_info"])

        result_spaces = parse_resume_content("    \n\t   ", chat_model=None)
        self.assertEqual(result_spaces["ats_score"], 50)

    @patch("services.resume_service.get_supabase")
    def test_get_cached_resume_found(self, mock_get_supabase):
        """Should retrieve cached resume data when hash matches existing record."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
            "id": "res_123456789012",
            "hash": "sample_sha256_hash",
            "raw_text": "Sample resume content",
            "structured_data": '{"name": "Anushka Saxena", "skills": ["Python", "Flask"]}',
            "ats_score": 88,
            "missing_info": '["Certifications"]'
        }])

        cached = get_cached_resume("sample_sha256_hash")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["ats_score"], 88)
        self.assertEqual(cached["structured_data"]["name"], "Anushka Saxena")
        self.assertIn("Python", cached["structured_data"]["skills"])

    @patch("services.resume_service.get_supabase")
    def test_get_cached_resume_miss(self, mock_get_supabase):
        """Should return None when resume hash is not found in cache."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])

        cached = get_cached_resume("non_existent_hash")
        self.assertIsNone(cached)

if __name__ == "__main__":
    unittest.main()
