from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
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
import core_v2_execution_state as state
import core_v2_executor as executor
import core_v2_runner as runner
from provider_adapters import AdapterFailure
from test_core_v2_api import CoreV2Fixture


class DurableExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.fixture = CoreV2Fixture(self.base)
        self.protocol, _ = runner.load_protocol(self.fixture.protocol)
        self.freeze = json.loads(self.fixture.freeze.read_text())
        self.auth = json.loads(self.fixture.authorization.read_text())
        all_rows = runner.read_csv(self.fixture.manifest)
        google = [r for r in all_rows if r['provider'] == 'Google' and r['window_id'] == 'STD'][:2]
        other = next(r for r in all_rows if r['provider'] == 'OpenAI' and r['window_id'] == 'STD')
        self.rows = [dict(google[0], execution_order=1), dict(google[1], execution_order=2),
                     dict(other, execution_order=3)]
        self.data_root = self.base / 'data'
        self.root = archive.wave_root(self.data_root, 'JP01', 'MIBO2-W01')
        self.clock = datetime(2026, 10, 6, tzinfo=timezone.utc)
        self.start = self.clock
        self.close = self.clock + timedelta(hours=48)
        self.calls = []
        owner = self

        class SyntheticDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return owner.clock if tz is not None else owner.clock.replace(tzinfo=None)

        self.datetime = SyntheticDatetime

    def result(self, **kwargs):
        self.calls.append((kwargs['provider'], self.clock))
        stamp = self.clock.isoformat().replace('+00:00', 'Z')
        return SimpleNamespace(request_payload={'model': kwargs['model_id']},
            response_json={'synthetic': True}, raw_response_text='{"synthetic":true}',
            http_status=200, returned_model=kwargs['model_id'], usage={},
            started_at_utc=stamp, completed_at_utc=stamp, duration_ms=0,
            response_metadata=None)

    def sleep(self, seconds):
        self.clock += timedelta(seconds=seconds)

    def execute(self, callback=None, extra=None):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, {
                'MIBO_CORE_V2_EXECUTION': executor.EXECUTION_SENTINEL}))
            stack.enter_context(mock.patch.object(executor, 'datetime', self.datetime))
            stack.enter_context(mock.patch.object(executor.time, 'sleep', side_effect=self.sleep))
            stack.enter_context(mock.patch.object(executor, 'preflight', return_value=(
                self.rows, self.freeze, self.auth, self.start, self.close)))
            stack.enter_context(mock.patch.object(executor, 'call_provider', side_effect=callback or self.result))
            if extra:
                stack.enter_context(extra)
            return executor.execute(protocol_path=self.fixture.protocol,
                manifest_path=self.fixture.manifest, freeze_path=self.fixture.freeze,
                authorization_path=self.fixture.authorization, data_root=self.data_root)

    def restore(self, **kwargs):
        kwargs.setdefault('current', self.clock)
        return state.restore(root=self.root, initial_rows=self.rows,
            clone_retry=executor._clone_retry_row,
            row_bounds=lambda row: executor._row_bounds(self.protocol, row),
            data_root=self.data_root,
            authorization_sha256=executor.sha256_file(self.fixture.authorization), **kwargs)

    def capture(self, row=None, *, started=None, completed=None):
        row = row or self.rows[0]
        started = started or self.clock
        completed = completed or started
        return archive.archive_success(data_root=self.data_root, row=row,
            request_payload={'model': row['model_id']}, response_json={'synthetic': True},
            raw_response_text='synthetic response', http_status=200,
            returned_model=row['model_id'], usage={}, started_at_utc=started.isoformat(),
            completed_at_utc=completed.isoformat(), duration_ms=0)

    def failure(self, row, *, status=503, retry_after=None):
        return archive.archive_failure(data_root=self.data_root, row=row,
            failure_kind='rate_limit' if status == 429 else 'provider_error',
            message='synthetic technical error', http_status=status,
            retry_after_seconds=retry_after,
            failed_at_utc=self.clock.isoformat().replace('+00:00', 'Z'))

    def test_503_recovery_block_uses_only_two_retries_and_survives_restart(self):
        def unavailable(**kwargs):
            if kwargs['provider'] != 'Google':
                return self.result(**kwargs)
            self.calls.append((kwargs['provider'], self.clock))
            raise AdapterFailure(kind='provider_error', message='synthetic unavailable', http_status=503)
        summary = self.execute(unavailable)
        google_calls = [stamp for provider, stamp in self.calls if provider == 'Google']
        self.assertEqual(google_calls, [self.start, self.start + timedelta(minutes=10),
                                       self.start + timedelta(minutes=40)])
        self.assertEqual(summary['lineage_suspensions'], 1)
        self.assertEqual(summary['valid'], 1)
        self.assertEqual(len(list((self.root / 'failures').glob('*.json'))), 3)
        self.assertFalse((self.root / 'dispatch' / (self.rows[1]['attempt_id'] + '.json')).exists())
        before = len(self.calls)
        again = self.execute(unavailable)
        self.assertEqual(len(self.calls), before)
        self.assertEqual(again['retained_lineage_suspensions'], 1)

    def test_restart_between_failure_and_retry_link_preserves_due_and_pause(self):
        def unavailable(**kwargs):
            self.calls.append((kwargs['provider'], self.clock))
            raise AdapterFailure(kind='provider_error', message='synthetic unavailable', http_status=503)
        with self.assertRaisesRegex(RuntimeError, 'power loss'):
            self.execute(unavailable, extra=mock.patch.object(archive, 'archive_retry_link',
                         side_effect=RuntimeError('synthetic power loss')))
        self.assertEqual(self.calls, [('Google', self.start)])
        self.execute()
        google_calls = [stamp for provider, stamp in self.calls if provider == 'Google']
        self.assertEqual(google_calls, [self.start, self.start + timedelta(minutes=10),
                                       self.start + timedelta(minutes=10)])
        retry = executor._clone_retry_row(self.rows[0], 2)
        link = json.loads((self.root / 'metadata' / ('retry-link-' + retry['attempt_id'] + '.json')).read_text())
        self.assertEqual(link['due_at_utc'], '2026-10-06T00:10:00Z')

    def test_uncertain_dispatch_after_provider_return_never_resends_and_other_lineage_continues(self):
        with self.assertRaisesRegex(OSError, 'disk interruption'):
            self.execute(extra=mock.patch.object(archive, 'archive_success',
                         side_effect=OSError('synthetic disk interruption')))
        self.assertEqual(self.calls, [('Google', self.start)])
        summary = self.execute()
        self.assertEqual(self.calls, [('Google', self.start), ('OpenAI', self.start)])
        self.assertEqual(summary['uncertain_dispatches'], 1)
        self.assertEqual(summary['skipped_after_suspension'], 2)
        self.assertTrue((self.root / 'deviations' /
            ('CORE-V2-UNCERTAIN-DISPATCH-' + self.rows[0]['attempt_id'] + '.json')).exists())

    def test_raw_written_without_metadata_holds_lineage_without_reading_answer(self):
        raw = self.root / 'api_raw' / (self.rows[0]['attempt_id'] + '.json')
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b'private synthetic response whose content must not be parsed')
        summary = self.execute()
        self.assertEqual([provider for provider, _ in self.calls], ['OpenAI'])
        self.assertEqual(summary['uncertain_dispatches'], 1)
        self.assertEqual(raw.read_bytes(), b'private synthetic response whose content must not be parsed')

    def test_completed_capture_is_not_sent_again(self):
        self.execute()
        self.assertEqual(len(self.calls), 3)
        self.execute()
        self.assertEqual(len(self.calls), 3)

    def test_backwards_wall_clock_during_wait_does_not_submit_retry_early(self):
        failed_once = False
        stepped_once = False
        def provider(**kwargs):
            nonlocal failed_once
            if kwargs['provider'] == 'Google' and not failed_once:
                failed_once = True
                self.calls.append(('Google', self.clock))
                raise AdapterFailure(kind='provider_error', message='synthetic 503', http_status=503)
            return self.result(**kwargs)
        def stepping_sleep(seconds):
            nonlocal stepped_once
            if not stepped_once:
                stepped_once = True
                self.clock = self.start - timedelta(minutes=1)
            else:
                self.clock += timedelta(seconds=seconds)
        self.sleep = stepping_sleep
        self.execute(provider)
        stamps = [stamp for name, stamp in self.calls if name == 'Google']
        self.assertEqual(stamps[0], self.start)
        self.assertTrue(all(stamp >= self.start + timedelta(minutes=10) for stamp in stamps[1:]))

    def test_corrupt_metadata_stops_before_any_provider_call(self):
        folder = self.root / 'metadata'
        folder.mkdir(parents=True)
        (folder / (self.rows[0]['attempt_id'] + '.json')).write_text('{partial')
        with self.assertRaisesRegex(ValueError, 'corrupt retained'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_window_closes_during_durable_claim_no_provider_call_occurs(self):
        original = state.claim_attempt
        def closing_claim(*args, **kwargs):
            original(*args, **kwargs)
            self.clock = self.close
        result = self.execute(extra=mock.patch.object(state, 'claim_attempt', side_effect=closing_claim))
        self.assertEqual(self.calls, [])
        self.assertEqual(result['uncertain_dispatches'], 1)
        self.assertTrue((self.root / 'dispatch' / (self.rows[0]['attempt_id'] + '.json')).exists())

    def test_capture_checksum_mismatch_stops_before_any_provider_call(self):
        self.execute()
        self.calls.clear()
        raw = self.root / 'api_raw' / (self.rows[0]['attempt_id'] + '.json')
        raw.write_text('synthetic changed bytes')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_capture_technical_identity_and_http_mutations_stop_before_calls(self):
        self.capture()
        path = self.root / 'metadata' / (self.rows[0]['attempt_id'] + '.json')
        original = json.loads(path.read_text())
        changes = {
            'http_status': 503, 'query_sha256': '0' * 64,
            'protocol_file_sha256': '0' * 64, 'provider_freeze_sha256': '0' * 64,
            'window_id': 'WB', 'service_lineage_id': 'MIBO-SL-001',
            'query_form_id': self.rows[1]['query_form_id'],
            'protocol_registration_id': 'foreign-registration', 'wave_id': 'MIBO2-W02',
            'model_id_requested': 'foreign-model', 'attempt': 2,
        }
        for key, value in changes.items():
            if value == original.get(key):
                value = 'foreign-query-form'
            with self.subTest(key=key):
                path.write_text(json.dumps(dict(original, **{key: value})))
                with self.assertRaises(ValueError):
                    self.execute()
                self.assertEqual(self.calls, [])
        path.write_text(json.dumps(original))
        self.assertIn(self.rows[0]['attempt_id'], self.restore(persist=False).done)

    def test_capture_timing_mutations_stop_before_calls(self):
        self.capture()
        path = self.root / 'metadata' / (self.rows[0]['attempt_id'] + '.json')
        original = json.loads(path.read_text())
        for values in (
            {'started_at_utc': (self.start - timedelta(seconds=1)).isoformat()},
            {'started_at_utc': self.close.isoformat(), 'completed_at_utc': self.close.isoformat()},
            {'completed_at_utc': (self.start - timedelta(seconds=1)).isoformat()},
            {'completed_at_utc': (self.clock + timedelta(seconds=1)).isoformat()},
            {'started_at_utc': self.start.replace(tzinfo=None).isoformat()},
        ):
            with self.subTest(values=values):
                path.write_text(json.dumps(dict(original, **values)))
                with self.assertRaises(ValueError):
                    self.execute()
                self.assertEqual(self.calls, [])

    def test_legacy_capture_is_retained_but_cannot_authorize_restart(self):
        self.capture()
        path = self.root / 'metadata' / (self.rows[0]['attempt_id'] + '.json')
        data = json.loads(path.read_text())
        del data['technical_metadata_version']
        path.write_text(json.dumps(data))
        raw = self.root / data['raw_file']
        before = raw.read_bytes()
        with self.assertRaisesRegex(state.LegacyCaptureMetadataError, 'legacy capture'):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual(raw.read_bytes(), before)

    def test_capture_validation_never_decodes_raw_response(self):
        self.capture()
        path = self.root / 'metadata' / (self.rows[0]['attempt_id'] + '.json')
        data = json.loads(path.read_text())
        raw = self.root / data['raw_file']
        raw.write_bytes(b'\xff\x00synthetic opaque non-JSON response')
        data['raw_file_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
        path.write_text(json.dumps(data))
        self.assertIn(self.rows[0]['attempt_id'], self.restore(persist=False).done)

    def test_post_close_completion_is_valid_when_dispatch_started_in_window(self):
        self.capture(started=self.close - timedelta(seconds=1),
                     completed=self.close + timedelta(seconds=1))
        restored = self.restore(persist=False, current=self.close + timedelta(seconds=2))
        self.assertIn(self.rows[0]['attempt_id'], restored.done)

    def test_invalid_new_capture_stops_before_next_provider_call_and_keeps_raw(self):
        def bad_transport(**kwargs):
            result = self.result(**kwargs)
            result.http_status = 503
            return result
        with self.assertRaisesRegex(ValueError, 'HTTP status'):
            self.execute(bad_transport)
        self.assertEqual(self.calls, [('Google', self.start)])
        self.assertTrue((self.root / 'api_raw' / (self.rows[0]['attempt_id'] + '.json')).exists())
        with self.assertRaisesRegex(ValueError, 'HTTP status'):
            self.execute()
        self.assertEqual(self.calls, [('Google', self.start)])

    def test_foreign_failure_identity_is_rejected_before_calls_or_repair_writes(self):
        self.failure(self.rows[0])
        path = self.root / 'failures' / (self.rows[0]['attempt_id'] + '.json')
        original = json.loads(path.read_text())
        changes = {'site_id': 'JP02', 'wave_id': 'MIBO2-W02', 'provider': 'OpenAI',
                   'protocol_registration_id': 'foreign-registration', 'line_id': 'foreign-line',
                   'query_form_id': 'foreign-query', 'query_sha256': '0' * 64,
                   'replication': original['replication'] + 1, 'attempt': 2, 'window_id': 'WB'}
        for key, value in changes.items():
            with self.subTest(key=key):
                path.write_text(json.dumps(dict(original, **{key: value})))
                with self.assertRaises(ValueError):
                    self.execute()
                self.assertEqual(self.calls, [])
                self.assertFalse((self.root / 'metadata').exists())
                self.assertFalse((self.root / 'deviations').exists())

    def test_early_retry_capture_failure_and_claim_are_rejected_before_calls(self):
        self.failure(self.rows[0])
        retry = executor._clone_retry_row(self.rows[0], 2)
        self.clock += timedelta(minutes=5)
        for kind in ('capture', 'failure', 'claim'):
            with self.subTest(kind=kind):
                if kind == 'capture':
                    self.capture(retry)
                elif kind == 'failure':
                    self.failure(retry)
                else:
                    state.claim_attempt(self.root, retry,
                        authorization_sha256=executor.sha256_file(self.fixture.authorization),
                        dispatched_at=self.clock)
                with self.assertRaisesRegex(ValueError, 'protocol-eligible due'):
                    self.execute()
                self.assertEqual(self.calls, [])
                self.assertFalse(list((self.root / 'metadata').glob('retry-link-*.json')))
                self.assertFalse((self.root / 'deviations').exists())
                for folder in ('metadata', 'api_raw', 'failures', 'dispatch'):
                    path = self.root / folder / (retry['attempt_id'] + '.json')
                    if path.exists():
                        path.unlink()

    def test_future_failure_and_claim_reject_before_calls(self):
        self.failure(self.rows[0])
        path = self.root / 'failures' / (self.rows[0]['attempt_id'] + '.json')
        data = json.loads(path.read_text())
        data['failed_at_utc'] = (self.clock + timedelta(seconds=1)).isoformat()
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'future'):
            self.execute()
        self.assertEqual(self.calls, [])
        path.unlink()
        state.claim_attempt(self.root, self.rows[0],
            authorization_sha256=executor.sha256_file(self.fixture.authorization),
            dispatched_at=self.clock + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, 'registered/current bounds'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_dispatch_claim_must_precede_terminal_capture_or_failure(self):
        self.capture()
        state.claim_attempt(self.root, self.rows[0],
            authorization_sha256=executor.sha256_file(self.fixture.authorization),
            dispatched_at=self.clock + timedelta(seconds=1))
        self.clock += timedelta(seconds=2)
        with self.assertRaisesRegex(ValueError, 'predates dispatch claim'):
            self.execute()
        self.assertEqual(self.calls, [])
        for folder in ('metadata', 'api_raw'):
            (self.root / folder / (self.rows[0]['attempt_id'] + '.json')).unlink()
        self.clock = self.start
        self.failure(self.rows[0])
        self.clock += timedelta(seconds=2)
        with self.assertRaisesRegex(ValueError, 'predates dispatch claim'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_lock_blocks_second_executor_and_is_released_after_exception(self):
        with state.wave_lock(self.root):
            with self.assertRaisesRegex(RuntimeError, 'wave lock'):
                self.execute()
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(RuntimeError, 'synthetic crash'):
            with state.wave_lock(self.root):
                raise RuntimeError('synthetic crash')
        with state.wave_lock(self.root):
            pass

    def test_retry_link_earlier_than_provider_retry_after_is_rejected(self):
        self.failure(self.rows[0], status=429, retry_after=1200)
        retry = executor._clone_retry_row(self.rows[0], 2)
        archive.archive_retry_link(data_root=self.data_root,
            original_attempt_id=self.rows[0]['attempt_id'], retry_attempt_id=retry['attempt_id'],
            site_id='JP01', wave_id='MIBO2-W01', due_at_utc='2026-10-06T00:10:00Z',
            failure_kind='rate_limit')
        with self.assertRaisesRegex(ValueError, 'timing'):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_429_wait_beyond_field_window_stops_fresh_lineage_submissions(self):
        def limited(**kwargs):
            if kwargs['provider'] != 'Google':
                return self.result(**kwargs)
            self.calls.append(('Google', self.clock))
            raise AdapterFailure(kind='rate_limit', message='synthetic limit',
                                 http_status=429, retry_after_seconds=172800)
        result = self.execute(limited)
        self.assertEqual(sum(name == 'Google' for name, _ in self.calls), 1)
        self.assertEqual(result['lineage_suspensions'], 1)
        self.assertEqual(result['valid'], 1)
        self.assertEqual(result['retries_scheduled'], 0)

    def test_restart_after_terminal429_before_deviation_remains_suspended(self):
        self.failure(self.rows[0], status=429, retry_after=172800)
        result = self.execute()
        self.assertEqual([name for name, _ in self.calls], ['OpenAI'])
        self.assertEqual(result['retained_lineage_suspensions'], 1)

    def test_retry_cannot_escape_its_calibration_window(self):
        all_rows = runner.read_csv(self.fixture.manifest)
        self.rows = [next(r for r in all_rows if r['provider'] == 'Google' and r['window_id'] == 'WA')]
        self.clock = self.start + timedelta(hours=11, minutes=55)
        self.failure(self.rows[0])
        restored = self.restore(persist=False)
        self.assertEqual(restored.retries, [])
        self.assertEqual(restored.suspended, {'MIBO-SL-003'})

    def test_fresh_low_order_STD_cell_is_held_until_WA_recovery_retry_succeeds(self):
        all_rows = runner.read_csv(self.fixture.manifest)
        failed = dict(next(r for r in all_rows if r['provider'] == 'Google' and r['window_id'] == 'WA'), execution_order=9)
        fresh = dict(self.rows[1], execution_order=1)
        other = dict(self.rows[2], execution_order=2)
        self.rows = [fresh, failed, other]
        self.failure(failed)
        retry = executor._clone_retry_row(failed, 2)
        seen_google = False
        def inspect_recovery(**kwargs):
            nonlocal seen_google
            if kwargs['provider'] == 'Google' and not seen_google:
                seen_google = True
                self.assertTrue((self.root / 'dispatch' / (retry['attempt_id'] + '.json')).exists())
                self.assertFalse((self.root / 'dispatch' / (fresh['attempt_id'] + '.json')).exists())
                self.assertEqual(self.clock, self.start + timedelta(minutes=10))
            return self.result(**kwargs)
        result = self.execute(inspect_recovery)
        self.assertEqual(result['valid'], 3)
        self.assertEqual([provider for provider, _ in self.calls], ['OpenAI', 'Google', 'Google'])

    def test_cross_namespace_claim_blocks_replay_and_nonoverlapping_locks_work(self):
        other = archive.wave_root(self.data_root, 'JP01', 'MIBO2-W01', '2.0.4')
        state.claim_attempt(other, dict(self.rows[0], protocol_version='2.0.4'),
            authorization_sha256=executor.sha256_file(self.fixture.authorization), dispatched_at=self.clock)
        with self.assertRaisesRegex(ValueError, 'another protocol namespace'):
            self.execute()
        self.assertEqual(self.calls, [])
        with state.lineage_locks(self.data_root, 'JP01', 'MIBO2-W01', {'MIBO-SL-003'}):
            with self.assertRaisesRegex(RuntimeError, 'lineage/wave lock'):
                with state.lineage_locks(self.data_root, 'JP01', 'MIBO2-W01', {'MIBO-SL-003'}):
                    pass
            with state.lineage_locks(self.data_root, 'JP01', 'MIBO2-W01', {'MIBO-SL-001'}):
                pass

    def test_cross_namespace_identity_cannot_hide_google_as_other_lineage(self):
        self.rows = self.rows[:1]
        other = archive.wave_root(self.data_root, 'JP01', 'MIBO2-W01', '2.0.4')
        aid = self.rows[0]['attempt_id']
        for folder in ('failures', 'metadata', 'dispatch'):
            with self.subTest(folder=folder):
                path = other / folder / (aid + '.json')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'attempt_id': aid, 'service_lineage_id': 'MIBO-SL-001'}))
                with self.assertRaisesRegex(ValueError, 'filename/lineage conflict'):
                    self.execute()
                self.assertEqual(self.calls, [])
                path.write_text(json.dumps({'attempt_id': self.rows[0]['attempt_id'] + '-foreign',
                                            'service_lineage_id': self.rows[0]['service_lineage_id']}))
                with self.assertRaisesRegex(ValueError, 'filename/identity conflict'):
                    self.execute()
                self.assertEqual(self.calls, [])
                path.unlink()

    def test_priority_and_standard_migration_guards_recognize_unresolved_claim(self):
        import core_v2_priority
        import core_v2_standard
        state.claim_attempt(self.root, self.rows[0],
            authorization_sha256=executor.sha256_file(self.fixture.authorization), dispatched_at=self.clock)
        for guard in (core_v2_priority.block_prior_google_attempts, core_v2_standard.block_prior_google_attempts):
            with self.assertRaisesRegex(ValueError, 'prior Google'):
                guard(self.data_root, 'JP01', 'MIBO2-W01')

    def test_frozen_input_mutation_during_claim_stops_before_provider_call(self):
        original = state.claim_attempt
        def mutating_claim(*args, **kwargs):
            original(*args, **kwargs)
            self.fixture.freeze.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'frozen execution input changed'):
            self.execute(extra=mock.patch.object(state, 'claim_attempt', side_effect=mutating_claim))
        self.assertEqual(self.calls, [])

    def test_direct_legacy_executor_rejects_future_human_authorization(self):
        auth = json.loads(self.fixture.authorization.read_text())
        auth['authorized_at_utc'] = '2026-10-07T00:00:00Z'
        self.fixture.authorization.write_text(json.dumps(auth))
        with self.assertRaisesRegex(ValueError, 'cannot precede human authorization'):
            executor.preflight(protocol_path=self.fixture.protocol, manifest_path=self.fixture.manifest,
                freeze_path=self.fixture.freeze, authorization_path=self.fixture.authorization,
                data_root=self.data_root, now=self.start)

    def test_fourth_attempt_or_retry_without_parent_failure_is_rejected(self):
        retry_one = executor._clone_retry_row(self.rows[0], 2)
        retry_two = executor._clone_retry_row(retry_one, 3)
        retry_three = executor._clone_retry_row(retry_two, 4)
        self.failure(retry_three)
        with self.assertRaisesRegex(ValueError, 'unregistered Attempt ID or excess retry'):
            self.restore(persist=False)

    def test_read_only_restore_does_not_create_missing_link_or_uncertain_deviation(self):
        self.failure(self.rows[0])
        before = sorted(path.relative_to(self.root) for path in self.root.rglob('*'))
        restored = self.restore(persist=False)
        self.assertEqual(len(restored.retries), 1)
        self.assertEqual(sorted(path.relative_to(self.root) for path in self.root.rglob('*')), before)

    def test_dispatch_is_durable_before_the_provider_is_called(self):
        def inspect_claim(**kwargs):
            row = self.rows[len(self.calls)]
            claim_path = self.root / 'dispatch' / (row['attempt_id'] + '.json')
            self.assertTrue(claim_path.is_file())
            claim = json.loads(claim_path.read_text())
            self.assertEqual(claim['authorization_sha256'], executor.sha256_file(self.fixture.authorization))
            self.assertNotIn('prompt', claim)
            self.assertNotIn('api_key', claim)
            return self.result(**kwargs)
        with mock.patch.object(archive.os, 'fsync', wraps=os.fsync) as synced:
            self.execute(inspect_claim)
            self.assertGreaterEqual(synced.call_count, 6)

    def test_lock_namespace_symlink_cannot_alias_other_wave(self):
        target = self.base / 'lock-target'
        target.mkdir()
        self.data_root.mkdir()
        (self.data_root / '.execution-locks').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'lock namespace.*symlink'):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual(list(target.iterdir()), [])

    def test_wave_namespace_rejects_traversal_and_symlink_alias(self):
        with self.assertRaisesRegex(ValueError, 'unsafe Core archive'):
            archive.wave_root(self.data_root, '../JP01', 'MIBO2-W01')
        self.data_root.mkdir()
        target = self.base / 'archive-target'
        target.mkdir()
        (self.data_root / 'v2.0').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'archive namespace.*symlink'):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
