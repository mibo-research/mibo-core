"""All provider responses are synthetic; recovery makes one mocked call only."""
from contextlib import ExitStack, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import api_preflight as api
import core_v2_preflight as preflight
import provider_adapters as adapters
from test_core_agent_amendment import AgentFixture

spec = importlib.util.spec_from_file_location('synthetic_recovery', HERE.parent / 'runtime/recover-core-v2-readiness.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def result(self, **kwargs):
        model = kwargs['model_id']
        return adapters.AdapterResult(kwargs['provider'], model, model, {'model': model},
            {'model': model}, json.dumps({'model': model}), 200,
            '2026-10-06T01:00:00Z', '2026-10-06T01:00:01Z', 1, None, 'synthetic ack')

    def fixture(self, root, stack):
        f = AgentFixture(root)
        frozen = json.loads(f.freeze.read_text())
        def catalog(provider, timeout_s=30):
            result = api.HTTPResult(provider, 'https://synthetic.invalid', 200,
                '2026-10-06T00:10:00Z', '2026-10-06T00:10:01Z', 1, '{}', {})
            return result, [entry['model_id'] for entry in frozen['core_api'].values()]
        def exact(provider, model, timeout_s=30):
            if provider == 'Perplexity':
                return None
            data = {'name': 'models/' + model} if provider == 'Google' else {'id': model}
            return api.HTTPResult(provider, 'https://synthetic.invalid', 200,
                '2026-10-06T00:10:00Z', '2026-10-06T00:10:01Z', 1, json.dumps(data), data)
        stack.enter_context(mock.patch.object(api, 'fetch_catalog', side_effect=catalog))
        stack.enter_context(mock.patch.object(api, 'fetch_exact_model', side_effect=exact))
        def first_probe(**kwargs):
            if kwargs['provider'] == 'Google':
                raise adapters.AdapterFailure('provider_error', 'synthetic high demand', 503,
                    response_body='{"error":{"message":"synthetic high demand"}}')
            return self.result(**kwargs)
        credentials = {entry['request_profile']['api_key_env']: 'synthetic-private-key'
                       for entry in frozen['core_api'].values()}
        credentials['MIBO_CORE_V2_SMOKE_TEST'] = preflight.SMOKE_SENTINEL
        stack.enter_context(mock.patch.dict(os.environ, credentials, clear=True))
        stack.enter_context(mock.patch.object(api, 'utc_now', return_value='2026-10-06T00:10:00Z'))
        ready = root / 'readiness'
        with mock.patch.object(preflight, 'call_provider', side_effect=first_probe):
            report = preflight.run_preflight(protocol_path=f.protocol, freeze_path=f.freeze,
                out_dir=ready / 'preflight', smoke=True)
        self.assertFalse(report['pass'])
        return f, ready / 'preflight/CORE_V2_API_PREFLIGHT_REPORT.json'

    def recover(self, f, report, destination, current=None):
        return recovery.recover(protocol_path=f.protocol, freeze_path=f.freeze,
            report_path=report, out_dir=destination,
            current=current or datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc))

    def test_only_google_is_reprobed_and_original_evidence_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            f, report = self.fixture(Path(d), stack)
            originals = {p: p.read_bytes() for p in report.parent.rglob('*') if p.is_file()}
            freeze_before = f.freeze.read_bytes()
            generated = stack.enter_context(mock.patch.object(adapters, 'call_provider', side_effect=self.result))
            destination = report.parents[1] / 'recovery-synthetic'
            with redirect_stdout(io.StringIO()):
                result = self.recover(f, report, destination)
            self.assertEqual(generated.call_count, 1)
            self.assertEqual(generated.call_args.kwargs['provider'], 'Google')
            self.assertEqual(generated.call_args.kwargs['prompt'], preflight.SYNTHETIC_PROMPT)
            self.assertEqual(result['initial_request_count'], 1120)
            self.assertEqual(f.freeze.read_bytes(), freeze_before)
            for path, data in originals.items():
                self.assertEqual(path.read_bytes(), data)
            merged = json.loads((destination / 'CORE_V2_API_PREFLIGHT_REPORT.json').read_text())
            self.assertTrue(merged['pass'])
            self.assertTrue(merged['original_failure_retained'])
            self.assertEqual(sum(c['pass'] for c in merged['synthetic_smoke_checks']), 4)
            auth = json.loads((destination / 'bundle/core_v2_execution_authorization.template.json').read_text())
            self.assertFalse(auth['authorized'])
            self.assertFalse(auth['authorize_confirmatory_api_core'])
            self.assertIsNone(auth['authorized_at_utc'])

    def test_recovery_wait_and_tampered_evidence_block_before_provider_call(self):
        for mode in ('wait', 'tamper'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                f, report = self.fixture(Path(d), stack)
                call = stack.enter_context(mock.patch.object(adapters, 'call_provider'))
                current = datetime(2026, 10, 6, 0, 10, 30, tzinfo=timezone.utc)
                if mode == 'tamper':
                    (report.parent / 'smoke/openai' / (json.loads(f.freeze.read_text())['core_api']['MIBO-SL-001']['model_id'] + '.json')).write_text('{}')
                    current = datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc)
                with self.assertRaises(ValueError):
                    self.recover(f, report, report.parents[1] / 'recovery-blocked', current)
                call.assert_not_called()

    def test_failed_retry_retains_redacted_failure_and_never_builds_bundle(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            f, report = self.fixture(Path(d), stack)
            call = stack.enter_context(mock.patch.object(adapters, 'call_provider',
                side_effect=adapters.AdapterFailure('provider_error', 'synthetic', 503,
                    response_body='synthetic-private-key: synthetic high demand')))
            destination = report.parents[1] / 'recovery-failed'
            with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                self.recover(f, report, destination)
            self.assertEqual(call.call_count, 1)
            failure = (destination / 'RECOVERY_FAILURE.json').read_text()
            self.assertNotIn('synthetic-private-key', failure)
            self.assertIn('[REDACTED]', failure)
            self.assertFalse((destination / 'bundle').exists())

    def test_two_failed_recoveries_or_non503_latest_failure_block(self):
        for mode in ('two', 'non503'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                f, report = self.fixture(Path(d), stack)
                parent = report.parents[1]
                for index in range(2 if mode == 'two' else 1):
                    recovery.write(parent / f'recovery-{index}/RECOVERY_FAILURE.json',
                        {'http_status': 503 if mode == 'two' else 400,
                         'recorded_at_utc': '2026-10-06T00:11:00Z'})
                call = stack.enter_context(mock.patch.object(adapters, 'call_provider'))
                with self.assertRaises(ValueError):
                    self.recover(f, report, parent / 'recovery-blocked')
                call.assert_not_called()

    def test_wrong_returned_model_is_retained_and_blocks_another_call(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            f, report = self.fixture(Path(d), stack)
            def wrong_model(**kwargs):
                return replace(self.result(**kwargs), returned_model='synthetic-wrong-model')
            call = stack.enter_context(mock.patch.object(adapters, 'call_provider', side_effect=wrong_model))
            destination = report.parents[1] / 'recovery-mismatch'
            with self.assertRaisesRegex(ValueError, 'model/status mismatch'):
                self.recover(f, report, destination)
            self.assertEqual(call.call_count, 1)
            self.assertTrue((destination / 'RECOVERED_SMOKE.json').exists())
            with self.assertRaisesRegex(ValueError, 'not HTTP 503'):
                self.recover(f, report, report.parents[1] / 'recovery-blocked')
            self.assertEqual(call.call_count, 1)


if __name__ == '__main__':
    unittest.main()
