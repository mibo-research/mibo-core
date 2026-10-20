"""Exercise the VM stager with synthetic Git/archive/host commands, offline."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
STAGER = REPO / "runtime/stage-core-v2-w02.sh"
COMMIT = "a" * 40


class CoreV2W02StagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.store = self.root / "private"
        self.store.mkdir()
        self.installs = self.root / "installs"
        self.installs.mkdir()
        self.audit = self.root / "command-audit.jsonl"
        self._stub("hostname", "#!/bin/sh\nprintf '%s\\n' synthetic-vm\n")
        self._stub("id", "#!/bin/sh\nprintf '%s\\n' 0\n")
        self._stub("getent", "#!/bin/sh\nprintf '%s\\n' 'mibo:x:999:'\n")
        self._stub("chown", "#!/bin/sh\nexit 0\n")
        self._stub("systemctl", "#!/bin/sh\necho 'service mutation forbidden' >&2\nexit 99\n")
        self._stub("mktemp", "#!/usr/bin/python3\nimport sys,tempfile\n"
                   f"root={str(self.root)!r}\n"
                   "target=sys.argv[-1]\n"
                   "parent=root+'/private' if target.startswith('/srv/mibo-private/') else root+'/installs'\n"
                   "print(tempfile.mkdtemp(prefix='candidate-',dir=parent))\n")
        self.env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                        OPENAI_API_KEY="synthetic-inherited-secret", MIBO_CORE_V2_EXECUTION="forbidden")
        # Redirect only the fixed evidence-root existence check. mktemp itself
        # is a synthetic command, so production /opt and /srv are never touched.
        self.script = self.root / "stager.sh"
        self.script.write_text(STAGER.read_text().replace("test -d /srv/mibo-private", f"test -d '{self.store}'"))

    def _stub(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def _payload(self, *, tests_pass=True):
        payload = self.root / "payload"
        (payload / "automation/tests").mkdir(parents=True, exist_ok=True)
        (payload / "automation/config").mkdir(exist_ok=True)
        (payload / "runtime").mkdir(exist_ok=True)
        for name in ("mibo_runner.py", "manifest_integrity.py", "runtime_health.py"):
            shutil.copyfile(REPO / "automation" / name, payload / "automation" / name)
        for path in (REPO / "automation/config").glob("*.json"):
            shutil.copyfile(path, payload / "automation/config" / path.name)
        shutil.copyfile(REPO / "automation/tests/provider_freeze.synthetic.json",
                        payload / "automation/tests/provider_freeze.synthetic.json")
        shutil.copyfile(REPO / "runtime/seal-installed-snapshot.py",
                        payload / "runtime/seal-installed-snapshot.py")
        (payload / "automation/tests/test_payload.py").write_text(
            "import os,unittest\nclass SyntheticPayload(unittest.TestCase):\n"
            " def test_clean_environment(self):\n"
            "  self.assertNotIn('OPENAI_API_KEY',os.environ)\n"
            "  self.assertNotIn('MIBO_CORE_V2_EXECUTION',os.environ)\n"
            "  self.assertEqual(os.environ.get('PYTHONDONTWRITEBYTECODE'),'1')\n"
            f"  self.assertTrue({tests_pass!r})\n")
        path = self.root / "payload.tar"
        with tarfile.open(path, "w") as tar:
            for item in sorted(payload.rglob("*")):
                tar.add(item, arcname=item.relative_to(payload).as_posix(), recursive=False)
        return path

    def _git(self, *, resolved_commit=COMMIT, tests_pass=True):
        payload = self._payload(tests_pass=tests_pass)
        self._stub("git", "#!/usr/bin/python3\nimport json,pathlib,sys\n"
                   f"audit=pathlib.Path({str(self.audit)!r})\n"
                   "with audit.open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
                   "args=sys.argv[1:]\n"
                   "if 'init' in args: pathlib.Path(args[-1]).mkdir()\n"
                   f"elif 'rev-parse' in args: print({resolved_commit!r})\n"
                   f"elif 'archive' in args: sys.stdout.buffer.write(pathlib.Path({str(payload)!r}).read_bytes())\n"
                   "elif 'fetch' not in args: raise SystemExit(98)\n")

    def _run(self, commit=COMMIT, host="synthetic-vm"):
        return subprocess.run(["bash", str(self.script), commit, host], env=self.env,
                              text=True, capture_output=True, timeout=30, check=False)

    def test_wrong_host_or_short_commit_refuses_before_git_or_candidate_writes(self):
        self._git()
        for commit, host in (("main", "synthetic-vm"), (COMMIT, "cloudshell")):
            with self.subTest(commit=commit, host=host):
                result = self._run(commit, host)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(list(self.store.iterdir()), [])
                self.assertEqual(list(self.installs.iterdir()), [])
                self.assertFalse(self.audit.exists())

    def test_reviewed_source_is_staged_tested_and_hash_bound_without_arming(self):
        self._git()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("STAGING_SOURCE_INTEGRITY=PASS", result.stdout)
        self.assertNotIn("synthetic-inherited-secret", result.stdout + result.stderr)
        evidence = next(self.store.iterdir())
        source = next(self.installs.iterdir())
        receipt_path = evidence / "W02_STAGING_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["source_commit_sha"], COMMIT)
        self.assertFalse(receipt["services_installed"])
        self.assertFalse(receipt["execution_authorized"])
        self.assertEqual(receipt["dispatched_calls"], 0)
        self.assertFalse(receipt["provider_readiness_checks_performed"])
        self.assertTrue(receipt["installed_snapshot_integrity_pass"])
        self.assertEqual(receipt["install_sha256s_sha256"],
                         hashlib.sha256((source / "INSTALL_SHA256SUMS.txt").read_bytes()).hexdigest())
        self.assertEqual(receipt["synthetic_tests_log_sha256"],
                         hashlib.sha256((evidence / "synthetic-tests.log").read_bytes()).hexdigest())
        self.assertEqual(receipt["staging_tool_sha256"], hashlib.sha256(self.script.read_bytes()).hexdigest())
        self.assertIn(hashlib.sha256(receipt_path.read_bytes()).hexdigest(), result.stdout)
        self.assertFalse(list(source.rglob("*.pyc")))
        self.assertFalse(list(source.rglob("__pycache__")))
        commands = [json.loads(line) for line in self.audit.read_text().splitlines()]
        fetch = next(cmd for cmd in commands if "fetch" in cmd)
        self.assertEqual(fetch[-2:], ["https://github.com/mibo-research/mibo-core.git", COMMIT])
        self.assertIn("credential.helper=", fetch)
        self.assertIn("core.hooksPath=/dev/null", fetch)
        # A second staging run creates a separate candidate; it cannot overwrite
        # the reviewed first candidate or any W01 installation.
        previous = receipt_path.read_bytes()
        again = self._run()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(len(list(self.store.iterdir())), 2)
        self.assertEqual(len(list(self.installs.iterdir())), 2)
        self.assertEqual(receipt_path.read_bytes(), previous)

    def test_mismatched_fetch_or_failed_synthetic_suite_preserves_failure_evidence(self):
        for commit, tests_pass in (("b" * 40, True), (COMMIT, False)):
            with self.subTest(commit=commit, tests_pass=tests_pass):
                self._git(resolved_commit=commit, tests_pass=tests_pass)
                result = self._run()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("retained private evidence", result.stderr)
                latest = max(self.store.iterdir(), key=lambda p: p.stat().st_mtime_ns)
                self.assertTrue((latest / "STAGING_FAILURE.txt").is_file())
                self.assertFalse((latest / "W02_STAGING_RECEIPT.json").exists())
                self.assertTrue(list(self.installs.iterdir()))
                self.assertNotIn("STAGING_SOURCE_INTEGRITY=PASS", result.stdout)

    def test_stager_has_no_private_config_or_collection_path(self):
        text = STAGER.read_text()
        for forbidden in ("/etc/mibo", "systemctl ", "prepare-core-v2", "core_v2_executor.py",
                          "api_preflight.py", "core_v2_preflight.py", "--execute"):
            self.assertNotIn(forbidden, text)
        self.assertIn("env -i PATH=/usr/bin:/bin", text)
        self.assertIn("python3 -B", text)


if __name__ == "__main__":
    unittest.main()
