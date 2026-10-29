"""NEM settlement-time helpers.

AEMO aggregated files are timestamped in NEM time, which is Australian Eastern
Standard Time all year (UTC+10, no daylight saving). The timestamp is the end
of the interval. The interval ending at 00:00 belongs to the previous trading day.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta


def bucket_end_30min(ts: datetime) -> datetime:
    """Return the end of the 30-minute bucket that contains a 5-minute interval."""
    ts = ts.replace(second=0, microsecond=0)
    if ts.minute == 0:
        return ts
    if ts.minute <= 30:
        return ts.replace(minute=30)
    return ts.replace(minute=0) + timedelta(hours=1)


def trading_date(ts: datetime):
    if ts.time() == time(0, 0):
        return (ts - timedelta(days=1)).date()
    return ts.date()


def hour_of_day(ts: datetime) -> int:
    """Clock hour containing the interval, derived from the interval end."""
    return (ts - timedelta(seconds=1)).hour
