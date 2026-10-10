"""Regression checks for altered execution order with otherwise valid counts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from test_core_v2_api import CoreV2Fixture, runner


class CoreV2ManifestOrderTests(unittest.TestCase):
    def _rows(self, root, wave_id):
        fixture = CoreV2Fixture(root)
        freeze = json.loads(fixture.freeze.read_text())
        freeze["wave_id"] = wave_id
        fixture.freeze.write_text(json.dumps(freeze))
        rows = runner.generate_manifest(protocol_path=fixture.protocol,
            freeze_path=fixture.freeze, wave_id=wave_id, site_id="JP01")
        return fixture, rows

    def test_swapped_order_is_rejected_in_both_wave_types(self):
        for wave_id in ("MIBO2-W01", "MIBO2-W02"):
            with self.subTest(wave=wave_id), tempfile.TemporaryDirectory() as d:
                fixture, rows = self._rows(Path(d), wave_id)
                rows[0]["execution_order"], rows[1]["execution_order"] = (
                    rows[1]["execution_order"], rows[0]["execution_order"])
                errors = runner.validate_manifest(rows,
                    protocol_path=fixture.protocol, freeze_path=fixture.freeze)
                self.assertTrue(any("deterministic manifest execution_order" in e
                                    for e in errors), errors)

    def test_csv_row_position_does_not_change_order_identity(self):
        with tempfile.TemporaryDirectory() as d:
            fixture, rows = self._rows(Path(d), "MIBO2-W02")
            rows.reverse()
            self.assertEqual(runner.validate_manifest(rows,
                protocol_path=fixture.protocol, freeze_path=fixture.freeze), [])

    def test_nonempty_observation_identity_cannot_enter_initial_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            fixture, rows = self._rows(Path(d), "MIBO2-W02")
            rows[0]["observation_id"] = "already-observed"
            errors = runner.validate_manifest(rows,
                protocol_path=fixture.protocol, freeze_path=fixture.freeze)
            self.assertTrue(any("deterministic manifest observation_id" in e
                                for e in errors), errors)

    def test_extra_columns_and_invalid_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            fixture, rows = self._rows(Path(d), "MIBO2-W02")
            extra = copy.deepcopy(rows)
            extra[0]["unfrozen_setting"] = "value"
            errors = runner.validate_manifest(extra,
                protocol_path=fixture.protocol, freeze_path=fixture.freeze)
            self.assertTrue(any("columns mismatch" in e for e in errors))
            rows[0]["execution_order"] = "invalid"
            self.assertIn("Core v2 manifest contains invalid integer fields",
                runner.validate_manifest(rows, protocol_path=fixture.protocol,
                                         freeze_path=fixture.freeze))


if __name__ == "__main__":
    unittest.main()
