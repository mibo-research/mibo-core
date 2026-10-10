"""Synthetic technical monitoring regressions, no provider traffic."""
from datetime import datetime, timezone
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive as archive
import core_v2_runner as runner
import core_v2_status as status
import core_v2_execution_state as execution_state
from test_core_v2_api import CoreV2Fixture


class TechnicalStatusTests(unittest.TestCase):
    def fixture(self, root):
        fixture = CoreV2Fixture(root)
        value = json.loads(fixture.freeze.read_text())
        value["wave_id"] = "MIBO2-W02"
        fixture.freeze.write_text(json.dumps(value))
        fixture.manifest.unlink()
        rows = runner.generate_manifest(protocol_path=fixture.protocol, freeze_path=fixture.freeze,
                                        wave_id="MIBO2-W02", site_id="JP01")
        runner.write_csv(rows, fixture.manifest)
        return fixture, rows

    def report(self, root, fixture, **kwargs):
        return status.build_report(protocol_path=fixture.protocol, freeze_path=fixture.freeze,
                                   manifest_path=fixture.manifest, data_root=root / "data",
                                   current=datetime(2026, 11, 5, tzinfo=timezone.utc),
                                   expected_wave="MIBO2-W02", **kwargs)

    def capture(self, root, row):
        return archive.archive_success(data_root=root / "data", row=row,
            request_payload={"prompt": "synthetic"}, response_json={"text": "SECRET-ANSWER"},
            raw_response_text="SECRET-ANSWER", http_status=200, returned_model="synthetic",
            usage={}, started_at_utc="2026-11-03T00:00:00Z", completed_at_utc="2026-11-03T00:00:01Z",
            duration_ms=1000)

    def test_three_captures_and_successful_process_cannot_mean_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture, rows = self.fixture(root)
            google = [r for r in rows if r["service_lineage_id"] == "MIBO-SL-003"]
            for row in google[:3]: self.capture(root, row)
            archive.archive_failure(data_root=root / "data", row=google[3], failure_kind="provider_error",
                message="SECRET-KEY", response_body="SECRET-ANSWER", http_status=503,
                failed_at_utc="2026-11-03T00:01:00Z")
            archive.write_deviation(data_root=root / "data", site_id="JP01", wave_id="MIBO2-W02",
                deviation_id="SYNTHETIC-SUSPENSION", record={"type": "lineage_suspended_after_retry_exhaustion",
                "service_lineage_id": "MIBO-SL-003"})
            with mock.patch.object(status.subprocess, "run") as proc:
                proc.return_value.returncode = 0
                proc.return_value.stdout = "ActiveState=inactive\nMainPID=0\nUnitFileState=disabled\nResult=success\n"
                service = status.service_states(["synthetic.service"])
            report = self.report(root, fixture)
            self.assertEqual(service["synthetic.service"]["Result"], "success")
            self.assertEqual(report["status"], "SUSPENDED")
            self.assertFalse(report["scientific_collection_complete"])
            self.assertEqual(report["planned_cells"], 960)
            self.assertEqual(report["lineages"]["MIBO-SL-003"], {
                "planned": 240, "captured": 3, "missing": 237,
                "failed_no_capture": 1, "unattempted_no_capture": 236,
                "uncertain_no_capture": 0, "technical_failure_attempts": 1, "suspended": True})
            self.assertNotIn("SECRET", json.dumps(report))

    def test_all960_are_complete_but_do_not_claim_independent_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture, rows = self.fixture(root)
            for row in rows: self.capture(root, row)
            report = self.report(root, fixture)
            self.assertEqual(report["status"], "COMPLETE")
            self.assertEqual(report["captured_cells"], 960)
            self.assertFalse(report["raw_content_inspected"])
            self.assertFalse(report["independent_backup_verified"])
            self.assertNotIn("SECRET-ANSWER", json.dumps(report))

    def test_hash_corruption_orphan_raw_corrupt_record_and_symlink_fail_closed(self):
        for mode in ("hash", "orphan", "metadata", "symlink"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                root = Path(d); fixture, rows = self.fixture(root)
                self.capture(root, rows[0])
                wave = archive.wave_root(root / "data", "JP01", "MIBO2-W02")
                raw = wave / "api_raw" / (rows[0]["attempt_id"] + ".json")
                if mode == "hash": raw.write_bytes(b"changed")
                if mode == "orphan": (wave / "api_raw" / "orphan.json").write_text("{}")
                if mode == "metadata": (wave / "metadata" / "broken.json").write_text("SECRET")
                if mode == "symlink": (wave / "external").symlink_to(fixture.protocol)
                report = self.report(root, fixture)
                self.assertEqual(report["status"], "INTEGRITY_ERROR")
                self.assertFalse(report["scientific_collection_complete"])
                self.assertNotIn("SECRET", json.dumps(report))

    def test_unknown_dispatch_is_uncertain_and_never_counted_as_unattempted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture, rows = self.fixture(root)
            wave = archive.wave_root(root / "data", "JP01", "MIBO2-W02")
            execution_state.claim_attempt(wave, rows[0], authorization_sha256="a" * 64,
                dispatched_at=datetime(2026, 11, 3, tzinfo=timezone.utc))
            report = self.report(root, fixture)
            self.assertEqual(report["status"], "SUSPENDED")
            self.assertEqual(report["lineages"][rows[0]["service_lineage_id"]]["uncertain_no_capture"], 1)

    def test_clock_and_manifest_identity_cannot_be_silently_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture, rows = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "wave mismatch"):
                status.build_report(protocol_path=fixture.protocol, freeze_path=fixture.freeze,
                    manifest_path=fixture.manifest, data_root=root / "data", expected_wave="MIBO2-W01")
            rows[0]["execution_order"], rows[1]["execution_order"] = rows[1]["execution_order"], rows[0]["execution_order"]
            fixture.manifest.unlink(); runner.write_csv(rows, fixture.manifest)
            with self.assertRaisesRegex(ValueError, "deterministic"):
                self.report(root, fixture)

    def test_complete_authorized_scope_does_not_certify_whole_wave(self):
        import test_core_lineage_admission as fixtures
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d)
            helper = fixtures.AdmissionTests()
            _, _, dest, built = helper.fixture(root, stack)
            auth = helper.authorize(dest, built)
            base = dest / "bundle"
            rows = runner.read_csv(base / built["manifest_file"])
            for row in rows:
                if row["service_lineage_id"] in fixtures.admission.INITIAL_SCOPE:
                    self.capture(root, row)
            report = status.build_report(protocol_path=base / built["protocol_file"],
                freeze_path=base / built["provider_freeze_file"], manifest_path=base / built["manifest_file"],
                authorization_path=auth, data_root=root / "data",
                current=datetime(2026, 10, 8, tzinfo=timezone.utc))
            self.assertEqual(report["intended_panel_cells"], 1120)
            self.assertEqual(report["planned_cells"], 840)
            self.assertTrue(report["scope_collection_complete"])
            self.assertFalse(report["registered_panel_fully_included"])
            self.assertFalse(report["whole_wave_completion_assessed"])
            self.assertIsNone(report["whole_wave_collection_complete"])


if __name__ == "__main__":
    unittest.main()
