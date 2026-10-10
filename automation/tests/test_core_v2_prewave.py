"""Synthetic deployment regressions; these tests never call provider APIs."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_prewave as prewave
import core_v2_runner as runner
import core_v2_waiter as waiter
from test_core_v2_api import CoreV2Fixture, sha256_file

BEFORE = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
START = datetime(2026, 11, 3, tzinfo=timezone.utc)
CLOSE = datetime(2026, 11, 5, tzinfo=timezone.utc)
CREDS = {
    "MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL,
    "OPENAI_API_KEY": "synthetic-secret-openai",
    "ANTHROPIC_API_KEY": "synthetic-secret-anthropic",
    "GEMINI_API_KEY": "synthetic-secret-google",
    "PERPLEXITY_API_KEY": "synthetic-secret-perplexity",
}


class WaveTwoFixture(CoreV2Fixture):
    def __init__(self, root):
        super().__init__(root)
        freeze = json.loads(self.freeze.read_text())
        freeze["wave_id"] = "MIBO2-W02"
        self.freeze.write_text(json.dumps(freeze))
        self.manifest.unlink()
        runner.write_csv(runner.generate_manifest(protocol_path=self.protocol,
            freeze_path=self.freeze, wave_id="MIBO2-W02", site_id="JP01"), self.manifest)
        auth = json.loads(self.authorization.read_text())
        auth.update(wave_id="MIBO2-W02", provider_freeze_sha256=sha256_file(self.freeze),
                    manifest_sha256=sha256_file(self.manifest))
        self.authorization.write_text(json.dumps(auth))
        self.data_root = root / "data"
        self.data_root.mkdir()

    def args(self):
        return dict(protocol_path=self.protocol, manifest_path=self.manifest,
                    freeze_path=self.freeze, authorization_path=self.authorization,
                    data_root=self.data_root, wave_id="MIBO2-W02")

    def rehash_auth(self):
        auth = json.loads(self.authorization.read_text())
        auth.update(provider_freeze_sha256=sha256_file(self.freeze),
                    manifest_sha256=sha256_file(self.manifest))
        self.authorization.write_text(json.dumps(auth))


class CoreV2PrewaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = WaveTwoFixture(Path(self.tmp.name))
        self.env = mock.patch.dict(os.environ, CREDS, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.clock = mock.patch.object(prewave.runtime_health, "ntp_state", return_value={
            "check_available": True, "ntp_synchronized": True, "raw": "yes"})
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.call = mock.patch.object(executor, "call_provider", side_effect=AssertionError("live call forbidden"))
        self.call_mock = self.call.start()
        self.addCleanup(self.call.stop)
        self.addCleanup(self.call_mock.assert_not_called)

    def check(self, **kwargs):
        return prewave.validate_prewave(**self.fixture.args(), now=BEFORE, **kwargs)

    def test_w02_validates_before_start_without_creating_observations(self):
        report = self.check()
        self.assertEqual(report["phase"], "armed_before_registered_start")
        self.assertEqual(report["intended_initial_cells"], 960)
        self.assertEqual(set(report["intended_cells_by_lineage"].values()), {240})
        self.assertEqual(report["registered_start_utc"], "2026-11-03T00:00:00Z")
        self.assertEqual(report["registered_close_utc"], "2026-11-05T00:00:00Z")
        self.assertEqual(report["provider_calls_made"], 0)
        self.assertFalse(report["observation_files_created"])
        self.assertEqual(list(self.fixture.data_root.iterdir()), [])
        for secret in CREDS.values():
            if secret.startswith("synthetic-secret"):
                self.assertNotIn(secret, json.dumps(report))
        # A prestart check does not relax the executor's execution window.
        with self.assertRaisesRegex(ValueError, "outside"):
            executor.preflight(**{k: v for k, v in self.fixture.args().items() if k != "wave_id"}, now=BEFORE)

    def test_stale_w01_configuration_is_rejected_before_waiting(self):
        with tempfile.TemporaryDirectory() as d:
            old = CoreV2Fixture(Path(d))
            args = self.fixture.args()
            args.update(protocol_path=old.protocol, manifest_path=old.manifest,
                        freeze_path=old.freeze, authorization_path=old.authorization)
            with self.assertRaisesRegex(ValueError, "wave/site"):
                prewave.validate_prewave(**args, now=BEFORE)

    def test_rehashed_execution_order_drift_is_still_rejected(self):
        rows = runner.read_csv(self.fixture.manifest)
        rows[0]["execution_order"], rows[1]["execution_order"] = rows[1]["execution_order"], rows[0]["execution_order"]
        self.fixture.manifest.unlink()
        runner.write_csv(rows, self.fixture.manifest)
        self.fixture.rehash_auth()
        errors = runner.validate_manifest(rows, protocol_path=self.fixture.protocol,
                                          freeze_path=self.fixture.freeze)
        self.assertTrue(any("deterministic manifest execution_order" in error for error in errors))
        with self.assertRaisesRegex(ValueError, "deterministic manifest execution_order"):
            self.check()

    def test_unsigned_template_future_signature_and_hash_drift_fail(self):
        original = self.fixture.authorization.read_text()
        for change, message in (({"authorized": False}, "gate authorized"),
                                ({"authorized_at_utc": "2026-11-03T00:00:00Z"}, "timestamps"),
                                ({"manifest_sha256": "0" * 64}, "manifest_sha256 mismatch")):
            with self.subTest(change=change):
                auth = json.loads(original)
                auth.update(change)
                self.fixture.authorization.write_text(json.dumps(auth))
                with self.assertRaisesRegex(ValueError, message):
                    self.check()
        self.fixture.authorization.write_text(original)

    def test_missing_credential_and_disabled_sentinel_fail_without_values(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY") as caught:
                self.check()
            self.assertNotIn(CREDS["OPENAI_API_KEY"], str(caught.exception))
        with mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": "DISABLED"}):
            with self.assertRaisesRegex(ValueError, "sentinel"):
                self.check()

    def test_closed_window_and_naive_clock_fail(self):
        with self.assertRaisesRegex(ValueError, "closed"):
            prewave.validate_prewave(**self.fixture.args(), now=CLOSE)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            prewave.validate_prewave(**self.fixture.args(), now=BEFORE.replace(tzinfo=None))

    def test_closed_wave_is_rejected_without_modification(self):
        root = archive.wave_root(self.fixture.data_root, "JP01", "MIBO2-W02")
        root.mkdir(parents=True)
        sums = root / "SHA256SUMS.txt"
        sums.write_text("retained original seal\n")
        with self.assertRaisesRegex(ValueError, "closed or sealed"):
            self.check()
        self.assertEqual(sums.read_text(), "retained original seal\n")

    def test_attempts_before_registered_start_block_new_arming(self):
        root = archive.wave_root(self.fixture.data_root, "JP01", "MIBO2-W02", "2.0.1")
        (root / "failures").mkdir(parents=True)
        marker = root / "failures" / "synthetic.json"
        marker.write_text("{}")
        with self.assertRaisesRegex(ValueError, "retained wave attempts"):
            self.check()
        self.assertEqual(marker.read_text(), "{}")

    def test_target_namespace_escape_and_write_permissions_fail(self):
        with tempfile.TemporaryDirectory() as other:
            (self.fixture.data_root / "v2.0").symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.check()
        (self.fixture.data_root / "v2.0").unlink()
        other_wave = self.fixture.data_root / "other-wave"
        other_wave.mkdir()
        (self.fixture.data_root / "v2.0").symlink_to(other_wave, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()
        (self.fixture.data_root / "v2.0").unlink()
        with mock.patch.object(prewave.tempfile, "TemporaryDirectory", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                self.check()

    def test_strict_vm_hostname_and_reviewed_commit_are_enforced(self):
        with mock.patch.object(prewave.socket, "gethostname", return_value="cloudshell"):
            with self.assertRaisesRegex(ValueError, "hostname mismatch"):
                self.check(expected_host="mibo-runtime-jp01")
        with self.assertRaisesRegex(ValueError, "explicit host and source commit"):
            self.check(strict_runtime=True)
        with mock.patch.object(prewave.socket, "gethostname", return_value="mibo-runtime-jp01"), \
             mock.patch.object(prewave.runtime_health, "provenance_state", return_value={
                 "commit_sha": "a" * 40, "commit_resolved": True, "working_tree_clean": True}):
            report = self.check(strict_runtime=True, expected_host="mibo-runtime-jp01",
                                expected_source_commit="a" * 40)
            self.assertTrue(report["runtime"]["strict_runtime"])
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                self.check(expected_source_commit="b" * 40)
        with self.assertRaisesRegex(ValueError, "40-hex"):
            self.check(expected_source_commit="main")

    def test_unknown_clock_and_source_tampering_block_strict_runtime(self):
        with mock.patch.object(prewave.runtime_health, "provenance_state", return_value={
                "commit_sha": "a" * 40, "commit_resolved": True, "working_tree_clean": False}):
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                self.check(expected_source_commit="a" * 40)
        for clock in ({"check_available": True, "ntp_synchronized": False},
                      {"check_available": False, "ntp_synchronized": None}):
            with self.subTest(clock=clock), \
                 mock.patch.object(prewave.socket, "gethostname", return_value="vm"), \
                 mock.patch.object(prewave.runtime_health, "provenance_state", return_value={
                     "commit_sha": "a" * 40, "commit_resolved": True, "working_tree_clean": True}), \
                 mock.patch.object(prewave.runtime_health, "ntp_state", return_value=clock):
                with self.assertRaisesRegex(ValueError, "clock"):
                    self.check(strict_runtime=True, expected_host="vm", expected_source_commit="a" * 40)

    def test_low_storage_and_symlink_input_block_preparation(self):
        with mock.patch.object(prewave.shutil, "disk_usage", return_value=type("U", (), {"free": 1})()):
            with self.assertRaisesRegex(ValueError, "2 GiB"):
                self.check()
        original = self.fixture.protocol
        link = original.with_name("linked-protocol.json")
        link.symlink_to(original)
        self.fixture.protocol = link
        with self.assertRaisesRegex(ValueError, "absolute regular files"):
            self.check()
        alias = original.parent / "configuration-alias"
        alias.symlink_to(original.parent, target_is_directory=True)
        self.fixture.protocol = alias / original.name
        with self.assertRaisesRegex(ValueError, "absolute regular files"):
            self.check()


class CoreV2WaiterTests(unittest.TestCase):
    def report(self):
        return {"phase": "armed_before_registered_start",
                "registered_start_utc": "2026-11-03T00:00:00Z",
                "registered_close_utc": "2026-11-05T00:00:00Z",
                "input_hashes": {"protocol_file_sha256": "a" * 64}}

    def argv(self):
        return ["waiter", "--protocol", "/private/protocol", "--wave", "MIBO2-W02",
                "--manifest", "/private/manifest", "--freeze", "/private/freeze",
                "--authorization", "/private/auth", "--data-root", "/data"]

    def test_waiter_validates_before_sleep_and_again_at_dispatch(self):
        with mock.patch.object(sys, "argv", self.argv()), \
             mock.patch.object(waiter.prewave, "validate_prewave", return_value=self.report()) as gate, \
             mock.patch.object(waiter, "datetime") as clock, \
             mock.patch.object(waiter.time, "sleep") as sleep, \
             mock.patch.object(waiter.subprocess, "run") as run:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.side_effect = [START - timedelta(seconds=30), START]
            run.return_value.returncode = 0
            self.assertEqual(waiter.main(), 0)
            self.assertEqual(gate.call_count, 2)
            self.assertEqual(gate.call_args.kwargs["wave_id"], "MIBO2-W02")
            sleep.assert_called_once_with(30.0)
            run.assert_called_once()
            self.assertIn("--execute", run.call_args.args[0])
            self.assertEqual(run.call_args.args[0][1], "-B")

    def test_invalid_prewave_configuration_never_sleeps_or_dispatches(self):
        with mock.patch.object(sys, "argv", self.argv()), \
             mock.patch.object(waiter.prewave, "validate_prewave", side_effect=ValueError("unsigned")), \
             mock.patch.object(waiter.time, "sleep") as sleep, \
             mock.patch.object(waiter.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "unsigned"):
                waiter.main()
            sleep.assert_not_called()
            run.assert_not_called()

    def test_invalid_request_timeout_is_rejected_before_waiting(self):
        with mock.patch.object(sys, "argv", self.argv() + ["--timeout", "0"]), \
             mock.patch.object(waiter.prewave, "validate_prewave") as gate, \
             mock.patch.object(waiter.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "timeout must be positive"):
                waiter.main()
            gate.assert_not_called()
            run.assert_not_called()

    def test_armed_input_drift_or_closed_window_never_dispatches(self):
        changed = self.report()
        changed["input_hashes"] = {"protocol_file_sha256": "b" * 64}
        for final, now, message in ((changed, START, "changed while waiting"),
                                    (self.report(), CLOSE, "closed")):
            with self.subTest(message=message), \
                 mock.patch.object(sys, "argv", self.argv()), \
                 mock.patch.object(waiter.prewave, "validate_prewave", side_effect=[self.report(), final]), \
                 mock.patch.object(waiter, "datetime") as clock, \
                 mock.patch.object(waiter.subprocess, "run") as run:
                clock.now.return_value = now
                clock.fromisoformat.side_effect = datetime.fromisoformat
                with self.assertRaisesRegex(SystemExit, message):
                    waiter.main()
                run.assert_not_called()

    def test_systemd_waiter_remains_armed_without_start_timeout_or_automatic_restart(self):
        service = (Path(__file__).resolve().parents[2] / "runtime/mibo-core-v2.service").read_text()
        self.assertIn("Type=simple\n", service)
        self.assertIn("TimeoutStartSec=infinity\n", service)
        self.assertIn("Restart=no\n", service)
        self.assertIn("--strict-runtime", service)
        self.assertIn("/usr/bin/python3 -B", service)
        self.assertIn("Environment=PYTHONDONTWRITEBYTECODE=1", service)


if __name__ == "__main__":
    unittest.main()
