import json
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import prewave_bundle as pb

UI_CONFIG = Path(__file__).with_name("ui_configuration.synthetic.json")
PROVIDER_FREEZE = Path(__file__).with_name("provider_freeze.synthetic.json")
ROSTER = Path(__file__).with_name("operator_roster.synthetic.json")


class PreWaveBundleTests(unittest.TestCase):
    def test_builds_w01_bundle_but_never_authorizes_collection(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "bundle"
            result = pb.build_bundle(
                wave_id="MIBO-W01",
                site_id="JP01",
                ui_configuration=UI_CONFIG,
                operator_roster_path=ROSTER,
                provider_freeze=PROVIDER_FREEZE,
                out_dir=out,
            )
            self.assertEqual(result["ui"]["rows"], 1120)
            self.assertEqual(len(result["ui"]["operator_roster_sha256"]), 64)
            self.assertEqual(result["ui"]["operations_lead"], "lead-test")
            self.assertEqual(result["paired"]["rows"], 160)
            self.assertEqual(result["paired"]["eligible_lineage_count"], 2)
            self.assertTrue(result["paired"]["primary_paired_ready"])
            self.assertEqual(result["authorization_status"], "NOT_AUTHORIZED_BY_BUNDLE_BUILDER")
            auth = json.loads((out / "execution_authorization.PAIRED.template.json").read_text(encoding="utf-8"))
            self.assertFalse(auth["authorized"])
            self.assertFalse(auth["terms_review_complete"])
            self.assertFalse(auth["dry_run_complete"])
            self.assertEqual(auth["operations_lead"], "lead-test")
            self.assertEqual(len(auth["manifest_sha256"]), 64)
            self.assertEqual(len(auth["provider_freeze_sha256"]), 64)
            self.assertEqual(len(auth["operator_roster_sha256"]), 64)
            self.assertTrue((out / "configuration" / "operator_roster.json").exists())
            self.assertTrue((out / "SHA256SUMS.txt").exists())

    def test_rejects_unready_ui_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bad = json.loads(UI_CONFIG.read_text(encoding="utf-8"))
            bad["ecological_live"]["MIBO-SL-001"]["status"] = "pending"
            bad_path = root / "bad-ui.json"
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not ready"):
                pb.build_bundle(
                    wave_id="MIBO-W01",
                    site_id="JP01",
                    ui_configuration=bad_path,
                    operator_roster_path=ROSTER,
                    provider_freeze=PROVIDER_FREEZE,
                    out_dir=root / "bundle",
                )

    def test_rejects_roster_with_unassigned_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bad = json.loads(ROSTER.read_text(encoding="utf-8"))
            bad["service_operators"]["MIBO-SL-004"] = []
            bad_path = root / "bad-roster.json"
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least one assigned"):
                pb.build_bundle(
                    wave_id="MIBO-W01",
                    site_id="JP01",
                    ui_configuration=UI_CONFIG,
                    operator_roster_path=bad_path,
                    provider_freeze=PROVIDER_FREEZE,
                    out_dir=root / "bundle",
                )


if __name__ == "__main__":
    unittest.main()
