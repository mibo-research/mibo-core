#!/usr/bin/env python3
"""Protocol-locked technical retry policy for MIBO Core v1.0."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

RETRY_ELIGIBLE = {
    "submission_failure",
    "provider_error",
    "timeout",
    "authentication_interruption",
    "rate_limit",
    "incomplete_generation",
    "corrupted_capture",
    "temporary_interface_failure",
}


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    next_attempt: int | None
    due_at_utc: str | None
    delay_seconds: int | None
    reason: str


def decide_retry(*, attempt: int, failure_kind: str, failed_at: datetime, provider_retry_after_seconds: int | None = None, field_close: datetime | None = None) -> RetryDecision:
    if failed_at.tzinfo is None:
        raise ValueError("failed_at must be timezone-aware")
    if failure_kind not in RETRY_ELIGIBLE:
        return RetryDecision(False, None, None, None, "failure is not retry eligible")
    if attempt >= 3:
        return RetryDecision(False, None, None, None, "maximum of two retries already used")
    base_delay = 600 if attempt == 1 else 1800
    delay = max(base_delay, int(provider_retry_after_seconds or 0))
    due = failed_at.astimezone(timezone.utc) + timedelta(seconds=delay)
    if field_close is not None and due >= field_close.astimezone(timezone.utc):
        return RetryDecision(False, None, None, None, "next retry would fall outside the primary field window")
    return RetryDecision(True, attempt + 1, due.isoformat().replace("+00:00", "Z"), delay, "protocol-eligible technical retry")
