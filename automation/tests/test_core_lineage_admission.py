"""Synthetic-only admission, evidence reuse, execution isolation and Google tests."""
from contextlib import ExitStack, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import core_v2_admission as admission
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_preflight as preflight
import core_v2_runner as runner
import provider_adapters as adapters
import test_core_readiness_recovery as recovery_fixture


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


scoped = module("synthetic_scoped", HERE.parent / "runtime/prepare-core-v2-scoped.py")
google = module("synthetic_google", HERE.parent / "runtime/admit-core-v2-google.py")
STAMP = "2026-10-06T02:00:00Z"


class AdmissionTests(unittest.TestCase):
    def fixture(self, root, stack):
        original, report_path = recovery_fixture.RecoveryTests().fixture(root, stack)
        freeze = json.loads(original.freeze.read_text())
        terms = root / "terms.json"
        terms.write_text(json.dumps({"official_terms_and_applicable_research_conditions_reviewed_by_human": True,
            "literal_ids_and_material_profiles_frozen_by_human": True}))
        for cfg in freeze["core_api"].values():
            cfg["terms_review_source"] = {"file": str(terms), "sha256": runner.sha256_file(terms)}
        original.freeze.write_text(json.dumps(freeze))
        # Complete this synthetic fixture's Terms binding before reuse; regenerate
        # the synthetic report's own checksum, leaving all response files intact.
        report = json.loads(report_path.read_text())
        report["provider_freeze_sha256"] = runner.sha256_file(original.freeze)
        report_path.write_text(json.dumps(report))
        sums = report_path.parent / "SHA256SUMS.txt"
        sums.write_text("\n".join(f"{runner.sha256_file(p)}  {p.relative_to(report_path.parent)}"
            for p in sorted(report_path.parent.rglob("*")) if p.is_file() and p != sums) + "\n")
        fake_source = root / "code"
        config = fake_source / "automation/config"
        config.mkdir(parents=True)
        (config / "core_v2_agent_provider_freeze.draft.json").write_text(json.dumps(freeze))
        protocol = json.loads(original.protocol.read_text())
        protocol.update(schema_version="2.0.2", protocol_version="2.0.2",
            protocol_registration_id="synthetic-scoped-registration",
            prior_agent_amendment_registration_id="https://github.com/mibo-research/mibo-core/blob/3045cbacaa15d19699deb8e79d1c7465b7d2f343/docs/v2.0.1/AMENDMENT_v2.0.1.md",
            lineage_admission_policy=admission.POLICY)
        protocol_path = root / "scoped-protocol.json"
        protocol_path.write_text(json.dumps(protocol))
        destination = root / "scoped-readiness"
        stack.enter_context(mock.patch.object(scoped, "SOURCE", fake_source))
        stack.enter_context(mock.patch.object(scoped, "now", return_value=STAMP))
        built = scoped.build_scoped(old_report_path=report_path,
            old_freeze_path=original.freeze, protocol_path=protocol_path, out_dir=destination)
        return original, report_path, destination, built

    def authorize(self, destination, built, scope=admission.INITIAL_SCOPE):
        path = destination / "core_v2_execution_authorization.scoped.json"
        auth = json.loads((destination / "bundle/core_v2_execution_authorization.template.json").read_text())
        auth.update(authorized=True, authorized_at_utc="2026-10-06T02:01:00Z", operations_lead="synthetic-human",
            terms_review_complete=True, authorize_confirmatory_api_core=True,
            prospective_agent_amendment_reviewed=True,
            late_activation_with_original_windows_approved=True,
            prospective_lineage_admission_amendment_reviewed=True)
        path.write_text(json.dumps(auth))
        return path

    def check(self, destination, built, auth, root):
        base = destination / "bundle"
        return executor.preflight(protocol_path=base / built["protocol_file"],
            freeze_path=base / built["provider_freeze_file"], manifest_path=base / built["manifest_file"],
            authorization_path=auth, data_root=root / "data",
            now=datetime(2026, 10, 6, 2, 2, tzinfo=timezone.utc))

    def test_reuses_exact_evidence_keeps_1120_rows_and_unauthorized_template(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            old, report, dest, built = self.fixture(Path(d), stack)
            before = {p: p.read_bytes() for p in report.parent.rglob("*") if p.is_file()}
            self.assertEqual(built["initial_request_count"], 1120)
            self.assertEqual(built["admitted_request_count"], 840)
            self.assertFalse(built["all_four_ready"])
            auth = json.loads((dest / "bundle/core_v2_execution_authorization.template.json").read_text())
            self.assertFalse(auth["authorized"])
            self.assertIsNone(auth["authorized_at_utc"])
            for path, value in before.items():
                self.assertEqual(path.read_bytes(), value)
            new_rows = runner.read_csv(dest / "bundle" / built["manifest_file"])
            old_rows = runner.read_csv(old.manifest)
            for a, b in zip(old_rows, new_rows):
                for key in ("attempt_id", "query_sha256", "query_form_id", "execution_order", "window_id", "random_seed"):
                    self.assertEqual(a[key], b[key])

    def test_preflight_filters_google_and_does_not_require_its_credential(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, dest, built = self.fixture(Path(d), stack)
            auth = self.authorize(dest, built)
            rows, frozen, _, _, _ = self.check(dest, built, auth, Path(d))
            self.assertEqual(len(rows), 840)
            self.assertEqual({r["service_lineage_id"] for r in rows}, set(admission.INITIAL_SCOPE))
            os.environ.pop(frozen["core_api"]["MIBO-SL-003"]["request_profile"]["api_key_env"], None)
            executor._validate_credentials(rows, frozen)
            with self.assertRaises(ValueError):
                executor._validate_credentials(runner.read_csv(dest / "bundle" / built["manifest_file"]), frozen)

    def test_arbitrary_scope_backdated_auth_or_tampered_evidence_block(self):
        for mode in ("scope", "time", "tamper", "review"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, dest, built = self.fixture(Path(d), stack)
                auth = self.authorize(dest, built)
                data = json.loads(auth.read_text())
                if mode == "scope": data["admitted_lineages"] = ["MIBO-SL-001", "MIBO-SL-003"]
                if mode == "time": data["authorized_at_utc"] = "2026-10-06T00:06:30Z"
                if mode == "review": data["prospective_lineage_admission_amendment_reviewed"] = False
                if mode == "tamper":
                    report = json.loads(Path(data["readiness_report_file"]).read_text())
                    Path(report["synthetic_smoke_checks"][0]["file"]).write_text("{}")
                auth.write_text(json.dumps(data))
                with self.assertRaises(ValueError): self.check(dest, built, auth, Path(d))

    def test_prior_versions_block_and_new_archive_is_separate(self):
        for version in ("2.0", "2.0.1"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, dest, built = self.fixture(Path(d), stack)
                auth = self.authorize(dest, built)
                path = archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", version) / "failures"
                path.mkdir(parents=True); (path / "existing.json").write_text("{}")
                with self.assertRaisesRegex(ValueError, "no mid-wave"):
                    self.check(dest, built, auth, Path(d))

    def test_executor_submits_only_admitted_lineages_and_preserves_dispatch(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, dest, built = self.fixture(Path(d), stack)
            auth = self.authorize(dest, built)
            checked = self.check(dest, built, auth, Path(d))
            rows = [next(r for r in checked[0] if r["service_lineage_id"] == sid and r["window_id"] == "STD") for sid in admission.INITIAL_SCOPE]
            stack.enter_context(mock.patch.object(executor, "preflight", return_value=(rows, *checked[1:])))
            stack.enter_context(mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}))
            called = stack.enter_context(mock.patch.object(executor, "call_provider", side_effect=recovery_fixture.RecoveryTests().result))
            base = dest / "bundle"
            summary = executor.execute(protocol_path=base / built["protocol_file"],
                freeze_path=base / built["provider_freeze_file"], manifest_path=base / built["manifest_file"],
                authorization_path=auth, data_root=Path(d) / "data")
            self.assertEqual(summary["valid"], 3)
            self.assertEqual({c.kwargs["provider"] for c in called.call_args_list}, {"OpenAI", "Anthropic", "Perplexity AI"})
            wave = archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", "2.0.2")
            self.assertEqual(len(list((wave / "metadata").glob("first-dispatch-*.json"))), 3)
            self.assertEqual(len(executor._processed_attempt_ids(Path(d) / "data", "JP01", "MIBO2-W01", "2.0.2")), 3)

    def test_google_pass_builds_unsigned_280_scope_with_identical_manifest(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, _, dest, built = self.fixture(Path(d), stack)
            auth = self.authorize(dest, built)
            stack.enter_context(mock.patch.object(google.scoped, "now", return_value="2026-10-06T02:05:00Z"))
            called = stack.enter_context(mock.patch.object(google, "call_provider", side_effect=recovery_fixture.RecoveryTests().result))
            result = google.probe(readiness=dest, current=datetime(2026, 10, 6, 2, 3, tzinfo=timezone.utc))
            self.assertEqual(called.call_count, 1)
            self.assertEqual(called.call_args.kwargs["prompt"], preflight.SYNTHETIC_PROMPT)
            self.assertEqual(called.call_args.kwargs["provider"], "Google")
            self.assertEqual(result["bundle"]["manifest_sha256"], built["manifest_sha256"])
            self.assertEqual(result["bundle"]["admitted_request_count"], 280)
            template = json.loads((result["out_dir"] / "bundle/core_v2_execution_authorization.template.json").read_text())
            self.assertFalse(template["authorized"])
            with self.assertRaises(ValueError): self.check(result["out_dir"], result["bundle"], result["out_dir"] / "bundle/core_v2_execution_authorization.template.json", Path(d))
            with self.assertRaisesRegex(ValueError, "already passed"):
                google.probe(readiness=dest, current=datetime(2026, 10, 6, 2, 6, tzinfo=timezone.utc))
            self.assertEqual(called.call_count, 1)

    def test_google_failure_waits_and_cap_preserve_original_evidence(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            _, report, dest, built = self.fixture(Path(d), stack)
            self.authorize(dest, built)
            original = report.read_bytes()
            failed = stack.enter_context(mock.patch.object(google, "call_provider", side_effect=adapters.AdapterFailure(
                "provider_error", "synthetic", 503, response_body="synthetic-private-key")))
            for index, stamp in enumerate(("2026-10-06T02:03:00Z", "2026-10-06T02:13:00Z", "2026-10-06T02:43:00Z")):
                with mock.patch.object(google.scoped, "now", return_value=stamp), self.assertRaises(ValueError):
                    google.probe(readiness=dest, current=runner.parse_aware_utc(stamp))
                if index == 0:
                    with self.assertRaisesRegex(ValueError, "wait has not elapsed"):
                        google.probe(readiness=dest, current=runner.parse_aware_utc("2026-10-06T02:04:00Z"))
                    self.assertEqual(failed.call_count, 1)
            self.assertEqual(failed.call_count, 3)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                google.probe(readiness=dest, current=runner.parse_aware_utc("2026-10-06T03:43:00Z"))
            self.assertEqual(failed.call_count, 3)
            self.assertEqual(report.read_bytes(), original)
            for path in (dest / "google-recovery-block").glob("probe-*/RESULT.json"):
                self.assertNotIn("synthetic-private-key", path.read_text())

    def test_google_mismatch_or_expired_field_prevents_more_calls(self):
        from dataclasses import replace
        for mode in ("mismatch", "closed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, dest, built = self.fixture(Path(d), stack)
                self.authorize(dest, built)
                def wrong(**kwargs): return replace(recovery_fixture.RecoveryTests().result(**kwargs), returned_model="synthetic-other")
                called = stack.enter_context(mock.patch.object(google, "call_provider", side_effect=wrong))
                stamp = "2026-10-08T00:00:00Z" if mode == "closed" else "2026-10-06T02:03:00Z"
                with self.assertRaises(ValueError): google.probe(readiness=dest, current=runner.parse_aware_utc(stamp))
                self.assertEqual(called.call_count, 0 if mode == "closed" else 1)
                if mode == "mismatch":
                    with self.assertRaisesRegex(ValueError, "cannot be retried"):
                        google.probe(readiness=dest, current=runner.parse_aware_utc("2026-10-06T03:03:00Z"))
                    self.assertEqual(called.call_count, 1)

    def test_private_human_authorization_starts_scoped_service_only_after_phrase(self):
        for phrase in ("wrong", "AUTHORIZE_READY_THREE"):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                _, _, dest, built = self.fixture(Path(d), stack)
                units = Path(d) / "units"; units.mkdir()
                (scoped.SOURCE / "INSTALL_PROVENANCE.json").write_text(json.dumps({"source_commit_sha": "c" * 40}))
                reader = io.StringIO("synthetic-human\n" + phrase + "\n")
                writer = io.StringIO()
                stack.enter_context(mock.patch("builtins.open", side_effect=[reader, writer]))
                stack.enter_context(mock.patch.object(scoped, "UNIT_DIR", units))
                stack.enter_context(mock.patch.object(scoped, "permissions"))
                stack.enter_context(mock.patch.object(scoped.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=os.getgid())))
                stack.enter_context(mock.patch("pwd.getpwnam", return_value=SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())))
                run = stack.enter_context(mock.patch.object(scoped.subprocess, "run"))
                stack.enter_context(mock.patch.object(scoped.subprocess, "check_output", return_value="ActiveState=active\nSubState=running\n"))
                original_preflight = executor.preflight
                def timed(**kwargs): return original_preflight(**kwargs, now=runner.parse_aware_utc("2026-10-06T02:02:00Z"))
                stack.enter_context(mock.patch.object(executor, "preflight", side_effect=timed))
                values = {cfg["request_profile"]["api_key_env"]: "synthetic-only"
                    for cfg in json.loads((dest / "bundle" / built["provider_freeze_file"]).read_text())["core_api"].values()}
                with redirect_stdout(io.StringIO()):
                    if phrase == "wrong":
                        with self.assertRaisesRegex(ValueError, "human execution"):
                            scoped.authorize_and_start(out_dir=dest, built=built, data_root=Path(d) / "data", values=values)
                        run.assert_not_called()
                        self.assertFalse((dest / "core_v2_execution_authorization.scoped.json").exists())
                    else:
                        scoped.authorize_and_start(out_dir=dest, built=built, data_root=Path(d) / "data", values=values)
                        unit = (units / scoped.SERVICE).read_text()
                        self.assertIn("Type=simple", unit)
                        self.assertIn("TimeoutStartSec=infinity", unit)
                        self.assertNotIn("GEMINI_API_KEY", (dest / "ready-three.env").read_text())
                        self.assertIn(mock.call(["systemctl", "enable", "--now", scoped.SERVICE], check=True), run.call_args_list)
                        auth = json.loads((dest / "core_v2_execution_authorization.scoped.json").read_text())
                        self.assertEqual(auth["explicit_human_phrase"], phrase)
                        self.assertEqual(auth["admitted_lineages"], admission.INITIAL_SCOPE)


if __name__ == "__main__":
    unittest.main()
