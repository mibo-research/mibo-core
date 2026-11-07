"""Synthetic three-series protocol/transport rehearsal. Never call live APIs."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive as archive
import core_v2_bundle as bundle
import core_v2_execution_state as state
import core_v2_executor as executor
import core_v2_preflight as readiness
import core_v2_prewave as prewave
import core_v2_runner as runner
import core_v2_status as status
import core_v21_policy as policy
import core_v21_waiter as entrypoint
from test_core_v2_api import CoreV2Fixture

CONFIG = Path(runner.__file__).parent / "config"
REGISTRATION = "10.5281/zenodo.999999999"  # Synthetic fixture, not a real registration.
ENV = {
    "MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL,
    policy.SENTINEL_ENV: policy.SENTINEL,
    "OPENAI_API_KEY": "synthetic-only",
    "ANTHROPIC_API_KEY": "synthetic-only",
    "GEMINI_API_KEY": "synthetic-only",
    "MIBO_RUNTIME_HOST": "synthetic-vm",
    "MIBO_CORE_V2_SOURCE_COMMIT": "a" * 40,
}


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class ThreeSeriesFixture:
    def __init__(self, root, wave="MIBO2-W03"):
        self.root, self.wave_id = root, wave
        self.protocol, self.freeze = root / "protocol.json", root / "freeze.json"
        self.manifest, self.authorization = root / "manifest.csv", root / "auth.json"
        self.report = root / "readiness" / "REPORT.json"
        self.data_root = root / "data"
        self.data_root.mkdir()
        protocol = json.loads((CONFIG / "core_v21_protocol.draft.json").read_text())
        protocol.update(protocol_status="finalized_and_prospectively_registered",
            protocol_registration_id=REGISTRATION, prospectively_registered_at_utc="2026-11-08T00:00:00Z",
            effective_from_wave_id="MIBO2-W03",
            W03_analysis_transition={"status": "separately-amended-prospectively",
                "registration_id": "10.5281/zenodo.999999998", "registered_at_utc": "2026-11-07T12:00:00Z"},
            )
        put(self.protocol, protocol)
        freeze = json.loads((CONFIG / "core_v21_provider_freeze.template.json").read_text())
        freeze.update(protocol_registration_id=REGISTRATION, wave_id=wave,
                      frozen_at_utc="2026-11-09T00:00:00Z")
        for sid, cfg in freeze["core_api"].items():
            cfg.update(status="eligible", model_id="synthetic-locked-" + sid,
                model_version_locked=True, selection_rationale="synthetic prospective fixture",
                provider_evidence="synthetic official metadata", verified_at_utc="2026-11-09T00:00:00Z",
                terms_review_date="2026-11-09", terms_review_source="synthetic terms evidence")
            cfg["request_profile"]["max_output_tokens"] = 512
        put(self.freeze, freeze)
        self.rows = runner.generate_manifest(protocol_path=self.protocol, freeze_path=self.freeze,
            wave_id=wave, site_id="JP01")
        runner.write_csv(self.rows, self.manifest)
        models, smoke = [], []
        for service in runner.services_for_protocol(protocol):
            sid = service["service_lineage_id"]
            metadata_path = self.report.parent / "models" / (sid + ".json")
            smoke_path = self.report.parent / "smoke" / (sid + ".json")
            model = freeze["core_api"][sid]["model_id"]
            put(metadata_path, {"synthetic_only": True,
                "response": {"name": "models/" + model} if service["provider"] == "Google" else {"id": model},
                "service_provider_label": service["provider"], "api_provider": service["provider"],
                "http_status": 200, "credential_value_recorded": False,
                "started_at_utc": "2026-11-09T01:00:00Z", "completed_at_utc": "2026-11-09T01:00:00Z"})
            put(smoke_path, {"synthetic_only": True, "pass": True, "service_lineage_id": sid,
                "requested_model": model, "returned_model": model, "registered_mibo_prompt_used": False})
            base = {"service_lineage_id": sid, "provider": service["provider"], "model_id": model}
            models.append({**base, "exact_metadata_verified": True,
                "verification_method": "exact_metadata_endpoint", "metadata_returned_model_id": model,
                "metadata_file": metadata_path.relative_to(self.report.parent).as_posix(),
                "metadata_sha256": runner.sha256_file(metadata_path)})
            smoke.append({**base, "pass": True, "file": smoke_path.relative_to(self.report.parent).as_posix(),
                "sha256": runner.sha256_file(smoke_path)})
        put(self.report, {"schema_version": "2.1", "protocol_version": "2.1",
            "protocol_registration_id": REGISTRATION, "protocol_file_sha256": runner.sha256_file(self.protocol),
            "provider_freeze_sha256": runner.sha256_file(self.freeze), "wave_id": wave, "site_id": "JP01",
            "scientific_class": runner.SCIENTIFIC_CLASS, "pass": True,
            "checked_at_utc": "2026-11-09T01:00:00Z", "synthetic_smoke_requested": True,
            "automatic_model_selection": False, "automatic_provider_substitution": False,
            "provider_freeze_modified": False, "registered_mibo_prompts_used": False, "errors": [],
            "model_checks": models, "synthetic_smoke_checks": smoke})
        put(self.authorization, {"schema_version": "2.1", "protocol_version": "2.1",
            "protocol_registration_id": REGISTRATION, "wave_id": wave, "site_id": "JP01",
            "authorized": True, "authorized_at_utc": "2026-11-10T00:00:00Z",
            "operations_lead": "SYNTHETIC-TEST-ONLY-NOT-A-HUMAN-SIGNATURE", "protocol_finalized": True,
            "prospective_registration_complete": True, "terms_review_complete": True,
            "model_freeze_complete": True, "synthetic_dry_run_complete": True,
            "authorize_confirmatory_api_core": True,
            "protocol_file_sha256": runner.sha256_file(self.protocol),
            "provider_freeze_sha256": runner.sha256_file(self.freeze),
            "manifest_sha256": runner.sha256_file(self.manifest),
            "readiness_report_file": str(self.report), "readiness_report_sha256": runner.sha256_file(self.report),
            **{gate: True for gate in policy.AUTHORIZATION_GATES}})

    def args(self):
        return dict(protocol_path=self.protocol, manifest_path=self.manifest, freeze_path=self.freeze,
            authorization_path=self.authorization, data_root=self.data_root)

    def validate_report(self):
        protocol, digest = runner.load_protocol(self.protocol)
        freeze, freeze_sha = runner.load_freeze(self.freeze, protocol=protocol, wave_id=self.wave_id, site_id="JP01")
        return policy.validate_readiness(self.report, protocol=protocol, protocol_sha=digest,
            freeze=freeze, freeze_sha=freeze_sha)


class ThreeSeriesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = ThreeSeriesFixture(self.root)

    def test_draft_is_inspectable_but_never_runnable(self):
        path = CONFIG / "core_v21_protocol.draft.json"
        draft, _ = runner.load_protocol(path, require_final=False)
        self.assertEqual(draft["effective_from_wave_id"], "MIBO2-W03")
        self.assertIsNone(draft["W03_analysis_transition"]["registration_id"])
        self.assertIsNone(draft["protocol_registration_id"])
        with self.assertRaisesRegex(ValueError, "not finalized"):
            runner.load_protocol(path)

    def test_exact_three_scope_and_720_deterministic_rows(self):
        f = self.fixture
        self.assertEqual(len(f.rows), 720)
        self.assertEqual(Counter(r["service_lineage_id"] for r in f.rows), dict.fromkeys(policy.LINEAGES, 240))
        self.assertEqual(runner.validate_manifest(f.rows, protocol_path=f.protocol, freeze_path=f.freeze), [])
        self.assertEqual(f.rows, runner.generate_manifest(protocol_path=f.protocol, freeze_path=f.freeze,
            wave_id=f.wave_id, site_id="JP01"))
        self.assertTrue(all(r["random_seed"] == runner.deterministic_seed(f.wave_id, "JP01") for r in f.rows))
        self.assertEqual({r["observation_surface"] for r in f.rows}, {"provider_api"})
        self.assertEqual({r["environment_class"] for r in f.rows}, {"CLOSED"})

    def test_extra_lineage_missing_lineage_and_wrong_adapter_fail(self):
        original = self.fixture.freeze.read_text()
        for action in ("extra", "missing", "adapter", "endpoint", "fallback"):
            with self.subTest(action=action):
                data = json.loads(original)
                cfg = data["core_api"][policy.LINEAGES[0]]
                if action == "extra": data["core_api"]["MIBO-SL-004"] = cfg
                if action == "missing": data["core_api"].pop(policy.LINEAGES[-1])
                if action == "adapter": cfg["request_profile"]["adapter"] = "perplexity_agent"
                if action == "endpoint": cfg["request_profile"]["endpoint"] = "https://example.invalid/request"
                if action == "fallback": cfg["request_profile"]["fallback_model"] = "other"
                put(self.fixture.freeze, data)
                with self.assertRaises(ValueError):
                    runner.load_freeze(self.fixture.freeze, protocol=runner.load_protocol(self.fixture.protocol)[0],
                        wave_id=self.fixture.wave_id, site_id="JP01")
        self.fixture.freeze.write_text(original)

    def test_registration_schedule_qualification_and_effective_wave_fail_closed(self):
        original = self.fixture.protocol.read_text()
        for change in ({"protocol_registration_id": policy.PRIOR_REGISTRATION},
                       {"protocol_registration_id": "https://github.com/mibo-research/mibo-core/blob/main/docs/v2.1/x.md"},
                       {"effective_from_wave_id": None}, {"effective_from_wave_id": "MIBO2-W02"},
                       {"analysis_transition_decision": None}, {"ai_scoring_qualification_plan": None},
                       {"prospectively_registered_at_utc": "2026-11-08T00:00:00"}):
            with self.subTest(change=change):
                put(self.fixture.protocol, {**json.loads(original), **change})
                with self.assertRaises(ValueError): runner.load_protocol(self.fixture.protocol)
        protocol = json.loads(original)
        protocol["waves"][2]["close_utc"] = "2026-12-04T00:00:00Z"
        put(self.fixture.protocol, protocol)
        with self.assertRaisesRegex(ValueError, "waves mismatch"): runner.load_protocol(self.fixture.protocol)

    def test_old_wave_and_late_freeze_are_not_relabelled(self):
        f = self.fixture
        with self.assertRaisesRegex(ValueError, "boundary"):
            runner.generate_manifest(protocol_path=f.protocol, freeze_path=f.freeze, wave_id="MIBO2-W02")
        data = json.loads(f.freeze.read_text())
        data["frozen_at_utc"] = "2026-12-01T00:00:00Z"
        put(f.freeze, data)
        with self.assertRaisesRegex(ValueError, "prospective"):
            runner.generate_manifest(protocol_path=f.protocol, freeze_path=f.freeze, wave_id=f.wave_id)

    def test_changed_order_or_denominator_rejected(self):
        rows = [dict(r) for r in self.fixture.rows]
        rows[0]["execution_order"], rows[1]["execution_order"] = rows[1]["execution_order"], rows[0]["execution_order"]
        self.assertTrue(any("execution_order" in e for e in runner.validate_manifest(rows,
            protocol_path=self.fixture.protocol, freeze_path=self.fixture.freeze)))
        self.assertTrue(any("count" in e for e in runner.validate_manifest(rows[:-1],
            protocol_path=self.fixture.protocol, freeze_path=self.fixture.freeze)))

    def test_existing_W03_analysis_cannot_be_silently_converted(self):
        f = self.fixture
        data = json.loads(f.protocol.read_text())
        data["W03_analysis_transition"] = None
        put(f.protocol, data)
        with self.assertRaisesRegex(ValueError, "existing four-series W03"): runner.load_protocol(f.protocol)
        data["W03_analysis_transition"] = {"status": "preserved-unmodified", "registration_id": policy.W03_ANALYSIS_REGISTRATION}
        put(f.protocol, data)
        with self.assertRaisesRegex(ValueError, "W03 activation"): runner.load_protocol(f.protocol)
        data["effective_from_wave_id"] = "MIBO2-W04"
        put(f.protocol, data)
        with self.assertRaisesRegex(ValueError, "no automatic substitution"):
            runner.load_protocol(f.protocol)

    def test_generic_sentinel_cannot_arm_v21_or_call_metadata(self):
        f = self.fixture
        with mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}, clear=True), \
                mock.patch.object(executor, "call_provider") as transport, \
                mock.patch.object(readiness.api, "fetch_catalog") as catalog:
            with self.assertRaisesRegex(ValueError, "dedicated"):
                executor.execute(**f.args())
            with self.assertRaisesRegex(ValueError, "readiness approval"):
                readiness.run_preflight(protocol_path=f.protocol, freeze_path=f.freeze, out_dir=self.root / "not-created")
            self.assertFalse((self.root / "not-created").exists())
            transport.assert_not_called(); catalog.assert_not_called()

    def test_authorization_gates_hashes_and_timestamp_are_enforced(self):
        f = self.fixture
        original = f.authorization.read_text()
        changes = [{gate: False} for gate in policy.AUTHORIZATION_GATES]
        changes += [{"authorized": False}, {"manifest_sha256": "0" * 64},
                    {"authorized_at_utc": "2026-11-08T00:00:00Z"},
                    {"authorized_at_utc": "2026-12-01T00:00:00Z"}, {"readiness_report_sha256": "0" * 64}]
        for change in changes:
            put(f.authorization, {**json.loads(original), **change})
            with self.subTest(change=change), self.assertRaises(ValueError):
                executor.preflight(**f.args(), now=datetime(2026, 12, 1, tzinfo=timezone.utc))

    def test_readiness_rejects_duplicate_old_panel_and_tampered_evidence(self):
        f = self.fixture
        self.assertTrue(f.validate_report()["pass"])
        original = f.report.read_text()
        for kind in ("duplicate", "four", "model", "path", "hash"):
            report = json.loads(original)
            smoke = report["synthetic_smoke_checks"]
            if kind == "duplicate": smoke[1] = dict(smoke[0])
            if kind == "four": smoke.append(dict(smoke[0]))
            if kind == "model": smoke[0]["model_id"] = "replacement"
            if kind == "path": smoke[0]["file"] = "../outside.json"
            if kind == "hash": smoke[0]["sha256"] = "0" * 64
            put(f.report, report)
            with self.subTest(kind=kind), self.assertRaises(ValueError): f.validate_report()

    def test_bundle_copies_evidence_and_never_signs_or_arms(self):
        f = self.fixture
        output = self.root / "bundle"
        report = bundle.build_bundle(protocol_path=f.protocol, freeze_path=f.freeze,
            preflight_report_path=f.report, wave_id=f.wave_id, site_id="JP01", out_dir=output)
        self.assertEqual(report["initial_request_count"], 720)
        template = json.loads((output / "core_v2_execution_authorization.template.json").read_text())
        self.assertFalse(template["authorized"])
        self.assertIsNone(template["operations_lead"])
        self.assertTrue(all(template[gate] is False for gate in policy.AUTHORIZATION_GATES))
        self.assertEqual(len(list((output / "configuration/smoke").glob("*.json"))), 3)

    def test_cross_version_attempts_and_global_locks_prevent_replay(self):
        f = self.fixture
        retained = dict(f.rows[0], protocol_version="2.0.1")
        archive.archive_failure(data_root=f.data_root, row=retained, failure_kind="provider_error",
            message="synthetic", failed_at_utc="2026-12-01T00:00:00Z", http_status=503)
        with self.assertRaisesRegex(ValueError, "no replay"):
            executor._block_other_namespace_attempts(f.data_root, f.rows)
        with state.lineage_locks(f.data_root, "JP01", f.wave_id, set(policy.LINEAGES)):
            with self.assertRaises(RuntimeError):
                with state.lineage_locks(f.data_root, "JP01", f.wave_id, {policy.LINEAGES[0]}): pass

    def test_v21_service_refuses_a_legacy_protocol(self):
        other = self.root / "legacy"; other.mkdir()
        legacy = CoreV2Fixture(other)
        with mock.patch.object(sys, "argv", ["entry", "--protocol", str(legacy.protocol)]), \
                mock.patch.object(entrypoint.waiter, "main") as waiter:
            with self.assertRaisesRegex(ValueError, "historical four-series"): entrypoint.main()
            waiter.assert_not_called()

    def test_old_single_lineage_scope_cannot_follow_a_different_v21_lineage(self):
        f = self.fixture
        retained = archive.wave_root(f.data_root, "JP01", f.wave_id, "2.1") / "metadata" / "first-dispatch-MIBO-SL-001.json"
        put(retained, {"synthetic_only": True, "service_lineage_id": "MIBO-SL-001"})
        google = next(r for r in f.rows if r["service_lineage_id"] == "MIBO-SL-003")
        legacy_rows = [dict(google, protocol_version="2.0.2")]
        with self.assertRaisesRegex(ValueError, "no mid-wave"):
            executor._block_other_namespace_attempts(f.data_root, legacy_rows)

    def test_rehashed_wrong_metadata_cannot_pass_a_true_summary_flag(self):
        f = self.fixture
        original = f.report.read_bytes()
        for provider in ("OpenAI", "Anthropic", "Google"):
            report = json.loads(original)
            check = next(c for c in report["model_checks"] if c["provider"] == provider)
            path = f.report.parent / check["metadata_file"]
            prior = path.read_bytes()
            evidence = json.loads(prior)
            evidence["response"] = {"name": "models/wrong-model"} if provider == "Google" else {"id": "wrong-model"}
            put(path, evidence)
            check["metadata_sha256"] = runner.sha256_file(path)
            put(f.report, report)
            with self.subTest(provider=provider), self.assertRaisesRegex(ValueError, "captured metadata"):
                f.validate_report()
            path.write_bytes(prior)
        f.report.write_bytes(original)

    def test_rehashed_non_success_or_wrong_provider_model_evidence_is_rejected(self):
        f = self.fixture
        original = f.report.read_bytes()
        for field, value in (("http_status", 503), ("api_provider", "Other"),
                ("completed_at_utc", "2026-12-01T00:00:00Z"), ("credential_value_recorded", True)):
            report = json.loads(original)
            check = report["model_checks"][0]
            path = f.report.parent / check["metadata_file"]
            prior = path.read_bytes()
            evidence = json.loads(prior); evidence[field] = value
            put(path, evidence); check["metadata_sha256"] = runner.sha256_file(path)
            put(f.report, report)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "provider/status/timing"):
                f.validate_report()
            path.write_bytes(prior)
        f.report.write_bytes(original)

    def test_catalog_fallback_must_contain_the_exact_model_in_captured_response(self):
        f = self.fixture
        report = json.loads(f.report.read_bytes())
        check = report["model_checks"][0]
        model = check["model_id"]
        check.update(metadata_file=None, metadata_sha256=None, metadata_returned_model_id=None,
            verification_method="catalog_listing", listed_in_catalog_response=True)
        path = f.report.parent / "catalog.json"
        capture = {"service_provider_label": "OpenAI", "api_provider": "OpenAI", "http_status": 200,
            "credential_value_recorded": False, "started_at_utc": "2026-11-09T01:00:00Z",
            "completed_at_utc": "2026-11-09T01:00:00Z", "response": {"data": [{"id": model}]},
            "normalized_model_ids": [model]}
        put(path, capture)
        report["catalogs"] = {"OpenAI": {"file": "catalog.json", "sha256": runner.sha256_file(path), "model_ids": [model]}}
        put(f.report, report)
        self.assertTrue(f.validate_report()["pass"])
        capture["response"] = {"data": []}; put(path, capture)
        report["catalogs"]["OpenAI"]["sha256"] = runner.sha256_file(path); put(f.report, report)
        with self.assertRaisesRegex(ValueError, "captured catalog"):
            f.validate_report()

    def test_historical_perplexity_only_attempt_also_prevents_midwave_conversion(self):
        f = self.fixture
        old = dict(f.rows[0], protocol_version="2.0.1", service_lineage_id="MIBO-SL-004", provider="Perplexity AI")
        old["attempt_id"] = old["attempt_id"].replace("SL001", "SL004")
        archive.archive_failure(data_root=f.data_root, row=old, failure_kind="provider_error",
            message="synthetic", failed_at_utc="2026-12-01T00:00:00Z", http_status=503)
        with self.assertRaisesRegex(ValueError, "no mid-wave"):
            executor._block_other_namespace_attempts(f.data_root, f.rows)

    def test_other_namespace_symlink_rejected_before_enumerating_its_target(self):
        f = self.fixture
        old = archive.wave_root(f.data_root, "JP01", f.wave_id, "2.0")
        old.mkdir(parents=True)
        outside = self.root / "synthetic-outside"; outside.mkdir()
        (old / "metadata").symlink_to(outside, target_is_directory=True)
        with mock.patch.object(Path, "glob", side_effect=AssertionError("must not enumerate symlink target")):
            with self.assertRaisesRegex(ValueError, "symlink"):
                executor._block_other_namespace_attempts(f.data_root, f.rows)

    def test_direct_executor_requires_real_controlled_runtime_gate(self):
        f = self.fixture
        start = datetime(2026, 12, 1, tzinfo=timezone.utc)
        with mock.patch.dict(os.environ, ENV, clear=True), \
                mock.patch.object(executor, "datetime", wraps=datetime) as clock, \
                mock.patch.object(prewave, "datetime", wraps=datetime) as preclock, \
                mock.patch.object(executor, "call_provider") as transport:
            clock.now.return_value = preclock.now.return_value = start
            with self.assertRaisesRegex(ValueError, "hostname mismatch"): executor.execute(**f.args())
            transport.assert_not_called()

    def test_mocked_readiness_calls_only_three_first_party_providers(self):
        f = self.fixture
        models = {s["provider"]: json.loads(f.freeze.read_text())["core_api"][s["service_lineage_id"]]["model_id"]
                  for s in runner.services_for_protocol(runner.load_protocol(f.protocol)[0])}
        def response(provider, model=None, **_):
            return SimpleNamespace(endpoint="https://example.invalid/synthetic", status=200,
                data={"name": "models/" + model} if model and provider == "Google" else {"id": model},
                started_at_utc="2026-11-09T01:00:00Z", completed_at_utc="2026-11-09T01:00:00Z", duration_ms=0)
        def catalog(provider, **kwargs): return response(provider), [models[provider]]
        def transport(**kwargs):
            return SimpleNamespace(request_payload={"synthetic_only": True}, response_json={"synthetic_only": True},
                returned_model=kwargs["model_id"], http_status=200, usage={}, started_at_utc="2026-11-09T01:00:00Z",
                completed_at_utc="2026-11-09T01:00:00Z", duration_ms=0, response_metadata=None)
        with mock.patch.dict(os.environ, {"MIBO_CORE_V21_READINESS": "ENABLED_AFTER_CORE_V21_READINESS_APPROVAL",
                "MIBO_CORE_V2_SMOKE_TEST": readiness.SMOKE_SENTINEL}, clear=True), \
                mock.patch.object(readiness.api, "fetch_catalog", side_effect=catalog) as catalogs, \
                mock.patch.object(readiness.api, "fetch_exact_model", side_effect=response) as exact, \
                mock.patch.object(readiness, "call_provider", side_effect=transport) as calls, \
                mock.patch.object(readiness, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 9, 2, tzinfo=timezone.utc)
            report = readiness.run_preflight(protocol_path=f.protocol, freeze_path=f.freeze,
                out_dir=self.root / "mocked-readiness", smoke=True)
        self.assertTrue(report["pass"])
        self.assertEqual([c.args[0] for c in catalogs.call_args_list], ["OpenAI", "Anthropic", "Google"])
        self.assertEqual(exact.call_count, 3)
        self.assertEqual(calls.call_count, 3)
        self.assertEqual({c.kwargs["prompt"] for c in calls.call_args_list}, {readiness.SYNTHETIC_PROMPT})
        checked = policy.validate_readiness(self.root / "mocked-readiness/CORE_V2_API_PREFLIGHT_REPORT.json",
            protocol=runner.load_protocol(f.protocol)[0], protocol_sha=runner.sha256_file(f.protocol),
            freeze=json.loads(f.freeze.read_text()), freeze_sha=runner.sha256_file(f.freeze))
        self.assertTrue(checked["pass"])

    def test_smoke_disabled_stops_before_any_catalog_request(self):
        f = self.fixture
        with mock.patch.dict(os.environ, {"MIBO_CORE_V21_READINESS": "ENABLED_AFTER_CORE_V21_READINESS_APPROVAL"}, clear=True), \
                mock.patch.object(readiness.api, "fetch_catalog") as catalog:
            with self.assertRaisesRegex(ValueError, "additional terms-review"):
                readiness.run_preflight(protocol_path=f.protocol, freeze_path=f.freeze,
                    out_dir=self.root / "not-created", smoke=True)
            catalog.assert_not_called()

    def test_revoked_dedicated_gate_during_durable_claim_stops_before_transport(self):
        f = self.fixture
        now = datetime(2026, 12, 1, tzinfo=timezone.utc)
        native_claim = state.claim_attempt
        def revoke(*args, **kwargs):
            result = native_claim(*args, **kwargs)
            os.environ[policy.SENTINEL_ENV] = "DISABLED"
            return result
        with mock.patch.dict(os.environ, ENV, clear=True), \
                mock.patch.object(executor, "datetime", wraps=datetime) as clock, \
                mock.patch.object(prewave, "datetime", wraps=datetime) as preclock, \
                mock.patch.object(prewave, "_runtime_gate", return_value={"synthetic_only": True}), \
                mock.patch.object(state, "claim_attempt", side_effect=revoke), \
                mock.patch.object(executor, "call_provider") as transport:
            clock.now.return_value = preclock.now.return_value = now
            with self.assertRaisesRegex(ValueError, "dedicated"): executor.execute(**f.args())
            transport.assert_not_called()
        root = archive.wave_root(f.data_root, "JP01", f.wave_id, "2.1")
        self.assertEqual(len(list((root / "dispatch").glob("*.json"))), 1)
        self.assertEqual(list((root / "api_raw").glob("*.json")), [])

    def test_new_closure_reads_v21_waiter_and_three_series_counts(self):
        f = self.fixture
        path = Path(runner.__file__).parents[1] / "runtime/close-core-v2-wave.py"
        spec = importlib.util.spec_from_file_location("v21_synthetic_close", path)
        close = importlib.util.module_from_spec(spec); spec.loader.exec_module(close)
        arguments = ["/usr/bin/python3", str(Path(runner.__file__).with_name("core_v21_waiter.py")),
            "--wave", f.wave_id, "--protocol", str(f.protocol), "--manifest", str(f.manifest),
            "--freeze", str(f.freeze), "--authorization", str(f.authorization), "--data-root", str(f.data_root)]
        archive.wave_root(f.data_root, "JP01", f.wave_id, "2.1").mkdir(parents=True)
        with mock.patch.object(close, "collector_state", return_value={"synthetic_only": True}), \
                mock.patch.object(close, "unit_arguments", return_value=(arguments, {})), \
                mock.patch.object(close.runtime_health, "provenance_state", return_value={
                    "commit_resolved": True, "working_tree_clean": True, "commit_sha": "a" * 40}):
            config = close.load_unit("mibo-core-v21.service", f.wave_id, "JP01",
                datetime(2026, 12, 3, tzinfo=timezone.utc))
        self.assertEqual(config["admitted"], list(policy.LINEAGES))
        self.assertEqual(len(config["rows"]), 720)
        self.assertEqual(config["root"].parts[-3], "v2.1")


class ThreeSeriesRehearsalTests(unittest.TestCase):
    def rehearse(self, wave, expected, windows):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            f = ThreeSeriesFixture(Path(d), wave)
            protocol, _ = runner.load_protocol(f.protocol)
            bounds = runner.wave(protocol, wave)
            current = [runner.parse_aware_utc(bounds["start_utc"])]
            calls = []
            def transport(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(request_payload={"prompt": kwargs["prompt"]},
                    response_json={"text": "synthetic valid refusal"}, raw_response_text="synthetic valid refusal",
                    http_status=200, returned_model=kwargs["model_id"], usage={},
                    started_at_utc=current[0].isoformat(), completed_at_utc=current[0].isoformat(),
                    duration_ms=0, response_metadata=None)
            stack.enter_context(mock.patch.dict(os.environ, ENV, clear=True))
            clock = stack.enter_context(mock.patch.object(executor, "datetime", wraps=datetime))
            preclock = stack.enter_context(mock.patch.object(prewave, "datetime", wraps=datetime))
            clock.now.side_effect = preclock.now.side_effect = lambda *_: current[0]
            stack.enter_context(mock.patch.object(prewave, "_runtime_gate", return_value={"synthetic_only": True}))
            stack.enter_context(mock.patch.object(executor.time, "sleep", side_effect=lambda seconds:
                current.__setitem__(0, current[0] + timedelta(seconds=seconds))))
            adapter = stack.enter_context(mock.patch.object(executor, "call_provider", side_effect=transport))
            first = executor.execute(**f.args())
            second = executor.execute(**f.args())
            self.assertEqual(first["valid"], expected)
            self.assertEqual(first["retries_scheduled"], 0)
            self.assertEqual(second["already_processed"], expected)
            self.assertEqual(second["valid"], 0)
            self.assertEqual(adapter.call_count, expected)
            self.assertEqual(Counter(c["provider"] for c in calls), dict.fromkeys(("OpenAI", "Anthropic", "Google"), expected // 3))
            self.assertEqual(Counter(r["window_id"] for r in f.rows), windows)
            prompts = executor._prompt_map()
            for call, row in zip(calls, f.rows):
                self.assertEqual(call["prompt"], prompts[row["query_form_id"]])
                self.assertEqual(call["model_id"], row["model_id"])
            report = status.build_report(**f.args(), expected_wave=wave,
                current=runner.parse_aware_utc(bounds["close_utc"]))
            self.assertEqual(report["status"], "COMPLETE")
            self.assertEqual(report["captured_cells"], expected)
            self.assertFalse((f.data_root / "v2.0.1").exists())

    def test_720_roundtrip_restart_and_no_perplexity_key(self):
        self.rehearse("MIBO2-W03", 720, {"STD": 720})

    def test_840_calibration_roundtrip_with_original_windows(self):
        self.rehearse("MIBO2-W04", 840, {"WA": 120, "WB": 120, "STD": 600})


if __name__ == "__main__":
    unittest.main()
