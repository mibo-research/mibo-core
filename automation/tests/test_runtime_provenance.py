import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import runtime_health as rh


class InstalledRuntimeProvenanceTests(unittest.TestCase):
    def test_installed_snapshot_verifies_commit_and_file_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "automation").mkdir()
            tracked = root / "automation" / "example.py"
            tracked.write_text("print('ok')\n", encoding="utf-8")
            provenance = {
                "schema_version": "1.0",
                "source_commit_sha": "a" * 40,
                "installed_at_utc": "2026-08-31T00:00:00Z",
                "source_worktree_clean": True,
                "collection_enabled_by_provisioner": False,
            }
            (root / "INSTALL_PROVENANCE.json").write_text(json.dumps(provenance), encoding="utf-8")
            entries = []
            for path in (tracked, root / "INSTALL_PROVENANCE.json"):
                entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
            (root / "INSTALL_SHA256SUMS.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
            state = rh.installed_snapshot_state(root)
            self.assertTrue(state["commit_resolved"])
            self.assertTrue(state["working_tree_clean"])
            self.assertEqual(state["commit_sha"], "a" * 40)
            tracked.write_text("tampered\n", encoding="utf-8")
            state = rh.installed_snapshot_state(root)
            self.assertFalse(state["working_tree_clean"])
            self.assertTrue(any("hash mismatch" in e for e in state["snapshot_errors"]))


if __name__ == "__main__":
    unittest.main()
