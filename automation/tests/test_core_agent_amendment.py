from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive as archive
import core_v2_bundle as bundle
import core_v2_executor as executor
import core_v2_runner as runner
from provider_adapters import AdapterFailure
from test_core_v2_api import CoreV2Fixture, sha256_file, CONFIG


class AgentFixture(CoreV2Fixture):
    """Entirely synthetic approvals and times; no provider calls."""
    def __init__(self, root):
        super().__init__(root)
        self.legacy_rows = runner.read_csv(self.manifest)
        protocol = json.loads((CONFIG / 'core_v2_agent_protocol.draft.json').read_text())
        protocol.update(protocol_status='finalized_and_prospectively_registered',
                        protocol_registration_id='synthetic-agent-registration',
                        prospectively_registered_at_utc='2026-10-06T00:05:00Z')
        self.protocol.write_text(json.dumps(protocol))
        freeze = json.loads(self.freeze.read_text())
        freeze.update(schema_version='2.0.1', protocol_version='2.0.1',
                      protocol_registration_id='synthetic-agent-registration',
                      frozen_at_utc='2026-10-06T00:06:00Z')
        cfg = freeze['core_api']['MIBO-SL-004']
        cfg['model_id'] = 'perplexity/synthetic-version-1'
        cfg['request_profile'].update(adapter='perplexity_agent',
            endpoint='https://api.perplexity.ai/v1/agent')
        self.freeze.write_text(json.dumps(freeze))
        self.manifest.unlink()
        runner.write_csv(runner.generate_manifest(
            protocol_path=self.protocol, freeze_path=self.freeze,
            wave_id='MIBO2-W01', site_id='JP01'), self.manifest)
        auth = json.loads(self.authorization.read_text())
        auth.update(schema_version='2.0.1', protocol_version='2.0.1',
                    protocol_registration_id='synthetic-agent-registration',
                    authorized_at_utc='2026-10-06T00:07:00Z',
                    prospective_agent_amendment_reviewed=True,
                    late_activation_with_original_windows_approved=True,
                    protocol_file_sha256=sha256_file(self.protocol),
                    provider_freeze_sha256=sha256_file(self.freeze),
                    manifest_sha256=sha256_file(self.manifest))
        self.authorization.write_text(json.dumps(auth))

    def check(self):
        return executor.preflight(protocol_path=self.protocol,
            manifest_path=self.manifest, freeze_path=self.freeze,
            authorization_path=self.authorization, data_root=self.root / 'data',
            now=datetime(2026, 10, 6, 0, 10, tzinfo=timezone.utc))


class AgentAmendmentTests(unittest.TestCase):
    def test_public_draft_and_pending_provider_cannot_execute(self):
        with self.assertRaisesRegex(ValueError, 'not finalized'):
            runner.load_protocol(CONFIG / 'core_v2_agent_protocol.draft.json')
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            protocol, _ = runner.load_protocol(f.protocol)
            with self.assertRaises(ValueError):
                runner.load_freeze(CONFIG / 'core_v2_agent_provider_freeze.draft.json',
                    protocol=protocol, wave_id='MIBO2-W01', site_id='JP01')

    def test_instrument_order_counts_ids_and_windows_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            rows = runner.read_csv(f.manifest)
            self.assertEqual(len(rows), 1120)
            for old, new in zip(f.legacy_rows, rows):
                for field in ('attempt_id', 'query_form_id', 'query_sha256',
                              'random_seed', 'execution_order', 'window_id',
                              'replication', 'language', 'service_lineage_id'):
                    self.assertEqual(old[field], new[field])
                self.assertEqual(new['protocol_version'], '2.0.1')
            self.assertEqual(runner.validate_manifest(rows,
                protocol_path=f.protocol, freeze_path=f.freeze), [])
            f.check()

    def test_new_version_requires_new_registration_and_unchanged_schedule(self):
        for change in ({'protocol_registration_id': runner.PRIOR_REGISTRATION},
                       {'prospectively_registered_at_utc': None},
                       {'perplexity_transport_contract': 'search-enabled'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                f = AgentFixture(Path(d))
                p = json.loads(f.protocol.read_text())
                p.update(change)
                f.protocol.write_text(json.dumps(p))
                with self.assertRaises(ValueError):
                    runner.load_protocol(f.protocol)
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            p = json.loads(f.protocol.read_text())
            p['waves'][0]['start_utc'] = '2026-10-06T01:00:00Z'
            p['waves'][0]['close_utc'] = '2026-10-08T01:00:00Z'
            f.protocol.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError, 'original registered schedule'):
                runner.load_protocol(f.protocol)

    def test_freeze_cannot_predate_registration_or_use_old_transport(self):
        for change in ('backdated', 'legacy', 'tools'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                f = AgentFixture(Path(d))
                data = json.loads(f.freeze.read_text())
                if change == 'backdated':
                    data['frozen_at_utc'] = '2026-10-06T00:00:00Z'
                elif change == 'legacy':
                    data['core_api']['MIBO-SL-004']['request_profile']['adapter'] = 'perplexity_sonar'
                else:
                    data['core_api']['MIBO-SL-004']['request_profile']['tools'] = []
                f.freeze.write_text(json.dumps(data))
                p, _ = runner.load_protocol(f.protocol)
                with self.assertRaises(ValueError):
                    runner.load_freeze(f.freeze, protocol=p, wave_id='MIBO2-W01', site_id='JP01')

    def test_legacy_authorization_or_unreviewed_change_fails_closed(self):
        for change in ({'schema_version': '2.0', 'protocol_version': '2.0'},
                       {'prospective_agent_amendment_reviewed': False},
                       {'late_activation_with_original_windows_approved': False},
                       {'authorized_at_utc': '2026-10-06T00:00:00Z'},
                       {'authorized_at_utc': '2026-10-06T01:00:00Z'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                f = AgentFixture(Path(d))
                data = json.loads(f.authorization.read_text())
                data.update(change)
                f.authorization.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    f.check()

    def test_archive_resume_and_retry_links_stay_in_new_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            row = runner.read_csv(f.manifest)[0]
            archive.archive_failure(data_root=f.root / 'data', row=row,
                failure_kind='provider_error', message='synthetic',
                failed_at_utc='2026-10-06T00:10:00Z')
            self.assertIn(row['attempt_id'], executor._processed_attempt_ids(
                f.root / 'data', 'JP01', 'MIBO2-W01', '2.0.1'))
            self.assertEqual(executor._processed_attempt_ids(
                f.root / 'data', 'JP01', 'MIBO2-W01'), set())
            retry = executor._clone_retry_row(row, 2)
            archive.archive_retry_link(data_root=f.root / 'data',
                original_attempt_id=row['attempt_id'], retry_attempt_id=retry['attempt_id'],
                site_id=row['site_id'], wave_id=row['wave_id'],
                due_at_utc='2026-10-06T00:20:00Z', failure_kind='provider_error',
                protocol_version='2.0.1')
            links = executor._existing_retry_rows(f.root / 'data', runner.read_csv(f.manifest))
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0][1]['protocol_version'], '2.0.1')
            self.assertFalse(archive.wave_root(f.root / 'data', 'JP01', 'MIBO2-W01').exists())

    def test_existing_original_attempts_block_midwave_migration(self):
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            legacy = archive.wave_root(f.root / 'data', 'JP01', 'MIBO2-W01') / 'failures'
            legacy.mkdir(parents=True)
            (legacy / 'synthetic-retained-attempt.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'no mid-wave amendment'):
                f.check()

    def test_bundle_preserves_version_and_does_not_authorize(self):
        with tempfile.TemporaryDirectory() as d:
            f = AgentFixture(Path(d))
            p, _ = runner.load_protocol(f.protocol)
            report = {'protocol_version': '2.0.1',
                'protocol_registration_id': p['protocol_registration_id'],
                'protocol_file_sha256': sha256_file(f.protocol),
                'scientific_class': runner.SCIENTIFIC_CLASS,
                'wave_id': 'MIBO2-W01', 'site_id': 'JP01',
                'provider_freeze_sha256': sha256_file(f.freeze), 'pass': True,
                'synthetic_smoke_requested': True,
                'synthetic_smoke_checks': [{'pass': True} for _ in range(4)]}
            report_path = f.root / 'synthetic-report.json'
            report_path.write_text(json.dumps(report))
            result = bundle.build_bundle(protocol_path=f.protocol, freeze_path=f.freeze,
                wave_id='MIBO2-W01', site_id='JP01', preflight_report_path=report_path,
                out_dir=f.root / 'bundle')
            self.assertEqual(result['protocol_version'], '2.0.1')
            auth = json.loads((f.root / 'bundle' / 'core_v2_execution_authorization.template.json').read_text())
            self.assertFalse(auth['authorized'])
            self.assertFalse(auth['prospective_agent_amendment_reviewed'])
            self.assertFalse(auth['late_activation_with_original_windows_approved'])

    def test_environment_mismatch_suspends_remaining_lineage_queue(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rows = [{'protocol_version': '2.0.1', 'site_id': 'JP01', 'wave_id': 'MIBO2-W01',
                     'service_lineage_id': 'MIBO-SL-004', 'execution_order': n,
                     'attempt_id': f'synthetic-{n}', 'attempt': 1,
                     'provider': 'Perplexity AI', 'model_id': 'perplexity/synthetic',
                     'query_form_id': 'synthetic-form'} for n in (1, 2)]
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            close = datetime(2099, 1, 1, tzinfo=timezone.utc)
            with mock.patch.dict(os.environ, {'MIBO_CORE_V2_EXECUTION': executor.EXECUTION_SENTINEL}), \
                 mock.patch.object(executor, 'preflight', return_value=(rows, {'core_api': {
                     'MIBO-SL-004': {'request_profile': {}}}}, {}, start, close)), \
                 mock.patch.object(runner, 'load_protocol', return_value=({}, 'synthetic')), \
                 mock.patch.object(executor, '_prompt_map', return_value={'synthetic-form': 'synthetic'}), \
                 mock.patch.object(executor, '_row_bounds', return_value=(start, close)), \
                 mock.patch.object(archive, 'archive_failure') as failure, \
                 mock.patch.object(archive, 'write_deviation') as deviation, \
                 mock.patch.object(executor, 'call_provider', side_effect=AdapterFailure(
                     kind='request_environment_mismatch', message='synthetic mismatch')) as call:
                result = executor.execute(protocol_path=root / 'unused', manifest_path=root / 'unused',
                    freeze_path=root / 'unused', authorization_path=root / 'unused', data_root=root / 'data')
            self.assertEqual(call.call_count, 1)
            self.assertEqual(result['retries_scheduled'], 0)
            self.assertEqual(result['skipped_after_suspension'], 1)
            self.assertEqual(deviation.call_args.kwargs['protocol_version'], '2.0.1')
            failure.assert_called_once()


if __name__ == '__main__':
    unittest.main()
