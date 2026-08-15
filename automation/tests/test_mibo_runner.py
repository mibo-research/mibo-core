import json
import tempfile
import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as m

FIXTURE = Path(__file__).with_name("provider_freeze.synthetic.json")


class ManifestTests(unittest.TestCase):
    def test_frozen_config_integrity(self):
        self.assertEqual(m.verify_frozen_config(), [])

    def test_seed_is_registered_formula(self):
        self.assertEqual(
            m.deterministic_seed("MIBO-W01", "JP01", "LUI"),
            int(__import__("hashlib").sha256(
                b"MIBO-v1.0|MIBO-W01|JP01|LUI"
            ).hexdigest()[:8], 16),
        )

    def test_w01_ui_count_and_windows(self):
        rows = m.generate_ui_manifest("MIBO-W01")
        self.assertEqual(len(rows), 1120)
        self.assertEqual(sum(r["window_id"] == "WA" for r in rows), 160)
        self.assertEqual(sum(r["window_id"] == "WB" for r in rows), 160)
        self.assertEqual(sum(r["window_id"] == "STD" for r in rows), 800)
        self.assertEqual(m.validate_manifest(rows), [])

    def test_non_calibration_count(self):
        rows = m.generate_ui_manifest("MIBO-W02")
        self.assertEqual(len(rows), 960)
        self.assertEqual(m.validate_manifest(rows), [])

    def test_paired_two_lineages_requires_final_freeze(self):
        rows = m.generate_paired_manifest(
            "MIBO-W01", ["MIBO-SL-002", "MIBO-SL-003"], FIXTURE
        )
        self.assertEqual(len(rows), 160)
        self.assertEqual(m.validate_manifest(rows), [])
        self.assertTrue(all(r["configuration_freeze_sha256"] for r in rows))
        self.assertTrue(all(r["model_id"].startswith("synthetic-") for r in rows))

    def test_pending_reserve_lineage_is_rejected(self):
        with self.assertRaises(ValueError):
            m.generate_paired_manifest("MIBO-W01", ["MIBO-SL-001"], FIXTURE)

    def test_perplexity_is_not_admissible_paired(self):
        with self.assertRaises(ValueError):
            m.generate_paired_manifest("MIBO-W01", ["MIBO-SL-004"], FIXTURE)

    def test_unfrozen_provider_record_is_rejected(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["frozen_at_utc"] = None
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "freeze.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                m.generate_paired_manifest("MIBO-W01", ["MIBO-SL-002"], path)


if __name__ == "__main__":
    unittest.main()
