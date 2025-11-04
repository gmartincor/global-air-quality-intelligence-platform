from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now()


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso_string(dt: datetime) -> str:
    return dt.isoformat()


def from_iso_string(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_datetime(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(date_str, fmt)


def add_hours(dt: datetime, hours: int) -> datetime:
    return dt + timedelta(hours=hours)


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


def truncate_to_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def truncate_to_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_date_range(
    start_date: datetime,
    end_date: datetime,
    step_days: int = 1,
) -> list[datetime]:
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current = add_days(current, step_days)
    return dates


def is_within_range(
    dt: datetime,
    start: datetime,
    end: datetime,
    inclusive: bool = True,
) -> bool:
    if inclusive:
        return start <= dt <= end
    return start < dt < end
