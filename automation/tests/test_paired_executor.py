import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mibo_runner as core
import paired_executor as pe

FIXTURE = Path(__file__).with_name("provider_freeze.synthetic.json")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PairedExecutorPreflightTests(unittest.TestCase):
    def make_files(self, root: Path, *, mutate_rows=None):
        manifest = root / "paired.csv"
        rows = core.generate_paired_manifest(
            "MIBO-W01", ["MIBO-SL-002", "MIBO-SL-003"], FIXTURE
        )
        if mutate_rows is not None:
            mutate_rows(rows)
        core.write_csv(rows, manifest)
        auth = root / "authorization.json"
        auth.write_text(json.dumps({
            "schema_version": "1.0",
            "protocol_doi": "10.5281/zenodo.21936410",
            "wave_id": "MIBO-W01",
            "site_id": "JP01",
            "authorized": True,
            "authorized_at_utc": "2026-08-31T23:30:00Z",
            "operations_lead": "Synthetic Test Lead",
            "terms_review_complete": True,
            "institutional_process_checked": True,
            "dry_run_complete": True,
            "manifest_sha256": sha256_file(manifest),
            "provider_freeze_sha256": sha256_file(FIXTURE),
        }), encoding="utf-8")
        return manifest, auth

    def test_preflight_passes_only_inside_registered_window(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, auth = self.make_files(root)
            rows, _, start, close = pe.preflight(
                manifest_path=manifest,
                freeze_path=FIXTURE,
                authorization_path=auth,
                data_root=root / "data",
                now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(len(rows), 160)
            self.assertEqual(start, datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))
            self.assertEqual(close, datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc))

    def test_preflight_rejects_wrong_manifest_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, auth = self.make_files(root)
            data = json.loads(auth.read_text(encoding="utf-8"))
            data["manifest_sha256"] = "0" * 64
            auth.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                pe.preflight(
                    manifest_path=manifest,
                    freeze_path=FIXTURE,
                    authorization_path=auth,
                    data_root=root / "data",
                    now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                )

    def test_preflight_rejects_model_id_not_bound_to_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, auth = self.make_files(
                root, mutate_rows=lambda rows: rows[0].__setitem__("model_id", "forged-model-id")
            )
            with self.assertRaisesRegex(ValueError, "model_id does not match provider freeze"):
                pe.preflight(
                    manifest_path=manifest,
                    freeze_path=FIXTURE,
                    authorization_path=auth,
                    data_root=root / "data",
                    now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                )

    def test_execution_preflight_requires_private_provider_credentials(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(d)
            manifest, auth = self.make_files(root)
            with self.assertRaisesRegex(ValueError, "required credential environment variable"):
                pe.preflight(
                    manifest_path=manifest,
                    freeze_path=FIXTURE,
                    authorization_path=auth,
                    data_root=root / "data",
                    now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                    require_credentials=True,
                )

    def test_execute_requires_explicit_runtime_sentinel_before_any_call(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                pe.execute(
                    manifest_path=Path("does-not-matter"),
                    freeze_path=Path("does-not-matter"),
                    authorization_path=Path("does-not-matter"),
                    data_root=Path("does-not-matter"),
                )


if __name__ == "__main__":
    unittest.main()
