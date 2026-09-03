import copy
from datetime import datetime, timezone
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

import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_runner as runner

RUNTIME = HERE.parent / "runtime"

CONFIG = HERE / "config"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CoreV2Fixture:
    def __init__(self, root: Path):
        self.root = root
        protocol = json.loads((CONFIG / "core_v2_protocol.draft.json").read_text(encoding="utf-8"))
        protocol["protocol_status"] = "finalized_and_prospectively_registered"
        protocol["protocol_registration_id"] = "synthetic-registration"
        self.protocol = root / "protocol.json"
        self.protocol.write_text(json.dumps(protocol), encoding="utf-8")

        freeze = json.loads((CONFIG / "core_v2_provider_freeze.example.json").read_text(encoding="utf-8"))
        freeze["protocol_registration_id"] = "synthetic-registration"
        freeze["frozen_at_utc"] = "2026-10-05T00:00:00Z"
        for sid, cfg in freeze["core_api"].items():
            cfg.update({
                "status": "eligible",
                "model_id": f"synthetic-version-locked-{sid}",
                "model_version_locked": True,
                "selection_rationale": "synthetic prospective selection",
                "provider_evidence": "synthetic official model evidence",
                "verified_at_utc": "2026-10-05T00:00:00Z",
                "terms_review_date": "2026-10-05",
                "terms_review_source": "synthetic official terms evidence",
            })
            cfg["request_profile"]["max_output_tokens"] = 512
        self.freeze = root / "freeze.json"
        self.freeze.write_text(json.dumps(freeze), encoding="utf-8")

        rows = runner.generate_manifest(
            protocol_path=self.protocol, freeze_path=self.freeze,
            wave_id="MIBO2-W01", site_id="JP01",
        )
        self.manifest = root / "manifest.csv"
        runner.write_csv(rows, self.manifest)
        auth = {
            "schema_version": "2.0", "protocol_version": "2.0",
            "protocol_registration_id": "synthetic-registration",
            "wave_id": "MIBO2-W01", "site_id": "JP01",
            "authorized": True, "authorized_at_utc": "2026-10-05T12:00:00Z",
            "operations_lead": "synthetic-lead", "protocol_finalized": True,
            "prospective_registration_complete": True, "terms_review_complete": True,
            "model_freeze_complete": True, "synthetic_dry_run_complete": True,
            "authorize_confirmatory_api_core": True,
            "protocol_file_sha256": sha256_file(self.protocol),
            "manifest_sha256": sha256_file(self.manifest),
            "provider_freeze_sha256": sha256_file(self.freeze),
        }
        self.authorization = root / "authorization.json"
        self.authorization.write_text(json.dumps(auth), encoding="utf-8")


class CoreV2ManifestTests(unittest.TestCase):
    def test_draft_protocol_is_not_runnable(self):
        with self.assertRaisesRegex(ValueError, "not finalized"):
            runner.load_protocol(CONFIG / "core_v2_protocol.draft.json")

    def test_four_lineage_manifest_is_960_confirmatory_api_rows(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            rows = runner.read_csv(fixture.manifest)
            self.assertEqual(len(rows), 960)
            self.assertTrue(all(r["scientific_class"] == "confirmatory_primary" for r in rows))
            self.assertTrue(all(r["observation_surface"] == "provider_api" for r in rows))
            self.assertTrue(all(r["environment_class"] == "CLOSED" for r in rows))
            self.assertEqual(runner.validate_manifest(
                rows, protocol_path=fixture.protocol, freeze_path=fixture.freeze,
            ), [])
            for sid in {r["service_lineage_id"] for r in rows}:
                subset = [r for r in rows if r["service_lineage_id"] == sid]
                self.assertEqual(len(subset), 240)

    def test_manifest_is_deterministic_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            a = runner.read_csv(fixture.manifest)
            b = runner.generate_manifest(
                protocol_path=fixture.protocol, freeze_path=fixture.freeze,
                wave_id="MIBO2-W01", site_id="JP01",
            )
            self.assertEqual(a, b)
            bad = copy.deepcopy(a)
            bad[0]["model_id"] = "forged"
            bad[1]["random_seed"] += 1
            errors = runner.validate_manifest(
                bad, protocol_path=fixture.protocol, freeze_path=fixture.freeze,
            )
            self.assertTrue(any("model ID" in e for e in errors))
            self.assertTrue(any("random seed" in e for e in errors))

    def test_perplexity_search_must_remain_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            data = json.loads(fixture.freeze.read_text(encoding="utf-8"))
            data["core_api"]["MIBO-SL-004"]["request_profile"]["disable_search"] = False
            bad = Path(d) / "bad-freeze.json"
            bad.write_text(json.dumps(data), encoding="utf-8")
            protocol, _ = runner.load_protocol(fixture.protocol)
            with self.assertRaisesRegex(ValueError, "disable_search"):
                runner.load_freeze(
                    bad, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01",
                )


class CoreV2ExecutionGateTests(unittest.TestCase):
    def test_preflight_binds_all_files_and_registered_window(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture = CoreV2Fixture(root)
            rows, freeze, auth, start, close = executor.preflight(
                protocol_path=fixture.protocol, manifest_path=fixture.manifest,
                freeze_path=fixture.freeze, authorization_path=fixture.authorization,
                data_root=root / "data",
                now=datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(len(rows), 960)
            self.assertTrue(auth["authorize_confirmatory_api_core"])
            self.assertEqual(len(freeze["core_api"]), 4)
            self.assertEqual(start, datetime(2026, 10, 6, 0, 0, tzinfo=timezone.utc))
            self.assertEqual(close, datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc))

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_execute_requires_separate_core_v2_sentinel_before_any_call(self):
        with mock.patch.object(executor, "call_provider") as call:
            with self.assertRaisesRegex(RuntimeError, "sentinel"):
                executor.execute(
                    protocol_path=Path("unused"), manifest_path=Path("unused"),
                    freeze_path=Path("unused"), authorization_path=Path("unused"),
                    data_root=Path("unused"),
                )
            call.assert_not_called()

    def test_authorization_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture = CoreV2Fixture(root)
            auth = json.loads(fixture.authorization.read_text(encoding="utf-8"))
            auth["manifest_sha256"] = "0" * 64
            fixture.authorization.write_text(json.dumps(auth), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest_sha256 mismatch"):
                executor.preflight(
                    protocol_path=fixture.protocol, manifest_path=fixture.manifest,
                    freeze_path=fixture.freeze, authorization_path=fixture.authorization,
                    data_root=root / "data",
                    now=datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc),
                )


class CoreV2ArchiveTests(unittest.TestCase):
    def test_archive_uses_v2_core_namespace_and_exclusive_create(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture = CoreV2Fixture(root)
            row = runner.read_csv(fixture.manifest)[0]
            path = archive.wave_root(root / "data", "JP01", "MIBO2-W01")
            self.assertIn("/v2.0/JP01/MIBO2-W01", path.as_posix())
            self.assertNotIn("/auxiliary/", path.as_posix())
            kwargs = dict(
                data_root=root / "data", row=row,
                request_payload={"model": row["model_id"], "input": "synthetic"},
                response_json={"output": []}, raw_response_text="{}", http_status=200,
                returned_model=row["model_id"], usage={},
                started_at_utc="2026-10-06T00:00:01Z",
                completed_at_utc="2026-10-06T00:00:02Z", duration_ms=1000,
            )
            archive.archive_success(**kwargs)
            with self.assertRaises(FileExistsError):
                archive.archive_success(**kwargs)


class InstalledSnapshotSealTests(unittest.TestCase):
    def test_seal_is_hash_bound_and_append_only(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "seal_installed_snapshot", RUNTIME / "seal-installed-snapshot.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "example.txt").write_text("ok\n", encoding="utf-8")
            result = module.seal(root, "a" * 40)
            self.assertEqual(result["source_commit_sha"], "a" * 40)
            self.assertEqual(result["hashed_file_count"], 2)
            sums = (root / "INSTALL_SHA256SUMS.txt").read_text(encoding="utf-8")
            self.assertIn("example.txt", sums)
            self.assertIn("INSTALL_PROVENANCE.json", sums)
            with self.assertRaises(FileExistsError):
                module.seal(root, "a" * 40)


if __name__ == "__main__":
    unittest.main()
