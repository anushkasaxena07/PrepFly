"""
Track Strategy Service for Ava AI Interviewer.
Modular strategy controllers for each of the 8 tracks:
MAANG, DSA, Resume Deep-Dive, CS Fundamentals, Guesstimate, Logic Puzzles, System Design, HR.
Enforces deterministic scope boundaries, resume fact verification, and expected depth.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional

from interviewer_config.track_configs import (
    TRACK_MAANG,
    TRACK_DSA,
    TRACK_RESUME_DEEP_DIVE,
    TRACK_CS_FUNDAMENTALS,
    TRACK_GUESSTIMATE,
    TRACK_LOGIC_PUZZLES,
    TRACK_SYSTEM_DESIGN,
    TRACK_HR_BEHAVIORAL,
    TRACK_CONFIGS,
    resolve_track,
    validate_question_against_track
)


class TrackStrategyService:
    """Provides track-specific question blueprints, follow-up strategies, and scope validation."""

    @classmethod
    def generate_opening_question(
        cls,
        track_id: str,
        session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates the first substantive track question (Turn 2) conforming to track constraints.
        For Resume tracks, binds to a verified resume_fact_id.
        """
        track_cfg = resolve_track(track_id)
        candidate = session_context.get("candidate", {})
        c_name = candidate.get("first_name", "there")
        personality = session_context.get("personality", {})
        p_id = personality.get("id", "professional")
        facts = session_context.get("resume_facts", {}).get("facts", [])

        tid = track_cfg["track_id"]

        if tid == TRACK_MAANG:
            q_text = (
                "Let's dive into technical architecture and algorithmic trade-offs. "
                "Can you walk me through the highest-scale distributed component you have designed or worked on, "
                "focusing on the trade-offs you made between throughput, data consistency, and operational complexity?"
            )
            skill = "sys_microservices"
            fact_id = None

        elif tid == TRACK_DSA:
            q_text = (
                "Let's begin with an algorithmic problem: Given an array of integers representing stock prices on consecutive days, "
                "design an algorithm to find the maximum profit you can achieve by completing at most two transactions. "
                "Please talk through your brute force intuition first, and then how you'd optimize the time and space complexity."
            )
            skill = "dsa_dp"
            fact_id = None

        elif tid == TRACK_RESUME_DEEP_DIVE:
            # Bind to top project fact
            proj_fact = next((f for f in facts if f["category"] == "project"), None)
            if proj_fact:
                raw_proj = proj_fact.get("raw_entity", "your documented project")
                fact_id = proj_fact.get("fact_id")
                q_text = (
                    f"Looking at your resume, you highlighted your work on {raw_proj}. "
                    "Could you walk me through the technical architecture of this project, "
                    "specifically focusing on what you individually architected and implemented versus what the broader team owned?"
                )
            else:
                fact_id = None
                q_text = (
                    "Looking at your background, could you walk me through the technical architecture "
                    "of the most complex software system you have built, detailing your individual technical contributions?"
                )
            skill = "project_ownership"

        elif tid == TRACK_CS_FUNDAMENTALS:
            q_text = (
                "Let's explore operating systems and concurrency: What is the fundamental difference between "
                "a process and a thread from the perspective of virtual memory and CPU scheduling, "
                "and how does the OS handle context switching overhead between them?"
            )
            skill = "cs_os_processes"
            fact_id = None

        elif tid == TRACK_GUESSTIMATE:
            q_text = (
                "Let's work through a Fermi estimation problem: Estimate the total number of commercial airplanes "
                "currently in the sky over the United States at 2:00 PM on a typical Tuesday. "
                "Please outline your key assumptions, your breakdown methodology, and walk me through your math aloud."
            )
            skill = "structured_estimation"
            fact_id = None

        elif tid == TRACK_LOGIC_PUZZLES:
            q_text = (
                "Here is an analytical reasoning puzzle: You have 12 identical-looking gold coins, where exactly one coin "
                "is counterfeit and has a slightly different weight (you don't know whether it's heavier or lighter). "
                "You are provided with a two-pan balance scale. In at most 3 weighings, how can you identify the counterfeit coin and determine whether it is heavier or lighter?"
            )
            skill = "logical_deduction"
            fact_id = None

        elif tid == TRACK_SYSTEM_DESIGN:
            q_text = (
                "Let's design a high-throughput URL shortening service (like TinyURL or Bitly) that handles 100 million "
                "new URLs per month with a 100:1 read-to-write ratio. "
                "Let's start by clarifying functional and non-functional requirements and outlining your high-level architecture."
            )
            skill = "sys_caching"
            fact_id = None

        elif tid == TRACK_HR_BEHAVIORAL:
            q_text = (
                "Tell me about a time when a critical project you were responsible for fell significantly behind schedule "
                "or experienced an unexpected setback. Using the STAR framework, walk me through the Situation, "
                "the specific Task, the Actions you personally took to remediate it, and the final Result."
            )
            skill = "star_storytelling"
            fact_id = None

        else:
            q_text = "Tell me about your technical background and experience."
            skill = "general_tech"
            fact_id = None

        return {
            "track_id": tid,
            "question_text": q_text,
            "skill_id": skill,
            "resume_fact_id": fact_id,
            "difficulty": track_cfg.get("difficulty_start_level", "Intermediate"),
            "stage": "Track Main Questioning"
        }

    @classmethod
    def generate_followup_question(
        cls,
        track_id: str,
        previous_question: str,
        candidate_answer: str,
        session_context: Dict[str, Any],
        followup_index: int = 1
    ) -> Dict[str, Any]:
        """
        Generates an active-listening follow-up that quotes/paraphrases the candidate's words
        and probes depth, scale, failure modes, or edge cases.
        """
        track_cfg = resolve_track(track_id)
        personality = session_context.get("personality", {})
        p_id = personality.get("id", "professional")
        tid = track_cfg["track_id"]

        words = candidate_answer.strip().split()
        candidate_quote = " ".join(words[:6]) if len(words) >= 6 else candidate_answer.strip()

        # Dynamic Opener Variation (Rule R1 & R3: Prevent consecutive opener repetition)
        openers = [
            f"You mentioned \"{candidate_quote}...\".",
            f"Building on what you said about \"{candidate_quote}...\":",
            f"Taking what you highlighted regarding \"{candidate_quote}...\":",
            f"Looking closer at your point on \"{candidate_quote}...\":",
            f"When you described \"{candidate_quote}...\":"
        ]
        chosen_opener = openers[(max(1, followup_index) - 1) % len(openers)]

        if tid == TRACK_MAANG:
            followup_text = (
                f"{chosen_opener} "
                "Now suppose our traffic and data ingestion scale 100x overnight. "
                "Which component in that pipeline will degrade or bottleneck first, and how would you redesign the caching and partitioning layers to handle that load?"
            )
        elif tid == TRACK_DSA:
            followup_text = (
                f"{chosen_opener} "
                "What is the exact worst-case Big-O time and auxiliary space complexity? "
                "And how does your solution behave if all stock prices are strictly decreasing or if the array contains duplicate prices?"
            )
        elif tid == TRACK_RESUME_DEEP_DIVE:
            followup_text = (
                f"{chosen_opener} "
                "What was the single most difficult technical roadblock or production bug you encountered while building this, "
                "and what specific trade-off did you have to accept to resolve it?"
            )
        elif tid == TRACK_CS_FUNDAMENTALS:
            followup_text = (
                f"{chosen_opener} "
                "Can you walk me through what happens at the hardware and operating system level when a thread encounters a page fault? "
                "What steps does the OS kernel take to resolve it?"
            )
        elif tid == TRACK_GUESSTIMATE:
            followup_text = (
                f"{chosen_opener} "
                "How would your total estimate change if we accounted for peak versus off-peak hours? "
                "Walk me through a quick sanity check to verify whether that final number is plausible."
            )
        elif tid == TRACK_LOGIC_PUZZLES:
            followup_text = (
                f"{chosen_opener} "
                "What is the invariant that guarantees you can always distinguish whether the counterfeit is heavier or lighter? "
                "Can this approach generalize to N coins?"
            )
        elif tid == TRACK_SYSTEM_DESIGN:
            followup_text = (
                f"{chosen_opener} "
                "In production during an availability zone outage, how do you prevent split-brain key collisions in your ID generator, "
                "and what are your exact SLA latency guarantees under 99.99% availability?"
            )
        elif tid == TRACK_HR_BEHAVIORAL:
            followup_text = (
                f"{chosen_opener} "
                "Reflecting on that experience, what was the single biggest lesson you learned, "
                "and what would you do differently if faced with the exact same situation today?"
            )
        else:
            followup_text = f"{chosen_opener} Could you elaborate further on what you meant by \"{candidate_quote}...\"?"

        return {
            "track_id": tid,
            "question_text": followup_text,
            "is_followup": True,
            "followup_index": followup_index,
            "quoted_phrase": candidate_quote
        }

    @classmethod
    def validate_track_question(
        cls,
        question_text: str,
        track_id: str,
        resume_facts: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Strict Scope Guard (Rule R2):
        1. Validates against track forbidden topics and allowed topics.
        2. For Resume Deep-Dive, ensures cited entities exist in candidate's verified resume facts.
        """
        track_cfg = resolve_track(track_id)
        tid = track_cfg["track_id"]

        # 1. Base track scope validation
        is_valid, reason = validate_question_against_track(question_text, track_cfg)
        if not is_valid:
            return False, reason

        # 2. Strict Resume Grounding Guard
        if tid == TRACK_RESUME_DEEP_DIVE:
            # If question explicitly mentions a specific technology or framework,
            # ensure candidate actually claimed it in their resume facts!
            common_techs = ["kubernetes", "golang", "rust", "graphql", "solidity", "hadoop", "spark"]
            q_lower = question_text.lower()
            fact_texts = " ".join([f.get("raw_entity", "").lower() for f in (resume_facts or [])])

            for tech in common_techs:
                if tech in q_lower and tech not in fact_texts:
                    return False, f"Question hallucinated technology '{tech}' which does not exist in candidate's verified resume facts."

        return True, None

