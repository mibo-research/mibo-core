import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import runtime_health as rh

SHADOW_FREEZE = Path(__file__).with_name("api_shadow_freeze.synthetic.json")


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

    def test_shadow_credentials_derive_only_from_eligible_shadow_lineages(self):
        envs = rh.shadow_credential_envs(SHADOW_FREEZE)
        self.assertEqual(
            envs,
            ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY"],
        )

    @mock.patch.object(rh, "provenance_state")
    @mock.patch.object(rh, "ntp_state")
    @mock.patch.object(rh.shutil, "disk_usage")
    def test_health_report_records_presence_not_secret_values(self, disk_usage, ntp_state, provenance_state):
        disk_usage.return_value = type("U", (), {"free": 10 * 1024 ** 3})()
        ntp_state.return_value = {"check_available": True, "ntp_synchronized": True, "raw": "yes"}
        provenance_state.return_value = {
            "commit_sha": "b" * 40,
            "commit_resolved": True,
            "working_tree_clean": True,
            "provenance_mode": "installed_snapshot",
        }
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"OPENAI_API_KEY": "super-secret"}):
            report = rh.build_report(
                repo_root=Path(d), data_root=Path(d), credential_envs=["OPENAI_API_KEY"]
            )
        self.assertTrue(report["pass"])
        self.assertTrue(report["credentials_present"]["OPENAI_API_KEY"])
        self.assertFalse(report["credentials_values_recorded"])
        self.assertNotIn("super-secret", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
