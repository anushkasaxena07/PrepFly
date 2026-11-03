import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.grading_service import (
    calculate_grade_info,
    compute_section_grades,
    award_badges,
    GRADE_TIERS
)

class TestGradingService(unittest.TestCase):
    """Unit tests for Candidate Grading, Dimension Scoring, and Badge Awards."""

    def test_calculate_grade_info_tiers(self):
        """Test accuracy of grade tiers across score boundaries."""
        tier_checks = [
            (98, "A+", "Strong Hire"),
            (95, "A+", "Strong Hire"),
            (92, "A", "Hire"),
            (87, "A-", "Hire with Reservations"),
            (82, "B+", "Hire with Reservations"),
            (76, "B", "Borderline"),
            (72, "B-", "Borderline"),
            (67, "C+", "No Hire"),
            (61, "C", "No Hire"),
            (52, "D", "Strong No Hire"),
            (35, "F", "Strong No Hire"),
            (0, "F", "Strong No Hire"),
        ]
        for score, expected_grade, expected_rec in tier_checks:
            with self.subTest(score=score):
                info = calculate_grade_info(score)
                self.assertEqual(info["grade"], expected_grade)
                self.assertEqual(info["rec"], expected_rec)

    def test_calculate_grade_info_out_of_bounds(self):
        """Scores outside [0, 100] should be clamped properly."""
        high = calculate_grade_info(150)
        self.assertEqual(high["score"], 100)
        self.assertEqual(high["grade"], "A+")

        low = calculate_grade_info(-25)
        self.assertEqual(low["score"], 0)
        self.assertEqual(low["grade"], "F")

    def test_compute_section_grades_defaults(self):
        """Empty feedback and raw_metrics should produce valid default scores for all 10 dimensions."""
        sections = compute_section_grades([], {})
        self.assertEqual(len(sections), 10)
        dimension_names = [s["name"] for s in sections]
        expected_names = [
            "Communication", "Technical Knowledge", "Problem Solving", "Confidence",
            "Behavioral Skills", "Resume Knowledge", "Project Explanation",
            "Leadership", "Grammar", "Vocabulary"
        ]
        for name in expected_names:
            self.assertIn(name, dimension_names)

        # Every section must contain valid score (0-100), grade, color and label
        for s in sections:
            self.assertGreaterEqual(s["score"], 0)
            self.assertLessEqual(s["score"], 100)
            self.assertIsInstance(s["grade"], str)
            self.assertIsInstance(s["label"], str)

    def test_compute_section_grades_with_metrics(self):
        """High clarity, optimal wpm, and high metric scores should reward the candidate."""
        feedbacks = [
            {
                "score": 9.0,
                "metrics": {
                    "communication": 9.5,
                    "technical_knowledge": 9.0,
                    "problem_solving": 9.2,
                    "confidence": 9.0,
                    "behavioral": 8.8,
                    "resume_understanding": 9.0,
                    "project_explanation": 9.1,
                    "leadership": 8.5
                }
            }
        ]
        raw_metrics = {
            "wpm": 140,         # Ideal wpm (110 - 165)
            "clarity": 95,       # High clarity (>= 80)
            "pause_count": 1,    # Low pauses (<= 2)
            "sentiment": "positive"
        }
        sections = compute_section_grades(feedbacks, raw_metrics)
        sec_map = {s["name"]: s["score"] for s in sections}

        self.assertGreaterEqual(sec_map["Communication"], 90)
        self.assertGreaterEqual(sec_map["Confidence"], 90)
        self.assertGreaterEqual(sec_map["Technical Knowledge"], 90)

    def test_award_badges_high_performer(self):
        """Top performer with multiple high dimension scores should earn specific excellence badges."""
        sections = [
            {"name": "Communication", "score": 92},
            {"name": "Technical Knowledge", "score": 95},
            {"name": "Problem Solving", "score": 90},
            {"name": "Leadership", "score": 85},
            {"name": "Project Explanation", "score": 88},
            {"name": "Behavioral Skills", "score": 86},
        ]
        badges = award_badges(overall_score=94.0, sections=sections)
        badge_names = [b["name"] for b in badges]

        self.assertIn("Excellent Communicator", badge_names)
        self.assertIn("Technical Expert", badge_names)
        self.assertIn("Problem Solver", badge_names)
        self.assertIn("Leadership Potential", badge_names)
        self.assertIn("Project Specialist", badge_names)
        self.assertIn("Behavioral Star", badge_names)
        self.assertIn("Quick Learner", badge_names)
        self.assertIn("Creative Thinker", badge_names)

    def test_award_badges_promising_candidate_fallback(self):
        """Candidate with decent score (>= 60) but no badge threshold hit gets 'Promising Candidate'."""
        sections = [
            {"name": "Communication", "score": 70},
            {"name": "Technical Knowledge", "score": 72},
            {"name": "Problem Solving", "score": 71},
            {"name": "Leadership", "score": 65},
        ]
        badges = award_badges(overall_score=71.0, sections=sections)
        self.assertEqual(len(badges), 1)
        self.assertEqual(badges[0]["name"], "Promising Candidate")

    def test_award_badges_failing_candidate_no_trophies(self):
        """Candidate scoring below 60 should receive zero badges."""
        sections = [
            {"name": "Communication", "score": 45},
            {"name": "Technical Knowledge", "score": 40},
        ]
        badges = award_badges(overall_score=42.0, sections=sections)
        self.assertEqual(len(badges), 0)

if __name__ == "__main__":
    unittest.main()
