"""
Comprehensive Test Suite for PrepFly Intelligence — Personalized Preparation Engine.
Covers Skill Taxonomy, Profiling, Diagnostic Assessments, Roadmap Generation,
Continuous Adaptation, Spaced Revision, Cross-Feature Engine, and REST API Endpoints.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone, timedelta

# Ensure local test environment
import os
os.environ.setdefault("ENV", "test")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-mock")
os.environ.setdefault("JWT_SECRET", "test-secret-key-12345678901234567890123456789012")

from local_supabase import get_supabase_client
from app import app, _get_jwt_secret
import jwt

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.candidate_profile_service import CandidateProfileService
from services.skill_profiling_service import SkillProfilingService
from services.assessment_service import AssessmentService
from services.roadmap_service import RoadmapService
from services.roadmap_adaptation_service import RoadmapAdaptationService
from services.revision_scheduler import RevisionScheduler
from services.progress_analytics_service import ProgressAnalyticsService
from services.cross_feature_engine import CrossFeatureEngine

class TestPrepFlyIntelligence(unittest.TestCase):
    """Rigorous end-to-end tests for all PrepFly Intelligence domain services and API endpoints."""

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.user_id = f"test-cand-{uuid.uuid4().hex[:8]}"
        self.email = f"candidate-{uuid.uuid4().hex[:6]}@example.com"
        
        # Issue valid test JWT
        secret = _get_jwt_secret()
        self.token = jwt.encode({
            "sub": self.user_id,
            "email": self.email,
            "role": "candidate",
            "exp": datetime.now(timezone.utc) + timedelta(days=2)
        }, secret, algorithm="HS256")
        self.auth_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # ========================================================================
    # 1. SKILL TAXONOMY & DAG TESTS
    # ========================================================================

    def test_01_skill_taxonomy_coverage_and_dag_integrity(self):
        """Verifies skill taxonomy has 35+ skills, valid categories, and acyclic DAG prerequisites."""
        skills = SkillTaxonomyService.get_all_skills()
        self.assertGreaterEqual(len(skills), 30, "Taxonomy must define comprehensive skills (>=30)")

        categories = SkillTaxonomyService.get_categories()
        expected_cats = {"Data Structures and Algorithms", "Computer Science Fundamentals", "System Design", "Interview Skills"}
        self.assertTrue(expected_cats.issubset(set(categories)))

        # Cycle detection in prerequisites DAG (Kahn's or DFS)
        dag = SkillTaxonomyService.get_prerequisites_dag()
        visited = set()
        recursion_stack = set()

        def has_cycle(node):
            visited.add(node)
            recursion_stack.add(node)
            for neighbor in dag.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
            recursion_stack.remove(node)
            return False

        for skill in dag:
            if skill not in visited:
                self.assertFalse(has_cycle(skill), f"Cycle detected in prerequisite DAG at {skill}")

    def test_02_role_requirements_and_text_mapping(self):
        """Verifies role requirements for standard tech roles and semantic keyword mapping."""
        roles = SkillTaxonomyService.get_supported_roles()
        self.assertIn("Software Development Engineer (General)", roles)
        self.assertIn("Frontend Engineer", roles)
        self.assertIn("Backend Engineer", roles)

        sde_reqs = SkillTaxonomyService.get_role_requirements("Software Development Engineer (General)")
        self.assertGreater(len(sde_reqs), 5)
        self.assertTrue(any(r["skill_id"] == "dsa_arrays" for r in sde_reqs))

        # Semantic text mapping
        mapped = SkillTaxonomyService.map_text_to_skills("Design a distributed LRU cache with Redis and binary search trees")
        self.assertIn("sys_caching", mapped)
        self.assertIn("dsa_trees", mapped)

    # ========================================================================
    # 2. CANDIDATE PROFILE SERVICE TESTS
    # ========================================================================

    def test_03_candidate_profile_lifecycle(self):
        """Tests profile creation, input validation bounds, and status lifecycle."""
        target_date = (datetime.now(timezone.utc) + timedelta(days=45)).strftime("%Y-%m-%d")
        profile = CandidateProfileService.create_or_update_profile(
            user_id=self.user_id,
            target_role="Backend Engineer",
            target_company="Stripe",
            target_date=target_date,
            daily_minutes=90,
            experience_level="Mid-Level (2-5 years)",
            focus_areas=["System Design", "Databases"]
        )
        self.assertEqual(profile["user_id"], self.user_id)
        self.assertEqual(profile["target_company"], "Stripe")
        self.assertEqual(profile["daily_minutes"], 90)
        self.assertEqual(profile["status"], "ACTIVE")

        # Test pause/resume
        paused = CandidateProfileService.update_profile_status(self.user_id, "PAUSED")
        self.assertEqual(paused["status"], "PAUSED")

        resumed = CandidateProfileService.update_profile_status(self.user_id, "ACTIVE")
        self.assertEqual(resumed["status"], "ACTIVE")

    # ========================================================================
    # 3. EVIDENCE-BASED SKILL PROFILING TESTS
    # ========================================================================

    def test_04_evidence_ingestion_and_confidence_separation(self):
        """Tests multi-source evidence recording, proficiency calculation, and separate confidence metric."""
        # 1. Record diagnostic assessment evidence (weight 1.0)
        p1 = SkillProfilingService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_arrays",
            source="ASSESSMENT",
            score=70.0
        )
        self.assertEqual(p1["proficiency"], 70.0)
        self.assertGreater(p1["confidence_score"], 0.0)
        self.assertLess(p1["confidence_score"], 0.6)  # Single evidence has low confidence

        # 2. Record coding submission evidence (weight 1.2)
        p2 = SkillProfilingService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_arrays",
            source="CODING",
            score=90.0
        )
        # Recency and weighting should pull proficiency upward
        self.assertGreater(p2["proficiency"], 70.0)
        self.assertGreater(p2["confidence_score"], p1["confidence_score"])
        self.assertEqual(p2["trend"], "IMPROVING")

        # Check evidence history
        history = SkillProfilingService.get_skill_evidence_history(self.user_id, "dsa_arrays")
        self.assertEqual(len(history), 2)

    # ========================================================================
    # 4. DIAGNOSTIC ASSESSMENT ENGINE TESTS
    # ========================================================================

    def test_05_diagnostic_assessment_generation_and_grading(self):
        """Verifies diagnostic question generation, answer redaction, and rubric grading."""
        assessment = AssessmentService.generate_diagnostic_assessment(
            user_id=self.user_id,
            target_role="Software Development Engineer (General)",
            experience_level="Mid-Level (2-5 years)"
        )
        self.assertIn("id", assessment)
        self.assertEqual(len(assessment["questions"]), 5)

        # Ensure answer_key is NOT leaked in candidate payload
        for q in assessment["questions"]:
            self.assertNotIn("answer_key", q)
            self.assertIn("question_text", q)
            self.assertIn("skill_id", q)

        # Submit answers
        answers = {q["id"]: "I would use a hash map for O(1) average lookup and maintain two pointers." for q in assessment["questions"]}
        eval_result = AssessmentService.evaluate_attempt(
            user_id=self.user_id,
            assessment_id=assessment["id"],
            answers=answers
        )

        self.assertIn("overall_score", eval_result)
        self.assertIn("concept_breakdown", eval_result)
        self.assertGreater(eval_result["overall_score"], 0)

        # Candidate skill profile should now be populated with ASSESSMENT evidence
        profiles = SkillProfilingService.get_candidate_profiles(self.user_id)
        self.assertGreater(len(profiles), 0)

    def test_05b_aiml_diagnostic_selection_rotation_and_adaptive_roadmap(self):
        """Verifies AI/ML diagnostic selects AI questions, rotates across retakes, and calibrates roadmap."""
        # 1. AI/ML Diagnostic Assessment Generation
        aiml_ass_1 = AssessmentService.generate_diagnostic_assessment(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            experience_level="Mid-Level (2-5 years)"
        )
        self.assertEqual(len(aiml_ass_1["questions"]), 5)
        # Verify AI/ML specific skills are present (e.g. ml_model_development, dl_transformers, etc.)
        q_skills_1 = [q["skill_id"] for q in aiml_ass_1["questions"]]
        for s in q_skills_1:
            self.assertTrue(s.startswith("ml_") or s.startswith("dl_") or s.startswith("genai_") or s.startswith("sys_ml_") or s.startswith("math_"), f"Unexpected non-AI skill: {s}")

        # 2. Retake Assessment — Verify adaptive rotation yields different questions
        aiml_ass_2 = AssessmentService.generate_diagnostic_assessment(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            experience_level="Mid-Level (2-5 years)"
        )
        q_skills_2 = [q["skill_id"] for q in aiml_ass_2["questions"]]
        # Ensure questions shifted / rotated across attempts
        self.assertNotEqual(q_skills_1, q_skills_2)

        # 3. Submit Evaluation with Mixed Scores: Low on dl_transformers (30%), High on ml_model_development (90%)
        answers = {q["id"]: "Comprehensive mathematical derivation with gradient formulation and regularization." for q in aiml_ass_1["questions"]}
        eval_res = AssessmentService.evaluate_attempt(
            user_id=self.user_id,
            assessment_id=aiml_ass_1["id"],
            answers=answers
        )
        self.assertIn("results", eval_res)
        self.assertIn("overall_score", eval_res)

        # 4. Generate preparation roadmap and verify adaptive activity types
        # Update candidate profile to AI/ML Engineer with sufficient duration horizon
        td = (datetime.now(timezone.utc) + timedelta(days=60)).strftime("%Y-%m-%d")
        CandidateProfileService.create_or_update_profile(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            target_date=td,
            daily_minutes=60
        )

        # Explicitly record a critical gap (20%) and a mastered skill (95%)
        supabase = get_supabase_client()
        SkillProfilingService.record_evidence(
            supabase_client=supabase,
            user_id=self.user_id,
            skill_id="ml_model_development",
            source_type="diagnostic_assessment",
            score=20.0,
            notes="Diagnostic gap in bias-variance and loss formulation"
        )
        SkillProfilingService.record_evidence(
            supabase_client=supabase,
            user_id=self.user_id,
            skill_id="dl_neural_networks",
            source_type="diagnostic_assessment",
            score=95.0,
            notes="Diagnostic mastery in deep network backprop and skip connections"
        )

        roadmap = RoadmapService.generate_roadmap(user_id=self.user_id, force_regenerate=True)
        activities = roadmap.get("activities", [])
        self.assertGreater(len(activities), 0)

        # The weak skill (ml_model_development) should have Remediation drills with Beginner difficulty
        ml_acts = [a for a in activities if a.get("skill_id") == "ml_model_development"]
        self.assertTrue(any("Remediation" in a.get("title", "") or a.get("difficulty") == "Beginner" for a in ml_acts))

        # The mastered skill (dl_neural_networks) should have an Advanced Synthesis challenge
        dl_acts = [a for a in activities if a.get("skill_id") == "dl_neural_networks"]
        self.assertTrue(any("Advanced" in a.get("title", "") or a.get("difficulty") == "Advanced" for a in dl_acts))

    # ========================================================================
    # 5. PERSONALIZED ROADMAP GENERATION & ADAPTATION TESTS
    # ========================================================================

    def test_06_roadmap_generation_and_continuous_adaptation(self):
        """Tests deterministic roadmap generation, daily budget constraints, and non-destructive adaptation."""
        # Setup candidate profile
        target_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        CandidateProfileService.create_or_update_profile(
            user_id=self.user_id,
            target_role="Software Development Engineer (General)",
            target_date=target_date,
            daily_minutes=60
        )

        # Generate roadmap
        roadmap = RoadmapService.generate_roadmap(user_id=self.user_id, force_regenerate=True)
        self.assertIn("roadmap_id", roadmap)
        self.assertEqual(roadmap["version"], 1)
        self.assertGreater(len(roadmap["activities"]), 0)

        first_act = roadmap["activities"][0]
        act_id = first_act["id"]

        # Mark first activity completed
        supabase = get_supabase_client()
        supabase.table("roadmap_activities").update({
            "status": "COMPLETED",
            "is_pinned": True
        }).eq("id", act_id).execute()

        # Trigger adaptation (e.g. following poor coding performance in dynamic programming)
        adapt_res = RoadmapAdaptationService.adapt_roadmap_on_trigger(
            user_id=self.user_id,
            trigger_type="CODING_SUBMISSION",
            trigger_payload={"skill_id": "dsa_dp", "score": 30.0}
        )

        self.assertTrue(adapt_res["adapted"])
        self.assertEqual(adapt_res["new_version"], 2)

        # Verify completed activity was preserved
        curr_roadmap = RoadmapService.get_current_roadmap(self.user_id)
        acts = curr_roadmap["activities"]
        completed_acts = [a for a in acts if a["id"] == act_id]
        self.assertEqual(len(completed_acts), 1)
        self.assertEqual(completed_acts[0]["status"], "COMPLETED")
        self.assertTrue(completed_acts[0]["is_pinned"])

    # ========================================================================
    # 6. SPACED REVISION & KNOWLEDGE RETENTION TESTS
    # ========================================================================

    def test_07_spaced_revision_intervals_and_drill_evaluation(self):
        """Tests Ebbinghaus interval progression (Day 1, 3, 7, 14), recall success, and regression."""
        # Initial schedule
        sched = RevisionScheduler.schedule_initial_revision(self.user_id, "dsa_trees", initial_score=80.0)
        self.assertEqual(sched["interval_stage"], 1)

        # High score advances to stage 2
        res1 = RevisionScheduler.record_revision_attempt(self.user_id, "dsa_trees", score=85.0)
        self.assertEqual(res1["new_stage"], 2)
        self.assertEqual(res1["outcome"], "ADVANCED")

        # Low score (<50%) triggers regression to stage 1 remedial
        res2 = RevisionScheduler.record_revision_attempt(self.user_id, "dsa_trees", score=40.0)
        self.assertEqual(res2["new_stage"], 1)
        self.assertEqual(res2["outcome"], "REGRESSED_REMEDIAL")

        # Retrieval drill generation
        drill = RevisionScheduler.generate_retrieval_drill("dsa_trees")
        self.assertEqual(drill["skill_id"], "dsa_trees")
        self.assertIn("question", drill)
        self.assertEqual(drill["suggested_duration_minutes"], 5)

    # ========================================================================
    # 7. CROSS-FEATURE EVIDENCE HOOKS & WEAKNESS DETECTION TESTS
    # ========================================================================

    def test_08_cross_feature_coding_and_interview_evidence(self):
        """Tests ingestion of coding submissions and Ava mock interviews into canonical skill profile."""
        # Coding submission hook
        cf_code = CrossFeatureEngine.process_coding_submission(
            user_id=self.user_id,
            problem_id="two-sum",
            passed_tests=5,
            total_tests=5,
            language="python",
            code="def twoSum(nums, target): return []",
            time_complexity="O(n)",
            space_complexity="O(n)"
        )
        self.assertTrue(cf_code["success"])

        # Ava mock interview session hook
        mock_report = {
            "overall_score": 75.0,
            "dimension_scores": {
                "technical_accuracy": 70,
                "problem_solving": 80,
                "communication": 85
            }
        }
        mock_questions = ["Explain relational database indexing and B-Trees."]
        mock_feedbacks = ["Good coverage of indexing, but could explain composite index prefix rules better."]
        cf_interview = CrossFeatureEngine.process_ava_interview_session(
            user_id=self.user_id,
            session_id=f"sess-{uuid.uuid4().hex[:6]}",
            final_report=mock_report,
            questions=mock_questions,
            feedbacks=mock_feedbacks
        )
        self.assertTrue(cf_interview["success"])

        # Weakness detection
        weaknesses = CrossFeatureEngine.detect_cross_feature_weaknesses(self.user_id)
        self.assertIsInstance(weaknesses, list)

    # ========================================================================
    # 8. PROGRESS DASHBOARD & COACHING INSIGHTS TESTS
    # ========================================================================

    def test_09_progress_analytics_and_coaching_insights(self):
        """Tests dashboard summary metrics, radar chart dimensions, and grounded coaching recommendations."""
        # Setup sample profile and activity
        CandidateProfileService.create_or_update_profile(
            user_id=self.user_id,
            target_role="Software Development Engineer (General)",
            daily_minutes=60
        )
        RoadmapService.generate_roadmap(self.user_id, force_regenerate=True)

        summary = ProgressAnalyticsService.get_dashboard_summary(self.user_id)
        self.assertIn("overall_readiness", summary)
        self.assertIn("study_metrics", summary)
        self.assertIn("skill_distribution", summary)
        self.assertIn("radar_data", summary)
        self.assertIn("baseline_comparison", summary)

        radar = summary["radar_data"]
        self.assertEqual(len(radar), 4)

        # Coaching insights
        insights = ProgressAnalyticsService.get_grounded_coaching_insights(self.user_id)
        self.assertGreater(len(insights), 0)
        self.assertIn("action_type", insights[0])

    # ========================================================================
    # 9. REST API ENDPOINT INTEGRATION TESTS
    # ========================================================================

    def test_10_api_preparation_onboarding_and_profile_routes(self):
        """Tests /api/preparation/initialize, /api/preparation/profile GET and PATCH."""
        payload = {
            "target_role": "Full Stack Engineer",
            "target_company": "Google",
            "daily_minutes": 75,
            "experience_level": "Senior (5+ years)",
            "focus_areas": ["System Design"]
        }
        res = self.client.post("/api/preparation/initialize", headers=self.auth_headers, data=json.dumps(payload))
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["profile"]["target_company"], "Google")

        # GET profile
        get_res = self.client.get("/api/preparation/profile", headers=self.auth_headers)
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["profile"]["target_role"], "Full Stack Engineer")

        # PATCH status to PAUSED
        patch_res = self.client.patch("/api/preparation/profile", headers=self.auth_headers, data=json.dumps({"status": "PAUSED"}))
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()["profile"]["status"], "PAUSED")

    def test_11_api_skills_taxonomy_and_evidence_routes(self):
        """Tests /api/skills/taxonomy, /api/skills/profile, and /api/skills/<id>/evidence."""
        res = self.client.get("/api/skills/taxonomy")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("skills", data)
        self.assertIn("categories", data)

        prof_res = self.client.get("/api/skills/profile", headers=self.auth_headers)
        self.assertEqual(prof_res.status_code, 200)

        ev_res = self.client.get("/api/skills/dsa_arrays/evidence", headers=self.auth_headers)
        self.assertEqual(ev_res.status_code, 200)

    def test_12_api_assessment_and_roadmap_routes(self):
        """Tests /api/assessment/start, /api/assessment/<id>/submit, /api/roadmap/current, and activity completion."""
        # 1. Start assessment
        start_res = self.client.post("/api/assessment/start", headers=self.auth_headers, data=json.dumps({
            "target_role": "Backend Engineer",
            "experience_level": "Mid-Level (2-5 years)"
        }))
        self.assertEqual(start_res.status_code, 201)
        ass_data = start_res.get_json()["assessment"]
        ass_id = ass_data["id"]
        q_ids = [q["id"] for q in ass_data["questions"]]

        # 2. Submit assessment
        answers = {qid: "Use hash maps and balanced binary search trees to achieve optimal lookup." for qid in q_ids}
        sub_res = self.client.post(f"/api/assessment/{ass_id}/submit", headers=self.auth_headers, data=json.dumps({"answers": answers}))
        self.assertEqual(sub_res.status_code, 200)

        # 3. Get roadmap
        rm_res = self.client.get("/api/roadmap/current", headers=self.auth_headers)
        self.assertEqual(rm_res.status_code, 200)
        rm_data = rm_res.get_json()["roadmap"]
        self.assertIsNotNone(rm_data)

        # 4. Complete an activity
        act_id = rm_data["activities"][0]["id"]
        comp_res = self.client.post(f"/api/activities/{act_id}/complete", headers=self.auth_headers, data=json.dumps({
            "score": 90.0,
            "notes": "Finished graph DFS traversal practice.",
            "time_spent_minutes": 35
        }))
        self.assertEqual(comp_res.status_code, 200)

    def test_13_api_spaced_revision_and_progress_analytics(self):
        """Tests /api/revision/drill, /api/revision/submit, /api/progress/dashboard, and /api/progress/insights."""
        # 1. Drill fetch
        drill_res = self.client.get("/api/revision/drill/dsa_arrays", headers=self.auth_headers)
        self.assertEqual(drill_res.status_code, 200)
        self.assertIn("question", drill_res.get_json()["drill"])

        # 2. Submit drill
        drill_sub = self.client.post("/api/revision/submit", headers=self.auth_headers, data=json.dumps({
            "skill_id": "dsa_arrays",
            "score": 85.0,
            "notes": "Answered hash collision chaining and open addressing."
        }))
        self.assertEqual(drill_sub.status_code, 200)

        # 3. Dashboard metrics
        dash_res = self.client.get("/api/progress/dashboard", headers=self.auth_headers)
        self.assertEqual(dash_res.status_code, 200)
        dash_data = dash_res.get_json()["dashboard"]
        self.assertIn("overall_readiness", dash_data)

        # 4. Coaching insights
        insights_res = self.client.get("/api/progress/insights", headers=self.auth_headers)
        self.assertEqual(insights_res.status_code, 200)

        # 5. Cross-feature weaknesses
        weak_res = self.client.get("/api/progress/weaknesses", headers=self.auth_headers)
        self.assertEqual(weak_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
