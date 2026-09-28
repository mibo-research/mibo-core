"""Synthetic-only checks for the proposed 1 October v2.1 executor."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import core_v21_archive as archive
import core_v21_executor as executor
import core_v21_runner as runner
import core_v2_runner as prior_runner

CONFIG = HERE / "config"
SYNTHETIC_DOI = "10.5281/zenodo.99999999"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V21Fixture:
    def __init__(self, root: Path):
        self.root = root
        p = json.loads((CONFIG / "core_v21_protocol.draft.json").read_text())
        p["protocol_status"] = "finalized_and_prospectively_registered"
        p["protocol_registration_id"] = SYNTHETIC_DOI
        self.protocol = root / "protocol.json"
        self.protocol.write_text(json.dumps(p))
        f = json.loads((CONFIG / "core_v21_provider_freeze.example.json").read_text())
        f["protocol_registration_id"] = SYNTHETIC_DOI
        f["frozen_at_utc"] = "2026-09-30T00:00:00Z"
        for sid, cfg in f["core_api"].items():
            cfg.update({
                "status": "eligible", "model_id": f"synthetic-locked-{sid}",
                "model_version_locked": True, "selection_rationale": "synthetic",
                "provider_evidence": "synthetic", "verified_at_utc": "2026-09-30T00:00:00Z",
                "terms_review_date": "2026-09-30", "terms_review_source": "synthetic",
            })
            cfg["request_profile"]["max_output_tokens"] = 512
        self.freeze = root / "freeze.json"
        self.freeze.write_text(json.dumps(f))
        self.manifest = root / "manifest.csv"
        runner.write_csv(runner.generate_manifest(
            protocol_path=self.protocol, freeze_path=self.freeze,
            wave_id="MIBO2-W01", site_id="JP01",
        ), self.manifest)
        a = {
            "schema_version": "2.1", "protocol_version": "2.1",
            "protocol_registration_id": SYNTHETIC_DOI,
            "wave_id": "MIBO2-W01", "site_id": "JP01",
            "authorized": True, "authorized_at_utc": "2026-09-30T12:00:00Z",
            "operations_lead": "synthetic-lead", "protocol_finalized": True,
            "prospective_registration_complete": True, "terms_review_complete": True,
            "model_freeze_complete": True, "synthetic_dry_run_complete": True,
            "authorize_confirmatory_api_core": True,
            "protocol_file_sha256": digest(self.protocol),
            "manifest_sha256": digest(self.manifest),
            "provider_freeze_sha256": digest(self.freeze),
        }
        self.authorization = root / "authorization.json"
        self.authorization.write_text(json.dumps(a))


class CoreV21Tests(unittest.TestCase):
    def test_draft_and_prior_version_are_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "not finalized"):
            runner.load_protocol(CONFIG / "core_v21_protocol.draft.json")
        with self.assertRaisesRegex(ValueError, "schema_version mismatch"):
            runner.load_protocol(CONFIG / "core_v2_protocol.v2.0.json")
        with tempfile.TemporaryDirectory() as d:
            p = json.loads((CONFIG / "core_v21_protocol.draft.json").read_text())
            p["protocol_status"] = "finalized_and_prospectively_registered"
            p["protocol_registration_id"] = "10.5281/zenodo.22264635"
            path = Path(d) / "reused-doi.json"
            path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError, "registration ID is not finalized"):
                runner.load_protocol(path)

    def test_w01_exact_1120_rows_and_strict_identity(self):
        with tempfile.TemporaryDirectory() as d:
            f = V21Fixture(Path(d))
            rows = runner.read_csv(f.manifest)
            self.assertEqual(len(rows), 1120)
            self.assertEqual(len({r["attempt_id"] for r in rows}), 1120)
            self.assertEqual({w: sum(r["window_id"] == w for r in rows)
                              for w in ("WA", "STD", "WB")},
                             {"WA": 160, "STD": 800, "WB": 160})
            self.assertEqual(runner.validate_manifest(
                rows, protocol_path=f.protocol, freeze_path=f.freeze), [])
            self.assertEqual({r["protocol_version"] for r in rows}, {"2.1"})
            self.assertEqual({r["protocol_registration_id"] for r in rows}, {SYNTHETIC_DOI})
            self.assertTrue(all(r["provider_freeze_sha256"] == digest(f.freeze) for r in rows))
            self.assertTrue(prior_runner.validate_manifest(
                rows, protocol_path=f.protocol, freeze_path=f.freeze))

    def test_execution_gate_uses_new_window_and_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = V21Fixture(root)
            args = dict(protocol_path=f.protocol, manifest_path=f.manifest,
                        freeze_path=f.freeze, authorization_path=f.authorization,
                        data_root=root / "data")
            with self.assertRaisesRegex(ValueError, "outside"):
                executor.preflight(**args, now=datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc))
            rows, _, _, start, close = executor.preflight(
                **args, now=datetime(2026, 10, 1, 0, 1, tzinfo=timezone.utc))
            self.assertEqual(len(rows), 1120)
            self.assertEqual(start.isoformat(), "2026-10-01T00:00:00+00:00")
            self.assertEqual(close.isoformat(), "2026-10-03T00:00:00+00:00")
            self.assertEqual(archive.wave_root(root / "data", "JP01", "MIBO2-W01"),
                             root / "data/v2.1/JP01/MIBO2-W01")
            self.assertNotEqual(executor.EXECUTION_SENTINEL, "ENABLED_AFTER_CORE_V2_GATE")

    def test_late_freeze_and_authorization_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = V21Fixture(root)
            frozen = json.loads(f.freeze.read_text())
            frozen["frozen_at_utc"] = "2026-10-01T00:01:00Z"
            f.freeze.write_text(json.dumps(frozen))
            p, _ = runner.load_protocol(f.protocol)
            with self.assertRaisesRegex(ValueError, "must precede"):
                runner.load_freeze(f.freeze, protocol=p, wave_id="MIBO2-W01", site_id="JP01")
            frozen["frozen_at_utc"] = "2026-09-30T00:00:00Z"
            f.freeze.write_text(json.dumps(frozen))
            auth = json.loads(f.authorization.read_text())
            auth["authorized_at_utc"] = "2026-10-01T00:01:00Z"
            f.authorization.write_text(json.dumps(auth))
            with self.assertRaisesRegex(ValueError, "must precede"):
                executor.load_authorization(
                    f.authorization, protocol_path=f.protocol, manifest_path=f.manifest,
                    freeze_path=f.freeze, protocol=p, wave_id="MIBO2-W01", site_id="JP01")


if __name__ == "__main__":
    unittest.main()
