import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_runner as runner
import provider_adapters as adapters
from test_core_v2_api import CoreV2Fixture


class AgentTransportTests(unittest.TestCase):
    def setUp(self):
        self.model = "perplexity/synthetic-version-1"
        self.profile = {
            "adapter": "perplexity_agent", "disable_search": True,
            "api_key_env": "PERPLEXITY_API_KEY", "max_output_tokens": 512,
            "temperature": None, "top_p": None, "reasoning": None,
        }
        self.response = {
            "model": self.model, "status": "completed", "store": False,
            "tools": [], "previous_response_id": None,
            "output": [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "synthetic acknowledgement"},
            ]}],
            "usage": {"input_tokens": 3, "output_tokens": 4,
                      "tool_calls_details": {}, "cost": {"tool_calls_cost": 0}},
        }

    def call_with_response(self, response):
        raw = json.dumps(response)
        with mock.patch.dict(os.environ, {"PERPLEXITY_API_KEY": "synthetic-key"}, clear=True):
            with mock.patch.object(adapters, "_post_json", return_value=(
                200, raw, response, 10, "2026-10-05T00:00:00Z", "2026-10-05T00:00:01Z",
            )) as post:
                result = adapters.call_provider(
                    provider="Perplexity AI", model_id=self.model,
                    prompt="Synthetic readiness prompt", profile=self.profile,
                )
        return result, post

    def test_closed_request_and_typed_capture(self):
        result, post = self.call_with_response(self.response)
        payload = post.call_args.kwargs["payload"]
        self.assertEqual(post.call_args.kwargs["url"], "https://api.perplexity.ai/v1/agent")
        self.assertEqual(payload["input"], [{"role": "user", "content": "Synthetic readiness prompt"}])
        self.assertEqual(payload["model"], self.model)
        self.assertEqual(payload["max_output_tokens"], 512)
        self.assertEqual(payload["tool_choice"], "none")
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["background"])
        self.assertFalse(payload["store"])
        self.assertEqual(payload["max_steps"], 1)
        for key in ("tools", "models", "preset", "profile", "instructions",
                    "previous_response_id", "messages", "web_search_options"):
            self.assertNotIn(key, payload)
        self.assertEqual(result.output_text, "synthetic acknowledgement")
        self.assertEqual(result.response_json, self.response)
        self.assertEqual(result.raw_response_text, json.dumps(self.response))
        self.assertEqual(result.returned_model, self.model)
        self.assertNotIn("synthetic-key", json.dumps(result.request_payload))

    def test_forbidden_profile_routes_fail_before_network(self):
        for field in ("tools", "models", "preset", "profile", "instructions",
                      "previous_response_id", "skills", "language_preference"):
            with self.subTest(field=field):
                cfg = {**self.profile, field: None}
                with mock.patch.object(adapters, "_post_json") as post:
                    with self.assertRaises(ValueError):
                        adapters.call_perplexity_agent(model_id=self.model, prompt="synthetic", profile=cfg)
                post.assert_not_called()

    def test_invalid_search_model_limit_or_endpoint_fail_before_network(self):
        cases = [
            (self.model, {**self.profile, "disable_search": False}),
            ("openai/synthetic-model", self.profile),
            (self.model, {**self.profile, "max_output_tokens": True}),
            (self.model, {**self.profile, "max_output_tokens": 0}),
            (self.model, {**self.profile, "endpoint": "https://example.invalid/agent"}),
        ]
        for model, cfg in cases:
            with self.subTest(model=model, profile=cfg):
                with mock.patch.object(adapters, "_post_json") as post:
                    with self.assertRaises(ValueError):
                        adapters.call_perplexity_agent(model_id=model, prompt="synthetic", profile=cfg)
                post.assert_not_called()

    def test_environment_mismatch_preserves_capture_without_retry(self):
        changes = [
            {"model": "perplexity/another-synthetic-model"},
            {"tools": [{"type": "web_search"}]},
            {"store": True}, {"previous_response_id": "synthetic-prior-id"},
            {"output": [{"type": "search_results", "results": []}]},
            {"usage": {"tool_calls_details": {"web_search": 1}}},
            {"usage": {"cost": {"tool_calls_cost": 0.01}}},
        ]
        for change in changes:
            data = {**copy.deepcopy(self.response), **change}
            with self.subTest(change=change):
                with self.assertRaises(adapters.AdapterFailure) as caught:
                    self.call_with_response(data)
                self.assertEqual(caught.exception.kind, "request_environment_mismatch")
                self.assertFalse(caught.exception.retry_eligible)
                self.assertEqual(json.loads(caught.exception.response_body), data)

    def test_incomplete_response_is_not_success(self):
        with self.assertRaises(adapters.AdapterFailure) as caught:
            self.call_with_response({**self.response, "status": "incomplete"})
        self.assertEqual(caught.exception.kind, "incomplete_generation")

    def test_provider_error_is_retained(self):
        data = {"error": {"message": "synthetic provider failure"}}
        with self.assertRaises(adapters.AdapterFailure) as caught:
            self.call_with_response(data)
        self.assertEqual(caught.exception.kind, "provider_error")
        self.assertEqual(json.loads(caught.exception.response_body), data)

    def test_registered_core_v2_still_rejects_agent_admission(self):
        with tempfile.TemporaryDirectory() as d:
            fixture = CoreV2Fixture(Path(d))
            freeze = json.loads(fixture.freeze.read_text())
            freeze["core_api"]["MIBO-SL-004"]["request_profile"]["adapter"] = "perplexity_agent"
            fixture.freeze.write_text(json.dumps(freeze))
            protocol, _ = runner.load_protocol(fixture.protocol)
            with self.assertRaisesRegex(ValueError, "adapter mismatch"):
                runner.load_freeze(fixture.freeze, protocol=protocol, wave_id="MIBO2-W01", site_id="JP01")


if __name__ == "__main__":
    unittest.main()
