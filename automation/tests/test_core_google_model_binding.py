from contextlib import ExitStack
from datetime import datetime, timezone
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_preflight as preflight
import core_v2_runner as runner
import provider_adapters as adapters
from test_core_agent_amendment import AgentFixture


class CoreGoogleModelBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = AgentFixture(self.root)
        self.freeze = json.loads(self.fixture.freeze.read_text())
        self.google = self.freeze['core_api']['MIBO-SL-003']
        self.model = self.google['model_id']
        self.timestamp = '2026-10-06T00:10:00Z'

    def http_response(self, returned_model):
        def respond(**kwargs):
            self.assertNotIn('service_tier', kwargs['payload'])
            self.assertIsNotNone(kwargs.get('response_metadata'))
            kwargs['response_metadata']['service_tier_actual'] = 'standard'
            data = {'modelVersion': returned_model,
                    'candidates': [{'content': {'parts': [{'text': 'synthetic acknowledgement'}]}}]}
            return 200, json.dumps(data), data, 1, self.timestamp, self.timestamp
        return respond

    def metadata_result(self, provider, model):
        data = {'name': 'models/' + model} if provider == 'Google' else {'id': model}
        return SimpleNamespace(endpoint='https://synthetic.invalid/models', status=200,
            started_at_utc=self.timestamp, completed_at_utc=self.timestamp, duration_ms=1, data=data)

    def readiness(self, returned_model):
        services = {s['provider']: s['service_lineage_id'] for s in __import__('mibo_runner')._services()}
        def catalog(provider, timeout_s=30):
            label = 'Perplexity AI' if provider == 'Perplexity' else provider
            model = self.freeze['core_api'][services[label]]['model_id']
            return self.metadata_result(provider, model), [model]
        def exact(provider, model_id, timeout_s=30):
            return self.metadata_result(provider, model_id)
        def route(**kwargs):
            self.assertEqual(kwargs['prompt'], preflight.SYNTHETIC_PROMPT)
            if kwargs['provider'] == 'Google':
                return adapters.call_provider(**kwargs)
            return SimpleNamespace(returned_model=kwargs['model_id'], http_status=200,
                started_at_utc=self.timestamp, completed_at_utc=self.timestamp,
                duration_ms=1, usage={}, request_payload={'model': kwargs['model_id']},
                response_json={'synthetic': True}, response_metadata=None)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, {
                self.google['request_profile']['api_key_env']: 'synthetic-private-key',
                'MIBO_CORE_V2_SMOKE_TEST': preflight.SMOKE_SENTINEL}, clear=True))
            stack.enter_context(mock.patch.object(preflight.api, 'fetch_catalog', side_effect=catalog))
            stack.enter_context(mock.patch.object(preflight.api, 'fetch_exact_model', side_effect=exact))
            stack.enter_context(mock.patch.object(preflight, 'call_provider', side_effect=route))
            http = stack.enter_context(mock.patch.object(adapters, '_post_json',
                                      side_effect=self.http_response(returned_model)))
            report = preflight.run_preflight(protocol_path=self.fixture.protocol,
                freeze_path=self.fixture.freeze, out_dir=self.root / 'readiness', smoke=True)
            self.assertEqual(http.call_count, 1)
        return report

    def collect(self, returned_model, count):
        checked = self.fixture.check()
        rows = [row for row in checked[0] if row['provider'] == 'Google' and row['window_id'] == 'STD'][:count]
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(executor, 'preflight', return_value=(rows, *checked[1:])))
            clock = stack.enter_context(mock.patch.object(executor, 'datetime', wraps=datetime))
            clock.now.return_value = datetime(2026, 10, 6, 0, 10, tzinfo=timezone.utc)
            stack.enter_context(mock.patch.dict(os.environ, {
                self.google['request_profile']['api_key_env']: 'synthetic-private-key',
                'MIBO_CORE_V2_EXECUTION': executor.EXECUTION_SENTINEL}, clear=True))
            # Keep the actual adapter and only replace its HTTP transport.
            http = stack.enter_context(mock.patch.object(adapters, '_post_json',
                                      side_effect=self.http_response(returned_model)))
            summary = executor.execute(protocol_path=self.fixture.protocol,
                manifest_path=self.fixture.manifest, freeze_path=self.fixture.freeze,
                authorization_path=self.fixture.authorization, data_root=self.root / 'data')
            self.assertEqual(http.call_count, 1)
        return summary, rows

    def test_agent_readiness_rejects_wrong_google_modelVersion_and_retains_technical_evidence(self):
        report = self.readiness('different-synthetic-model')
        self.assertFalse(report['pass'])
        check = next(c for c in report['synthetic_smoke_checks'] if c['provider'] == 'Google')
        self.assertEqual(check['failure_kind'], 'request_environment_mismatch')
        retained = json.loads((self.root / 'readiness' / check['file']).read_text())
        self.assertFalse(retained['registered_mibo_prompt_used'])
        self.assertEqual(retained['response_metadata']['provider_model_version'], 'different-synthetic-model')

    def test_agent_executor_retains_wrong_google_modelVersion_without_retry_and_suspends(self):
        summary, rows = self.collect('different-synthetic-model', 2)
        self.assertEqual(summary['failed_attempts'], 1)
        self.assertEqual(summary['retries_scheduled'], 0)
        self.assertEqual(summary['lineage_suspensions'], 1)
        self.assertEqual(summary['skipped_after_suspension'], 1)
        wave = archive.wave_root(self.root / 'data', 'JP01', 'MIBO2-W01', '2.0.1')
        retained = json.loads((wave / 'failures' / (rows[0]['attempt_id'] + '.json')).read_text())
        self.assertEqual(retained['failure_kind'], 'request_environment_mismatch')
        self.assertEqual(retained['response_metadata']['provider_model_version'], 'different-synthetic-model')
        self.assertFalse((wave / 'api_raw').exists())

    def test_agent_google_valid_standard_request_preserves_wire_profile_and_model_evidence(self):
        summary, rows = self.collect(self.model, 1)
        self.assertEqual(summary['valid'], 1)
        wave = archive.wave_root(self.root / 'data', 'JP01', 'MIBO2-W01', '2.0.1')
        retained = json.loads((wave / 'api_raw' / (rows[0]['attempt_id'] + '.json')).read_text())
        self.assertNotIn('service_tier', retained['request_payload'])
        self.assertEqual(retained['response_metadata']['provider_model_version'], self.model)
        self.assertEqual(retained['request_payload']['generationConfig']['maxOutputTokens'],
                         self.google['request_profile']['max_output_tokens'])
        self.assertEqual(retained['request_payload']['contents'][0]['parts'][0]['text'],
                         executor._prompt_map()[rows[0]['query_form_id']])


if __name__ == '__main__':
    unittest.main()
