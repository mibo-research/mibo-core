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

import provider_adapters as pa
import shadow_archive as sa
import shadow_bundle as sb
import shadow_executor as se
import shadow_freeze as sf
import shadow_runner as sr

FREEZE = Path(__file__).with_name("api_shadow_freeze.synthetic.json")


class ShadowManifestTests(unittest.TestCase):
    def test_four_lineage_manifest_is_960_and_exploratory_only(self):
        rows = sr.generate_shadow_manifest("MIBO-W01", FREEZE, "JP01")
        self.assertEqual(len(rows), 960)
        self.assertTrue(all(r["line_id"] == "ASH" for r in rows))
        self.assertTrue(all(r["archive_class"] == "exploratory_auxiliary" for r in rows))
        self.assertTrue(all(r["confirmatory_use"] == "prohibited" for r in rows))
        self.assertTrue(all(r["environment_class"] == "CLOSED" for r in rows))
        self.assertEqual(sr.validate_shadow_manifest(rows, FREEZE), [])
        for sid in {r["service_lineage_id"] for r in rows}:
            subset = [r for r in rows if r["service_lineage_id"] == sid]
            self.assertEqual(len(subset), 240)
            for qid in {r["query_form_id"] for r in subset}:
                self.assertEqual(sum(r["query_form_id"] == qid for r in subset), 10)

    def test_manifest_is_deterministic_and_mutations_are_detected(self):
        a = sr.generate_shadow_manifest("MIBO-W01", FREEZE, "JP01")
        b = sr.generate_shadow_manifest("MIBO-W01", FREEZE, "JP01")
        self.assertEqual(a, b)
        mutated = copy.deepcopy(a)
        mutated[0]["random_seed"] += 1
        mutated[1]["model_id"] = "forged"
        mutated[2]["attempt_id"] = mutated[2]["attempt_id"].replace("-A01", "-A02")
        errors = sr.validate_shadow_manifest(mutated, FREEZE)
        self.assertTrue(any("random seed" in e for e in errors))
        self.assertTrue(any("model ID" in e for e in errors))
        self.assertTrue(any("attempt ID" in e for e in errors))

    def test_final_freeze_rejects_pending_or_search_enabled_perplexity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = json.loads(FREEZE.read_text(encoding="utf-8"))
            data["shadow_api"]["MIBO-SL-001"]["status"] = "pending"
            p = root / "pending.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "eligible or ineligible"):
                sr.load_shadow_freeze(p, "MIBO-W01", "JP01")

            data = json.loads(FREEZE.read_text(encoding="utf-8"))
            data["shadow_api"]["MIBO-SL-004"]["request_profile"]["disable_search"] = False
            p = root / "search-on.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "disable_search"):
                sr.load_shadow_freeze(p, "MIBO-W01", "JP01")


class PerplexityAdapterTests(unittest.TestCase):
    @mock.patch.object(pa, "_post_json")
    @mock.patch.dict(os.environ, {"PERPLEXITY_API_KEY": "secret"})
    def test_closed_sonar_payload_disables_search(self, post):
        response = {
            "model": "sonar",
            "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "citations": [],
            "search_results": [],
        }
        post.return_value = (200, json.dumps(response), response, 10, "s", "e")
        result = pa.call_perplexity(
            model_id="sonar", prompt="hello",
            profile={
                "adapter": "perplexity_sonar",
                "api_key_env": "PERPLEXITY_API_KEY",
                "disable_search": True,
                "max_output_tokens": 128,
            },
        )
        self.assertEqual(result.output_text, "ok")
        self.assertTrue(result.request_payload["web_search_options"]["disable_search"])
        self.assertNotIn("tools", result.request_payload)
        self.assertEqual(result.request_payload["messages"], [{"role": "user", "content": "hello"}])


class ShadowAuthorizationAndBundleTests(unittest.TestCase):
    def _manifest_and_auth(self, root: Path):
        rows = sr.generate_shadow_manifest("MIBO-W01", FREEZE, "JP01")
        manifest = root / "shadow.csv"
        sr.write_csv(rows, manifest)
        auth = {
            "schema_version": "0.1",
            "archive_class": "exploratory_auxiliary",
            "confirmatory_use": "prohibited",
            "protocol_doi": "10.5281/zenodo.21936410",
            "wave_id": "MIBO-W01",
            "site_id": "JP01",
            "authorized": True,
            "authorized_at_utc": "2026-08-31T12:00:00Z",
            "operations_lead": "synthetic-lead",
            "terms_review_complete": True,
            "institutional_process_checked": True,
            "dry_run_complete": True,
            "acknowledge_exploratory_only": True,
            "manifest_sha256": se.sha256_file(manifest),
            "shadow_freeze_sha256": se.sha256_file(FREEZE),
        }
        auth_path = root / "auth.json"
        auth_path.write_text(json.dumps(auth), encoding="utf-8")
        return rows, manifest, auth_path

    def test_executor_preflight_binds_manifest_freeze_and_field_window(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rows, manifest, auth = self._manifest_and_auth(root)
            loaded, freeze, authorization, start, close = se.preflight(
                manifest_path=manifest, freeze_path=FREEZE, authorization_path=auth,
                data_root=root / "data", now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc),
                require_credentials=False,
            )
            self.assertEqual(len(loaded), 960)
            self.assertTrue(authorization["acknowledge_exploratory_only"])
            self.assertEqual(freeze["archive_class"], "exploratory_auxiliary")
            self.assertEqual(start, datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))
            self.assertEqual(close, datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc))

    def test_bundle_never_authorizes_shadow(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = {
                "archive_class": "exploratory_auxiliary",
                "confirmatory_use": "prohibited",
                "wave_id": "MIBO-W01",
                "site_id": "JP01",
                "shadow_freeze_sha256": sb.sha256_file(FREEZE),
                "pass": True,
            }
            preflight = root / "preflight.json"
            preflight.write_text(json.dumps(report), encoding="utf-8")
            out = root / "bundle"
            result = sb.build_bundle(
                wave_id="MIBO-W01", site_id="JP01", freeze_path=FREEZE,
                preflight_report_path=preflight, out_dir=out,
            )
            self.assertEqual(result["initial_request_count"], 960)
            auth = json.loads((out / "execution_authorization.SHADOW.template.json").read_text(encoding="utf-8"))
            self.assertFalse(auth["authorized"])
            self.assertFalse(auth["acknowledge_exploratory_only"])
            self.assertEqual(auth["confirmatory_use"], "prohibited")


class ShadowArchiveFreezeTests(unittest.TestCase):
    def test_archive_namespace_is_separate_from_core(self):
        root = sa.shadow_wave_root(Path("/tmp/mibo"), "JP01", "MIBO-W01")
        self.assertIn("auxiliary/api-shadow-v0.1", root.as_posix())
        self.assertNotIn("/v1.0/JP01/MIBO-W01", root.as_posix())

    def test_wave_freeze_is_after_close_and_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "shadow.csv"
            sr.write_csv(sr.generate_shadow_manifest("MIBO-W01", FREEZE, "JP01"), manifest)
            with self.assertRaisesRegex(ValueError, "before the registered field closes"):
                sf.freeze_wave(
                    data_root=root / "data", manifest_path=manifest, freeze_path=FREEZE,
                    now=datetime(2026, 9, 2, 23, 59, tzinfo=timezone.utc),
                )
            record = sf.freeze_wave(
                data_root=root / "data", manifest_path=manifest, freeze_path=FREEZE,
                now=datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(record["archive_class"], "exploratory_auxiliary")
            self.assertEqual(record["valid_initial_observations"], 0)
            self.assertEqual(record["missing_initial_observations"], 960)
            with self.assertRaises(FileExistsError):
                sf.freeze_wave(
                    data_root=root / "data", manifest_path=manifest, freeze_path=FREEZE,
                    now=datetime(2026, 9, 3, 0, 1, tzinfo=timezone.utc),
                )


if __name__ == "__main__":
    unittest.main()
