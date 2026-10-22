"""
hours.py – Working hours checker for Tehran shops.
Parses the weekly_hours JSON and determines if a shop is currently open.
"""

import json
from datetime import datetime, timezone, timedelta

# Tehran timezone: UTC+3:30
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)
TEHRAN_TZ = timezone(TEHRAN_OFFSET)

# Map Python weekday (0=Mon) to the dataset day keys
_WEEKDAY_MAP = {
    5: "sat",  # Saturday = weekday 5
    6: "sun",  # Sunday = weekday 6
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
}


def get_tehran_now() -> datetime:
    """Current datetime in Tehran timezone."""
    return datetime.now(TEHRAN_TZ)


def parse_weekly_hours(weekly_hours_str: str) -> dict | None:
    """Parse the weekly_hours JSON string from the database."""
    if not weekly_hours_str or weekly_hours_str == "null":
        return None
    try:
        return json.loads(weekly_hours_str)
    except (json.JSONDecodeError, TypeError):
        return None


def check_shop_status(weekly_hours_str: str) -> dict:
    """
    Check if a shop is currently open based on its weekly_hours.
    Returns:
        {
            "is_open": True/False/None,
            "status_text": "باز است" / "بسته است" / "نامشخص",
            "detail": "امروز ۱۰:۰۰ تا ۱۹:۰۰",
            "closes_in_minutes": 120,  # if currently open
            "opens_at": "10:00",  # if currently closed but opens today
        }
    """
    hours = parse_weekly_hours(weekly_hours_str)
    if not hours:
        return {
            "is_open": None,
            "status_text": "ساعت کاری نامشخص",
            "detail": "",
            "closes_in_minutes": None,
            "opens_at": None,
        }

    now = get_tehran_now()
    weekday = now.weekday()
    day_key = _WEEKDAY_MAP.get(weekday)

    if not day_key or day_key not in hours:
        return {
            "is_open": None,
            "status_text": "ساعت کاری نامشخص",
            "detail": "",
            "closes_in_minutes": None,
            "opens_at": None,
        }

    day_info = hours[day_key]
    status = day_info.get("status", "")

    if status == "closed":
        # Find next opening day
        return {
            "is_open": False,
            "status_text": "امروز تعطیل است",
            "detail": _get_next_open_day(hours, weekday),
            "closes_in_minutes": None,
            "opens_at": None,
        }

    if status == "unsupported":
        return {
            "is_open": None,
            "status_text": "ساعت کاری ثبت نشده",
            "detail": "",
            "closes_in_minutes": None,
            "opens_at": None,
        }

    # Status is "declared" – check shifts
    shifts = day_info.get("shifts", [])
    current_time = now.strftime("%H:%M:%S")

    for shift in shifts:
        start = shift.get("start_time", "00:00:00")
        end = shift.get("end_time", "00:00:00")

        # Skip invalid shifts (start == end == "00:00:00")
        if start == "00:00:00" and end == "00:00:00":
            continue

        if start <= current_time <= end:
            # Currently open
            closes_at = end[:5]
            # Calculate minutes until closing
            eh, em = int(end[:2]), int(end[3:5])
            nh, nm = now.hour, now.minute
            close_mins = (eh * 60 + em) - (nh * 60 + nm)

            status_text = "باز است"
            if 0 < close_mins <= 60:
                status_text = f"باز · {close_mins} دقیقه تا بسته‌شدن"

            return {
                "is_open": True,
                "status_text": status_text,
                "detail": f"امروز {_persian_time(start)} تا {_persian_time(end)}",
                "closes_in_minutes": close_mins if close_mins > 0 else None,
                "opens_at": None,
            }
        elif current_time < start:
            # Not yet open
            return {
                "is_open": False,
                "status_text": f"هنوز باز نشده · ساعت {_persian_time(start)} باز می‌شود",
                "detail": f"امروز {_persian_time(start)} تا {_persian_time(end)}",
                "closes_in_minutes": None,
                "opens_at": start[:5],
            }

    # Past all shifts today
    return {
        "is_open": False,
        "status_text": "بسته شده",
        "detail": _get_next_open_day(hours, weekday),
        "closes_in_minutes": None,
        "opens_at": None,
    }


def _persian_time(t: str) -> str:
    """Convert HH:MM:SS to a friendlier Persian format."""
    parts = t.split(":")
    return f"{parts[0]}:{parts[1]}"


_DAY_NAMES = {
    "sat": "شنبه",
    "sun": "یکشنبه",
    "mon": "دوشنبه",
    "tue": "سه‌شنبه",
    "wed": "چهارشنبه",
    "thu": "پنج‌شنبه",
    "fri": "جمعه",
}

_DAY_ORDER = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]


def _get_next_open_day(hours: dict, current_weekday: int) -> str:
    """Find the next open day and return a descriptive string."""
    current_day_key = _WEEKDAY_MAP.get(current_weekday)
    start_idx = _DAY_ORDER.index(current_day_key) if current_day_key in _DAY_ORDER else 0

    for i in range(1, 8):
        day_key = _DAY_ORDER[(start_idx + i) % 7]
        if day_key in hours:
            info = hours[day_key]
            if info.get("status") == "declared":
                shifts = info.get("shifts", [])
                for s in shifts:
                    if s.get("start_time") != "00:00:00" or s.get("end_time") != "00:00:00":
                        return f"{_DAY_NAMES.get(day_key, day_key)} {_persian_time(s['start_time'])} باز می‌شود"
    return ""


def get_today_hours_text(weekly_hours_str: str) -> str:
    """Get a short text of today's working hours."""
    result = check_shop_status(weekly_hours_str)
    if result["detail"]:
        return result["detail"]
    return result["status_text"]
