"""Synthetic installed-runtime corruption and path-boundary tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_health


class InstalledSnapshotIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "installed"
        self.root.mkdir()
        (self.root / "automation").mkdir()
        self.payload = self.root / "automation" / "collector.py"
        self.payload.write_text("# synthetic source\n", encoding="utf-8")
        self.provenance = self.root / "INSTALL_PROVENANCE.json"
        self.provenance.write_text(json.dumps({
            "source_commit_sha": "a" * 40, "source_worktree_clean": True,
        }), encoding="utf-8")
        self.sums = self.root / "INSTALL_SHA256SUMS.txt"
        self.seal()

    def seal(self):
        self.lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(self.root).as_posix()}"
                      for p in (self.provenance, self.payload)]
        self.sums.write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    def assert_failed(self, fragment):
        state = runtime_health.installed_snapshot_state(self.root)
        self.assertFalse(state["snapshot_integrity_pass"])
        self.assertFalse(state["working_tree_clean"])
        self.assertTrue(any(fragment in error for error in state["snapshot_errors"]), state)
        return state

    def test_complete_synthetic_snapshot_passes(self):
        self.assertTrue(runtime_health.installed_snapshot_state(self.root)["snapshot_integrity_pass"])

    def test_absent_seal_is_none_but_partial_seal_fails_closed(self):
        self.sums.unlink()
        self.assert_failed("INSTALL_SHA256SUMS")
        self.provenance.unlink()
        self.assertIsNone(runtime_health.installed_snapshot_state(self.root))

    def test_empty_or_provenance_only_manifest_fails(self):
        self.sums.write_text("\n", encoding="utf-8")
        self.assert_failed("empty")
        self.sums.write_text(self.lines[0] + "\n", encoding="utf-8")
        self.assert_failed("absent from checksum")

    def test_unbound_provenance_and_extra_code_fail(self):
        self.sums.write_text(self.lines[1] + "\n", encoding="utf-8")
        self.assert_failed("INSTALL_PROVENANCE.json")
        self.seal()
        (self.root / "automation" / "extra.py").write_text("# synthetic\n", encoding="utf-8")
        self.assert_failed("extra.py")

    def test_unbound_bytecode_is_not_exempted(self):
        cache = self.root / "automation" / "__pycache__"
        cache.mkdir()
        (cache / "collector.cpython-312.pyc").write_bytes(b"synthetic bytecode")
        self.assert_failed("collector.cpython-312.pyc")

    def test_invalid_commit_or_dirty_source_fails_after_rehash(self):
        for commit, clean in (("z" * 40, True), ("a" * 39, True), ("A" * 40, True), ("a" * 40, False)):
            with self.subTest(commit=commit, clean=clean):
                self.provenance.write_text(json.dumps({"source_commit_sha": commit, "source_worktree_clean": clean}))
                self.seal()
                self.assert_failed("source commit" if clean else "source worktree")

    def test_invalid_provenance_shape_and_encoding_fail(self):
        for payload in (b"[]", b"null", b"not-json", b"\xff"):
            with self.subTest(payload=payload):
                self.provenance.write_bytes(payload)
                self.seal()
                self.assert_failed("INSTALL_PROVENANCE")

    def test_duplicate_malformed_and_invalid_hash_lines_fail(self):
        for bad, fragment in ((self.lines[1], "duplicate"), ("malformed", "malformed"),
                              ("x" * 64 + "  automation/collector.py", "invalid checksum digest")):
            with self.subTest(bad=bad):
                self.sums.write_text("\n".join(self.lines + [bad]) + "\n")
                self.assert_failed(fragment)

    def test_escaping_absolute_and_noncanonical_paths_are_never_hashed(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("synthetic outside\n", encoding="utf-8")
        for rel in ("../outside.txt", str(outside), "automation/../INSTALL_PROVENANCE.json",
                    "automation//collector.py", "./automation/collector.py", "automation\\collector.py",
                    "INSTALL_SHA256SUMS.txt"):
            with self.subTest(rel=rel):
                self.sums.write_text("\n".join(self.lines + ["b" * 64 + "  " + rel]) + "\n")
                with mock.patch.object(runtime_health, "_sha256", wraps=runtime_health._sha256) as hashed:
                    self.assert_failed("unsafe checksum path")
                self.assertTrue(all(call.args[0].is_relative_to(self.root) for call in hashed.call_args_list))

    def test_symlink_payload_directory_and_markers_fail_without_reading_target(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("synthetic outside\n")
        link = self.root / "automation" / "linked"
        link.symlink_to(outside, target_is_directory=True)
        self.assert_failed("symlink")
        link.unlink()
        self.payload.unlink()
        self.payload.symlink_to(outside / "secret.txt")
        self.assert_failed("symlink")
        self.payload.unlink()
        self.payload.write_text("# synthetic source\n")
        self.provenance.unlink()
        self.provenance.symlink_to(outside / "secret.txt")
        self.assert_failed("symlink")
        self.provenance.unlink()
        self.provenance.write_text('{"source_commit_sha":"' + "a" * 40 + '","source_worktree_clean":true}')
        self.seal()
        self.sums.unlink()
        self.sums.symlink_to(outside / "secret.txt")
        self.assert_failed("INSTALL_SHA256SUMS")

    def test_installed_root_symlink_is_rejected(self):
        link = Path(self.temp.name) / "linked-root"
        link.symlink_to(self.root, target_is_directory=True)
        state = runtime_health.installed_snapshot_state(link)
        self.assertFalse(state["snapshot_integrity_pass"])
        self.assertIn("installed root must be a real directory", state["snapshot_errors"])

    def test_damaged_seal_does_not_fall_back_to_parent_git_checkout(self):
        self.sums.unlink()
        with mock.patch.object(runtime_health, "_run", return_value=(0, "a" * 40)) as git:
            state = runtime_health.provenance_state(self.root)
        self.assertFalse(state["working_tree_clean"])
        git.assert_not_called()


if __name__ == "__main__":
    unittest.main()
