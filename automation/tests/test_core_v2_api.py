import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_preflight as preflight
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

    def test_calibration_manifest_has_registered_window_counts(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            rows = runner.read_csv(fixture.manifest)
            self.assertEqual(len(rows), 1120)
            self.assertTrue(all(r["scientific_class"] == "confirmatory_primary" for r in rows))
            self.assertTrue(all(r["observation_surface"] == "provider_api" for r in rows))
            self.assertTrue(all(r["environment_class"] == "CLOSED" for r in rows))
            self.assertEqual(runner.validate_manifest(
                rows, protocol_path=fixture.protocol, freeze_path=fixture.freeze,
            ), [])
            for sid in {r["service_lineage_id"] for r in rows}:
                subset = [r for r in rows if r["service_lineage_id"] == sid]
                self.assertEqual(len(subset), 280)
            self.assertEqual(sum(r["window_id"] == "WA" for r in rows), 160)
            self.assertEqual(sum(r["window_id"] == "WB" for r in rows), 160)
            self.assertEqual(sum(r["window_id"] == "STD" for r in rows), 800)

    def test_non_calibration_manifest_is_960_rows(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            freeze = json.loads(fixture.freeze.read_text(encoding="utf-8"))
            freeze["wave_id"] = "MIBO2-W02"
            freeze_path = Path(d) / "freeze-w02.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
            rows = runner.generate_manifest(
                protocol_path=fixture.protocol, freeze_path=freeze_path,
                wave_id="MIBO2-W02", site_id="JP01",
            )
            self.assertEqual(len(rows), 960)
            self.assertTrue(all(r["window_id"] == "STD" for r in rows))

    def test_protocol_registers_twelve_waves_and_four_calibration_waves(self):
        protocol = json.loads((CONFIG / "core_v2_protocol.draft.json").read_text(encoding="utf-8"))
        self.assertEqual(len(protocol["waves"]), 12)
        self.assertEqual(
            [w["wave_id"] for w in protocol["waves"] if w["calibration_wave"]],
            ["MIBO2-W01", "MIBO2-W04", "MIBO2-W07", "MIBO2-W10"],
        )

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


class CoreV2ReadinessTests(unittest.TestCase):
    @mock.patch.object(preflight, "call_provider")
    @mock.patch.object(preflight.api, "fetch_exact_model")
    @mock.patch.object(preflight.api, "fetch_catalog")
    def test_perplexity_sonar_can_be_verified_by_exact_smoke_return_model(
            self, fetch_catalog, fetch_exact_model, call_provider):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture = CoreV2Fixture(root)
            freeze = json.loads(fixture.freeze.read_text(encoding="utf-8"))
            freeze["core_api"]["MIBO-SL-004"]["model_id"] = "sonar-pro"
            fixture.freeze.write_text(json.dumps(freeze), encoding="utf-8")

            def catalog_side(provider, timeout_s=30):
                ids = ["perplexity/sonar"] if provider == "Perplexity" else [
                    freeze["core_api"][sid]["model_id"]
                    for sid in freeze["core_api"]
                    if {
                        "MIBO-SL-001": "OpenAI",
                        "MIBO-SL-002": "Anthropic",
                        "MIBO-SL-003": "Google",
                    }.get(sid) == provider
                ]
                return SimpleNamespace(
                    provider=provider,
                    endpoint="https://example.invalid/models",
                    status=200,
                    started_at_utc="2026-09-03T00:00:00Z",
                    completed_at_utc="2026-09-03T00:00:01Z",
                    duration_ms=1000,
                    data={"data": []},
                ), ids

            def exact_side(provider, model_id, timeout_s=30):
                if provider == "Perplexity":
                    return None
                data = {"name": f"models/{model_id}"} if provider == "Google" else {"id": model_id}
                return SimpleNamespace(
                    provider=provider,
                    endpoint="https://example.invalid/model",
                    status=200,
                    started_at_utc="2026-09-03T00:00:00Z",
                    completed_at_utc="2026-09-03T00:00:01Z",
                    duration_ms=1000,
                    data=data,
                )

            def call_side(*, provider, model_id, prompt, profile, timeout_s):
                return SimpleNamespace(
                    returned_model=model_id,
                    http_status=200,
                    started_at_utc="2026-09-03T00:00:00Z",
                    completed_at_utc="2026-09-03T00:00:01Z",
                    duration_ms=1000,
                    usage={},
                    request_payload={"model": model_id},
                    response_json={"model": model_id},
                )

            fetch_catalog.side_effect = catalog_side
            fetch_exact_model.side_effect = exact_side
            call_provider.side_effect = call_side
            with mock.patch.dict(os.environ, {
                "MIBO_CORE_V2_SMOKE_TEST": "ENABLED_AFTER_TERMS_REVIEW",
            }, clear=True):
                result = preflight.run_preflight(
                    protocol_path=fixture.protocol,
                    freeze_path=fixture.freeze,
                    out_dir=root / "evidence",
                    smoke=True,
                )
            self.assertTrue(result["pass"])
            perplexity = next(
                c for c in result["model_checks"]
                if c["provider"] == "Perplexity AI"
            )
            self.assertFalse(perplexity["listed_in_catalog_response"])
            self.assertTrue(perplexity["exact_metadata_verified"])
            self.assertEqual(
                perplexity["verification_method"],
                "synthetic_smoke_returned_model",
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
            self.assertEqual(len(rows), 1120)
            self.assertTrue(auth["authorize_confirmatory_api_core"])
            self.assertEqual(len(freeze["core_api"]), 4)
            self.assertEqual(start, datetime(2026, 10, 6, 0, 0, tzinfo=timezone.utc))
            self.assertEqual(close, datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc))

    def test_calibration_row_bounds_use_registered_windows(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            protocol, _ = runner.load_protocol(fixture.protocol)
            rows = runner.read_csv(fixture.manifest)
            wa = next(r for r in rows if r["window_id"] == "WA")
            wb = next(r for r in rows if r["window_id"] == "WB")
            self.assertEqual(
                executor._row_bounds(protocol, wa),
                (datetime(2026, 10, 6, 0, 0, tzinfo=timezone.utc),
                 datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)),
            )
            self.assertEqual(
                executor._row_bounds(protocol, wb),
                (datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc),
                 datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)),
            )

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
