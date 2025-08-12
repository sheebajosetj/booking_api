"""
Utility helpers for timezone handling.
"""
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

def ensure_ist(dt: datetime) -> datetime:
    """Ensure datetime is IST or convert naive to IST"""
    if dt.tzinfo is None:
        return IST.localize(dt)
    if dt.tzinfo != IST:
        return dt.astimezone(IST)
    return dt

def to_utc(dt: datetime) -> datetime:
    """Convert IST to UTC (enforce IST input)"""
    ist_dt = ensure_ist(dt)
    return ist_dt.astimezone(UTC)

def from_utc(utc_dt: datetime, to_tz: str) -> datetime:
    """Convert UTC to any timezone"""
    if utc_dt.tzinfo != UTC:
        raise ValueError("Input must be UTC datetime")
    return utc_dt.astimezone(pytz.timezone(to_tz))

def format_datetime(dt: datetime) -> str:
    """Format datetime with timezone abbreviation"""
    return dt.strftime("%d %b %Y, %I:%M %p %Z")