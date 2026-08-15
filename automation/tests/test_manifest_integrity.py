import copy
import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as m
from manifest_integrity import strict_validate_manifest

FIXTURE = Path(__file__).with_name("provider_freeze.synthetic.json")


class StrictManifestIntegrityTests(unittest.TestCase):
    def test_ui_control_passes(self):
        rows = m.generate_ui_manifest("MIBO-W01")
        self.assertEqual(strict_validate_manifest(rows), [])

    def test_ui_random_seed_mutation_is_rejected(self):
        rows = m.generate_ui_manifest("MIBO-W01")
        rows[0]["random_seed"] = 0
        errors = strict_validate_manifest(rows)
        self.assertTrue(any("random_seed mismatch" in e for e in errors))

    def test_ui_unique_attempt_id_mutation_is_rejected(self):
        rows = m.generate_ui_manifest("MIBO-W01")
        rows[0]["attempt_id"] = "forged-but-unique"
        errors = strict_validate_manifest(rows)
        self.assertTrue(any("attempt_id mismatch" in e for e in errors))

    def test_service_and_anchor_mutations_are_rejected(self):
        rows = m.generate_ui_manifest("MIBO-W01")
        rows[0]["service_name"] = "Wrong Service"
        rows[0]["provider"] = "Wrong Provider"
        rows[0]["anchor"] = "true" if rows[0]["anchor"] == "false" else "false"
        errors = strict_validate_manifest(rows)
        self.assertTrue(any("service_name mismatch" in e for e in errors))
        self.assertTrue(any("provider mismatch" in e for e in errors))
        self.assertTrue(any("anchor flag mismatch" in e for e in errors))

    def test_paired_seed_and_attempt_id_mutations_are_rejected(self):
        rows = m.generate_paired_manifest(
            "MIBO-W01", ["MIBO-SL-002", "MIBO-SL-003"], FIXTURE
        )
        control = strict_validate_manifest(copy.deepcopy(rows))
        self.assertEqual(control, [])

        rows[0]["random_seed"] = 1
        rows[1]["attempt_id"] = "paired-forged-but-unique"
        errors = strict_validate_manifest(rows)
        self.assertTrue(any("random_seed mismatch" in e for e in errors))
        self.assertTrue(any("attempt_id mismatch" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
