"""Synthetic, offline regression tests for prospective Core v2 wave closure."""
from contextlib import ExitStack, redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import shutil
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from test_core_v2_api import CoreV2Fixture
import core_v2_archive as archive
import core_v2_archive_verify as verifier
import core_v2_execution_state as state
import core_v2_runner as runner

spec = importlib.util.spec_from_file_location("generic_close", HERE.parent / "runtime/close-core-v2-wave.py")
close = importlib.util.module_from_spec(spec)
spec.loader.exec_module(close)


class GenericCloseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.units = self.base / "units"
        self.units.mkdir()
        self.private = self.base / "private"
        self.private.mkdir()
        self.proc = self.base / "proc"
        self.proc.mkdir()
        self.unit = "mibo-core-v2-w02.service"
        self.data = self.base / "data"
        self.fixture = self.make_fixture("MIBO2-W02")
        self.root = archive.wave_root(self.data, "JP01", "MIBO2-W02", "2.0")
        self.root.mkdir(parents=True)
        self.rows = runner.read_csv(self.fixture.manifest)
        self.source = self.base / "source"
        (self.source / "automation").mkdir(parents=True)
        waiter = self.source / "automation/core_v2_waiter.py"
        waiter.write_text("# synthetic frozen collector source\n")
        (self.source / "INSTALL_PROVENANCE.json").write_text(json.dumps({"source_commit_sha": "1" * 40, "source_worktree_clean": True}))
        sums = {"automation/core_v2_waiter.py": close.sha(waiter),
                "INSTALL_PROVENANCE.json": close.sha(self.source / "INSTALL_PROVENANCE.json")}
        (self.source / "INSTALL_SHA256SUMS.txt").write_text("".join(digest + "  " + path + "\n" for path, digest in sums.items()))
        self.make_unit(self.unit)
        self.patches = ExitStack()
        self.patches.enter_context(patch.object(close, "UNIT_DIRECTORY", self.units))
        self.patches.enter_context(patch.object(close, "PROC_DIRECTORY", self.proc))
        self.patches.enter_context(patch.object(close.subprocess, "check_output", side_effect=self.system_state))
        self.future = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def tearDown(self):
        self.patches.close()
        # Synthetic seal tests remove write bits, just as the production tool.
        for path in [self.base, *self.base.rglob("*")]:
            if not path.is_symlink():
                path.chmod(0o700 if path.is_dir() else 0o600)
        self.temporary.cleanup()

    def make_fixture(self, wave):
        fixture = CoreV2Fixture(self.base)
        freeze = json.loads(fixture.freeze.read_text())
        freeze["wave_id"] = wave
        fixture.freeze.write_text(json.dumps(freeze))
        fixture.manifest.unlink()
        rows = runner.generate_manifest(protocol_path=fixture.protocol, freeze_path=fixture.freeze,
            wave_id=wave, site_id="JP01")
        runner.write_csv(rows, fixture.manifest)
        authorization = json.loads(fixture.authorization.read_text())
        authorization.update(wave_id=wave, provider_freeze_sha256=close.sha(fixture.freeze),
            manifest_sha256=close.sha(fixture.manifest))
        fixture.authorization.write_text(json.dumps(authorization))
        return fixture

    def make_unit(self, unit, generic=False):
        paths = dict(protocol=self.fixture.protocol, manifest=self.fixture.manifest,
                     freeze=self.fixture.freeze, authorization=self.fixture.authorization,
                     **{"data-root": self.data})
        if generic:
            env = self.base / "runtime.env"
            values = dict(MIBO_CORE_V2_PROTOCOL=str(paths["protocol"]),
                MIBO_CORE_V2_WAVE="MIBO2-W02", MIBO_CORE_V2_MANIFEST=str(paths["manifest"]),
                MIBO_CORE_V2_FREEZE=str(paths["freeze"]), MIBO_CORE_V2_AUTHORIZATION=str(paths["authorization"]),
                MIBO_DATA_ROOT=str(self.data), MIBO_RUNTIME_HOST=socket.gethostname().split(".", 1)[0],
                MIBO_CORE_V2_SOURCE_COMMIT="1" * 40)
            env.write_text("SYNTHETIC_API_KEY=SYNTHETIC_SECRET_VALUE\n" + "".join(key + "=" + json.dumps(value) + "\n" for key, value in values.items()))
            template = (HERE.parent / "runtime/mibo-core-v2.service").read_text()
            template = template.replace("/opt/mibo-core", str(self.source))
            template = template.replace("/etc/mibo/mibo-core-v2.env", str(env))
            (self.units / unit).write_text(template)
        else:
            command = "/usr/bin/python3 -B " + str(self.source / "automation/core_v2_waiter.py") + " --wave MIBO2-W02 "
            command += " ".join("--" + key + " " + str(value) for key, value in paths.items())
            (self.units / unit).write_text("[Service]\nExecStart=" + command + "\n")

    def system_state(self, command, **_kwargs):
        unit = command[2]
        return ("ActiveState=inactive\nMainPID=0\nUnitFileState=disabled\nControlGroup=\nResult=success\n"
                + "InactiveEnterTimestamp=synthetic\nFragmentPath=" + str(self.units / unit) + "\nDropInPaths=\n")

    def config(self):
        return close.load_unit(self.unit, "MIBO2-W02", "JP01", self.future)

    def capture(self, row=None):
        row = row or self.rows[0]
        bounds = runner.wave(runner.load_protocol(self.fixture.protocol)[0], "MIBO2-W02")
        started = runner.parse_aware_utc(bounds["start_utc"]) + timedelta(minutes=5)
        if int(row["attempt"]) > 1:
            started += timedelta(minutes=10 if int(row["attempt"]) == 2 else 40)
        return archive.archive_success(data_root=self.data, row=row,
            request_payload={"synthetic": True}, response_json={"answer": "SYNTHETIC_PRIVATE_ANSWER"},
            raw_response_text="SYNTHETIC_PRIVATE_ANSWER", http_status=200, returned_model=row["model_id"], usage={},
            started_at_utc=started.isoformat(), completed_at_utc=(started + timedelta(seconds=1)).isoformat(), duration_ms=1000)

    def failure(self, row=None, at=None):
        row = row or self.rows[0]
        return archive.archive_failure(data_root=self.data, row=row,
            failure_kind="provider_error", message="SYNTHETIC_PRIVATE_PROVIDER_BODY", http_status=503,
            failed_at_utc=at or "2026-11-03T00:05:00Z", response_body="SYNTHETIC_PRIVATE_PROVIDER_BODY")

    def run_close(self, perform=True):
        return close.close_wave(units=[self.unit], wave="MIBO2-W02", private_root=self.private,
                                perform_close=perform, now=self.future)

    def seal_patches(self):
        patches = ExitStack()
        patches.enter_context(patch.object(close.os, "geteuid", return_value=0))
        patches.enter_context(patch.object(close.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=os.getgid())))
        patches.enter_context(patch.object(close, "utc", return_value="2030-01-01T00:00:00+00:00"))
        patches.enter_context(patch.object(close.os, "sync"))
        # These are synthetic fixtures; ownership is not changed on test hosts.
        def synthetic_seal(root, _gid):
            close.safe_tree(root)
            for path in [*root.rglob("*"), root]:
                path.chmod(0o550 if path.is_dir() else 0o440)
        patches.enter_context(patch.object(close, "seal", side_effect=synthetic_seal))
        return patches

    def test_noncalibration_expected_counts_are_manifest_bound(self):
        self.capture()
        with redirect_stdout(io.StringIO()):
            result = self.run_close(False)
        self.assertFalse(result["closure_performed"])
        self.assertTrue(result["registered_panel_fully_included"])
        self.assertEqual(sum(value["planned"] for value in result["namespaces"]["v2.0"].values()), 960)
        self.assertEqual(sum(value["captured"] for value in result["namespaces"]["v2.0"].values()), 1)
        self.assertFalse((self.root / "closure").exists())
        self.assertFalse((self.root / ".executor.lock").exists())
        self.assertEqual(list(self.private.iterdir()), [])

    def test_exact_generic_unit_template_expands_only_reviewed_values(self):
        self.make_unit(self.unit, generic=True)
        config = self.config()
        self.assertEqual(config["root"], self.root)
        self.assertEqual(config["source_commit"], "1" * 40)
        self.assertEqual(len(config["rows"]), 960)

    def test_calibration_counts_are_derived_from_the_manifest(self):
        base = self.base / "calibration"
        base.mkdir()
        fixture = CoreV2Fixture(base)
        calibration_root = archive.wave_root(self.data, "JP01", "MIBO2-W01", "2.0")
        calibration_root.mkdir(parents=True)
        text = (self.units / self.unit).read_text().replace("--wave MIBO2-W02", "--wave MIBO2-W01")
        for name in ("protocol", "manifest", "freeze", "authorization"):
            text = text.replace(str(getattr(self.fixture, name)), str(getattr(fixture, name)))
        (self.units / self.unit).write_text(text)
        with redirect_stdout(io.StringIO()):
            result = close.close_wave(units=[self.unit], wave="MIBO2-W01", now=self.future)
        self.assertEqual(sum(value["planned"] for value in result["namespaces"]["v2.0"].values()), 1120)
        self.assertFalse((calibration_root / "closure").exists())

    def test_fqdn_runtime_host_matches_registered_short_hostname(self):
        self.make_unit(self.unit, generic=True)
        with patch("socket.gethostname", return_value=socket.gethostname().split(".", 1)[0] + ".internal"):
            self.assertEqual(self.config()["source_commit"], "1" * 40)

    def test_bound_source_commit_mismatch_blocks_closure(self):
        self.make_unit(self.unit, generic=True)
        env = self.base / "runtime.env"
        env.write_text(env.read_text().replace("1" * 40, "2" * 40))
        with self.assertRaisesRegex(ValueError, "prospectively bound commit"):
            self.config()

    def test_inputs_changed_after_authorization_validation_are_rejected(self):
        native = close.runtime_health.provenance_state
        for label in ("protocol", "manifest", "freeze", "authorization"):
            path = getattr(self.fixture, label)
            original = path.read_bytes()
            def changed(source):
                path.write_bytes(original + b"\n")
                return native(source)
            try:
                with self.subTest(label=label), patch.object(close.runtime_health, "provenance_state", side_effect=changed):
                    with self.assertRaisesRegex(ValueError, "changed during closure configuration"):
                        self.config()
            finally:
                path.write_bytes(original)

    def test_failed_but_quiescent_unit_preserves_failure_result(self):
        output = self.system_state(["systemctl", "show", self.unit])
        output = output.replace("ActiveState=inactive", "ActiveState=failed").replace("Result=success", "Result=exit-code")
        with patch.object(close.subprocess, "check_output", return_value=output):
            self.assertEqual(self.config()["state"]["Result"], "exit-code")

    def test_before_registered_close_refuses_without_writes(self):
        with self.assertRaisesRegex(ValueError, "not closed"):
            close.load_unit(self.unit, "MIBO2-W02", "JP01", datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertFalse((self.root / "closure").exists())

    def test_active_enabled_and_remaining_process_are_blocked(self):
        normal = self.system_state(["systemctl", "show", self.unit])
        for output in (normal.replace("inactive", "active"), normal.replace("disabled", "enabled"), normal.replace("MainPID=0", "MainPID=123")):
            with self.subTest(output=output), patch.object(close.subprocess, "check_output", return_value=output):
                with self.assertRaises(ValueError):
                    self.config()
        process = self.proc / "123"
        process.mkdir()
        (process / "cmdline").write_bytes(b"python\0/opt/mibo-core/automation/core_v2_executor.py\0")
        with self.assertRaisesRegex(ValueError, "active Core"):
            self.run_close(False)

    def test_overlap_and_wrong_wave_are_rejected(self):
        second = "mibo-core-v2-second.service"
        self.make_unit(second)
        with self.assertRaisesRegex(ValueError, "overlap"):
            close.close_wave(units=[self.unit, second], wave="MIBO2-W02", now=self.future)
        with self.assertRaisesRegex(ValueError, "different wave"):
            close.load_unit(self.unit, "MIBO2-W03", "JP01", self.future)

    def test_tampered_manifest_and_capture_hash_abort(self):
        self.capture()
        raw = next((self.root / "api_raw").glob("*.json"))
        raw.write_text("SYNTHETIC_TAMPER")
        with self.assertRaisesRegex(ValueError, "checksum"):
            close.inspect(self.config())
        self.fixture.manifest.write_text(self.fixture.manifest.read_text().replace("STD", "WA", 1))
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.config()

    def test_retry_capture_is_one_cell_and_outage_missingness_retained(self):
        row = self.rows[0]
        self.failure(row)
        retry = close.executor._clone_retry_row(row, 2)
        self.capture(retry)
        result = close.inspect(self.config())
        self.assertEqual(sum(value["captured"] for value in result["summary"].values()), 1)
        self.assertEqual(sum(value["without_capture"] for value in result["summary"].values()), 959)
        self.assertEqual(sum(count for key, count in result["counts"].items() if key[0] == "attempt"), 2)

    def test_retry_without_eligible_failure_is_rejected(self):
        self.capture(close.executor._clone_retry_row(self.rows[0], 2))
        with self.assertRaisesRegex(ValueError, "parent failure"):
            close.inspect(self.config())

    def test_uncertain_dispatch_and_raw_only_are_never_promoted_to_capture(self):
        state.claim_attempt(self.root, self.rows[0], authorization_sha256=close.sha(self.fixture.authorization),
            dispatched_at=datetime(2026, 11, 3, tzinfo=timezone.utc))
        raw = self.root / "api_raw" / (self.rows[0]["attempt_id"] + ".json")
        raw.parent.mkdir(exist_ok=True)
        raw.write_text('{"answer":"SYNTHETIC_PRIVATE_ANSWER"}')
        result = close.inspect(self.config())
        self.assertEqual(sum(value["captured"] for value in result["summary"].values()), 0)
        self.assertEqual(sum(value["unresolved"] for value in result["summary"].values()), 1)
        self.assertTrue(any(row[-1] == "outcome_unknown_without_terminal_metadata" for row in result["cells"]))
        self.assertFalse((self.root / "deviations").exists())

    def test_unregistered_orphan_and_symlink_are_rejected(self):
        folder = self.root / "api_raw"
        folder.mkdir()
        orphan = folder / "orphan.json"
        orphan.write_text("{}")
        with self.assertRaises(ValueError):
            close.inspect(self.config())
        orphan.unlink()
        orphan.symlink_to(self.fixture.freeze)
        with self.assertRaisesRegex(ValueError, "symlink"):
            close.inspect(self.config())

    def test_real_terminal_completion_does_not_seek(self):
        master, slave = pty.openpty()
        device, native = os.ttyname(slave), open
        try:
            os.write(master, "合成担当者\n".encode())
            with patch("builtins.open", side_effect=lambda file, *args, **kwargs: native(device if file == "/dev/tty" else file, *args, **kwargs)):
                self.assertEqual(close.completion_name(), "合成担当者")
        finally:
            os.close(master)
            os.close(slave)

    def test_blank_signoff_leaves_wave_and_export_unclosed(self):
        self.capture()
        with self.seal_patches(), patch.object(close, "completion_name", return_value=""), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "sign-off"):
                self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertEqual(list(self.private.iterdir()), [])

    def test_bad_candidate_archive_aborts_before_raw_closure(self):
        self.capture()
        original = next((self.root / "api_raw").glob("*.json")).read_bytes()
        with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Lead"), patch.object(verifier, "verify_tar_content", side_effect=ValueError("synthetic corrupt export")), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "corrupt export"):
                self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertFalse((self.root / "SHA256SUMS.txt").exists())
        self.assertEqual(next((self.root / "api_raw").glob("*.json")).read_bytes(), original)

    def test_active_cross_version_lineage_lock_blocks_closure(self):
        self.capture()
        with state.lineage_locks(self.data, "JP01", "MIBO2-W02", {self.rows[0]["service_lineage_id"]}):
            with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Lead"), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "lineage/wave lock"):
                    self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertEqual(list(self.private.iterdir()), [])

    def test_frozen_copy_bytes_are_checked_against_bound_digest(self):
        config = self.config()
        inspection = close.inspect(config)
        self.fixture.freeze.write_text("{\"synthetic_changed\":true}")
        with self.assertRaisesRegex(ValueError, "frozen closure copy"):
            close.closure_bytes(config, inspection, "Synthetic Lead", self.future.isoformat())

    def test_source_change_after_archive_check_aborts_before_raw_mutation(self):
        self.capture()
        native = verifier.verify_tar_content
        def changed(archive_path, expected):
            native(archive_path, expected)
            (self.source / "automation/core_v2_waiter.py").write_text("# synthetic changed source\n")
        with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Lead"), patch.object(verifier, "verify_tar_content", side_effect=changed), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "changed during completion"):
                self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertFalse((self.root / "SHA256SUMS.txt").exists())

    def test_frozen_input_change_after_archive_check_aborts_before_raw_mutation(self):
        self.capture()
        native = verifier.verify_tar_content
        def changed(archive_path, expected):
            native(archive_path, expected)
            self.fixture.authorization.write_text("{\"synthetic_changed\":true}")
        with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Lead"), patch.object(verifier, "verify_tar_content", side_effect=changed), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "changed during completion"):
                self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertFalse((self.root / "SHA256SUMS.txt").exists())

    def test_archive_space_failure_leaves_original_wave_unclosed(self):
        self.capture()
        with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Lead"), patch.object(close.shutil, "disk_usage", return_value=SimpleNamespace(free=0)), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "archive reserve"):
                self.run_close()
        self.assertFalse((self.root / "closure").exists())
        self.assertFalse((self.root / "SHA256SUMS.txt").exists())
        self.assertEqual(list(self.private.iterdir()), [])

    def test_complete_offline_signed_close_and_verified_restore(self):
        self.capture()
        self.failure(self.rows[240])
        output = io.StringIO()
        with self.seal_patches(), patch.object(close, "completion_name", return_value="Synthetic Operations Lead"), redirect_stdout(output):
            result = self.run_close()
        self.assertTrue(result["closure_performed"])
        self.assertFalse(result["independent_backup_verified"])
        self.assertIn("ARCHIVE_CONTENT_VERIFY=PASS", output.getvalue())
        self.assertNotIn("SYNTHETIC_PRIVATE", output.getvalue())
        self.assertNotIn("SYNTHETIC_SECRET", output.getvalue())
        completion = json.loads((self.root / "closure/COMPLETION_RECORD.json").read_text())
        self.assertEqual(completion["operations_lead"], "Synthetic Operations Lead")
        self.assertFalse(completion["scientific_capture_complete"])
        self.assertEqual(sum(value["without_capture"] for value in completion["summary"].values()), 959)
        self.assertFalse(any(path.stat().st_mode & 0o222 for path in [self.root, *self.root.rglob("*")]))
        restored = self.base / "synthetic-restored-data"
        shutil.copytree(self.data / "v2.0", restored / "v2.0")
        with patch.object(verifier.os, "fstatvfs", return_value=SimpleNamespace(f_flag=os.ST_RDONLY)):
            check = verifier.verify_archive(archive=Path(result["archive_path"]), receipt=Path(result["receipt_path"]),
                expected_receipt_sha256=result["receipt_sha256"], wave="MIBO2-W02", site="JP01", restored_data_root=restored)
        self.assertEqual(check["restoration_check"], "PASS")
        self.assertTrue(check["restoration_filesystem_read_only"])
        with self.assertRaisesRegex(ValueError, "existing closure"):
            self.run_close(False)

    def test_wave_one_write_guard_is_explicit(self):
        with patch.object(close.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(ValueError, "W01"):
                close.close_wave(units=[self.unit], wave="MIBO2-W01", perform_close=True, now=self.future)


if __name__ == "__main__":
    unittest.main()
