"""Synthetic-only Priority payload, headers, admission and private recovery tests."""
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timezone
from email.message import Message
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import core_v2_admission as admission
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_preflight as preflight
import core_v2_priority as priority
import core_v2_runner as runner
import provider_adapters as adapters
import test_core_lineage_admission as fixtures

runtime = fixtures.module("synthetic_priority", HERE.parent / "runtime/prepare-core-v2-priority.py")


class PriorityTransportTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"adapter": "gemini_generate_content", "api_key_env": "GEMINI_API_KEY",
            "max_output_tokens": 4096, "temperature": None, "top_p": None, "service_tier": "priority"}

    def result(self, tier="priority", **kwargs):
        body = {"modelVersion": "gemini-3.8-flash", "candidates": [{"content": {"parts": [{"text": "synthetic ack"}]}}]}
        headers = Message()
        if tier is not None: headers["X-Gemini-Service-Tier"] = tier
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200; response.headers = headers
        response.read.return_value = json.dumps(body).encode()
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key"}, clear=True), mock.patch.object(adapters, "urlopen", return_value=response) as urlopen:
            result = adapters.call_gemini(model_id="gemini-3.8-flash", prompt=preflight.SYNTHETIC_PROMPT,
                profile=kwargs.get("profile", self.profile))
        return result, urlopen

    def test_priority_is_top_level_and_actual_header_is_retained_without_credentials(self):
        result, opened = self.result()
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["service_tier"], "priority")
        self.assertEqual(payload["generationConfig"], {"maxOutputTokens": 4096})
        self.assertEqual(result.response_metadata["service_tier_actual"], "priority")
        self.assertEqual(result.response_metadata["response_headers"], {"x-gemini-service-tier": "priority"})
        self.assertEqual(result.response_metadata["provider_model_version"], "gemini-3.8-flash")
        self.assertNotIn("synthetic-key", json.dumps(result.request_payload))
        self.assertNotIn("synthetic-key", json.dumps(result.response_metadata))

    def test_provider_downgrade_or_missing_header_does_not_trigger_another_call(self):
        for tier in ("standard", None):
            with self.subTest(tier=tier):
                result, opened = self.result(tier)
                self.assertEqual(opened.call_count, 1)
                self.assertEqual(result.response_metadata["service_tier_actual"], tier)
                self.assertEqual(result.response_metadata["provider_downgraded_to_standard"], tier == "standard")
                self.assertEqual(result.response_metadata["service_tier_unknown"], tier is None)

    def test_legacy_standard_request_has_unchanged_payload_and_no_priority_metadata(self):
        profile = {key: value for key, value in self.profile.items() if key != "service_tier"}
        result, opened = self.result(profile=profile)
        self.assertNotIn("service_tier", json.loads(opened.call_args.args[0].data))
        self.assertIsNone(result.response_metadata)

    def test_http_error_keeps_retry_after_and_tier_without_secret_headers(self):
        headers = Message(); headers["X-Gemini-Service-Tier"] = "priority"; headers["Retry-After"] = "901"
        headers["Set-Cookie"] = "synthetic-secret"
        error = HTTPError("https://synthetic.invalid", 503, "synthetic", headers, io.BytesIO(b'{"error":"busy"}'))
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key"}), mock.patch.object(adapters, "urlopen", side_effect=error):
            with self.assertRaises(adapters.AdapterFailure) as caught:
                adapters.call_gemini(model_id="gemini-3.8-flash", prompt="synthetic", profile=self.profile)
        self.assertEqual(caught.exception.retry_after_seconds, 901)
        self.assertEqual(caught.exception.response_metadata["service_tier_requested"], "priority")
        self.assertNotIn("synthetic-secret", json.dumps(caught.exception.response_metadata))

    def test_wrong_model_version_is_retained_and_not_retryable(self):
        raw = json.dumps({"modelVersion": "gemini-another", "candidates": []})
        def post(**kwargs):
            kwargs["response_metadata"].update(service_tier_actual="priority", response_headers={"x-gemini-service-tier": "priority"})
            return 200, raw, json.loads(raw), 1, "2026-10-06T02:40:00Z", "2026-10-06T02:40:01Z"
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key"}), mock.patch.object(adapters, "_post_json", side_effect=post):
            with self.assertRaises(adapters.AdapterFailure) as caught:
                adapters.call_gemini(model_id="gemini-3.8-flash", prompt="synthetic", profile=self.profile)
        self.assertEqual(caught.exception.kind, "request_environment_mismatch")
        self.assertFalse(caught.exception.retry_eligible)
        self.assertEqual(caught.exception.response_body, raw)


class PriorityAdmissionTests(unittest.TestCase):
    def fixture(self, root, stack):
        old, old_report, old_dest, _ = fixtures.AdmissionTests().fixture(root, stack)
        source = fixtures.scoped.SOURCE
        stack.enter_context(mock.patch.object(runtime, "SOURCE", source))
        stack.enter_context(mock.patch.object(runtime.scoped, "now", return_value="2026-10-06T02:45:00Z"))
        protocol = json.loads((HERE / "config/core_v2_protocol.v2.0.3.json").read_text())
        protocol.update(protocol_registration_id="synthetic-priority-registration", prospectively_registered_at_utc="2026-10-06T00:05:00Z")
        path = root / "priority-protocol.json"; path.write_text(json.dumps(protocol))
        target = root / "priority-readiness"
        runtime.prepare_configuration(protocol_path=path, old_protocol_path=old.protocol,
            old_freeze_path=old.freeze, old_report_path=old_report, out_dir=target)
        return old, old_report, target

    def result(self, tier="priority", **kwargs):
        model = kwargs["model_id"]
        return adapters.AdapterResult("Google", model, model,
            {"contents": [{"parts": [{"text": preflight.SYNTHETIC_PROMPT}]}], "service_tier": "priority"},
            {"modelVersion": model}, json.dumps({"modelVersion": model}), 200,
            "2026-10-06T02:40:00Z", "2026-10-06T02:40:01Z", 1, None, "synthetic ack",
            {"service_tier_requested": "priority", "service_tier_actual": tier,
             "response_headers": {"x-gemini-service-tier": tier} if tier else {},
             "provider_model_version": model})

    def call(self, target, stamp="2026-10-06T02:47:00Z"):
        return runtime.probe(out_dir=target, current=runner.parse_aware_utc(stamp))

    def authorize(self, target, built):
        auth = json.loads((target / "bundle/core_v2_execution_authorization.template.json").read_text())
        auth.update(authorized=True, authorized_at_utc="2026-10-06T02:50:00Z", operations_lead="synthetic-human",
            terms_review_complete=True, authorize_confirmatory_api_core=True,
            prospective_agent_amendment_reviewed=True, late_activation_with_original_windows_approved=True,
            prospective_lineage_admission_amendment_reviewed=True, prospective_gemini_priority_amendment_reviewed=True)
        path = target / "authorization.json"; path.write_text(json.dumps(auth))
        return path

    def check(self, target, built, auth, root):
        return executor.preflight(protocol_path=target / "bundle" / built["protocol_file"],
            freeze_path=target / "bundle" / built["provider_freeze_file"],
            manifest_path=target / "bundle" / built["manifest_file"], authorization_path=auth,
            data_root=root / "data", now=runner.parse_aware_utc("2026-10-06T02:51:00Z"))

    def test_one_priority_probe_keeps_queries_profiles_and_original_evidence(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            old, old_report, target = self.fixture(Path(d), stack)
            originals = {path: path.read_bytes() for path in old_report.parent.rglob("*") if path.is_file()}
            old_freeze = old.freeze.read_bytes()
            called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); built = result["bundle"]
            self.assertEqual(called.call_count, 1)
            self.assertEqual(called.call_args.kwargs["provider"], "Google")
            self.assertEqual(called.call_args.kwargs["prompt"], preflight.SYNTHETIC_PROMPT)
            self.assertEqual(called.call_args.kwargs["profile"]["service_tier"], "priority")
            self.assertEqual(built["initial_request_count"], 1120)
            self.assertEqual(built["admitted_request_count"], 280)
            template = json.loads((result["out_dir"] / "bundle/core_v2_execution_authorization.template.json").read_text())
            self.assertFalse(template["authorized"])
            self.assertFalse(template["prospective_gemini_priority_amendment_reviewed"])
            for path, value in originals.items(): self.assertEqual(path.read_bytes(), value)
            self.assertEqual(old.freeze.read_bytes(), old_freeze)
            again = self.call(target)
            self.assertFalse(again["provider_called"])
            self.assertEqual(called.call_count, 1)
            auth = self.authorize(result["out_dir"], built)
            rows, _, _, _, _ = self.check(result["out_dir"], built, auth, Path(d))
            self.assertEqual(len(rows), 280)
            self.assertEqual({r["service_lineage_id"] for r in rows}, set(admission.GOOGLE_SCOPE))

    def test_standard_or_unknown_priority_never_admits(self):
        for tier in ("standard", None):
            with self.subTest(tier=tier), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, target = self.fixture(Path(d), stack)
                called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=lambda **kw: self.result(tier, **kw)))
                with self.assertRaisesRegex(ValueError, "not confirmed"): self.call(target)
                with self.assertRaisesRegex(ValueError, "not retryable"): self.call(target, "2026-10-06T03:47:00Z")
                self.assertEqual(called.call_count, 1)
                self.assertFalse(list((target / "priority-recovery-block").glob("probe-*/bundle")))

    def test_failed_priority_block_waits_honors_provider_and_is_capped(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target = self.fixture(Path(d), stack)
            called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=adapters.AdapterFailure(
                "provider_error", "synthetic", 503, 901, "synthetic-private-key")))
            for stamp in ("2026-10-06T02:47:00Z", "2026-10-06T03:02:01Z", "2026-10-06T03:32:01Z"):
                with mock.patch.object(runtime.scoped, "now", return_value=stamp), self.assertRaises(ValueError): self.call(target, stamp)
                if stamp.startswith("2026-10-06T02"):
                    with self.assertRaisesRegex(ValueError, "wait has not elapsed"): self.call(target, "2026-10-06T02:57:00Z")
                    self.assertEqual(called.call_count, 1)
            self.assertEqual(called.call_count, 3)
            with self.assertRaisesRegex(ValueError, "exhausted"): self.call(target, "2026-10-06T04:32:01Z")
            for path in (target / "priority-recovery-block").glob("probe-*/RESULT.json"):
                self.assertNotIn("synthetic-private-key", path.read_text())

    def test_older_google_attempt_blocks_but_other_lineages_can_continue(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target = self.fixture(Path(d), stack)
            stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); built = result["bundle"]; location = result["out_dir"]
            auth = self.authorize(location, built)
            previous = archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", "2.0.2") / "api_raw"
            previous.mkdir(parents=True)
            (previous / "three-provider.json").write_text(json.dumps({"service_lineage_id": "MIBO-SL-001"}))
            self.check(location, built, auth, Path(d))
            (previous / "google.json").write_text(json.dumps({"service_lineage_id": "MIBO-SL-003"}))
            with self.assertRaisesRegex(ValueError, "no Priority queue replay"): self.check(location, built, auth, Path(d))

    def test_old_version_cannot_silently_take_priority(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            old, _, target = self.fixture(Path(d), stack)
            freeze = json.loads(old.freeze.read_text()); freeze["core_api"]["MIBO-SL-003"]["request_profile"]["service_tier"] = "priority"
            old.freeze.write_text(json.dumps(freeze))
            protocol, _ = runner.load_protocol(old.protocol)
            with self.assertRaisesRegex(ValueError, "prospective protocol version"):
                runner.load_freeze(old.freeze, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")

    def test_priority_requires_specific_human_review_and_google_only_scope(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target = self.fixture(Path(d), stack)
            stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); built = result["bundle"]; location = result["out_dir"]
            auth = self.authorize(location, built)
            value = json.loads(auth.read_text())
            value["prospective_gemini_priority_amendment_reviewed"] = False
            auth.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Priority human amendment"):
                self.check(location, built, auth, Path(d))
            report = location / "PRIORITY_READINESS_REPORT.json"
            protocol, protocol_sha = runner.load_protocol(location / "bundle" / built["protocol_file"])
            freeze, freeze_sha = runner.load_freeze(location / "bundle" / built["provider_freeze_file"],
                protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")
            with self.assertRaisesRegex(ValueError, "only Google"):
                priority.validate_report(report, protocol=protocol, protocol_sha=protocol_sha,
                    freeze=freeze, freeze_sha=freeze_sha, admitted=admission.INITIAL_SCOPE)

    def test_downgraded_confirmatory_response_is_saved_without_retry(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target = self.fixture(Path(d), stack)
            stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); built = result["bundle"]; location = result["out_dir"]
            auth = self.authorize(location, built)
            checked = self.check(location, built, auth, Path(d))
            row = next(r for r in checked[0] if r["window_id"] == "STD")
            stack.enter_context(mock.patch.object(executor, "preflight", return_value=([row], *checked[1:])))
            clock = stack.enter_context(mock.patch.object(executor, "datetime", wraps=datetime))
            clock.now.return_value = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
            stack.enter_context(mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}))
            called = stack.enter_context(mock.patch.object(executor, "call_provider", side_effect=lambda **kw: self.result("standard", **kw)))
            summary = executor.execute(protocol_path=location / "bundle" / built["protocol_file"],
                freeze_path=location / "bundle" / built["provider_freeze_file"], manifest_path=location / "bundle" / built["manifest_file"],
                authorization_path=auth, data_root=Path(d) / "data")
            self.assertEqual(summary["valid"], 1); self.assertEqual(summary["retries_scheduled"], 0)
            self.assertEqual(called.call_count, 1)
            raw = archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", "2.0.3") / "api_raw" / (row["attempt_id"] + ".json")
            saved = json.loads(raw.read_text())
            self.assertEqual(saved["request_payload"]["service_tier"], "priority")
            self.assertEqual(saved["response_metadata"]["service_tier_actual"], "standard")


if __name__ == "__main__": unittest.main()
