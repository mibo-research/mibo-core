"""Synthetic-only generic close tests. Never control a real unit or dispatch API calls."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
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
import core_v2_archive as archive
import core_v2_runner as runner
from test_core_v2_api import CoreV2Fixture

spec = importlib.util.spec_from_file_location("generic_wave_close", HERE.parent / "runtime/close-core-v2-wave.py")
close = importlib.util.module_from_spec(spec)
spec.loader.exec_module(close)


class GenericCloseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fixture = CoreV2Fixture(self.base)
        self.after = datetime(2026, 11, 6, tzinfo=timezone.utc)
        self.configure("MIBO2-W02")

    def tearDown(self):
        for path in self.base.rglob("*"):
            if path.is_dir():
                path.chmod(0o700)
            elif path.is_file():
                path.chmod(0o600)
        self.temp.cleanup()

    def configure(self, wave):
        frozen = json.loads(self.fixture.freeze.read_text())
        frozen["wave_id"] = wave
        self.fixture.freeze.write_text(json.dumps(frozen))
        self.fixture.manifest.unlink()
        self.rows = runner.generate_manifest(protocol_path=self.fixture.protocol,
            freeze_path=self.fixture.freeze, wave_id=wave, site_id="JP01")
        runner.write_csv(self.rows, self.fixture.manifest)
        auth = json.loads(self.fixture.authorization.read_text())
        auth.update(wave_id=wave, manifest_sha256=close.sha(self.fixture.manifest),
                    provider_freeze_sha256=close.sha(self.fixture.freeze))
        self.fixture.authorization.write_text(json.dumps(auth))
        self.data = self.base / "data"
        self.root = self.data / "v2.0/JP01" / wave
        self.root.mkdir(parents=True, exist_ok=True)
        for folder in ("api_raw", "metadata", "failures", "deviations"):
            (self.root / folder).mkdir(exist_ok=True)
        self.backup = self.base / "private"
        self.backup.mkdir(exist_ok=True)
        self.env = self.base / "collector.env"
        self.env.write_text("MIBO_CORE_V2_EXECUTION=DISABLED\nSYNTHETIC_API_KEY=private-do-not-print\n")
        source = self.base / "source"
        (source / "automation").mkdir(parents=True, exist_ok=True)
        (source / "automation/core_v2_waiter.py").write_text("# synthetic collector; never executed\n")
        (source / "INSTALL_PROVENANCE.json").write_text('{"source_commit_sha":"synthetic-close-test"}')
        self.unit = self.base / "synthetic.service"
        command = f"/usr/bin/python3 -B {source}/automation/core_v2_waiter.py --protocol {self.fixture.protocol} --wave {wave} --manifest {self.fixture.manifest} --freeze {self.fixture.freeze} --authorization {self.fixture.authorization} --data-root {self.data}"
        self.unit.write_text(f"[Service]\nEnvironmentFile={self.env}\nExecStart={command}\n")
        self.inputs = {"protocol": self.fixture.protocol, "manifest": self.fixture.manifest,
            "freeze": self.fixture.freeze, "authorization": self.fixture.authorization}
        entry = {"version": "2.0", "unit": "synthetic.service", "unit_file": str(self.unit),
            "environment_file": str(self.env), "lineages": sorted(close.LINEAGES),
            **{key: str(path) for key, path in self.inputs.items()},
            "expected_hashes": {key: close.sha(path) for key, path in self.inputs.items()}}
        self.config = self.base / "close.json"
        self.config.write_text(json.dumps({"schema_version": "core-v2-wave-close-1", "wave_id": wave,
            "site_id": "JP01", "data_root": str(self.data), "backup_parent": str(self.backup),
            "namespaces": [entry]}))
        self.save_capture(self.rows[0])

    def state(self, *args, **kwargs):
        return "ActiveState=inactive\nMainPID=0\nUnitFileState=disabled\nControlGroup=\nResult=success\nFragmentPath=" + str(self.unit) + "\nDropInPaths=\nEnvironment=\n"

    def prepare(self, current=None):
        with mock.patch.object(close.subprocess, "check_output", side_effect=self.state), mock.patch.object(close, "verify_no_collector"), mock.patch.dict(os.environ, {close.SENTINEL: "DISABLED"}):
            return close.prepare(self.config, current=current or self.after)

    def save_capture(self, row, *, started=None, completed=None):
        stamp = "2026-10-06T00:01:" if row["wave_id"] == "MIBO2-W01" else "2026-11-03T00:01:"
        return archive.archive_success(data_root=self.data, row=row,
            request_payload={"synthetic": True}, response_json={"synthetic": True},
            raw_response_text="SYNTHETIC_PRIVATE_ANSWER", http_status=200,
            returned_model=row["model_id"], usage={}, started_at_utc=started or stamp + "00Z",
            completed_at_utc=completed or stamp + "01Z", duration_ms=1000)

    def dispatch(self, row, stamp="2026-11-03T00:00:30Z"):
        archive.archive_dispatch(data_root=self.data, row=row)
        path = self.root / "dispatch" / (row["attempt_id"] + ".json")
        record = json.loads(path.read_text())
        record["dispatch_at_utc"] = stamp
        path.write_text(json.dumps(record))

    def test_w02_retains_all_960_planned_rows_and_missingness(self):
        config, work = self.prepare()
        self.assertEqual(len(work[0]["cells"]), 960)
        self.assertEqual(sum(s["captured"] for s in work[0]["summary"].values()), 1)
        self.assertTrue(all(s["planned"] == 240 for s in work[0]["summary"].values()))
        self.assertFalse((self.root / "closure").exists())

    def test_w01_calibration_denominator_comes_from_protocol(self):
        self.configure("MIBO2-W01")
        _, work = self.prepare()
        self.assertEqual(len(work[0]["cells"]), 1120)
        self.assertTrue(all(s["planned"] == 280 for s in work[0]["summary"].values()))
        self.assertEqual({w: sum(row[4] == w for row in work[0]["cells"]) for w in ("WA", "STD", "WB")}, {"WA": 160, "STD": 800, "WB": 160})

    def test_open_window_cannot_be_closed(self):
        with self.assertRaisesRegex(ValueError, "remains open"):
            self.prepare(datetime(2026, 11, 4, tzinfo=timezone.utc))

    def test_reviewed_input_hash_mismatch_aborts(self):
        self.fixture.authorization.write_text(self.fixture.authorization.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "input hash mismatch"):
            self.prepare()

    def test_missing_or_sealed_wave_is_never_created_or_rewritten(self):
        renamed = self.root.with_name("unexecuted-synthetic")
        self.root.rename(renamed)
        with self.assertRaisesRegex(ValueError, "absent/unexecuted"):
            self.prepare()
        self.assertFalse(self.root.exists())
        renamed.rename(self.root)
        (self.root / "SHA256SUMS.txt").write_text("synthetic-sealed")
        before = close.sha(self.root / "SHA256SUMS.txt")
        with self.assertRaisesRegex(ValueError, "already sealed"):
            self.prepare()
        self.assertEqual(close.sha(self.root / "SHA256SUMS.txt"), before)

    def test_partial_closure_aborts(self):
        (self.root / "closure").mkdir()
        with self.assertRaisesRegex(ValueError, "partially closed"):
            self.prepare()

    def test_unresolved_dispatch_blocks_close_without_resend(self):
        self.dispatch(self.rows[1])
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            self.prepare()
        self.assertFalse((self.root / "closure").exists())

    def test_terminal_dispatch_and_retry_capture_are_linked(self):
        row = self.rows[1]
        self.dispatch(row)
        archive.archive_failure(data_root=self.data, row=row, failure_kind="provider_error",
            message="synthetic", failed_at_utc="2026-11-03T00:02:00Z", http_status=503)
        retry = close.executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data, original_attempt_id=row["attempt_id"],
            retry_attempt_id=retry["attempt_id"], site_id="JP01", wave_id="MIBO2-W02",
            due_at_utc="2026-11-03T00:12:00Z", failure_kind="provider_error", protocol_version="2.0")
        self.dispatch(retry, "2026-11-03T00:12:00Z")
        self.save_capture(retry, started="2026-11-03T00:12:01Z", completed="2026-11-03T00:12:02Z")
        _, work = self.prepare()
        self.assertEqual(sum(s["captured"] for s in work[0]["summary"].values()), 2)
        self.assertEqual(sum(n for key, n in work[0]["counts"].items() if key[0] == "attempt"), 3)

    def test_early_or_ineligible_retry_is_rejected(self):
        row = self.rows[1]
        archive.archive_failure(data_root=self.data, row=row, failure_kind="provider_error",
            message="synthetic", failed_at_utc="2026-11-03T00:02:00Z", http_status=503)
        retry = close.executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data, original_attempt_id=row["attempt_id"],
            retry_attempt_id=retry["attempt_id"], site_id="JP01", wave_id="MIBO2-W02",
            due_at_utc="2026-11-03T00:12:00Z", failure_kind="provider_error", protocol_version="2.0")
        self.save_capture(retry, started="2026-11-03T00:01:00Z", completed="2026-11-03T00:01:01Z")
        with self.assertRaisesRegex(ValueError, "before registered due"):
            self.prepare()
        failure_path = self.root / "failures" / (row["attempt_id"] + ".json")
        failure = json.loads(failure_path.read_text())
        failure["failure_kind"] = "request_environment_mismatch"
        failure_path.write_text(json.dumps(failure))
        link_path = self.root / "metadata" / ("retry-link-" + retry["attempt_id"] + ".json")
        link = json.loads(link_path.read_text())
        link["failure_kind"] = "request_environment_mismatch"
        link_path.write_text(json.dumps(link))
        with self.assertRaisesRegex(ValueError, "not eligible"):
            self.prepare()

    def test_retry_due_ignoring_provider_wait_is_rejected(self):
        row = self.rows[1]
        archive.archive_failure(data_root=self.data, row=row, failure_kind="rate_limit",
            message="synthetic", failed_at_utc="2026-11-03T00:02:00Z", http_status=429,
            retry_after_seconds=1200)
        retry = close.executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data, original_attempt_id=row["attempt_id"],
            retry_attempt_id=retry["attempt_id"], site_id="JP01", wave_id="MIBO2-W02",
            due_at_utc="2026-11-03T00:12:00Z", failure_kind="rate_limit", protocol_version="2.0")
        with self.assertRaisesRegex(ValueError, "violates registered wait"):
            self.prepare()

    def test_missing_parent_failure_and_link_are_rejected(self):
        row = self.rows[1]
        retry = close.executor._clone_retry_row(row, 2)
        self.save_capture(retry, started="2026-11-03T00:12:01Z", completed="2026-11-03T00:12:02Z")
        with self.assertRaisesRegex(ValueError, "no verified retry link"):
            self.prepare()
        archive.archive_retry_link(data_root=self.data, original_attempt_id=row["attempt_id"],
            retry_attempt_id=retry["attempt_id"], site_id="JP01", wave_id="MIBO2-W02",
            due_at_utc="2026-11-03T00:12:00Z", failure_kind="provider_error", protocol_version="2.0")
        with self.assertRaisesRegex(ValueError, "retained parent technical failure"):
            self.prepare()

    def test_http_failure_cannot_be_relabelled_capture(self):
        raw = next((self.root / "api_raw").glob("*.json"))
        data = json.loads(raw.read_text()); data["http_status"] = 503
        raw.write_text(json.dumps(data))
        metadata = next((self.root / "metadata").glob("*.json"))
        record = json.loads(metadata.read_text()); record["raw_file_sha256"] = close.sha(raw)
        metadata.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "HTTP status mismatch"):
            self.prepare()

    def test_completion_after_close_is_retained_if_dispatch_start_was_eligible(self):
        raw = next((self.root / "api_raw").glob("*.json"))
        data = json.loads(raw.read_text())
        data.update(started_at_utc="2026-11-04T23:59:59Z", completed_at_utc="2026-11-05T00:00:20Z")
        raw.write_text(json.dumps(data))
        metadata = next((self.root / "metadata").glob("*.json"))
        record = json.loads(metadata.read_text()); record["raw_file_sha256"] = close.sha(raw)
        metadata.write_text(json.dumps(record))
        _, work = self.prepare()
        self.assertEqual(sum(s["captured"] for s in work[0]["summary"].values()), 1)

    def test_mixed_namespaces_keep_separate_closures_and_full_denominator(self):
        # Full protocol/manifest validation stays real. Private readiness/auth
        # lookup alone is replaced by synthetic scoped authorization objects.
        config = json.loads(self.config.read_text())
        source = self.base / "source"
        entries, assigned_rows = [], []
        for version, scope in (("2.0.2", sorted(close.LINEAGES - {"MIBO-SL-003"})),
                               ("2.0.4", ["MIBO-SL-003"])):
            directory = self.base / ("synthetic-" + version); directory.mkdir()
            protocol = json.loads((HERE / "config" / ("core_v2_protocol.v" + version + ".json")).read_text())
            protocol_path = directory / "protocol.json"; protocol_path.write_text(json.dumps(protocol))
            frozen = json.loads((HERE / "config/core_v2_agent_provider_freeze.draft.json").read_text())
            frozen.update(schema_version=version, protocol_version=version,
                protocol_registration_id=protocol["protocol_registration_id"], wave_id="MIBO2-W02",
                frozen_at_utc="2026-11-02T00:00:00Z")
            for cfg in frozen["core_api"].values():
                cfg.update(status="eligible", model_version_locked=True, provider_evidence="synthetic",
                    verified_at_utc="2026-11-02T00:00:00Z", terms_review_date="2026-11-02",
                    terms_review_source="synthetic private evidence")
            freeze = directory / "freeze.json"; freeze.write_text(json.dumps(frozen))
            rows = runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze,
                wave_id="MIBO2-W02", site_id="JP01")
            manifest = directory / "manifest.csv"; runner.write_csv(rows, manifest)
            auth = directory / "authorization.json"; auth.write_text('{"synthetic_only":true}')
            unit = directory / ("collector-" + version + ".service")
            env = directory / "collector.env"; env.write_text("MIBO_CORE_V2_EXECUTION=DISABLED\n")
            unit.write_text(f"[Service]\nEnvironmentFile={env}\nExecStart=/usr/bin/python3 -B {source}/automation/core_v2_waiter.py --protocol {protocol_path} --wave MIBO2-W02 --manifest {manifest} --freeze {freeze} --authorization {auth} --data-root {self.data}\n")
            inputs = {"protocol": protocol_path, "manifest": manifest, "freeze": freeze, "authorization": auth}
            entries.append({"version": version, "lineages": scope, "unit": unit.name,
                "unit_file": str(unit), "environment_file": str(env),
                **{key: str(path) for key, path in inputs.items()},
                "expected_hashes": {key: close.sha(path) for key, path in inputs.items()}})
            row = next(row for row in rows if row["service_lineage_id"] in scope)
            assigned_rows.append(row)
            self.save_capture(row)
        config["namespaces"] = entries; self.config.write_text(json.dumps(config))
        unit_lookup = {entry["unit"]: entry["unit_file"] for entry in entries}
        def state(command, **kwargs):
            return self.state().replace(str(self.unit), unit_lookup[command[2]])
        def authorization(path, **kwargs):
            return {"admitted_lineages": next(entry["lineages"] for entry in entries if Path(entry["authorization"]) == path)}
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(close.subprocess, "check_output", side_effect=state))
            stack.enter_context(mock.patch.object(close, "verify_no_collector"))
            stack.enter_context(mock.patch.object(close.executor, "load_authorization", side_effect=authorization))
            stack.enter_context(mock.patch.object(close.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=os.getgid())))
            stack.enter_context(mock.patch.object(close.os, "sync"))
            stack.enter_context(mock.patch.dict(os.environ, {close.SENTINEL: "DISABLED"}))
            prepared, work = close.prepare(self.config, current=self.after)
            self.assertEqual(sum(len(item["cells"]) for item in work), 960)
            self.assertEqual([len(item["cells"]) for item in work], [720, 240])
            result = close.finish(prepared, work, "Synthetic Operations Lead")
        self.assertTrue(result.is_file())
        for row in assigned_rows:
            root = self.data / ("v" + row["protocol_version"]) / "JP01/MIBO2-W02"
            record = json.loads((root / "closure/COMPLETION_RECORD.json").read_text())
            self.assertEqual(sum(s["captured"] for s in record["summary"].values()), 1)

    def test_capture_hash_or_frozen_identity_mismatch_aborts(self):
        raw = next((self.root / "api_raw").glob("*.json"))
        data = json.loads(raw.read_text())
        data["query_sha256"] = "forged"
        raw.write_text(json.dumps(data))
        metadata = next((self.root / "metadata").glob("*.json"))
        record = json.loads(metadata.read_text())
        record["raw_file_sha256"] = close.sha(raw)
        metadata.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "frozen design mismatch"):
            self.prepare()

    def test_symlink_and_orphan_raw_abort(self):
        extra = self.root / "api_raw/orphan.json"
        extra.write_text("{}")
        with self.assertRaisesRegex(ValueError, "Unlinked"):
            self.prepare()
        extra.unlink()
        extra.symlink_to(self.fixture.authorization)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.prepare()

    def test_unit_or_sentinel_failure_aborts(self):
        with mock.patch.object(close.subprocess, "check_output", return_value=self.state().replace("ActiveState=inactive", "ActiveState=active")), mock.patch.object(close, "verify_no_collector"):
            with self.assertRaisesRegex(ValueError, "inactive and disabled"):
                close.prepare(self.config, current=self.after)
        self.env.write_text("MIBO_CORE_V2_EXECUTION=ENABLED_AFTER_CORE_V2_GATE\n")
        with self.assertRaisesRegex(ValueError, "sentinel"):
            self.prepare()

    def test_scope_does_not_follow_config_without_authorization(self):
        config = json.loads(self.config.read_text())
        config["namespaces"][0]["lineages"] = ["MIBO-SL-003"]
        self.config.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "private execution authorization"):
            self.prepare()

    def test_blank_signoff_and_toctou_do_not_mutate(self):
        config, work = self.prepare()
        with self.assertRaisesRegex(ValueError, "sign-off"):
            close.finish(config, work, "")
        (self.root / "deviations/new.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Evidence changed"):
            close.finish(config, work, "Synthetic Operations Lead")
        self.assertFalse((self.root / "closure").exists())

    def test_full_close_archive_verifies_and_backup_stays_unverified(self):
        config, work = self.prepare()
        out = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(close.subprocess, "check_output", side_effect=self.state))
            stack.enter_context(mock.patch.object(close, "verify_no_collector"))
            stack.enter_context(mock.patch.object(close.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=os.getgid())))
            stack.enter_context(mock.patch.object(close.os, "sync"))
            stack.enter_context(mock.patch.dict(os.environ, {close.SENTINEL: "DISABLED"}))
            stack.enter_context(redirect_stdout(out))
            result = close.finish(config, work, "Synthetic Operations Lead")
        self.assertTrue(result.is_file())
        record = json.loads((self.root / "closure/COMPLETION_RECORD.json").read_text())
        self.assertEqual(record["independent_backup_at_signoff"], "not_verified")
        self.assertTrue(record["capture_is_not_content_analysis_eligibility"])
        self.assertEqual(record["operations_lead"], "Synthetic Operations Lead")
        receipt = json.loads((result.parent / "CLOSE_RECEIPT.json").read_text())
        self.assertIn("same_VM", receipt["backup_scope"])
        self.assertTrue(all(not path.stat().st_mode & 0o222 for path in [self.root] + list(self.root.rglob("*"))))
        self.assertNotIn("SYNTHETIC_PRIVATE_ANSWER", out.getvalue())
        self.assertNotIn("private-do-not-print", out.getvalue())

    def test_cli_does_not_print_secret_from_unexpected_errors(self):
        stderr = io.StringIO()
        with mock.patch.object(close, "main", side_effect=ValueError("SYNTHETIC_PRIVATE_API_SECRET")), redirect_stderr(stderr):
            self.assertEqual(close.run_cli([]), 1)
        self.assertIn("ValueError", stderr.getvalue())
        self.assertNotIn("SYNTHETIC_PRIVATE_API_SECRET", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
