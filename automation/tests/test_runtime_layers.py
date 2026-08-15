import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import provider_adapters as pa
import raw_archive as ra
import retry_policy as rp


class RetryPolicyTests(unittest.TestCase):
    def test_retry_delays_are_protocol_locked(self):
        t = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
        first = rp.decide_retry(attempt=1, failure_kind="timeout", failed_at=t)
        second = rp.decide_retry(attempt=2, failure_kind="rate_limit", failed_at=t)
        self.assertEqual(first.delay_seconds, 600)
        self.assertEqual(second.delay_seconds, 1800)
        self.assertEqual(first.next_attempt, 2)
        self.assertEqual(second.next_attempt, 3)

    def test_valid_content_outcome_is_not_a_retry_class(self):
        t = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
        d = rp.decide_retry(attempt=1, failure_kind="valid_refusal", failed_at=t)
        self.assertFalse(d.retry)

    def test_provider_retry_after_can_only_extend_wait(self):
        t = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
        d = rp.decide_retry(attempt=1, failure_kind="rate_limit", failed_at=t, provider_retry_after_seconds=1200)
        self.assertEqual(d.delay_seconds, 1200)


class AdapterPayloadTests(unittest.TestCase):
    @mock.patch.object(pa, "_post_json")
    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": "secret"})
    def test_openai_is_stateless_and_has_no_tools(self, post):
        post.return_value = (200, '{"status":"completed","model":"m","output":[],"usage":{}}', {"status":"completed","model":"m","output":[],"usage":{}}, 10, "s", "e")
        result = pa.call_openai(model_id="m", prompt="hello", profile={"adapter":"openai_responses"})
        self.assertFalse(result.request_payload["store"])
        self.assertNotIn("tools", result.request_payload)
        self.assertNotIn("instructions", result.request_payload)

    @mock.patch.object(pa, "_post_json")
    @mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret"})
    def test_anthropic_has_user_message_only(self, post):
        post.return_value = (200, '{"model":"m","content":[],"usage":{}}', {"model":"m","content":[],"usage":{}}, 10, "s", "e")
        result = pa.call_anthropic(model_id="m", prompt="hello", profile={"adapter":"anthropic_messages","max_output_tokens":512})
        self.assertEqual(result.request_payload["messages"], [{"role":"user","content":"hello"}])
        self.assertNotIn("tools", result.request_payload)
        self.assertNotIn("system", result.request_payload)

    @mock.patch.object(pa, "_post_json")
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "secret"})
    def test_gemini_has_no_tools_or_system_instruction(self, post):
        post.return_value = (200, '{"candidates":[],"usageMetadata":{}}', {"candidates":[],"usageMetadata":{}}, 10, "s", "e")
        result = pa.call_gemini(model_id="m", prompt="hello", profile={"adapter":"gemini_generate_content","max_output_tokens":512})
        self.assertNotIn("tools", result.request_payload)
        self.assertNotIn("systemInstruction", result.request_payload)


class RawArchiveTests(unittest.TestCase):
    def row(self):
        return {
            "attempt_id":"MIBO-SITE-JP01-W01-SL002-PLR-I03-EN-STD-R01-A01",
            "protocol_doi":"10.5281/zenodo.21936410", "wave_id":"MIBO-W01", "site_id":"JP01",
            "service_lineage_id":"MIBO-SL-002", "provider":"Anthropic", "line_id":"PLR",
            "query_form_id":"MIBO-I03-EN", "replication":1, "attempt":1,
            "configuration_freeze_sha256":"abc", "model_id":"synthetic-model"
        }

    def test_archive_is_append_only_and_hashes_raw_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meta = ra.archive_success(
                data_root=root, row=self.row(), request_payload={"model":"synthetic-model"},
                response_json={"content":[]}, raw_response_text='{"content":[]}', http_status=200,
                returned_model="synthetic-model", usage={}, started_at_utc="s", completed_at_utc="e", duration_ms=10,
            )
            self.assertEqual(len(meta["raw_file_sha256"]), 64)
            with self.assertRaises(FileExistsError):
                ra.archive_success(
                    data_root=root, row=self.row(), request_payload={"model":"synthetic-model"},
                    response_json={"content":[]}, raw_response_text='{"content":[]}', http_status=200,
                    returned_model="synthetic-model", usage={}, started_at_utc="s", completed_at_utc="e", duration_ms=10,
                )


if __name__ == "__main__":
    unittest.main()
