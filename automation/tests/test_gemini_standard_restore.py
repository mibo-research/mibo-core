"""Synthetic-only Standard restoration, retained history and Google isolation."""
from contextlib import ExitStack
from dataclasses import replace
from email.message import Message
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import core_v2_admission as admission
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_preflight as preflight
import core_v2_runner as runner
import core_v2_standard as standard
import provider_adapters as adapters
import test_core_lineage_admission as fixtures

runtime = fixtures.module("synthetic_standard_restore", HERE.parent / "runtime/prepare-core-v2-standard.py")


class StandardRestorationTests(unittest.TestCase):
    def fixture(self, root, stack, prior_wait=False):
        old, report, _, _ = fixtures.AdmissionTests().fixture(root, stack)
        stack.enter_context(mock.patch.object(runtime, "SOURCE", fixtures.scoped.SOURCE))
        stack.enter_context(mock.patch.object(runtime.scoped, "now", return_value="2026-10-06T03:54:00Z"))
        protocol = json.loads((HERE / "config/core_v2_protocol.v2.0.4.json").read_text())
        protocol.update(protocol_registration_id="synthetic-standard-registration",
                        prospectively_registered_at_utc="2026-10-06T03:38:00Z")
        path = root / "standard-protocol.json"; path.write_text(json.dumps(protocol))
        prior = root / "priority/probe-2"; prior.mkdir(parents=True)
        model = json.loads(old.freeze.read_text())["core_api"]["MIBO-SL-003"]["model_id"]
        smoke = prior / "SMOKE.json"
        smoke.write_text(json.dumps({"readiness_only": True, "pass": False,
            "http_status": 200, "requested_model": model, "returned_model": model,
            "request_payload": {"service_tier": "priority"}, "response": {"modelVersion": model}}))
        result = prior / "RESULT.json"
        result.write_text(json.dumps({"readiness_only": True, "pass": False, "http_status": 200,
            "failure_kind": "priority_tier_or_model_unconfirmed", "recorded_at_utc": "2026-10-06T03:20:00Z",
            "evidence_sha256": runner.sha256_file(smoke)}))
        failure = report.parent / next(c["file"] for c in json.loads(report.read_text())["synthetic_smoke_checks"] if not c["pass"])
        history = [smoke, result, failure]
        if prior_wait:
            wait = root / "prior-standard/RESULT.json"; wait.parent.mkdir()
            wait.write_text(json.dumps({"readiness_only": True, "pass": False, "http_status": 503,
                "failure_kind": "provider_error", "recorded_at_utc": "2026-10-06T03:54:00Z",
                "retry_after_seconds": 901}))
            history.append(wait)
        target = root / "standard-readiness"
        runtime.prepare_configuration(protocol_path=path, old_protocol_path=old.protocol,
            old_freeze_path=old.freeze, old_report_path=report, out_dir=target,
            history_files=history)
        stack.enter_context(mock.patch.object(runtime.scoped, "now", return_value="2026-10-06T03:55:02Z"))
        return old, report, target, prior

    def result(self, **kwargs):
        model = kwargs["model_id"]; profile = kwargs["profile"]
        generation = {dst: profile[src] for src, dst in
            (("max_output_tokens", "maxOutputTokens"), ("temperature", "temperature"), ("top_p", "topP"))
            if profile.get(src) is not None}
        payload = {"contents": [{"role": "user", "parts": [{"text": preflight.SYNTHETIC_PROMPT}]}],
                   "generationConfig": generation}
        return adapters.AdapterResult("Google", model, model, payload, {"modelVersion": model},
            json.dumps({"modelVersion": model}), 200, "2026-10-06T03:55:00Z", "2026-10-06T03:55:01Z",
            1, None, "synthetic ack", {"service_tier_requested": "standard_default",
            "service_tier_actual": "standard", "response_headers": {"x-gemini-service-tier": "standard"}})

    def call(self, target, stamp="2026-10-06T03:55:00Z"):
        return runtime.probe(out_dir=target, current=runner.parse_aware_utc(stamp))

    def authorize(self, target):
        auth = json.loads((target / "bundle/core_v2_execution_authorization.template.json").read_text())
        auth.update(authorized=True, authorized_at_utc="2026-10-06T03:56:00Z", operations_lead="synthetic-human",
            terms_review_complete=True, authorize_confirmatory_api_core=True,
            prospective_agent_amendment_reviewed=True, late_activation_with_original_windows_approved=True,
            prospective_lineage_admission_amendment_reviewed=True, prospective_gemini_standard_amendment_reviewed=True)
        path = target / "authorization.json"; path.write_text(json.dumps(auth)); return path

    def check(self, target, built, auth, root):
        return executor.preflight(protocol_path=target / "bundle" / built["protocol_file"],
            freeze_path=target / "bundle" / built["provider_freeze_file"],
            manifest_path=target / "bundle" / built["manifest_file"], authorization_path=auth,
            data_root=root / "data", now=runner.parse_aware_utc("2026-10-06T03:57:00Z"))

    def test_new_standard_probe_restores_exact_profiles_preserves_history_and_google_only_queue(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d); old, report, target, prior = self.fixture(root, stack)
            original = {p: p.read_bytes() for p in [old.freeze, report, *prior.glob("*.json")]}
            called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); location = result["out_dir"]; built = result["bundle"]
            self.assertEqual(called.call_count, 1)
            self.assertNotIn("service_tier", called.call_args.kwargs["profile"])
            self.assertEqual(called.call_args.kwargs["prompt"], preflight.SYNTHETIC_PROMPT)
            self.assertEqual(built["initial_request_count"], 1120)
            self.assertEqual(built["admitted_request_count"], 280)
            template = json.loads((location / "bundle/core_v2_execution_authorization.template.json").read_text())
            self.assertFalse(template["authorized"])
            self.assertFalse(template["prospective_gemini_standard_amendment_reviewed"])
            again = self.call(target)
            self.assertFalse(again["provider_called"]); self.assertEqual(called.call_count, 1)
            for p, content in original.items(): self.assertEqual(p.read_bytes(), content)
            auth = self.authorize(location)
            rows, frozen, *_ = self.check(location, built, auth, root)
            self.assertEqual(len(rows), 280)
            self.assertEqual({r["service_lineage_id"] for r in rows}, set(admission.GOOGLE_SCOPE))
            self.assertEqual(frozen["core_api"], json.loads(old.freeze.read_text())["core_api"])
            self.assertEqual(runner.validate_manifest(runner.read_csv(location / "bundle" / built["manifest_file"]),
                protocol_path=location / "bundle" / built["protocol_file"], freeze_path=location / "bundle" / built["provider_freeze_file"]), [])

    def test_prior_technical_wait_tamper_and_interrupted_new_probe_make_no_call(self):
        for mode in ("wait", "tamper", "interrupted"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, target, prior = self.fixture(Path(d), stack, prior_wait=mode == "wait")
                called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
                if mode == "wait":
                    stamp = "2026-10-06T03:55:00Z"
                else:
                    stamp = "2026-10-06T03:55:00Z"
                    if mode == "tamper": (prior / "SMOKE.json").write_text("{}")
                    if mode == "interrupted": (target / "standard-recovery-block/probe-1").mkdir(parents=True)
                with self.assertRaises(ValueError): self.call(target, stamp)
                called.assert_not_called()

    def test_retry_wait_and_cap_are_preserved_and_secrets_are_redacted(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target, _ = self.fixture(Path(d), stack)
            called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=adapters.AdapterFailure(
                "provider_error", "synthetic", 503, 901, "synthetic-private-key")))
            for stamp in ("2026-10-06T03:55:00Z", "2026-10-06T04:10:01Z", "2026-10-06T04:40:01Z"):
                with mock.patch.object(runtime.scoped, "now", return_value=stamp), self.assertRaises(ValueError): self.call(target, stamp)
                if stamp == "2026-10-06T03:55:00Z":
                    with self.assertRaisesRegex(ValueError, "wait has not elapsed"): self.call(target, "2026-10-06T04:05:00Z")
                    self.assertEqual(called.call_count, 1)
            with self.assertRaisesRegex(ValueError, "exhausted"): self.call(target, "2026-10-06T05:40:00Z")
            self.assertEqual(called.call_count, 3)
            for p in (target / "standard-recovery-block").glob("probe-*/RESULT.json"):
                self.assertNotIn("synthetic-private-key", p.read_text())

    def test_wrong_model_or_priority_request_is_retained_and_not_retried(self):
        for mode in ("model", "wire"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, target, _ = self.fixture(Path(d), stack)
                def wrong(**kw):
                    value = self.result(**kw)
                    return replace(value, response_json={"modelVersion": "another-model"}) if mode == "model" else replace(value, request_payload={**value.request_payload, "service_tier": "priority"})
                called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=wrong))
                with self.assertRaisesRegex(ValueError, "not confirmed"): self.call(target)
                with self.assertRaisesRegex(ValueError, "not retryable"): self.call(target, "2026-10-06T04:55:00Z")
                self.assertEqual(called.call_count, 1)

    def test_all_older_google_paths_and_unknown_attempts_block_but_three_provider_records_are_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for version in ("2.0", "2.0.1", "2.0.2", "2.0.3"):
                path = archive.wave_root(root, "JP01", "MIBO2-W01", version) / "failures/old.json"
                path.parent.mkdir(parents=True); path.write_text(json.dumps({"service_lineage_id": "MIBO-SL-001"}))
                standard.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
                path.write_text(json.dumps({"service_lineage_id": "MIBO-SL-003"}))
                with self.assertRaisesRegex(ValueError, "queue replay"): standard.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
                path.write_text("{}")
                with self.assertRaisesRegex(ValueError, "classified"): standard.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
                path.unlink()
                dispatch = path.parents[1] / "metadata/first-dispatch-MIBO-SL-003.json"
                dispatch.parent.mkdir(); dispatch.write_text("{}")
                with self.assertRaisesRegex(ValueError, "dispatch exists"): standard.block_prior_google_attempts(root, "JP01", "MIBO2-W01")
                dispatch.unlink()

    def test_specific_human_review_and_original_closing_time_are_required(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, target, _ = self.fixture(Path(d), stack)
            called = stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            with self.assertRaisesRegex(ValueError, "window is not open"): self.call(target, "2026-10-08T00:00:00Z")
            called.assert_not_called()
            result = self.call(target); location = result["out_dir"]
            auth = self.authorize(location); value = json.loads(auth.read_text())
            value["prospective_gemini_standard_amendment_reviewed"] = False; auth.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Standard human amendment"): self.check(location, result["bundle"], auth, Path(d))

    def test_confirmatory_executor_calls_only_google_and_preserves_new_namespace_and_tier(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d); _, _, target, _ = self.fixture(root, stack)
            stack.enter_context(mock.patch.object(runtime, "call_provider", side_effect=self.result))
            result = self.call(target); location = result["out_dir"]; built = result["bundle"]
            auth = self.authorize(location); checked = self.check(location, built, auth, root)
            row = next(r for r in checked[0] if r["window_id"] == "STD")
            stack.enter_context(mock.patch.object(executor, "preflight", return_value=([row], *checked[1:])))
            clock = stack.enter_context(mock.patch.object(executor, "datetime", wraps=datetime))
            clock.now.return_value = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
            dispatch_stamp = clock.now.return_value.isoformat()
            stack.enter_context(mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}))
            called = stack.enter_context(mock.patch.object(executor, "call_provider", side_effect=lambda **kw: replace(
                self.result(**kw), started_at_utc=dispatch_stamp,
                completed_at_utc=dispatch_stamp, duration_ms=0)))
            summary = executor.execute(protocol_path=location / "bundle" / built["protocol_file"],
                freeze_path=location / "bundle" / built["provider_freeze_file"],
                manifest_path=location / "bundle" / built["manifest_file"], authorization_path=auth, data_root=root / "data")
            self.assertEqual(called.call_count, 1); self.assertEqual(called.call_args.kwargs["provider"], "Google")
            self.assertTrue(called.call_args.kwargs["capture_response_metadata"])
            self.assertEqual(summary["valid"], 1); self.assertEqual(summary["retries_scheduled"], 0)
            path = archive.wave_root(root / "data", "JP01", "MIBO2-W01", "2.0.4") / "api_raw" / (row["attempt_id"] + ".json")
            record = json.loads(path.read_text())
            self.assertNotIn("service_tier", record["request_payload"])
            self.assertEqual(record["response_metadata"]["service_tier_actual"], "standard")

    def test_standard_metadata_capture_does_not_change_wire_or_legacy_behavior(self):
        profile = {"adapter": "gemini_generate_content", "api_key_env": "GEMINI_API_KEY", "max_output_tokens": 4096}
        for wrong in (False, True):
            with self.subTest(wrong=wrong):
                body = {"modelVersion": "another-model" if wrong else "gemini-3.8-flash", "candidates": []}
                response = mock.MagicMock(); response.__enter__.return_value = response
                response.status = 200; response.headers = Message(); response.headers["X-Gemini-Service-Tier"] = "standard"
                response.read.return_value = json.dumps(body).encode()
                with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key"}), mock.patch.object(adapters, "urlopen", return_value=response) as called:
                    if wrong:
                        with self.assertRaises(adapters.AdapterFailure) as caught:
                            adapters.call_gemini(model_id="gemini-3.8-flash", prompt="synthetic", profile=profile, capture_response_metadata=True)
                        self.assertFalse(caught.exception.retry_eligible)
                    else:
                        result = adapters.call_gemini(model_id="gemini-3.8-flash", prompt="synthetic", profile=profile, capture_response_metadata=True)
                        self.assertEqual(result.response_metadata["service_tier_requested"], "standard_default")
                        self.assertFalse(result.response_metadata["provider_downgraded_to_standard"])
                    self.assertNotIn("service_tier", json.loads(called.call_args.args[0].data))
                    self.assertEqual(called.call_count, 1)


if __name__ == "__main__": unittest.main()
