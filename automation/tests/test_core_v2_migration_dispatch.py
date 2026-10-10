"""Unresolved dispatch must block changing Google's execution namespace."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_priority as priority
import core_v2_standard as standard


class DispatchMigrationTests(unittest.TestCase):
    def test_old_first_dispatch_blocks_priority_before_raw_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "v2.0.2/JP01/MIBO2-W02/metadata"
            root.mkdir(parents=True)
            (root / "first-dispatch-MIBO-SL-003.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "prior Google dispatch"):
                priority.block_prior_google_attempts(Path(d), "JP01", "MIBO2-W02")

    def test_unresolved_google_dispatch_blocks_both_migrations(self):
        for module in (priority, standard):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "v2.0.2/JP01/MIBO2-W02/dispatch"
                root.mkdir(parents=True)
                (root / "synthetic.json").write_text(json.dumps({
                    "service_lineage_id": "MIBO-SL-003"}))
                with self.assertRaisesRegex(ValueError, "prior Google confirmatory"):
                    module.block_prior_google_attempts(Path(d), "JP01", "MIBO2-W02")

    def test_other_lineage_dispatch_does_not_block_google(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "v2.0.2/JP01/MIBO2-W02/dispatch"
            root.mkdir(parents=True)
            (root / "synthetic.json").write_text(json.dumps({
                "service_lineage_id": "MIBO-SL-001"}))
            priority.block_prior_google_attempts(Path(d), "JP01", "MIBO2-W02")
            standard.block_prior_google_attempts(Path(d), "JP01", "MIBO2-W02")

    def test_unknown_prior_dispatch_lineage_blocks_migration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "v2.0.2/JP01/MIBO2-W02/dispatch"
            root.mkdir(parents=True)
            (root / "synthetic.json").write_text("{}")
            for module in (priority, standard):
                with self.assertRaisesRegex(ValueError, "cannot be classified"):
                    module.block_prior_google_attempts(Path(d), "JP01", "MIBO2-W02")


if __name__ == "__main__":
    unittest.main()
