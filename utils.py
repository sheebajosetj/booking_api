"""
Utility helpers for timezone handling.
"""
from datetime import datetime
import pytz


def to_utc(dt: datetime, tz_name: str) -> datetime:
    tz = pytz.timezone(tz_name)
    localized = tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)
    return localized.astimezone(pytz.UTC)


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(pytz.UTC).isoformat()


def from_utc_iso_to_tz(utc_iso_str: str, tz_name: str) -> str:
    utc = datetime.fromisoformat(utc_iso_str)
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=pytz.UTC)
    target = utc.astimezone(pytz.timezone(tz_name))
    return target.isoformat()