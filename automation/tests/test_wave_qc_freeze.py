from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as core
import ui_capture
import wave_freeze
import wave_qc

UI_CONFIG = Path(__file__).with_name("ui_configuration.synthetic.json")
ROSTER = Path(__file__).with_name("operator_roster.synthetic.json")


class WaveQcFreezeTests(unittest.TestCase):
    def prepare(self, root: Path):
        rows = core.generate_ui_manifest("MIBO-W01")
        manifest = root / "ui.csv"
        core.write_csv(rows, manifest)
        target = [
            r for r in rows
            if r["service_lineage_id"] == "MIBO-SL-001"
            and r["query_form_id"] == "MIBO-I03-EN"
            and r["window_id"] == "WA"
        ]
        self.assertEqual(len(target), 10)
        prompt = next(f["text"] for f in core._forms() if f["query_form_id"] == "MIBO-I03-EN")
        for idx, row in enumerate(target[:8], 1):
            ui_capture.capture_ui_observation(
                data_root=root / "data", row=row, prompt_text=prompt,
                output_text=f"synthetic response {idx}",
                ui_configuration_path=UI_CONFIG,
                operator_roster_path=ROSTER,
                operator_id="operator-openai",
                operator_confirmed_new_session=True,
                submitted_at_utc=f"2026-09-01T01:{idx:02d}:00Z",
                captured_at_utc=f"2026-09-01T01:{idx:02d}:30Z",
                sources_displayed=False,
                sources_text=None,
                now=datetime(2026, 9, 1, 1, idx, 30, tzinfo=timezone.utc),
            )
        return rows, manifest

    def test_qc_classifies_eight_of_ten_as_primary_without_imputation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, manifest = self.prepare(root)
            report = wave_qc.run_qc(
                data_root=root / "data",
                ui_manifest=manifest,
                ui_configuration=UI_CONFIG,
                operator_roster_path=ROSTER,
            )
            self.assertTrue(report["integrity_pass"])
            self.assertFalse(report["imputation_performed"])
            cell = next(
                c for c in report["cells"]
                if c["service_lineage_id"] == "MIBO-SL-001"
                and c["query_form_id"] == "MIBO-I03-EN"
                and c["window_id"] == "WA"
            )
            self.assertEqual(cell["valid_replications"], 8)
            self.assertEqual(cell["eligibility"], "primary")
            self.assertEqual(report["operational_audit"]["sample_size"], 1)

    def test_wave_freeze_is_forbidden_before_close_and_append_only_after_close(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, manifest = self.prepare(root)
            with self.assertRaisesRegex(ValueError, "before registered field close"):
                wave_freeze.freeze_wave(
                    data_root=root / "data", ui_manifest=manifest,
                    ui_configuration=UI_CONFIG, operator_roster=ROSTER,
                    now=datetime(2026, 9, 2, 23, 59, tzinfo=timezone.utc),
                    repo_root=HERE.parent,
                )
            result = wave_freeze.freeze_wave(
                data_root=root / "data", ui_manifest=manifest,
                ui_configuration=UI_CONFIG, operator_roster=ROSTER,
                now=datetime(2026, 9, 3, 0, 1, tzinfo=timezone.utc),
                repo_root=HERE.parent,
            )
            self.assertEqual(result["status"], "WAVE_FROZEN_BEFORE_SUBSTANTIVE_CODING")
            self.assertEqual(len(result["sha256s_sha256"]), 64)
            release = root / "data" / "v1.0" / "JP01" / "MIBO-W01" / "release"
            self.assertTrue((release / "WAVE_QC_REPORT.json").exists())
            self.assertTrue((release / "OPERATIONAL_AUDIT_SAMPLE.json").exists())
            self.assertTrue((release / "WAVE_FREEZE_RECORD.json").exists())
            self.assertTrue((release / "SHA256SUMS.txt").exists())
            with self.assertRaises(FileExistsError):
                wave_freeze.freeze_wave(
                    data_root=root / "data", ui_manifest=manifest,
                    ui_configuration=UI_CONFIG, operator_roster=ROSTER,
                    now=datetime(2026, 9, 3, 0, 2, tzinfo=timezone.utc),
                    repo_root=HERE.parent,
                )


if __name__ == "__main__":
    unittest.main()
