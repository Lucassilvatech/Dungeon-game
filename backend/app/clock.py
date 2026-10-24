"""Existing SQL columns store naive timestamps in UTC; never use local time."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
