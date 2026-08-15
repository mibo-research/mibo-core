from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import api_preflight as ap

FREEZE = Path(__file__).with_name("provider_freeze.synthetic.json")


def http_result(provider: str, data: dict) -> ap.HTTPResult:
    return ap.HTTPResult(
        provider=provider,
        endpoint=f"https://example.invalid/{provider}",
        status=200,
        started_at_utc="2026-08-31T00:00:00Z",
        completed_at_utc="2026-08-31T00:00:01Z",
        duration_ms=1000,
        raw_text="{}",
        data=data,
    )


class APIPreflightTests(unittest.TestCase):
    def test_google_catalog_ids_are_normalized(self):
        ids = ap.catalog_model_ids("Google", {
            "models": [{"name": "models/gemini-a"}, {"name": "models/gemini-b"}]
        })
        self.assertEqual(ids, ["gemini-a", "gemini-b"])

    @mock.patch.object(ap, "fetch_exact_model")
    @mock.patch.object(ap, "fetch_catalog")
    def test_preflight_verifies_frozen_ids_without_selecting_models(self, catalog, exact):
        def catalog_side(provider, timeout_s=30):
            ids = {
                "Anthropic": ["synthetic-live-claude", "synthetic-frozen-claude"],
                "Google": ["synthetic-live-gemini", "synthetic-frozen-gemini"],
            }[provider]
            payload = {"data": [{"id": x} for x in ids]}
            if provider == "Google":
                payload = {"models": [{"name": f"models/{x}"} for x in ids]}
            return http_result(provider, payload), ids

        def exact_side(provider, model_id, timeout_s=30):
            if provider == "Google":
                return http_result(provider, {"name": f"models/{model_id}"})
            return http_result(provider, {"id": model_id})

        catalog.side_effect = catalog_side
        exact.side_effect = exact_side
        with tempfile.TemporaryDirectory() as d:
            result = ap.run_preflight(
                freeze_path=FREEZE,
                out_dir=Path(d) / "api-evidence",
            )
            self.assertTrue(result["pass"])
            self.assertEqual(result["eligible_lineage_count"], 2)
            self.assertEqual(len(result["exact_model_checks"]), 4)
            self.assertFalse(result["automatic_model_selection"])
            self.assertFalse(result["automatic_provider_promotion"])
            self.assertFalse(result["configuration_freeze_modified"])
            self.assertFalse(result["confirmatory_prompts_used"])
            self.assertTrue(Path(result["report_file"]).exists())
            self.assertEqual(len(result["report_sha256"]), 64)

    @mock.patch.object(ap, "fetch_exact_model")
    @mock.patch.object(ap, "fetch_catalog")
    def test_smoke_test_is_fail_closed_without_explicit_sentinel(self, catalog, exact):
        def catalog_side(provider, timeout_s=30):
            ids = {
                "Anthropic": ["synthetic-live-claude", "synthetic-frozen-claude"],
                "Google": ["synthetic-live-gemini", "synthetic-frozen-gemini"],
            }[provider]
            return http_result(provider, {}), ids

        def exact_side(provider, model_id, timeout_s=30):
            if provider == "Google":
                return http_result(provider, {"name": f"models/{model_id}"})
            return http_result(provider, {"id": model_id})

        catalog.side_effect = catalog_side
        exact.side_effect = exact_side
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(ap.APIPreflightFailure, "MIBO_API_SMOKE_TEST"):
                    ap.run_preflight(
                        freeze_path=FREEZE,
                        out_dir=Path(d) / "api-evidence",
                        smoke=True,
                    )

    def test_synthetic_prompt_is_not_a_registered_query(self):
        self.assertIn("non-confirmatory", ap.SYNTHETIC_SMOKE_PROMPT)
        self.assertNotIn("sleep deprivation", ap.SYNTHETIC_SMOKE_PROMPT.lower())
        self.assertNotIn("retrieval-augmented generation", ap.SYNTHETIC_SMOKE_PROMPT.lower())


if __name__ == "__main__":
    unittest.main()
