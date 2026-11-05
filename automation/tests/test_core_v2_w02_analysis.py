import copy
import csv
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_core_v2_wave_audit import SECRET, audit, capture, failure, fixture, write_json

import core_v2_w02_analysis as analysis


def seal_synthetic_tree(spec):
    root = Path(spec["raw_root"])
    seal = root / "SHA256SUMS.txt"
    seal.write_text("".join(f"{audit.sha(path)}  {path.relative_to(root).as_posix()}\n"
                            for path in sorted(root.rglob("*")) if path.is_file()), encoding="utf-8")
    return audit.sha(seal)


class W02AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.home = Path(temp.name)
        cls.spec, cls.rows = fixture(cls.home, version="2.0.1")
        cls.coded_rows = []
        for form, count in (("I03-EN", 7), ("I05-JA", 8), ("I05-EN", 10), ("I01-EN", 1), ("I07-JA", 2)):
            selected = [r for r in cls.rows if r["service_lineage_id"] == "MIBO-SL-001"
                        and r["query_form_id"] == "MIBO-" + form][:count]
            for index, row in enumerate(selected):
                oid = row["attempt_id"]
                cid = oid
                if form == "I05-EN" and index == 0:
                    failure(cls.spec, row)
                    cid = oid[:-2] + "02"
                    write_json(Path(cls.spec["raw_root"]) / "metadata" / f"retry-link-{cid}.json", {
                        "original_attempt_id": oid, "retry_attempt_id": cid,
                        "due_at_utc": "2026-11-03T00:12:00Z", "failure_kind": "provider_error",
                        "protocol_version": analysis.VERSION,
                    })
                    capture(cls.spec, row, aid=cid, parent=oid, number=2,
                            start="2026-11-03T00:13:00Z", end="2026-11-03T00:14:00Z")
                elif form == "I05-EN" and index == 9:
                    capture(cls.spec, row, start="2026-11-04T23:59:59Z", end="2026-11-05T00:00:01Z")
                else:
                    capture(cls.spec, row)
                validity, kind, state, score = "valid", "answer", "scored", "1"
                if form == "I05-EN":
                    kind = "refusal" if index == 0 else "answer"
                    score = "0" if index == 0 else ("8" if index < 6 else "9")
                if form == "I05-JA" and index == 0:
                    kind, state, score = "substantive_nonanswer", "cannot_determine", ""
                if form == "I01-EN":
                    kind, state, score = "safety_response", "not_in_scope", ""
                if form == "I07-JA":
                    validity = "invalid_administration" if index == 0 else "undetermined"
                    kind, state, score = "", "not_in_scope", ""
                cls.coded_rows.append(dict(zip(analysis.CODING_FIELDS, (oid, cid, validity, kind, state, score))))

        cls.seal_sha = seal_synthetic_tree(cls.spec)
        cls.report = audit.audit_wave(
            baseline_manifest=cls.spec["manifest"], namespaces=[cls.spec], wave_id=analysis.WAVE,
            now=datetime(2026, 11, 5, 1, tzinfo=timezone.utc),
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.home)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.report_path = self.base / "AUDIT_REPORT.json"
        self.approval = self.base / "approval.json"
        self.coding = self.base / "coded.csv"
        self.out = self.base / "out"
        write_json(self.report_path, self.report)
        self.coding.write_bytes(analysis.csv_bytes(self.coded_rows, analysis.CODING_FIELDS))
        self.approve()

    def approve(self, **changes):
        approval = {
            "schema_version": analysis.SCHEMA, "decision": "approved",
            "analysis_record_id": "MIBO2-W02-JP01-ACI-AER-001", "coding_method": "human",
            "approved_by": "Synthetic PI", "approved_at_utc": "2026-11-05T02:00:00Z",
            "reviewed_code_commit": "a" * 40, "environment": analysis.execution_environment(),
            "input_hashes": {
                "audit_report_sha256": audit.sha(self.report_path), "wave_seal_sha256": self.seal_sha,
            },
        }
        write_json(self.approval, {**approval, **changes})

    def invoke(self, coded=False, *, out=None, seal=None, extra=()):
        arguments = [
            sys.executable, "-B", analysis.__file__, "--audit-report", str(self.report_path),
            "--expected-seal-sha256", seal or self.seal_sha, "--output-dir", str(out or self.out),
        ]
        if coded:
            arguments.extend(("--coding", str(self.coding), "--expected-coding-sha256",
                              audit.sha(self.coding), "--approval", str(self.approval)))
        return subprocess.run([*arguments, *extra], capture_output=True, text=True, check=False)

    def table(self, name):
        with (self.out / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def by_form(self, name):
        return {r["query_form_id"]: r for r in self.table(name) if r["service_lineage_id"] == "MIBO-SL-001"}

    def assert_rejected(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())
        self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_technical_only_has_full_denominator_and_no_content_fields(self):
        self.assertEqual(self.invoke().returncode, 0)
        qc = self.table("W02_CELL_QC.csv")
        self.assertEqual(len(qc), 96)
        self.assertEqual(sum(int(r["n_planned"]) for r in qc), 960)
        self.assertNotIn("n_valid", qc[0])
        self.assertFalse((self.out / "W02_ANCHOR_CELLS.csv").exists())
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        for path in self.out.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(SECRET, path.read_text())

    def test_coded_output_counts_retries_and_keeps_refusals_and_real_scores(self):
        result = self.invoke(coded=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        qc = self.by_form("W02_CELL_QC.csv")
        for form, n, eligible in (("I03-EN", 7, False), ("I05-JA", 8, True), ("I05-EN", 10, True)):
            row = qc["MIBO-" + form]
            self.assertEqual((row["n_valid"], row["primary_eligible"]), (str(n), str(eligible)))
        row = qc["MIBO-I05-EN"]
        self.assertEqual((row["n_refusal"], row["n_submitted_attempts_lower_bound"],
                          row["n_submitted_retry_attempts_lower_bound"], row["n_completed_after_close"],
                          row["n_technical_failure_attempts"]), ("1", "11", "1", "1", "1"))
        self.assertEqual(qc["MIBO-I01-EN"]["n_safety_response"], "1")
        self.assertEqual((qc["MIBO-I07-JA"]["n_invalid_administration"], qc["MIBO-I07-JA"]["n_undetermined"]),
                         ("1", "1"))
        anchors = self.table("W02_ANCHOR_CELLS.csv")
        self.assertEqual(len(anchors), 32)
        self.assertEqual(len(self.table("W02_ANCHOR_FREQUENCIES.csv")), 200)
        cells = self.by_form("W02_ANCHOR_CELLS.csv")
        en = cells["MIBO-I05-EN"]
        self.assertEqual((en["score_denominator"], en["n_scored"], en["modal_deviation_rate"]), ("9", "10", "0.5"))
        self.assertEqual((en["min_points"], en["max_points"]), ("0", "9"))
        ja = cells["MIBO-I05-JA"]
        self.assertEqual((ja["n_valid"], ja["n_scored"], ja["n_cannot_determine"], ja["modal_deviation_rate"]),
                         ("8", "7", "1", ""))
        result = self.invoke(coded=True, out=self.base / "second")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in self.out.iterdir():
            self.assertNotIn(SECRET, path.read_text())
            self.assertEqual(path.read_bytes(), (self.base / "second" / path.name).read_bytes())

    def test_complete_960_capture_rehearsal(self):
        spec, rows = fixture(self.base / "full", version=analysis.VERSION)
        coded_rows = []
        for row in rows:
            capture(spec, row)
            anchor = analysis.ANCHORS.get(row["query_form_id"].rsplit("-", 1)[0])
            oid = row["attempt_id"]
            state, points = ("scored", str(anchor[1])) if anchor else ("not_in_scope", "")
            coded_rows.append(dict(zip(analysis.CODING_FIELDS, (
                oid, oid, "valid", "answer" if anchor else "", state, points,
            ))))
        self.seal_sha = seal_synthetic_tree(spec)
        report = audit.audit_wave(baseline_manifest=spec["manifest"], namespaces=[spec], wave_id=analysis.WAVE,
                                 now=datetime(2026, 11, 5, 1, tzinfo=timezone.utc))
        write_json(self.report_path, report)
        self.coding.write_bytes(analysis.csv_bytes(coded_rows, analysis.CODING_FIELDS))
        self.approve()
        result = self.invoke(coded=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        qc = self.table("W02_CELL_QC.csv")
        self.assertEqual(len(qc), 96)
        self.assertTrue(all(row["n_valid"] == "10" and row["complete_10"] == "True" for row in qc))
        self.assertEqual(sum(int(row["n_response_kind_unclassified"]) for row in qc), 640)
        anchors = self.table("W02_ANCHOR_CELLS.csv")
        self.assertEqual(len(anchors), 32)
        self.assertTrue(all(row["n_scored"] == "10" and row["normalized_mean"] == "1" for row in anchors))

    def test_rejects_seal_mismatch(self):
        self.assert_rejected(self.invoke(seal="0" * 64))

    def test_rejects_bad_approval_and_environment(self):
        for changes in ({"decision": "draft"}, {"environment": {}}, {"input_hashes": {}},
                        {"approved_at_utc": "2026-11-05T00:00:00Z"}):
            with self.subTest(changes=changes):
                self.approve(**changes)
                self.assert_rejected(self.invoke(coded=True))

    def test_rejects_missing_coding_foreign_or_wrong_attempt_and_inapplicable_score(self):
        candidates = [self.coded_rows[:-1]]
        for change in ({"capture_attempt_id": "A01"}, {"score_status": "cannot_determine", "score_points": "9"}):
            candidates.append([{**self.coded_rows[0], **change}, *self.coded_rows[1:]])
        for rows in candidates:
            self.coding.write_bytes(analysis.csv_bytes(rows, analysis.CODING_FIELDS))
            self.assert_rejected(self.invoke(coded=True))

    def test_rejects_duplicate_slot_cross_version_and_out_of_window_capture(self):
        for case in ("duplicate", "version", "window"):
            report = copy.deepcopy(self.report)
            row = next(r for r in report["observations"] if r["status"] == "verified_capture")
            if case == "duplicate":
                report["observations"][-1] = row
            if case == "version":
                row["variants"][0]["version"] = "2.0.4"
            if case == "window":
                entry = next(e for e in row["attempt_evidence"] if e["verified_capture"])
                entry["started_at_utc"] = "2026-11-05T00:00:00Z"
            write_json(self.report_path, report)
            self.assert_rejected(self.invoke())

    def test_rejects_partial_coded_mode_and_does_not_overwrite_output(self):
        self.assert_rejected(self.invoke(extra=("--coding", str(self.coding))))
        self.assert_rejected(self.invoke(coded=True, extra=("--expected-coding-sha256", "0" * 64)))
        self.assertEqual(self.invoke().returncode, 0)
        prior = (self.out / "W02_RUN_MANIFEST.json").read_bytes()
        self.assertNotEqual(self.invoke(coded=True).returncode, 0)
        self.assertEqual((self.out / "W02_RUN_MANIFEST.json").read_bytes(), prior)


if __name__ == "__main__":
    unittest.main()
