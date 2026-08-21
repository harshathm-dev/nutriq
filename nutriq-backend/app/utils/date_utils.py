from datetime import datetime, date, time, timezone, timedelta
from typing import Tuple, Optional
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Kolkata"

def get_tz(tz_name: Optional[str] = None):
    try:
        return ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    except Exception:
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except Exception:
            return timezone(timedelta(hours=5, minutes=30))

def get_today_local(tz_name: str = DEFAULT_TIMEZONE) -> date:
    """
    Returns today's calendar date in the specified local timezone (Asia/Kolkata by default).
    """
    tz = get_tz(tz_name)
    return datetime.now(tz).date()

def get_date_bounds_utc(target_date: date, tz_name: str = DEFAULT_TIMEZONE) -> Tuple[datetime, datetime]:
    """
    Converts a local calendar date in the specified timezone into exact UTC start and end bounds.
    E.g. For 2026-08-20 in Asia/Kolkata (IST = UTC+05:30):
    start_utc = 2026-08-19 18:30:00 UTC
    end_utc = 2026-08-20 18:30:00 UTC
    """
    tz = get_tz(tz_name)
    start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = start_utc + timedelta(days=1)
    return start_utc, end_utc

def parse_datetime_with_tz(
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    fallback_dt: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> datetime:
    """
    Constructs a timezone-aware UTC datetime given a local date and time.
    If date_str is '2026-08-19' and time_str is '08:30', it is interpreted as
    2026-08-19 08:30:00 in Asia/Kolkata and converted to its equivalent UTC datetime.
    """
    tz = get_tz(tz_name)

    if date_str:
        try:
            clean_date = date_str.split("T")[0]
            d = date.fromisoformat(clean_date)
            t_hour, t_min, t_sec = 12, 0, 0
            if time_str:
                clean_time = time_str.replace(":", " ").split()
                if len(clean_time) >= 2:
                    t_hour = int(clean_time[0])
                    t_min = int(clean_time[1])
                    if len(clean_time) >= 3:
                        t_sec = int(clean_time[2])
            local_dt = datetime(d.year, d.month, d.day, t_hour, t_min, t_sec, tzinfo=tz)
            return local_dt.astimezone(timezone.utc)
        except Exception:
            pass

    if fallback_dt:
        if fallback_dt.tzinfo is None:
            # If naive datetime from SQLite or payload, assume UTC
            return fallback_dt.replace(tzinfo=timezone.utc)
        return fallback_dt.astimezone(timezone.utc)

    return datetime.now(timezone.utc)

def get_local_date(dt: Optional[datetime], tz_name: str = DEFAULT_TIMEZONE) -> date:
    """
    Converts a UTC datetime to a local calendar date in tz_name.
    """
    if not dt:
        return get_today_local(tz_name)
    tz = get_tz(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()

def format_local_time(dt: Optional[datetime], tz_name: str = DEFAULT_TIMEZONE) -> str:
    """
    Formats a UTC datetime into HH:MM local time string.
    """
    if not dt:
        return ""
    tz = get_tz(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%H:%M")
