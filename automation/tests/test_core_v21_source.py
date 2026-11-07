"""Immutable Git-source snapshot tests. Only temporary local repositories."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v21_source as source


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        (self.root / ".gitattributes").write_text("*.md text eol=lf\n")
        (self.root / "example.md").write_bytes(b"synthetic\r\n")
        self.commit = self.commit_all()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL)

    def commit_all(self):
        self.git("add", "--all")
        self.git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic local fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_clean_git_snapshot_uses_committed_LF_not_filtered_worktree_bytes(self):
        identity, files = source.committed_snapshot(self.root, self.commit)
        self.assertEqual(files["example.md"], b"synthetic\n")
        self.assertEqual((self.root / "example.md").read_bytes(), b"synthetic\r\n")
        self.assertTrue(identity["source_worktree_git_clean"])
        self.assertEqual(identity["reviewed_candidate_commit"], self.commit)

    def test_dirty_worktree_cannot_be_pinned(self):
        (self.root / "example.md").write_text("modified\n")
        with self.assertRaisesRegex(ValueError, "clean"):
            source.committed_snapshot(self.root, self.commit)

    def test_untracked_or_staged_changes_cannot_be_pinned(self):
        path = self.root / "new.txt"
        path.write_text("synthetic")
        for staged in (False, True):
            if staged: self.git("add", "new.txt")
            with self.subTest(staged=staged), self.assertRaisesRegex(ValueError, "clean"):
                source.committed_snapshot(self.root, self.commit)

    def test_short_or_wrong_commit_cannot_be_pinned(self):
        for commit in (self.commit[:12], "0" * 40):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                source.committed_snapshot(self.root, commit)

    def test_staged_snapshot_matches_the_later_clean_commit_tree(self):
        (self.root / "second.txt").write_text("synthetic second file")
        self.git("add", "--all")
        staged, expected = source.staged_snapshot(self.root)
        commit = self.commit_all()
        actual, files = source.committed_snapshot(self.root, commit)
        self.assertEqual(staged["source_tree_sha1"], actual["source_tree_sha1"])
        self.assertEqual(expected, files)

    def test_staged_snapshot_refuses_unstaged_or_untracked_inputs(self):
        (self.root / "example.md").write_text("modified\n")
        with self.assertRaisesRegex(ValueError, "stage only"):
            source.staged_snapshot(self.root)

    def test_source_tree_links_are_rejected(self):
        os.symlink("example.md", self.root / "linked.md")
        self.commit = self.commit_all()
        with self.assertRaisesRegex(ValueError, "link"):
            source.committed_snapshot(self.root, self.commit)

    def test_export_ignore_cannot_omit_an_unreviewed_source_member(self):
        (self.root / ".gitattributes").write_text("*.md text eol=lf\nexample.md export-ignore\n")
        self.commit = self.commit_all()
        _identity, files = source.committed_snapshot(self.root, self.commit)
        self.assertEqual(files["example.md"], b"synthetic\n")

    def test_autocrlf_true_cannot_transform_source_blob_bytes(self):
        self.git("config", "core.autocrlf", "true")
        _identity, files = source.committed_snapshot(self.root, self.commit)
        self.assertEqual(files["example.md"], b"synthetic\n")

    def test_private_source_paths_are_rejected_without_printing_content(self):
        (self.root / ".env").write_text("SYNTHETIC-NOT-A-KEY")
        self.commit = self.commit_all()
        with self.assertRaisesRegex(ValueError, "private") as caught:
            source.committed_snapshot(self.root, self.commit)
        self.assertNotIn("SYNTHETIC-NOT-A-KEY", str(caught.exception))

    def test_snapshot_writes_only_to_an_empty_destination(self):
        target = Path(self.tmp.name) / "snapshot"
        target.mkdir()
        source.write_snapshot(target, {"sub/example.txt": b"synthetic"})
        self.assertEqual((target / "sub/example.txt").read_bytes(), b"synthetic")
        with self.assertRaisesRegex(ValueError, "empty"):
            source.write_snapshot(target, {"other.txt": b"synthetic"})

    def test_snapshot_rejects_path_traversal(self):
        target = Path(self.tmp.name) / "snapshot"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            source.write_snapshot(target, {"../escape": b"synthetic"})


if __name__ == "__main__":
    unittest.main()
