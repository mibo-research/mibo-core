import csv
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("close", Path(__file__).resolve().parents[2] / "runtime/close-core-v2-w01.py")
close = importlib.util.module_from_spec(spec)
spec.loader.exec_module(close)

def fixture(base, version, admitted, capture_all=False):
    root = base / "data" / ("v" + version) / "JP01" / close.WAVE
    for folder in ("metadata", "failures", "api_raw", "deviations"):
        (root / folder).mkdir(parents=True)
    inputs = {}
    for name in ("protocol", "freeze"):
        p = base / (name + version + ".json")
        p.write_text(json.dumps({"synthetic": True, "version": version}))
        inputs[name] = p
    hashes = {name: close.sha(p) for name, p in inputs.items()}
    rows = []
    for sid in sorted(admitted):
        for i in range(280):
            rows.append(dict(attempt_id=sid + "-" + str(i), service_lineage_id=sid,
                query_form_id="SYNTHETIC-F" + str(i % 4), language="JA" if i % 2 else "EN",
                window_id="WA" if i < 40 else "STD" if i < 240 else "WB",
                protocol_version=version, protocol_file_sha256=hashes["protocol"],
                provider_freeze_sha256=hashes["freeze"], wave_id=close.WAVE, site_id="JP01", attempt=1))
    manifest = base / ("manifest" + version + ".csv")
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    inputs["manifest"] = manifest
    hashes["manifest"] = close.sha(manifest)
    for row in (rows if capture_all else rows[:3]):
        save_capture(root, row, row["attempt_id"], None)
    if not capture_all:
        for row, n in zip(rows[3:6], (3, 2, 2)):
            parent = None
            for a in range(1, n + 1):
                aid = row["attempt_id"] if a == 1 else row["attempt_id"] + "-R" + str(a)
                save_failure(root, row, aid, parent, a)
                parent = aid
        (root / "deviations" / "SUSPEND.json").write_text(json.dumps({"type": "lineage_suspended_after_retry_exhaustion", "service_lineage_id": rows[0]["service_lineage_id"]}))
    return root, rows, inputs, hashes

def save_capture(root, row, aid, parent):
    raw = root / "api_raw" / (aid + ".json")
    raw.write_text('{"raw_response_text":"SYNTHETIC_PRIVATE_ANSWER"}')
    record = {"attempt_id": aid, "retry_of_attempt_id": parent, "protocol_version": row["protocol_version"], "service_lineage_id": row["service_lineage_id"], "window_id": row["window_id"], "status": "valid_confirmatory_api_capture", "raw_file": str(raw.relative_to(root)), "raw_file_sha256": close.sha(raw)}
    (root / "metadata" / (aid + ".json")).write_text(json.dumps(record))

def save_failure(root, row, aid, parent, attempt):
    record = {"attempt_id": aid, "retry_of_attempt_id": parent, "attempt": attempt, "protocol_version": row["protocol_version"], "service_lineage_id": row["service_lineage_id"], "window_id": row["window_id"], "failure_kind": "provider_error", "http_status": 503, "provider_response_body": "SYNTHETIC_PRIVATE_ERROR"}
    (root / "failures" / (aid + ".json")).write_text(json.dumps(record))

class CloseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.admitted = {"MIBO-SL-003"}
        self.root, self.rows, self.inputs, self.hashes = fixture(self.base, "2.0.4", self.admitted)
    def tearDown(self):
        self.tmp.cleanup()
    def inspect(self):
        return close.inspect(self.root, self.inputs["manifest"], self.admitted, "2.0.4", self.hashes)
    def test_missingness_and_retry_failure_counts(self):
        cells, counts, summary = self.inspect()
        self.assertEqual(summary["Google"], {"planned": 280, "captured": 3, "without_capture": 277})
        self.assertEqual(sum(n for k, n in counts.items() if k[0] == "attempt" and k[-1].startswith("failure:")), 7)
        self.assertEqual(sum(r[-1] == "failed_no_capture" for r in cells), 3)
        self.assertEqual(sum(r[-1] == "missing_after_lineage_suspension" for r in cells), 274)
    def test_retry_success_is_one_planned_cell(self):
        row = self.rows[0]; initial = row["attempt_id"]
        (self.root / "metadata" / (initial + ".json")).unlink()
        (self.root / "api_raw" / (initial + ".json")).unlink()
        save_failure(self.root, row, initial, None, 1)
        save_failure(self.root, row, initial + "-R2", initial, 2)
        save_capture(self.root, row, initial + "-R3", initial + "-R2")
        self.assertEqual(self.inspect()[2]["Google"]["captured"], 3)
    def test_tampered_raw_aborts(self):
        next((self.root / "api_raw").glob("*.json")).write_text("tampered")
        with self.assertRaisesRegex(ValueError, "Capture hash"):
            self.inspect()
        self.assertFalse((self.root / "closure").exists())
    def test_orphan_capture_aborts(self):
        (self.root / "api_raw" / "orphan.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Unlinked"):
            self.inspect()
    def test_symlink_and_path_escape_abort(self):
        (self.root / "api_raw" / "link.json").symlink_to(self.inputs["freeze"])
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.inspect()
    def test_freeze_mismatch_aborts(self):
        self.hashes["freeze"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Frozen manifest"):
            self.inspect()
    def test_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            close.original("a", {"a": "b", "b": "a"}, {})
    def test_full_offline_close_and_archive(self):
        others = set(close.LABELS) - self.admitted
        root2, _, inputs2, _ = fixture(self.base, "2.0.2", others, True)
        units = self.base / "units"; units.mkdir()
        source = self.base / "source"; source.mkdir()
        (source / "INSTALL_PROVENANCE.json").write_text('{"source_commit_sha":"synthetic"}')
        for unit, inputs in (("mibo-core-v2-ready-three.service", inputs2), ("mibo-core-v2-google-standard.service", self.inputs)):
            (units / unit).write_text("ExecStart=/usr/bin/python3 -B " + str(source / "automation/core_v2_waiter.py") + " --data-root " + str(self.base / "data") + " " + " ".join("--" + k + " " + str(v) for k, v in inputs.items()))
        private = self.base / "private"; private.mkdir()
        proc = self.base / "proc"; proc.mkdir()
        native_path = Path
        def routed_path(*parts):
            if parts and str(parts[0]) == "/etc/systemd/system":
                return units.joinpath(*parts[1:])
            if parts and str(parts[0]) == "/srv/mibo-private":
                return private.joinpath(*parts[1:])
            if parts and str(parts[0]) == "/proc":
                return proc.joinpath(*parts[1:])
            return native_path(*parts)
        class TTY(io.StringIO):
            def write(self, s):
                return len(s)
        native_open = open
        def routed_open(file, *args, **kwargs):
            return TTY("Synthetic Operations Lead\n") if file == "/dev/tty" else native_open(file, *args, **kwargs)
        out = io.StringIO()
        state = "ActiveState=inactive\nMainPID=0\nUnitFileState=disabled\nControlGroup=\nResult=success\nInactiveEnterTimestamp=synthetic\n"
        with patch.object(close, "Path", routed_path), patch.object(close.subprocess, "check_output", return_value=state), patch.object(close.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=os.getgid())), patch("builtins.open", side_effect=routed_open), patch.object(close.os, "sync"), redirect_stdout(out):
            close.main()
        self.assertIn("ARCHIVE_CONTENT_VERIFY=PASS", out.getvalue())
        self.assertIn("INDEPENDENT_BACKUP=PENDING", out.getvalue())
        self.assertNotIn("SYNTHETIC_PRIVATE", out.getvalue())
        for root in (root2, self.root):
            self.assertTrue((root / "closure/COMPLETION_RECORD.json").exists())
            self.assertFalse(any(p.stat().st_mode & 0o222 for p in [root] + list(root.rglob("*"))))
        self.assertEqual(len(list(private.glob("*/MIBO2-W01-sealed.tar.gz"))), 1)

if __name__ == "__main__":
    unittest.main()
