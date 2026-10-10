import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_wave_audit as audit

CONFIG = Path(__file__).resolve().parents[1] / "config"
SECRET = "SYNTHETIC_PRIVATE_ANSWER_AND_SECRET"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture(base, version="2.0.2", wave_id="MIBO2-W02", lineages=None, profile=None):
    home = base / version
    root = home / "raw"
    for name in ("metadata", "api_raw", "failures", "dispatch", "deviations"):
        (root / name).mkdir(parents=True, exist_ok=True)
    protocol = json.loads((CONFIG / ("core_v2_protocol.v" + version + ".json")).read_text())
    freeze = {"core_api": {"MIBO-SL-00" + str(n): {"model_id": "synthetic-model-" + str(n), "request_profile": profile or {"synthetic": True, "secret_value": SECRET}} for n in range(1, 5)}}
    pp, fp = home / "protocol.json", home / "freeze.json"
    write_json(pp, protocol); write_json(fp, freeze)
    forms = json.loads((CONFIG / "instrument_v1.0.json").read_text())["forms"]
    calibration = int(wave_id[-2:]) in (1, 4, 7, 10)
    rows = []
    for n in range(1, 5):
        for form in forms:
            windows = ("WA", "WB") if calibration and form["anchor"] and form["language"] == "EN" else ("STD",)
            for window in windows:
                for rep in range(1, 11):
                    rows.append({"attempt_id": f"MIBO2-SITE-JP01-{wave_id.replace('MIBO2-', '')}-SL{n:03d}-ACI-{form['item_id'].replace('MIBO-', '')}-{form['language']}-{window}-R{rep:02d}-A01", "protocol_version": version, "wave_id": wave_id, "site_id": "JP01", "service_lineage_id": "MIBO-SL-00" + str(n), "query_form_id": form["query_form_id"], "language": form["language"], "window_id": window, "replication": str(rep), "query_sha256": form["sha256"], "attempt": "1", "protocol_file_sha256": audit.sha(pp), "provider_freeze_sha256": audit.sha(fp), "model_id": freeze["core_api"]["MIBO-SL-00" + str(n)]["model_id"]})
    mp = home / "manifest.csv"
    with mp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return {"version": version, "raw_root": str(root), "manifest": str(mp), "protocol": str(pp), "freeze": str(fp), "lineages": lineages or ["MIBO-SL-00" + str(n) for n in range(1, 5)]}, rows


def capture(spec, row, *, aid=None, parent=None, start="2026-11-03T00:01:00Z", end="2026-11-03T00:02:00Z", number=1):
    aid = aid or row["attempt_id"]
    raw = Path(spec["raw_root"]) / "api_raw" / (aid + ".json")
    envelope = {**row, "attempt_id": aid, "retry_of_attempt_id": parent, "attempt": number, "http_status": 200, "model_id_requested": row["model_id"], "started_at_utc": start, "completed_at_utc": end, "raw_response_text": SECRET, "raw_response": {"answer": SECRET}, "request_payload": {"api_key": SECRET}}
    write_json(raw, envelope)
    metadata = {"protocol_version": row["protocol_version"], "attempt_id": aid, "retry_of_attempt_id": parent, "service_lineage_id": row["service_lineage_id"], "window_id": row["window_id"], "raw_file": str(raw.relative_to(Path(spec["raw_root"]))), "raw_file_sha256": audit.sha(raw), "status": "valid_confirmatory_api_capture", "started_at_utc": start, "completed_at_utc": end}
    write_json(Path(spec["raw_root"]) / "metadata" / (aid + ".json"), metadata)


def failure(spec, row, *, aid=None, parent=None, number=1, kind="provider_error", code=503, at="2026-11-03T00:02:00Z"):
    value = {**row, "attempt_id": aid or row["attempt_id"], "retry_of_attempt_id": parent, "attempt": number, "failure_kind": kind, "failed_at_utc": at, "http_status": code, "provider_response_body": SECRET, "message": SECRET}
    write_json(Path(spec["raw_root"]) / "failures" / (value["attempt_id"] + ".json"), value)


class WaveAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.spec, self.rows = fixture(self.base)
    def tearDown(self):
        self.tmp.cleanup()
    def run_audit(self, specs=None, baseline=None, wave="MIBO2-W02"):
        return audit.audit_wave(baseline_manifest=baseline or self.spec["manifest"], namespaces=specs or [self.spec], wave_id=wave)
    def test_full_denominator_content_blind_and_threshold(self):
        for row in self.rows[:8]:
            capture(self.spec, row)
        report = self.run_audit()
        self.assertEqual(report["totals"]["planned"], 960)
        self.assertEqual(report["totals"]["verified_capture"], 8)
        self.assertEqual(report["totals"]["technical_capture_candidate_cells_n_ge_8"], 1)
        self.assertNotIn(SECRET, json.dumps(report))
        self.assertEqual(report["totals"]["unsubmitted_unknown"], 952)
    def test_failure_not_submission_expired_not_failed(self):
        failure(self.spec, self.rows[0], kind="timeout", code=None)
        failure(self.spec, self.rows[1], kind=audit.EXPIRED, code=503)
        report = self.run_audit()
        self.assertEqual(report["totals"]["submitted"], 0)
        self.assertEqual(report["totals"]["failed"], 1)
        self.assertEqual(report["totals"]["window_expired"], 1)
    def test_dispatch_intent_without_terminal_is_evidence_missing(self):
        row = self.rows[0]
        write_json(Path(self.spec["raw_root"]) / "dispatch" / (row["attempt_id"] + ".json"), {**row, "dispatch_at_utc": "2026-11-03T00:00:01Z"})
        report = self.run_audit()
        self.assertEqual(report["totals"]["submitted"], 0)
        self.assertEqual(report["totals"]["evidence_missing"], 1)
    def test_retry_capture_counts_one_initial_slot(self):
        row = self.rows[0]; aid = row["attempt_id"][:-2] + "02"
        failure(self.spec, row)
        write_json(Path(self.spec["raw_root"]) / "metadata" / ("retry-link-" + aid + ".json"), {"original_attempt_id": row["attempt_id"], "retry_attempt_id": aid, "due_at_utc": "2026-11-03T00:12:00Z", "failure_kind": "provider_error", "protocol_version": row["protocol_version"]})
        capture(self.spec, row, aid=aid, parent=row["attempt_id"], number=2, start="2026-11-03T00:12:00Z", end="2026-11-03T00:13:00Z")
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 1)
        self.assertEqual(report["totals"]["submitted"], 1)
    def test_retry_early_or_ineligible_excluded(self):
        row = self.rows[0]; aid = row["attempt_id"][:-2] + "02"
        failure(self.spec, row, kind="request_environment_mismatch")
        write_json(Path(self.spec["raw_root"]) / "metadata" / ("retry-link-" + aid + ".json"), {"original_attempt_id": row["attempt_id"], "retry_attempt_id": aid, "due_at_utc": "2026-11-03T00:03:00Z", "failure_kind": "request_environment_mismatch", "protocol_version": row["protocol_version"]})
        capture(self.spec, row, aid=aid, parent=row["attempt_id"], number=2, start="2026-11-03T00:03:00Z", end="2026-11-03T00:04:00Z")
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 0)
        self.assertIn("retry_due_before_registered_wait", report["observations"][0]["issues"])
        self.assertIn("retry_after_ineligible_failure", report["observations"][0]["issues"])
    def test_mixed_versions_scope_and_profiles_recorded(self):
        self.spec["lineages"] = ["MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-004"]
        second, rows = fixture(self.base, "2.0.4", lineages=["MIBO-SL-003"], profile={"processing": "standard"})
        for row in self.rows[:8]: capture(self.spec, row)
        google = [r for r in rows if r["service_lineage_id"] == "MIBO-SL-003"]
        capture(second, google[0])
        report = self.run_audit([self.spec, second])
        self.assertEqual(report["totals"]["planned"], 960)
        self.assertEqual(report["totals"]["verified_capture"], 9)
        self.assertTrue(all(r["variant_count"] == 1 for r in report["observations"]))
    def test_same_id_cross_versions_is_not_silently_pooled(self):
        second, rows = fixture(self.base, "2.0.4", profile={"processing": "changed"})
        capture(self.spec, self.rows[0]); capture(second, rows[0])
        report = self.run_audit([self.spec, second])
        self.assertEqual(report["totals"]["planned"], 960)
        self.assertEqual(report["totals"]["verified_capture"], 0)
        row = report["observations"][0]
        self.assertEqual(row["variant_count"], 2)
        self.assertTrue(row["variant_profile_difference"])
        self.assertIn("multiple_captures_for_one_logical_observation", row["issues"])
    def test_missing_metadata_is_incomplete_write(self):
        row = self.rows[0]
        raw = Path(self.spec["raw_root"]) / "api_raw" / (row["attempt_id"] + ".json")
        raw.write_text(SECRET)
        report = self.run_audit()
        self.assertEqual(report["totals"]["incomplete_write"], 1)
        self.assertNotIn(SECRET, json.dumps(report))
    def test_hash_mismatch_time_and_seal_are_checked(self):
        capture(self.spec, self.rows[0])
        raw = next((Path(self.spec["raw_root"]) / "api_raw").glob("*.json"))
        raw.write_text("{}")
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 0)
        self.assertIn("raw_hash_mismatch", report["observations"][0]["issues"])
    def test_outside_window_capture_excluded(self):
        capture(self.spec, self.rows[0], start="2026-11-05T00:00:00Z", end="2026-11-05T00:00:01Z")
        self.assertEqual(self.run_audit()["totals"]["verified_capture"], 0)
    def test_http_failure_cannot_be_verified_capture_even_with_matching_hash(self):
        capture(self.spec, self.rows[0])
        root = Path(self.spec["raw_root"])
        raw = next((root / "api_raw").glob("*.json"))
        value = json.loads(raw.read_text()); value["http_status"] = 503
        write_json(raw, value)
        metadata = next((root / "metadata").glob("*.json"))
        value = json.loads(metadata.read_text()); value["raw_file_sha256"] = audit.sha(raw)
        write_json(metadata, value)
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 0)
        self.assertEqual(report["totals"]["submitted"], 1)
        self.assertIn("capture_http_status_not_successful", report["observations"][0]["issues"])
    def test_inflight_completion_after_close_is_not_new_scientific_exclusion(self):
        capture(self.spec, self.rows[0], start="2026-11-04T23:59:59Z", end="2026-11-05T00:00:01Z")
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 1)
        self.assertIn("capture_completed_after_registered_window_close", report["observations"][0]["review_notes"])
    def test_sealed_pair_verified_then_tampered_metadata_excluded(self):
        capture(self.spec, self.rows[0])
        root = Path(self.spec["raw_root"])
        entries = {str(p.relative_to(root)): audit.sha(p) for p in root.rglob("*") if p.is_file()}
        (root / "SHA256SUMS.txt").write_text("".join(h + "  " + name + "\n" for name, h in entries.items()))
        self.assertEqual(self.run_audit()["totals"]["verified_capture"], 1)
        metadata = next((root / "metadata").glob("*.json"))
        metadata.write_text(metadata.read_text() + "\n")
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 0)
        self.assertIn("sealed_file_missing_or_hash_mismatch", report["namespaces"][0]["issues"])
    def test_same_attempt_failure_and_capture_never_deduplicated(self):
        capture(self.spec, self.rows[0]); failure(self.spec, self.rows[0])
        report = self.run_audit()
        self.assertEqual(report["totals"]["verified_capture"], 0)
        self.assertIn("duplicate_or_conflicting_terminal_record", report["observations"][0]["issues"])
    def test_incomplete_baseline_denominator_rejected(self):
        manifest = Path(self.spec["manifest"])
        manifest.write_text("\n".join(manifest.read_text().splitlines()[:-1]) + "\n")
        with self.assertRaisesRegex(ValueError, "complete registered"): self.run_audit()
    def test_baseline_attempt_identity_checked(self):
        manifest = Path(self.spec["manifest"])
        manifest.write_text(manifest.read_text().replace(self.rows[0]["attempt_id"], "SYNTHETIC-WRONG-INITIAL-ID"))
        with self.assertRaisesRegex(ValueError, "initial attempt ID"): self.run_audit()
    def test_symlink_and_path_escape_rejected(self):
        (Path(self.spec["raw_root"]) / "api_raw" / "bad.json").symlink_to(self.spec["freeze"])
        with self.assertRaises(ValueError): self.run_audit()
    def test_duplicate_manifest_and_incomplete_baseline_rejected(self):
        path = Path(self.spec["manifest"])
        with path.open("a", encoding="utf-8") as f: f.write(path.read_text().splitlines()[1] + "\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"): self.run_audit()
    def test_read_only_input_and_exclusive_private_output(self):
        capture(self.spec, self.rows[0])
        root = Path(self.spec["raw_root"])
        before = {str(p): (audit.sha(p), p.stat().st_mtime_ns, p.stat().st_mode) for p in root.rglob("*") if p.is_file()}
        report = self.run_audit()
        out = self.base / "private-report"
        audit.write_report(report, out, forbidden_roots=[root])
        self.assertEqual(before, {str(p): (audit.sha(p), p.stat().st_mtime_ns, p.stat().st_mode) for p in root.rglob("*") if p.is_file()})
        self.assertEqual((out.stat().st_mode & 0o777), 0o700)
        self.assertEqual(((out / "AUDIT_REPORT.json").stat().st_mode & 0o777), 0o600)
        with self.assertRaises(FileExistsError): audit.write_report(report, out, forbidden_roots=[root])
        with self.assertRaises(ValueError): audit.write_report(report, root / "new-audit", forbidden_roots=[root])
    def test_calibration_complete_denominator(self):
        other = self.base / "calibration"
        spec, rows = fixture(other, wave_id="MIBO2-W01")
        report = self.run_audit([spec], baseline=spec["manifest"], wave="MIBO2-W01")
        self.assertEqual(report["totals"]["planned"], 1120)
        self.assertEqual(sum(c["planned"] for c in report["cells"] if c["window_id"] == "WA"), 160)
        self.assertEqual(sum(c["planned"] for c in report["cells"] if c["window_id"] == "STD"), 800)
        self.assertEqual(sum(c["planned"] for c in report["cells"] if c["window_id"] == "WB"), 160)
    def test_concurrently_changed_input_aborts_before_report(self):
        inspect = audit._inspect_namespace
        def changed(*args):
            result = inspect(*args)
            (Path(self.spec["raw_root"]) / "new-unlinked-file").write_text(SECRET)
            return result
        with patch.object(audit, "_inspect_namespace", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "changed during"): self.run_audit()


if __name__ == "__main__":
    unittest.main()
