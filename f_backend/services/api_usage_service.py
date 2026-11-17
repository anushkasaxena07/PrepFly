"""
Per-User API Usage Tracking & Spending Limits Service for PrepFly.

Provides:
  1. Real-time cost calculation based on Google Gemini model rates.
  2. Per-user and per-feature API usage tracking (tokens, cost, timestamps).
  3. Monthly budget and spending limit enforcement (hard/soft caps).
  4. Integration with Supabase and DailyTokenBudgetTracker.
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("prepfly.api_usage")

# ── Gemini Pricing Schedule (USD per 1,000,000 tokens) ────────────────────────
# Official Gemini Developer API pricing:
# Flash models: $0.075 / 1M prompt tokens, $0.300 / 1M completion tokens (<= 128k context)
# Flash-Lite models: $0.0375 / 1M prompt tokens, $0.150 / 1M completion tokens
# Pro models: $1.25 / 1M prompt tokens, $5.00 / 1M completion tokens
MODEL_PRICING_PER_MILLION = {
    "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.300},
    "gemini-3.8-flash": {"prompt": 0.075, "completion": 0.300},
    "gemini-2.0-flash": {"prompt": 0.075, "completion": 0.300},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.300},
    "gemini-flash-latest": {"prompt": 0.075, "completion": 0.300},
    "gemini-3.5-flash-lite": {"prompt": 0.0375, "completion": 0.150},
    "gemini-1.5-flash-8b": {"prompt": 0.0375, "completion": 0.150},
    "gemini-2.5-pro": {"prompt": 1.250, "completion": 5.000},
    "gemini-1.5-pro": {"prompt": 1.250, "completion": 5.000},
}

DEFAULT_FLASH_RATE = {"prompt": 0.075, "completion": 0.300}
DEFAULT_MONTHLY_BUDGET_USD = 5.00
DEFAULT_DAILY_TOKEN_LIMIT = 120000


class SpendingLimitExceededError(RuntimeError):
    """Raised when a candidate's monthly API spending quota has been exhausted."""

    def __init__(self, user_id: str, current_spend: float, budget_limit: float):
        self.user_id = user_id
        self.current_spend = current_spend
        self.budget_limit = budget_limit
        self.status_code = 429
        super().__init__(
            f"Monthly AI spending limit reached (${current_spend:.4f} / ${budget_limit:.2f} USD). "
            "Please upgrade your plan or wait for the next billing cycle."
        )


def _get_supabase_client():
    try:
        from local_supabase import get_supabase_client
        return get_supabase_client()
    except Exception:
        try:
            import app
            return getattr(app, "supabase", None)
        except Exception:
            return None


def estimate_token_count(text: Any) -> int:
    """Estimates tokens conservatively at ~4 chars per token plus base structural overhead."""
    if not text:
        return 0
    s = str(text)
    return max(1, len(s) // 4)


def calculate_call_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Computes exact cost in USD for a given Gemini model call.
    Returns value rounded to 6 decimal places.
    """
    clean_model = (model_name or "").lower().replace("models/", "").strip()
    rate = MODEL_PRICING_PER_MILLION.get(clean_model, DEFAULT_FLASH_RATE)
    prompt_cost = (prompt_tokens / 1_000_000.0) * rate["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * rate["completion"]
    total = prompt_cost + completion_cost
    return round(total, 6)


class ApiUsageService:
    """Thread-safe service to record API usage and enforce student spending limits."""

    _lock = threading.Lock()
    _memory_usage_log: List[Dict[str, Any]] = []
    _memory_limits: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_or_create_spending_limit(
        cls,
        user_id: Optional[str],
        default_budget_usd: float = DEFAULT_MONTHLY_BUDGET_USD,
    ) -> Dict[str, Any]:
        """Fetches existing spending limit or creates a default record."""
        uid = str(user_id or "anonymous").strip()

        with cls._lock:
            if uid in cls._memory_limits:
                return dict(cls._memory_limits[uid])

        client = _get_supabase_client()
        if client is not None:
            try:
                res = client.table("user_api_spending_limits").select("*").eq("user_id", uid).execute()
                if res and res.data and len(res.data) > 0:
                    val = dict(res.data[0])
                    with cls._lock:
                        cls._memory_limits[uid] = val
                    return val
            except Exception as e:
                logger.debug("Failed to query user_api_spending_limits from DB: %s", e)

        # Fallback / memory cache
        with cls._lock:
            default_limit = {
                "user_id": uid,
                "monthly_budget_usd": float(default_budget_usd),
                "daily_token_limit": DEFAULT_DAILY_TOKEN_LIMIT,
                "is_hard_limit": True,
                "alert_threshold_pct": 80,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            cls._memory_limits[uid] = default_limit

        if client is not None:
            try:
                client.table("user_api_spending_limits").upsert(default_limit).execute()
            except Exception:
                pass

        return default_limit

        return default_limit

    @classmethod
    def set_user_spending_limit(
        cls,
        user_id: str,
        monthly_budget_usd: float,
        daily_token_limit: int = DEFAULT_DAILY_TOKEN_LIMIT,
        is_hard_limit: bool = True,
        alert_threshold_pct: int = 80,
    ) -> Dict[str, Any]:
        """Sets or updates a student's monthly spending limit."""
        uid = str(user_id or "anonymous").strip()
        record = {
            "user_id": uid,
            "monthly_budget_usd": float(monthly_budget_usd),
            "daily_token_limit": int(daily_token_limit),
            "is_hard_limit": bool(is_hard_limit),
            "alert_threshold_pct": int(alert_threshold_pct),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with cls._lock:
            cls._memory_limits[uid] = record

        client = _get_supabase_client()
        if client is not None:
            try:
                client.table("user_api_spending_limits").upsert(record).execute()
            except Exception as e:
                logger.warning("Failed to persist user spending limit for %s: %s", uid, e)

        return record

    @classmethod
    def get_user_monthly_spend(
        cls,
        user_id: Optional[str],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculates total spend and token counts for current calendar month."""
        uid = str(user_id or "anonymous").strip()
        ref_time = now or datetime.now(timezone.utc)
        month_start_iso = ref_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        client = _get_supabase_client()
        db_rows: List[Dict[str, Any]] = []

        if client is not None:
            try:
                res = (
                    client.table("user_api_usage")
                    .select("id,cost_usd,prompt_tokens,completion_tokens,total_tokens,feature,created_at")
                    .eq("user_id", uid)
                    .gte("created_at", month_start_iso)
                    .execute()
                )
                if res and res.data:
                    db_rows = res.data
            except Exception as e:
                logger.debug("Database read failed for user_api_usage: %s", e)

        # Merge with in-memory records
        total_calls = 0
        total_spend = 0.0
        total_prompt = 0
        total_completion = 0
        by_feature: Dict[str, float] = {}

        seen_ids = set()
        for row in db_rows:
            rid = str(row.get("id") or "")
            if rid:
                seen_ids.add(rid)
            cost = float(row.get("cost_usd") or 0.0)
            total_spend += cost
            total_prompt += int(row.get("prompt_tokens") or 0)
            total_completion += int(row.get("completion_tokens") or 0)
            total_calls += 1
            feat = row.get("feature", "unknown")
            by_feature[feat] = round(by_feature.get(feat, 0.0) + cost, 6)

        with cls._lock:
            for item in cls._memory_usage_log:
                if item.get("user_id") == uid and item.get("created_at", "") >= month_start_iso:
                    iid = item.get("id")
                    if iid and iid in seen_ids:
                        continue
                    if iid:
                        seen_ids.add(iid)
                    cost = float(item.get("cost_usd") or 0.0)
                    total_spend += cost
                    total_prompt += int(item.get("prompt_tokens") or 0)
                    total_completion += int(item.get("completion_tokens") or 0)
                    total_calls += 1
                    feat = item.get("feature", "unknown")
                    by_feature[feat] = round(by_feature.get(feat, 0.0) + cost, 6)

        return {
            "user_id": uid,
            "billing_month": month_start_iso[:7],
            "total_calls": total_calls,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "total_spend_usd": round(total_spend, 6),
            "by_feature_spend_usd": by_feature,
        }

    @classmethod
    def check_user_spending_limit(
        cls,
        user_id: Optional[str],
        estimated_cost_usd: float = 0.001,
        raise_on_exceeded: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates whether user has sufficient budget for the planned AI call.
        Returns (is_allowed: bool, details: dict).
        """
        uid = str(user_id or "anonymous").strip()
        limit_config = cls.get_or_create_spending_limit(uid)
        raw_b = limit_config.get("monthly_budget_usd")
        budget = float(raw_b) if raw_b is not None else DEFAULT_MONTHLY_BUDGET_USD
        is_hard = bool(limit_config.get("is_hard_limit", True))
        alert_pct = int(limit_config.get("alert_threshold_pct", 80))

        spend_info = cls.get_user_monthly_spend(uid)
        current_spend = spend_info["total_spend_usd"]
        projected_spend = round(current_spend + estimated_cost_usd, 6)
        pct_used = round((current_spend / budget) * 100.0, 1) if budget > 0 else 100.0

        details = {
            "user_id": uid,
            "current_spend_usd": current_spend,
            "budget_usd": budget,
            "pct_used": pct_used,
            "is_hard_limit": is_hard,
            "alert_triggered": pct_used >= alert_pct,
            "remaining_budget_usd": max(0.0, round(budget - current_spend, 6)),
        }

        if is_hard and projected_spend > budget:
            details["allowed"] = False
            details["reason"] = f"Budget of ${budget:.2f} exceeded (current spend: ${current_spend:.4f})"
            if raise_on_exceeded:
                raise SpendingLimitExceededError(uid, current_spend, budget)
            return False, details

        details["allowed"] = True
        return True, details

    @classmethod
    def record_api_usage(
        cls,
        user_id: Optional[str],
        feature: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Persists a single AI invocation record, calculates cost, and keeps daily tracking synced.
        """
        uid = str(user_id or "anonymous").strip()
        p_tok = max(0, int(prompt_tokens))
        c_tok = max(0, int(completion_tokens))
        tot_tok = p_tok + c_tok
        cost = calculate_call_cost(model, p_tok, c_tok)

        record = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "feature": str(feature or "general"),
            "model": str(model or "gemini-2.5-flash"),
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "total_tokens": tot_tok,
            "cost_usd": cost,
            "session_id": str(session_id) if session_id else None,
            "metadata": json.dumps(metadata or {}) if isinstance(metadata, dict) else str(metadata or "{}"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Keep in-memory ring buffer
        with cls._lock:
            cls._memory_usage_log.append(record)
            if len(cls._memory_usage_log) > 5000:
                cls._memory_usage_log = cls._memory_usage_log[-2500:]

        # Sync with DailyTokenBudgetTracker
        try:
            from services.interview_reliability_service import DailyTokenBudgetTracker
            DailyTokenBudgetTracker.record_usage(uid, prompt_chars=p_tok * 4, output_chars=c_tok * 4)
        except Exception:
            pass

        # Persist to database
        client = _get_supabase_client()
        if client is not None:
            try:
                client.table("user_api_usage").insert(record).execute()
            except Exception as e:
                logger.debug("Failed to insert record into user_api_usage: %s", e)

        return record

    @classmethod
    def reset_for_tests(cls) -> None:
        """Utility for test suite cleanup."""
        with cls._lock:
            cls._memory_usage_log.clear()
            cls._memory_limits.clear()
        client = _get_supabase_client()
        if client is not None:
            try:
                client.table("user_api_usage").delete().neq("id", "none").execute()
            except Exception:
                pass
            try:
                client.table("user_api_spending_limits").delete().neq("user_id", "none").execute()
            except Exception:
                pass
