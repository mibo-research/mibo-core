"""Synthetic private-VM readiness; every subprocess/provider operation is mocked."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import api_preflight as api
import core_v2_preflight as preflight
from provider_adapters import AdapterFailure, AdapterResult

spec = importlib.util.spec_from_file_location("agent_vm_preparation", HERE.parent / "runtime/prepare-core-v2-agent.py")
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc)


class ReadinessTests(unittest.TestCase):
    def test_terminal_requires_explicit_review_word(self):
        freeze = json.loads((HERE / 'config/core_v2_agent_provider_freeze.draft.json').read_text())
        for reply in ('\n\n', 'human\nno\n'):
            with self.assertRaisesRegex(ValueError, 'not completed'):
                vm.attest(io.StringIO(reply), io.StringIO(), freeze)
        self.assertEqual(vm.attest(io.StringIO('synthetic human\nTERMS_AND_PROFILE_REVIEWED\n'),
                                   io.StringIO(), freeze), 'synthetic human')

    def environment(self, root):
        data = root / 'data'
        data.mkdir()
        env = root / 'private.env'
        env.write_text(f'MIBO_DATA_ROOT={data}\nMIBO_CORE_V2_EXECUTION=ENABLED_AFTER_CORE_V2_GATE\n'
            'OPENAI_API_KEY=synthetic-secret-1\nANTHROPIC_API_KEY=synthetic-secret-2\n'
            'GEMINI_API_KEY=synthetic-secret-3\nPERPLEXITY_API_KEY=synthetic-secret-4\n')
        return env, data

    def api_mocks(self):
        ids = {'OpenAI': 'gpt-6.1-sol', 'Anthropic': 'claude-sonnet-5-5',
               'Google': 'gemini-3.8-flash', 'Perplexity': 'perplexity/sonar'}
        def result(provider, model):
            data = {'name': f'models/{model}'} if provider == 'Google' else {'id': model}
            return api.HTTPResult(provider, 'https://synthetic.invalid/model', 200,
                '2026-10-06T01:00:00Z', '2026-10-06T01:00:01Z', 1, json.dumps(data), data)
        def catalog(provider, timeout_s=30):
            return result(provider, ids[provider]), [ids[provider]]
        def exact(provider, model, timeout_s=30):
            return None if provider == 'Perplexity' else result(provider, model)
        return catalog, exact

    def common(self, stack):
        stack.enter_context(mock.patch.object(vm.os, 'geteuid', return_value=0))
        stack.enter_context(mock.patch.object(vm, 'datetime', Clock))
        stack.enter_context(mock.patch.object(vm.subprocess, 'run', return_value=SimpleNamespace(stdout='inactive\n')))
        stack.enter_context(mock.patch.object(vm.subprocess, 'check_output', return_value='yes\n'))
        stack.enter_context(mock.patch.object(vm.shutil, 'disk_usage', return_value=SimpleNamespace(free=10 * 1024**3)))

    def test_unconfirmed_terms_never_freeze_or_generate(self):
        from contextlib import ExitStack
        catalog, exact = self.api_mocks()
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            env, data = self.environment(Path(d))
            self.common(stack)
            stack.enter_context(mock.patch.dict(os.environ, {}, clear=True))
            stack.enter_context(mock.patch.object(api, 'fetch_catalog', side_effect=catalog))
            stack.enter_context(mock.patch.object(api, 'fetch_exact_model', side_effect=exact))
            stack.enter_context(mock.patch('builtins.open', return_value=io.StringIO()))
            stack.enter_context(mock.patch.object(vm, 'attest', side_effect=ValueError('not reviewed')))
            generated = stack.enter_context(mock.patch.object(preflight, 'call_provider'))
            out = Path(d) / 'readiness'
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'not reviewed'):
                vm.prepare(env_path=env, out_dir=out,
                    protocol_path=HERE / 'config/core_v2_agent_protocol.v2.0.1.json')
            generated.assert_not_called()
            self.assertFalse((out / 'core_v2_provider_freeze.json').exists())
            self.assertNotIn('MIBO_CORE_V2_EXECUTION', os.environ)

    def test_success_builds_unsigned_bundle_and_records_actual_readiness(self):
        from contextlib import ExitStack
        catalog, exact = self.api_mocks()
        def generate(**kwargs):
            model = kwargs['model_id']
            self.assertEqual(kwargs['prompt'], preflight.SYNTHETIC_PROMPT)
            return AdapterResult(kwargs['provider'], model, model, {'model': model},
                {'model': model}, json.dumps({'model': model}), 200,
                '2026-10-06T01:00:00Z', '2026-10-06T01:00:01Z', 1, None, 'synthetic ack')
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            env, data = self.environment(Path(d))
            self.common(stack)
            stack.enter_context(mock.patch.dict(os.environ, {}, clear=True))
            stack.enter_context(mock.patch.object(api, 'fetch_catalog', side_effect=catalog))
            stack.enter_context(mock.patch.object(api, 'fetch_exact_model', side_effect=exact))
            stack.enter_context(mock.patch('builtins.open', return_value=io.StringIO()))
            stack.enter_context(mock.patch.object(vm, 'attest', return_value='synthetic human'))
            generated = stack.enter_context(mock.patch.object(preflight, 'call_provider', side_effect=generate))
            stack.enter_context(mock.patch.object(vm, 'now', return_value='2026-10-06T01:00:02Z'))
            out = Path(d) / 'readiness'
            with redirect_stdout(io.StringIO()) as terminal:
                vm.prepare(env_path=env, out_dir=out,
                    protocol_path=HERE / 'config/core_v2_agent_protocol.v2.0.1.json')
            self.assertEqual(generated.call_count, 4)
            auth = json.loads((out / 'bundle/core_v2_execution_authorization.template.json').read_text())
            self.assertFalse(auth['authorized'])
            self.assertFalse(auth['authorize_confirmatory_api_core'])
            self.assertIsNone(auth['authorized_at_utc'])
            status = json.loads((out / 'READINESS_STATUS.json').read_text())
            self.assertEqual(status['technical_readiness_completed_at_utc'], '2026-10-06T01:00:02Z')
            self.assertIsNone(status['actual_preparation_completed_at_utc'])
            self.assertIsNone(status['actual_observation_start_at_utc'])
            self.assertTrue(status['strict_deterministic_manifest_comparison_passed'])
            self.assertFalse(status['collection_enabled'])
            self.assertNotIn('synthetic-secret-', terminal.getvalue())

    def test_retained_original_wave_stops_before_discovery(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            env, data = self.environment(Path(d))
            legacy = data / 'v2.0/JP01/MIBO2-W01/api_raw'
            legacy.mkdir(parents=True)
            (legacy / 'synthetic.json').write_text('{}')
            self.common(stack)
            discovery = stack.enter_context(mock.patch.object(api, 'fetch_catalog'))
            with self.assertRaisesRegex(ValueError, 'retained wave attempts'):
                vm.prepare(env_path=env, out_dir=Path(d) / 'readiness',
                    protocol_path=HERE / 'config/core_v2_agent_protocol.v2.0.1.json')
            discovery.assert_not_called()

    def test_environment_is_literal_and_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'private.env'
            path.write_text('MIBO_DATA_ROOT="/tmp/$(literal-command)"\n')
            self.assertEqual(vm.read_environment(path)['MIBO_DATA_ROOT'], '/tmp/$(literal-command)')
            path.write_text('A=1\nA=2\n')
            with self.assertRaises(ValueError):
                vm.read_environment(path)

    def test_private_smoke_failure_retains_error_and_redacts_keys(self):
        from contextlib import ExitStack
        from test_core_agent_amendment import AgentFixture
        catalog, exact = self.api_mocks()
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            fixture = AgentFixture(Path(d))
            # Catalogs must verify the synthetic fixture IDs, not the real selected IDs.
            frozen = json.loads(fixture.freeze.read_text())
            def synthetic_catalog(provider, timeout_s=30):
                matches = [entry['model_id'] for entry in frozen['core_api'].values()]
                return catalog(provider)[0], matches
            def synthetic_exact(provider, model, timeout_s=30):
                if provider == 'Perplexity':
                    return None
                raw = {'name': 'models/' + model} if provider == 'Google' else {'id': model}
                return api.HTTPResult(provider, 'https://synthetic.invalid', 200,
                    '2026-10-06T01:00:00Z', '2026-10-06T01:00:01Z', 1, json.dumps(raw), raw)
            stack.enter_context(mock.patch.object(api, 'fetch_catalog', side_effect=synthetic_catalog))
            stack.enter_context(mock.patch.object(api, 'fetch_exact_model', side_effect=synthetic_exact))
            credentials = {entry['request_profile']['api_key_env']: 'synthetic-private-key'
                           for entry in frozen['core_api'].values()}
            credentials['MIBO_CORE_V2_SMOKE_TEST'] = preflight.SMOKE_SENTINEL
            stack.enter_context(mock.patch.dict(os.environ, credentials, clear=True))
            stack.enter_context(mock.patch.object(preflight, 'call_provider', side_effect=AdapterFailure(
                'request_environment_mismatch', 'synthetic', 200, response_body='synthetic-private-key: rejected environment')))
            out = Path(d) / 'preflight'
            report = preflight.run_preflight(protocol_path=fixture.protocol,
                freeze_path=fixture.freeze, out_dir=out, smoke=True)
            self.assertFalse(report['pass'])
            self.assertEqual(len(report['synthetic_smoke_checks']), 4)
            for check in report['synthetic_smoke_checks']:
                text = (out / check['file']).read_text()
                self.assertNotIn('synthetic-private-key', text)
                self.assertIn('[REDACTED]', text)
                self.assertIn('request_environment_mismatch', text)


if __name__ == '__main__':
    unittest.main()
