import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as m


class ManifestTests(unittest.TestCase):
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

    def test_paired_two_lineages(self):
        rows = m.generate_paired_manifest(
            "MIBO-W01", ["MIBO-SL-002", "MIBO-SL-003"]
        )
        self.assertEqual(len(rows), 160)
        self.assertEqual(m.validate_manifest(rows), [])

    def test_perplexity_is_not_admissible_paired(self):
        with self.assertRaises(ValueError):
            m.generate_paired_manifest("MIBO-W01", ["MIBO-SL-004"])


if __name__ == "__main__":
    unittest.main()
