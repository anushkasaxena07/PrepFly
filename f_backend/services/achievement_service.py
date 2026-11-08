"""
PrepFly Server-Validated Achievements and Milestones Engine
Evaluates milestone conditions idempotently upon preparation events, guarantees zero duplicate
rewards, enforces transactional unlocking, and computes candidate progress across all definitions.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json
import uuid

from local_supabase import get_supabase_client


class AchievementService:
    """Manages configurable milestone definitions, idempotent unlocking, and reward claims."""

    @classmethod
    def evaluate_achievements(
        cls,
        supabase,
        user_id: str,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates active achievement definitions against candidate performance.
        Atomically unlocks qualifying achievements that have not already been unlocked.
        """
        if not user_id:
            return []

        # 1. Fetch all active achievement definitions matching this trigger_event
        def_res = supabase.table("achievement_definitions").select("*").eq("is_active", 1).eq("trigger_event", event_type).execute()
        definitions = def_res.data if (def_res and def_res.data) else []

        if not definitions:
            return []

        # 2. Fetch already unlocked achievements for user to prevent duplicate evaluation
        unlocked_res = supabase.table("user_achievements").select("achievement_id").eq("user_id", user_id).execute()
        already_unlocked = {row["achievement_id"] for row in (unlocked_res.data or [])}

        newly_unlocked = []

        for ach_def in definitions:
            ach_id = ach_def["id"]
            if ach_id in already_unlocked:
                continue

            # Evaluate condition
            is_eligible, metadata = cls._check_eligibility(supabase, user_id, ach_def, payload)
            if is_eligible:
                now_iso = datetime.now(timezone.utc).isoformat()
                user_ach_id = f"uach_{uuid.uuid4().hex[:12]}"

                row = {
                    "id": user_ach_id,
                    "user_id": user_id,
                    "achievement_id": ach_id,
                    "triggering_event_id": event_id,
                    "unlocked_at": now_iso,
                    "reward_claimed": 0,
                    "metadata_json": json.dumps(metadata)
                }

                try:
                    supabase.table("user_achievements").insert(row).execute()
                    already_unlocked.add(ach_id)
                    newly_unlocked.append({
                        "id": ach_id,
                        "name": ach_def["name"],
                        "description": ach_def["description"],
                        "category": ach_def["category"],
                        "badge_icon": ach_def["badge_icon"],
                        "reward_points": ach_def.get("reward_points", 50),
                        "unlocked_at": now_iso
                    })
                except Exception as ex:
                    # Invariant: idempotent ignore if concurrent worker already inserted
                    print(f"[AchievementService] Idempotent skip for {ach_id}: {ex}")

        return newly_unlocked

    @classmethod
    def _check_eligibility(
        cls,
        supabase,
        user_id: str,
        ach_def: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluates whether the candidate meets the condition threshold."""
        cond_type = ach_def.get("condition_type", "count_gte")
        threshold = float(ach_def.get("threshold_value", 1.0))
        event_type = ach_def.get("trigger_event")

        # 1. Score Threshold (score_gte)
        if cond_type == "score_gte":
            current_score = float(payload.get("score") or payload.get("overall_score") or 0.0)
            if current_score >= threshold:
                return True, {"score": current_score, "threshold": threshold}
            return False, {}

        # 2. Delta Improvement Threshold (delta_gte)
        elif cond_type == "delta_gte":
            delta = float(payload.get("delta") or payload.get("overall_delta") or 0.0)
            if delta >= threshold:
                return True, {"delta": delta, "threshold": threshold}
            return False, {}

        # 3. Count Threshold (count_gte)
        elif cond_type == "count_gte":
            # Count past events of this type from preparation_events ledger
            res = supabase.table("preparation_events").select("id").eq("user_id", user_id).eq("event_type", event_type).execute()
            count = len(res.data) if (res and res.data) else 0
            if count >= threshold:
                return True, {"count": count, "threshold": threshold}
            return False, {}

        return False, {}

    @classmethod
    def get_user_achievements_with_progress(
        cls,
        user_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Returns all achievement definitions paired with user unlock status,
        unlocked timestamps, and current numeric progress towards each goal.
        """
        supabase = supabase_client or get_supabase_client()

        # Fetch definitions
        def_res = supabase.table("achievement_definitions").select("*").eq("is_active", 1).execute()
        definitions = def_res.data if (def_res and def_res.data) else []

        # Fetch unlocked records
        unlocked_res = supabase.table("user_achievements").select("*").eq("user_id", user_id).execute()
        unlocked_map = {row["achievement_id"]: row for row in (unlocked_res.data or [])}

        # Fetch event counts for progress calculation
        ev_res = supabase.table("preparation_events").select("event_type").eq("user_id", user_id).execute()
        event_counts = {}
        for ev in (ev_res.data or []):
            et = ev["event_type"]
            event_counts[et] = event_counts.get(et, 0) + 1

        total_earned_points = 0
        total_possible_points = 0
        unlocked_count = 0

        achievements_list = []

        for ach in definitions:
            ach_id = ach["id"]
            pts = int(ach.get("reward_points", 50))
            total_possible_points += pts

            is_unlocked = ach_id in unlocked_map
            unlocked_row = unlocked_map.get(ach_id)
            if is_unlocked:
                unlocked_count += 1
                total_earned_points += pts

            # Calculate progress percentage
            threshold = float(ach.get("threshold_value", 1.0))
            cond_type = ach.get("condition_type", "count_gte")
            ev_type = ach.get("trigger_event")

            if is_unlocked:
                current_val = threshold
                pct = 100.0
            elif cond_type == "count_gte":
                current_val = float(event_counts.get(ev_type, 0))
                pct = min(100.0, round((current_val / threshold) * 100.0, 1)) if threshold > 0 else 0.0
            else:
                current_val = 0.0
                pct = 0.0

            achievements_list.append({
                "id": ach_id,
                "name": ach["name"],
                "description": ach["description"],
                "category": ach["category"],
                "badge_icon": ach["badge_icon"],
                "reward_points": pts,
                "threshold_value": threshold,
                "condition_type": cond_type,
                "current_progress": current_val,
                "progress_percentage": pct,
                "is_unlocked": is_unlocked,
                "unlocked_at": unlocked_row.get("unlocked_at") if unlocked_row else None,
                "reward_claimed": bool(unlocked_row.get("reward_claimed", 0)) if unlocked_row else False
            })

        return {
            "total_unlocked": unlocked_count,
            "total_definitions": len(definitions),
            "total_earned_points": total_earned_points,
            "total_possible_points": total_possible_points,
            "achievements": achievements_list
        }

    @classmethod
    def claim_achievement_reward(
        cls,
        user_id: str,
        achievement_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """Marks achievement reward as claimed and awards points."""
        supabase = supabase_client or get_supabase_client()
        res = supabase.table("user_achievements").select("*").eq("user_id", user_id).eq("achievement_id", achievement_id).execute()
        if not res or not res.data:
            raise ValueError(f"Achievement not unlocked: {achievement_id}")

        user_ach = res.data[0]
        if user_ach.get("reward_claimed") == 1:
            return {"status": "ALREADY_CLAIMED", "points": 0}

        # Look up points
        def_res = supabase.table("achievement_definitions").select("reward_points").eq("id", achievement_id).execute()
        points = def_res.data[0].get("reward_points", 50) if (def_res and def_res.data) else 50

        supabase.table("user_achievements").update({"reward_claimed": 1}).eq("id", user_ach["id"]).execute()

        return {
            "status": "CLAIMED",
            "achievement_id": achievement_id,
            "points_awarded": points
        }



