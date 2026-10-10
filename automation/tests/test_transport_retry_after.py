"""Synthetic HTTP transport tests; no requests leave this process."""
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import format_datetime
import io
from pathlib import Path
import sys
import unittest
from unittest import mock
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import provider_adapters as adapters
import retry_policy


class RetryAfterTransportTests(unittest.TestCase):
    NOW = datetime(2026, 11, 3, 0, 0, 0, 250000, tzinfo=timezone.utc)

    def test_seconds_and_http_date_both_extend_registered_wait(self):
        for value in ("2400", "Tue, 03 Nov 2026 00:40:00 GMT"):
            with self.subTest(value=value):
                wait = adapters._retry_after({"Retry-After": value}, now=self.NOW)
                self.assertEqual(wait, 2400)
                for attempt in (1, 2):
                    decision = retry_policy.decide_retry(
                        attempt=attempt, failure_kind="rate_limit", failed_at=self.NOW,
                        provider_retry_after_seconds=wait,
                    )
                    self.assertEqual(decision.delay_seconds, 2400)
                self.assertFalse(retry_policy.decide_retry(
                    attempt=3, failure_kind="rate_limit", failed_at=self.NOW,
                    provider_retry_after_seconds=wait,
                ).retry)

    def test_provider_short_wait_never_reduces_protocol_minimum(self):
        for value in ("1", "Tue, 03 Nov 2026 00:00:01 GMT", "Mon, 02 Nov 2026 23:59:59 GMT"):
            with self.subTest(value=value):
                wait = adapters._retry_after({"Retry-After": value}, now=self.NOW)
                for attempt, minimum in ((1, 600), (2, 1800)):
                    decision = retry_policy.decide_retry(
                        attempt=attempt, failure_kind="provider_error", failed_at=self.NOW,
                        provider_retry_after_seconds=wait,
                    )
                    self.assertEqual(decision.delay_seconds, minimum)

    def test_fractional_receipt_time_is_rounded_up(self):
        value = format_datetime(self.NOW + timedelta(seconds=600), usegmt=True)
        self.assertEqual(adapters._retry_after({"Retry-After": value}, now=self.NOW), 600)

    def test_obsolete_http_dates_are_supported(self):
        for value in ("Tuesday, 03-Nov-26 00:40:00 GMT", "Tue Nov  3 00:40:00 2026"):
            with self.subTest(value=value):
                self.assertEqual(adapters._retry_after({"Retry-After": value}, now=self.NOW), 2400)

    def test_missing_and_invalid_headers_do_not_raise(self):
        for value in (None, "", "not a date", "1.5", "Tue, 32 Nov 2026 00:00:00 GMT"):
            with self.subTest(value=value):
                self.assertIsNone(adapters._retry_after({"Retry-After": value}, now=self.NOW))
        self.assertIsNone(adapters._retry_after(None, now=self.NOW))

    def test_http_error_records_date_wait_without_credential_headers(self):
        headers = Message()
        headers["Retry-After"] = "Tue, 03 Nov 2026 00:40:00 GMT"
        headers["Set-Cookie"] = "synthetic-secret"
        error = HTTPError("https://synthetic.invalid", 503, "busy", headers, io.BytesIO(b"{}"))
        with mock.patch.object(adapters, "urlopen", side_effect=error), \
                mock.patch.object(adapters, "datetime") as clock:
            clock.now.return_value = self.NOW
            with self.assertRaises(adapters.AdapterFailure) as caught:
                adapters._post_json(url="https://synthetic.invalid", headers={}, payload={}, timeout_s=1)
        self.assertEqual(caught.exception.retry_after_seconds, 2400)
        self.assertEqual(caught.exception.http_status, 503)
        self.assertNotIn("synthetic-secret", str(caught.exception))

    def test_long_date_wait_that_reaches_close_is_not_scheduled(self):
        close = self.NOW + timedelta(minutes=30)
        wait = adapters._retry_after({"Retry-After": "Tue, 03 Nov 2026 00:40:00 GMT"}, now=self.NOW)
        decision = retry_policy.decide_retry(attempt=1, failure_kind="provider_error",
            failed_at=self.NOW, provider_retry_after_seconds=wait, field_close=close)
        self.assertFalse(decision.retry)


if __name__ == "__main__":
    unittest.main()
