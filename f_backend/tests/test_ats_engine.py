import unittest
import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ats_engine import (
    normalize_skill,
    extract_skills,
    extract_years_experience,
    calculate_ats_match,
    SKILL_DICTIONARY,
    ALL_SKILLS,
)

class TestAtsEngine(unittest.TestCase):
    """Unit tests for deterministic ATS Skill & Matching Engine."""

    def test_normalize_skill_aliases(self):
        """Test canonical mapping of skill aliases and variations."""
        test_cases = [
            ("nodejs", "node.js"),
            ("k8s", "kubernetes"),
            ("postgres", "postgresql"),
            ("pg", "postgresql"),
            ("ts", "typescript"),
            ("js", "javascript"),
            ("py", "python"),
            ("golang", "go"),
            ("cpp", "c++"),
            ("ml", "machine learning"),
            ("dl", "deep learning"),
            ("nlp", "natural language processing"),
            ("llm", "large language model"),
        ]
        for raw, canonical in test_cases:
            with self.subTest(raw=raw, expected=canonical):
                self.assertEqual(normalize_skill(raw), canonical)

    def test_normalize_skill_unregistered(self):
        """Unknown skills should return lowercase stripped version."""
        self.assertEqual(normalize_skill("  CustomSkill_123  "), "customskill_123")

    def test_extract_skills_single_and_multiword(self):
        """Test skill extraction for single, hyphenated, and multi-word skills."""
        text = "Experienced with Python, React, Next.js, Machine Learning, and Docker in production."
        skills = extract_skills(text)
        self.assertIn("python", skills)
        self.assertIn("react", skills)
        self.assertIn("next.js", skills)
        self.assertIn("machine learning", skills)
        self.assertIn("docker", skills)

    def test_extract_skills_with_aliases(self):
        """Test alias recognition in plain text."""
        text = "Built services with k8s, nodejs, and postgres databases."
        skills = extract_skills(text)
        self.assertIn("kubernetes", skills)
        self.assertIn("node.js", skills)
        self.assertIn("postgresql", skills)

    def test_extract_skills_empty_text(self):
        """Empty or irrelevant text should return an empty list without exceptions."""
        self.assertEqual(extract_skills(""), [])
        self.assertEqual(extract_skills("The quick brown fox jumps over the lazy dog."), [])

    def test_extract_years_experience(self):
        """Test parsing of experience duration across various phrasing patterns."""
        cases = [
            ("Over 5 years of experience building web apps", 5),
            ("Requires 3+ years experience with React", 3),
            ("Candidate has exp of 8 years in backend engineering", 8),
            ("Minimum 2 yrs of hands-on Python experience", 2),
            ("Passionate junior coder with recent bootcamp training", None),
        ]
        for text, expected in cases:
            with self.subTest(text=text, expected=expected):
                self.assertEqual(extract_years_experience(text), expected)

    def test_extract_years_experience_takes_maximum(self):
        """If multiple experience mentions exist, it should choose the maximum."""
        text = "2 years of frontend and 5 years of backend engineering experience."
        self.assertEqual(extract_years_experience(text), 5)

    def test_calculate_ats_match_perfect_score(self):
        """Candidate with matching skills and sufficient experience should score high."""
        resume = """
        Summary: Experienced Senior Engineer.
        Experience: 6 years of experience building scalable microservices.
        Education: B.Tech Computer Science.
        Skills: Python, Docker, Kubernetes, AWS, PostgreSQL, Redis, System Design.
        Projects: Built high-throughput payment processor.
        """
        jd = """
        Job Description:
        Looking for a Senior Backend Engineer with 5 years experience in Python, Docker, Kubernetes, PostgreSQL.
        """
        result = calculate_ats_match(resume, jd)
        self.assertIn("ats_score", result)
        self.assertGreaterEqual(result["ats_score"], 80)
        self.assertIn(result["overall_grade"], ["A", "S"])
        self.assertEqual(result["skill_match_pct"], 100)
        self.assertEqual(result["experience_pct"], 100)
        self.assertEqual(len(result["missing_skills"]), 0)

    def test_calculate_ats_match_empty_inputs(self):
        """ATS calculation should gracefully handle empty text without zero-division error."""
        result = calculate_ats_match("", "")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["ats_score"], 20)  # experience_pct=100 * 0.20
        self.assertEqual(result["skill_match_pct"], 0)
        self.assertEqual(result["matched_skills"], [])

    def test_calculate_ats_match_missing_skills_and_bonus(self):
        """Check accurate separation of matched, missing, and bonus skills."""
        resume = "Skills: Python, Flask, MongoDB, Docker."
        jd = "Requirements: Python, Flask, PostgreSQL, Kubernetes, Redis."
        result = calculate_ats_match(resume, jd)

        self.assertIn("python", result["matched_skills"])
        self.assertIn("flask", result["matched_skills"])
        self.assertIn("postgresql", result["missing_skills"])
        self.assertIn("kubernetes", result["missing_skills"])
        self.assertIn("mongodb", result["bonus_skills"])

    def test_ats_section_scores_bounded(self):
        """Section scores (experience, skills, format, projects) must stay between 1 and 10."""
        resume = "Some general text with education and skills and projects."
        jd = "Python engineer needed."
        result = calculate_ats_match(resume, jd)
        for section, score in result["section_scores"].items():
            self.assertGreaterEqual(score, 1, f"{section} score below minimum")
            self.assertLessEqual(score, 10, f"{section} score exceeded maximum")

if __name__ == "__main__":
    unittest.main()
