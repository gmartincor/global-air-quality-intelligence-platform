import pytest
from datetime import datetime, timezone, timedelta

from src.common.utils.datetime_utils import (
    now_utc,
    now_local,
    to_utc,
    to_iso_string,
    from_iso_string,
    format_datetime,
    parse_datetime,
    add_hours,
    add_days,
    add_minutes,
    truncate_to_hour,
    truncate_to_day,
    get_date_range,
    is_within_range,
)


class TestDateTimeUtilities:
    def test_now_utc(self):
        result = now_utc()
        assert result.tzinfo == timezone.utc
        assert isinstance(result, datetime)

    def test_now_local(self):
        result = now_local()
        assert isinstance(result, datetime)

    def test_to_utc_naive(self):
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = to_utc(naive_dt)
        assert result.tzinfo == timezone.utc

    def test_to_utc_aware(self):
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc(aware_dt)
        assert result.tzinfo == timezone.utc

    def test_to_iso_string(self):
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = to_iso_string(dt)
        assert isinstance(result, str)
        assert "2024-01-01" in result

    def test_from_iso_string(self):
        iso_str = "2024-01-01T12:00:00+00:00"
        result = from_iso_string(iso_str)
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_format_datetime(self):
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = format_datetime(dt)
        assert result == "2024-01-01 12:30:45"

    def test_parse_datetime(self):
        date_str = "2024-01-01 12:30:45"
        result = parse_datetime(date_str)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_add_hours(self):
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = add_hours(dt, 3)
        assert result.hour == 15

    def test_add_days(self):
        dt = datetime(2024, 1, 1)
        result = add_days(dt, 5)
        assert result.day == 6

    def test_add_minutes(self):
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = add_minutes(dt, 30)
        assert result.minute == 30

    def test_truncate_to_hour(self):
        dt = datetime(2024, 1, 1, 12, 34, 56, 789)
        result = truncate_to_hour(dt)
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_truncate_to_day(self):
        dt = datetime(2024, 1, 1, 12, 34, 56, 789)
        result = truncate_to_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_get_date_range(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)
        result = get_date_range(start, end)
        assert len(result) == 5
        assert result[0] == start
        assert result[-1] == end

    def test_is_within_range_inclusive(self):
        dt = datetime(2024, 1, 2)
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        assert is_within_range(dt, start, end, inclusive=True)

    def test_is_within_range_exclusive(self):
        dt = datetime(2024, 1, 1)
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        assert not is_within_range(dt, start, end, inclusive=False)
