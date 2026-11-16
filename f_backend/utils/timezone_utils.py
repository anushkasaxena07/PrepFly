"""
PrepFly Timezone Utilities
Golden Rule 8: Dates are timezone-safe. Store the user's IANA timezone (e.g. Asia/Kolkata).
All 'today', 'tomorrow', 'missed yesterday' logic uses that timezone with date-only comparisons.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Tuple
import zoneinfo

DEFAULT_TIMEZONE = "Asia/Kolkata"

def get_timezone(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """Returns a valid ZoneInfo instance, falling back to Asia/Kolkata if invalid or omitted."""
    if not tz_name or not isinstance(tz_name, str):
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return zoneinfo.ZoneInfo(tz_name.strip())
    except Exception:
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)

def get_current_user_datetime(tz_name: Optional[str] = None) -> datetime:
    """Returns the current aware datetime in the user's timezone."""
    tz = get_timezone(tz_name)
    return datetime.now(tz)

def get_current_user_date(tz_name: Optional[str] = None) -> date:
    """Returns the current date in the user's timezone."""
    return get_current_user_datetime(tz_name).date()

def determine_plan_start_date(tz_name: Optional[str] = None, available_today_minutes: int = 0) -> Tuple[date, str]:
    """
    Section 8.2: If the user finishes onboarding before 6 PM local time (18:00)
    and has >= 20 min left today, the plan starts today; otherwise it starts tomorrow.
    Returns: (start_date, 'Today' | 'Tomorrow')
    """
    now = get_current_user_datetime(tz_name)
    today = now.date()
    
    if now.hour < 18 and available_today_minutes >= 20:
        return today, "Today"
    else:
        tomorrow = today + timedelta(days=1)
        return tomorrow, "Tomorrow"

def format_date_iso(d: date) -> str:
    """Formats date to ISO YYYY-MM-DD."""
    return d.isoformat()

def parse_date_iso(date_str: str) -> date:
    """Parses date from ISO YYYY-MM-DD."""
    return datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()

def calculate_days_between(start_d: date, end_d: date) -> int:
    """Returns (end_d - start_d).days."""
    return (end_d - start_d).days

def is_missed_day(target_date_str: str, tz_name: Optional[str] = None) -> bool:
    """Returns True only if target_date is strictly before user's current local date."""
    target_d = parse_date_iso(target_date_str)
    today_d = get_current_user_date(tz_name)
    return target_d < today_d

def get_relative_date_label(target_date_str: str, tz_name: Optional[str] = None) -> str:
    """Returns 'Today', 'Tomorrow', 'Yesterday', or ISO date string based on local calendar."""
    target_d = parse_date_iso(target_date_str)
    today_d = get_current_user_date(tz_name)
    diff = (target_d - today_d).days
    if diff == 0:
        return "Today"
    elif diff == 1:
        return "Tomorrow"
    elif diff == -1:
        return "Yesterday"
    elif diff > 1:
        return f"In {diff} days"
    else:
        return f"{abs(diff)} days ago"

