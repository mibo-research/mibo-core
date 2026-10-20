"""Full-size W02 rehearsal with injected transport/clock, never live APIs."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_executor as executor
import core_v2_runner as runner
import core_v2_status as status
from test_core_agent_amendment import AgentFixture


class W02RehearsalTests(unittest.TestCase):
    def test960_cells_exact_payload_identity_and_restart_without_redispatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture = AgentFixture(root)
            freeze = json.loads(fixture.freeze.read_text())
            freeze["wave_id"] = "MIBO2-W02"
            fixture.freeze.write_text(json.dumps(freeze))
            fixture.manifest.unlink()
            rows = runner.generate_manifest(protocol_path=fixture.protocol, freeze_path=fixture.freeze,
                                            wave_id="MIBO2-W02", site_id="JP01")
            runner.write_csv(rows, fixture.manifest)
            auth = json.loads(fixture.authorization.read_text())
            auth.update(wave_id="MIBO2-W02", manifest_sha256=runner.sha256_file(fixture.manifest),
                        provider_freeze_sha256=runner.sha256_file(fixture.freeze))
            fixture.authorization.write_text(json.dumps(auth))
            env = {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}
            env.update({cfg["request_profile"]["api_key_env"]: "synthetic-only"
                        for cfg in freeze["core_api"].values()})
            clock_time = datetime(2026, 11, 3, tzinfo=timezone.utc)
            calls = []

            def transport(**kwargs):
                calls.append(kwargs)
                # A valid refusal is an observation; answer text cannot cause
                # retries, model replacement or another registered prompt.
                return SimpleNamespace(request_payload={"prompt": kwargs["prompt"]},
                    response_json={"text": "synthetic refusal"}, raw_response_text="synthetic refusal",
                    http_status=200, returned_model=kwargs["model_id"], usage={},
                    started_at_utc=clock_time.isoformat(), completed_at_utc=clock_time.isoformat(),
                    duration_ms=0, response_metadata=None)

            arguments = dict(protocol_path=fixture.protocol, manifest_path=fixture.manifest,
                freeze_path=fixture.freeze, authorization_path=fixture.authorization, data_root=root / "data")
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(executor, "datetime", wraps=datetime) as clock, \
                    mock.patch.object(executor, "call_provider", side_effect=transport), \
                    mock.patch.object(executor.time, "sleep") as sleep:
                clock.now.return_value = clock_time
                first = executor.execute(**arguments)
                second = executor.execute(**arguments)
            self.assertEqual(first["valid"], 960)
            self.assertEqual(first["retries_scheduled"], 0)
            self.assertEqual(second["valid"], 0)
            self.assertEqual(second["already_processed"], 960)
            self.assertEqual(len(calls), 960)
            self.assertEqual(freeze["core_api"]["MIBO-SL-004"]["request_profile"]["adapter"], "perplexity_agent")
            sleep.assert_not_called()
            self.assertEqual(Counter(c["provider"] for c in calls),
                             {"OpenAI": 240, "Anthropic": 240, "Google": 240, "Perplexity AI": 240})
            prompts = executor._prompt_map()
            for call, row in zip(calls, rows):
                self.assertEqual(call["prompt"], prompts[row["query_form_id"]])
                self.assertEqual(call["model_id"], freeze["core_api"][row["service_lineage_id"]]["model_id"])
                self.assertEqual(call["profile"], freeze["core_api"][row["service_lineage_id"]]["request_profile"])
            report = status.build_report(**{k: v for k, v in arguments.items() if k != "authorization_path"},
                authorization_path=fixture.authorization, current=datetime(2026, 11, 5, tzinfo=timezone.utc),
                expected_wave="MIBO2-W02")
            self.assertEqual(report["status"], "COMPLETE")
            self.assertEqual(report["captured_cells"], 960)
            self.assertEqual(len(report["dimension_counts"]), 96)
            self.assertTrue(all(n["count"] == 10 and n["window_id"] == "STD"
                                for n in report["dimension_counts"]))
            self.assertFalse(report["independent_backup_verified"])


if __name__ == "__main__":
    unittest.main()
