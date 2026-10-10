"""Synthetic checks for both HTTP Retry-After forms and registered windows."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provider_adapters import _retry_after
from retry_policy import decide_retry


class RetryAfterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 0, 0, 0, 500000, tzinfo=timezone.utc)

    def test_delta_seconds_and_malformed_headers(self):
        for value, expected in [("1200", 1200), ("0", 0), ("-1", 0),
                                ("not a date", None), ("", None)]:
            with self.subTest(value=value):
                self.assertEqual(_retry_after({"Retry-After": value}, now=self.now), expected)
        self.assertIsNone(_retry_after(None, now=self.now))

    def test_future_date_rounds_up_to_honor_minimum(self):
        delay = _retry_after({"Retry-After": "Tue, 03 Nov 2026 00:20:00 GMT"}, now=self.now)
        self.assertEqual(delay, 1200)
        decision = decide_retry(attempt=1, failure_kind="rate_limit", failed_at=self.now,
                                provider_retry_after_seconds=delay,
                                field_close=self.now + timedelta(hours=48))
        self.assertEqual(decision.delay_seconds, 1200)
        self.assertEqual(decision.due_at_utc, "2026-11-03T00:20:00.500000Z")

    def test_past_date_does_not_shorten_registered_wait(self):
        delay = _retry_after({"Retry-After": "Tue, 03 Nov 2026 00:00:00 GMT"}, now=self.now)
        self.assertEqual(delay, 0)
        decision = decide_retry(attempt=1, failure_kind="rate_limit", failed_at=self.now,
                                provider_retry_after_seconds=delay,
                                field_close=self.now + timedelta(hours=48))
        self.assertEqual(decision.delay_seconds, 600)

    def test_date_past_close_cannot_extend_registered_field_window(self):
        delay = _retry_after({"Retry-After": "Tue, 03 Nov 2026 02:00:00 GMT"}, now=self.now)
        decision = decide_retry(attempt=1, failure_kind="rate_limit", failed_at=self.now,
                                provider_retry_after_seconds=delay,
                                field_close=self.now + timedelta(hours=1))
        self.assertFalse(decision.retry)
        self.assertIsNone(decision.due_at_utc)


if __name__ == "__main__":
    unittest.main()
