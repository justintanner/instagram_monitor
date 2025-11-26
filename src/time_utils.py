"""Date and time utility functions for Instagram monitor."""

import calendar
import random
from datetime import datetime, timezone
from typing import List, Optional, Union

import pytz
from dateutil import relativedelta
from dateutil.parser import isoparse, parse


def display_time(seconds: int, granularity: int = 2) -> str:
    """Convert seconds to human readable format.

    Args:
        seconds: Number of seconds
        granularity: Number of units to show

    Returns:
        Human readable time string (e.g., "2 hours, 30 minutes")
    """
    intervals = (
        ("years", 31556952),
        ("months", 2629746),
        ("weeks", 604800),
        ("days", 86400),
        ("hours", 3600),
        ("minutes", 60),
        ("seconds", 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip("s")
                result.append(f"{value} {name}")
        return ", ".join(result[:granularity])
    else:
        return "0 seconds"


def calculate_timespan(
    timestamp1: Union[int, float, datetime, str],
    timestamp2: Union[int, float, datetime, str],
    show_weeks: bool = True,
    show_hours: bool = True,
    show_minutes: bool = True,
    show_seconds: bool = False,
    granularity: int = 3,
) -> str:
    """Calculate time span between two timestamps.

    Args:
        timestamp1: First timestamp (int, float, datetime, or ISO string)
        timestamp2: Second timestamp (int, float, datetime, or ISO string)
        show_weeks: Include weeks in output
        show_hours: Include hours in output
        show_minutes: Include minutes in output
        show_seconds: Include seconds in output
        granularity: Number of units to show

    Returns:
        Human readable time span string
    """
    result: List[str] = []
    intervals = ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]

    # Parse timestamp1
    dt1 = _parse_timestamp(timestamp1)
    if dt1 is None:
        return ""
    ts1 = int(round(dt1.timestamp()))

    # Parse timestamp2
    dt2 = _parse_timestamp(timestamp2)
    if dt2 is None:
        return ""
    ts2 = int(round(dt2.timestamp()))

    # Ensure dt1 > dt2
    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        days_total = date_diff.days

        if show_weeks:
            weeks = days_total // 7
            days = days_total % 7
        else:
            weeks = 0
            days = days_total

        hours = date_diff.hours if show_hours or ts_diff <= 86400 else 0
        minutes = date_diff.minutes if show_minutes or ts_diff <= 3600 else 0
        seconds = date_diff.seconds if show_seconds or ts_diff <= 60 else 0

        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip("s")
                result.append(f"{interval} {name}")

        return ", ".join(result[:granularity])
    else:
        return "0 seconds"


def _parse_timestamp(ts: Union[int, float, datetime, str]) -> Optional[datetime]:
    """Parse various timestamp formats to datetime.

    Args:
        ts: Timestamp as int, float, datetime, or ISO string

    Returns:
        Datetime object in UTC, or None if parsing fails
    """
    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return None

    if isinstance(ts, int):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, float):
        return datetime.fromtimestamp(int(round(ts)), tz=timezone.utc)
    elif isinstance(ts, datetime):
        if ts.tzinfo is None:
            return pytz.utc.localize(ts)
        else:
            return ts.astimezone(pytz.utc)
    return None


def convert_to_local_naive(dt: Optional[datetime], local_timezone: str) -> Optional[datetime]:
    """Convert datetime to local timezone and remove timezone info.

    Args:
        dt: Datetime to convert (can be None)
        local_timezone: Target timezone name

    Returns:
        Naive datetime in local timezone, or None
    """
    if dt is None:
        return None

    tz = pytz.timezone(local_timezone)

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    dt_local = dt.astimezone(tz)
    return dt_local.replace(tzinfo=None)


def now_local_naive(local_timezone: str) -> datetime:
    """Get current local time without timezone info.

    Args:
        local_timezone: Timezone name

    Returns:
        Current naive datetime in local timezone
    """
    return datetime.now(pytz.timezone(local_timezone)).replace(microsecond=0, tzinfo=None)


def now_local(local_timezone: str) -> datetime:
    """Get current local time with timezone info.

    Args:
        local_timezone: Timezone name

    Returns:
        Current aware datetime in local timezone
    """
    return datetime.now(pytz.timezone(local_timezone))


def convert_utc_datetime_to_tz_datetime(
    dt_utc: Optional[datetime], local_timezone: str
) -> Optional[datetime]:
    """Convert UTC datetime to specified timezone.

    Args:
        dt_utc: UTC datetime object
        local_timezone: Target timezone name

    Returns:
        Datetime in target timezone, or None
    """
    if not dt_utc:
        return None

    try:
        if dt_utc.tzinfo is None:
            dt_utc = pytz.utc.localize(dt_utc)
        return dt_utc.astimezone(pytz.timezone(local_timezone))
    except Exception:
        return None


def convert_utc_str_to_tz_datetime(dt_str: str, local_timezone: str) -> Optional[datetime]:
    """Convert UTC string to datetime in specified timezone.

    Args:
        dt_str: UTC datetime string
        local_timezone: Target timezone name

    Returns:
        Datetime in target timezone, or None
    """
    if not dt_str:
        return None

    try:
        dt = parse(dt_str)

        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)

        return dt.astimezone(pytz.timezone(local_timezone))

    except Exception:
        return None


def get_cur_ts(local_timezone: str, ts_str: str = "") -> str:
    """Get current date/time in human readable format.

    Args:
        local_timezone: Timezone name
        ts_str: Optional prefix string

    Returns:
        Formatted timestamp (e.g., "Sun 21 Apr 2024, 15:08:45")
    """
    now = now_local_naive(local_timezone)
    return f'{ts_str}{calendar.day_abbr[now.weekday()]}, {now.strftime("%d %b %Y, %H:%M:%S")}'


def print_cur_ts(local_timezone: str, horizontal_line: int = 113, ts_str: str = "") -> None:
    """Print current date/time with separator line.

    Args:
        local_timezone: Timezone name
        horizontal_line: Width of separator line
        ts_str: Optional prefix string
    """
    print(get_cur_ts(local_timezone, str(ts_str)))
    print("─" * horizontal_line)


def get_date_from_ts(ts: Union[int, float, datetime, str], local_timezone: str) -> str:
    """Format timestamp as long date string.

    Args:
        ts: Timestamp to format
        local_timezone: Timezone name

    Returns:
        Formatted date (e.g., "Sun 21 Apr 2024, 15:08:45")
    """
    tz = pytz.timezone(local_timezone)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)
    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)
    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)
    else:
        return ""

    return f'{calendar.day_abbr[ts_new.weekday()]} {ts_new.strftime("%d %b %Y, %H:%M:%S")}'


def get_short_date_from_ts(
    ts: Union[int, float, datetime, str],
    local_timezone: str,
    show_year: bool = False,
    show_hour: bool = True,
    show_weekday: bool = True,
    show_seconds: bool = False,
    always_show_year: bool = False,
) -> str:
    """Format timestamp as short date string.

    Args:
        ts: Timestamp to format
        local_timezone: Timezone name
        show_year: Show year if different from current
        show_hour: Include hour:minute
        show_weekday: Include weekday abbreviation
        show_seconds: Include seconds
        always_show_year: Always show year

    Returns:
        Formatted date (e.g., "Sun 21 Apr 15:08")
    """
    tz = pytz.timezone(local_timezone)
    if always_show_year:
        show_year = True

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)
    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)
    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M:%S" if show_seconds else " %H:%M"
    else:
        hour_strftime = ""

    weekday_str = f"{calendar.day_abbr[ts_new.weekday()]} " if show_weekday else ""

    if (show_year and ts_new.year != datetime.now(tz).year) or always_show_year:
        hour_prefix = "," if show_hour else ""
        return f'{weekday_str}{ts_new.strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}'
    else:
        return f'{weekday_str}{ts_new.strftime(f"%d %b{hour_strftime}")}'


def get_hour_min_from_ts(
    ts: Union[int, float, datetime, str], local_timezone: str, show_seconds: bool = False
) -> str:
    """Format timestamp as hour:minute string.

    Args:
        ts: Timestamp to format
        local_timezone: Timezone name
        show_seconds: Include seconds

    Returns:
        Formatted time (e.g., "15:08" or "15:08:32")
    """
    tz = pytz.timezone(local_timezone)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)
    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)
    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)
    else:
        return ""

    out_strf = "%H:%M:%S" if show_seconds else "%H:%M"
    return ts_new.strftime(out_strf)


def get_range_of_dates_from_tss(
    ts1: Union[int, float, datetime],
    ts2: Union[int, float, datetime],
    local_timezone: str,
    between_sep: str = " - ",
    short: bool = False,
) -> str:
    """Format range between two timestamps.

    Args:
        ts1: First timestamp
        ts2: Second timestamp
        local_timezone: Timezone name
        between_sep: Separator between dates
        short: Use short date format

    Returns:
        Formatted date range (e.g., "Sun 21 Apr 14:09 - 14:15")
    """
    tz = pytz.timezone(local_timezone)

    if isinstance(ts1, datetime):
        ts1_new = int(round(ts1.timestamp()))
    elif isinstance(ts1, int):
        ts1_new = ts1
    elif isinstance(ts1, float):
        ts1_new = int(round(ts1))
    else:
        return ""

    if isinstance(ts2, datetime):
        ts2_new = int(round(ts2.timestamp()))
    elif isinstance(ts2, int):
        ts2_new = ts2
    elif isinstance(ts2, float):
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new, tz).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new, tz).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new, local_timezone)}{between_sep}{get_hour_min_from_ts(ts2_new, local_timezone)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new, local_timezone)}{between_sep}{get_hour_min_from_ts(ts2_new, local_timezone, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new, local_timezone)}{between_sep}{get_short_date_from_ts(ts2_new, local_timezone)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new, local_timezone)}{between_sep}{get_date_from_ts(ts2_new, local_timezone)}"

    return str(out_str)


def randomize_number(number: int, diff_low: int, diff_high: int) -> int:
    """Randomize a number within a range.

    Args:
        number: Base number
        diff_low: Amount to subtract from minimum
        diff_high: Amount to add to maximum

    Returns:
        Random number in range [number - diff_low, number + diff_high]
    """
    if number > diff_low:
        return random.randint(number - diff_low, number + diff_high)
    else:
        return random.randint(number, number + diff_high)
