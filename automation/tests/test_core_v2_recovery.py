"""Synthetic W02 regressions: no network, no registered answer inspection."""
import json
import os
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_runner as runner
from provider_adapters import AdapterFailure, AdapterResult
from test_core_v2_api import CoreV2Fixture
from test_core_agent_amendment import AgentFixture
import test_core_lineage_admission as admission_fixtures
import test_core_readiness_recovery as readiness_fixtures


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = CoreV2Fixture(self.root)
        self.freeze = json.loads(self.fixture.freeze.read_text())
        self.freeze["wave_id"] = "MIBO2-W02"
        self.fixture.freeze.write_text(json.dumps(self.freeze))
        self.rows = runner.generate_manifest(protocol_path=self.fixture.protocol,
            freeze_path=self.fixture.freeze, wave_id="MIBO2-W02")
        self.protocol, _ = runner.load_protocol(self.fixture.protocol)
        self.data = self.root / "data"
        self.wave = archive.wave_root(self.data, "JP01", "MIBO2-W02")
        self.start = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.close = self.start + timedelta(hours=48)
        self.clock = self.start

    def result(self, **kwargs):
        stamp = self.clock.isoformat()
        return AdapterResult(provider=kwargs["provider"], requested_model=kwargs["model_id"],
            returned_model=kwargs["model_id"], request_payload={"input": "SYNTHETIC"},
            response_json={"synthetic": True}, raw_response_text='{"synthetic":true}',
            http_status=200, started_at_utc=stamp, completed_at_utc=stamp,
            duration_ms=0, usage={}, output_text="SYNTHETIC")

    def execute(self, side_effect, rows=None):
        test = self
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return test.clock
        def sleep(seconds):
            test.clock += timedelta(seconds=seconds)
        selected = self.rows[:2] if rows is None else rows
        with mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}), \
             mock.patch.object(executor, "preflight", return_value=(selected, self.freeze, {}, self.start, self.close)), \
             mock.patch.object(executor, "datetime", Clock), \
             mock.patch.object(archive, "datetime", Clock), \
             mock.patch.object(executor.time, "sleep", side_effect=sleep), \
             mock.patch.object(executor, "_prompt_map", return_value={r["query_form_id"]: "SYNTHETIC" for r in selected}), \
             mock.patch.object(executor, "call_provider", side_effect=side_effect) as call:
            summary = executor.execute(protocol_path=self.fixture.protocol,
                manifest_path=self.fixture.manifest, freeze_path=self.fixture.freeze,
                authorization_path=self.fixture.authorization, data_root=self.data)
        return summary, call

    def failure(self, row, *, attempt=1, kind="timeout", status=None):
        record = row if attempt == 1 else executor._clone_retry_row(row, attempt)
        archive.archive_failure(data_root=self.data, row=record, failure_kind=kind,
            message="SYNTHETIC", failed_at_utc=self.clock.isoformat(), http_status=status)
        return record

    def test_w02_fixture_preserves_960_initial_rows(self):
        self.assertEqual(len(self.rows), 960)
        self.assertEqual({r["window_id"] for r in self.rows}, {"STD"})
        self.assertEqual(runner.validate_manifest(self.rows, protocol_path=self.fixture.protocol,
            freeze_path=self.fixture.freeze), [])

    def test_restart_keeps_environment_mismatch_suspension(self):
        first, call = self.execute(AdapterFailure(kind="request_environment_mismatch", message="SYNTHETIC"))
        self.assertEqual(call.call_count, 1)
        self.assertEqual(first["skipped_after_suspension"], 1)
        second, call = self.execute(self.result)
        self.assertEqual(call.call_count, 0)
        self.assertEqual(second["skipped_after_suspension"], 1)

    def test_restart_keeps_exhausted_outage_stop_without_deviation_write(self):
        row = self.rows[0]
        first = self.failure(row, kind="provider_error", status=503)
        second = executor._clone_retry_row(first, 2)
        self.clock += timedelta(minutes=10)
        self.failure(second, kind="provider_error", status=503)
        third = executor._clone_retry_row(second, 3)
        self.clock += timedelta(minutes=30)
        self.failure(third, kind="provider_error", status=503)
        _, suspended = executor._restore_runtime_state(self.data, self.rows[:2], self.protocol)
        self.assertIn(row["service_lineage_id"], suspended)
        _, call = self.execute(self.result)
        self.assertEqual(call.call_count, 0)

    def test_restart_keeps_rate_limit_wait_for_untouched_initial_rows(self):
        self.failure(self.rows[0], kind="rate_limit", status=429)
        minimum = self.clock + timedelta(minutes=10)
        observed = []
        def result(**kwargs):
            observed.append(self.clock)
            return self.result(**kwargs)
        summary, call = self.execute(result)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(summary["valid"], 2)
        self.assertTrue(all(t >= minimum for t in observed))

    def test_failure_saved_before_retry_link_is_recovered_with_same_due(self):
        self.failure(self.rows[0])
        pause, suspended = executor._restore_runtime_state(self.data, self.rows[:2], self.protocol)
        retries = executor._existing_retry_rows(self.data, self.rows[:2])
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0][0], self.clock + timedelta(minutes=10))
        self.assertEqual(retries[0][1]["attempt"], 2)
        self.assertEqual(pause, {})
        self.assertEqual(suspended, set())
        executor._restore_runtime_state(self.data, self.rows[:2], self.protocol)
        self.assertEqual(len(list((self.wave / "metadata").glob("retry-link-*"))), 1)

    def test_unresolved_dispatch_blocks_all_calls_after_restart(self):
        archive.archive_dispatch(data_root=self.data, row=self.rows[0])
        with self.assertRaisesRegex(ValueError, "unresolved dispatch"):
            self.execute(self.result)
        self.assertFalse((self.wave / "api_raw").exists())

    def test_retry_link_without_parent_failure_cannot_dispatch_initial_or_retry(self):
        row = self.rows[0]
        retry = executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data,
            original_attempt_id=row["attempt_id"], retry_attempt_id=retry["attempt_id"],
            site_id=row["site_id"], wave_id=row["wave_id"],
            due_at_utc=(self.clock + timedelta(minutes=10)).isoformat(),
            failure_kind="timeout")
        with mock.patch.object(executor, "call_provider") as call:
            with self.assertRaisesRegex(ValueError, "no parent technical failure"):
                self.execute(self.result)
            call.assert_not_called()
        self.assertFalse((self.wave / "dispatch").exists())

    def test_retry_link_for_noneligible_failure_cannot_dispatch(self):
        row = self.rows[0]
        self.failure(row, kind="request_environment_mismatch")
        retry = executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data,
            original_attempt_id=row["attempt_id"], retry_attempt_id=retry["attempt_id"],
            site_id=row["site_id"], wave_id=row["wave_id"],
            due_at_utc=(self.clock + timedelta(minutes=10)).isoformat(),
            failure_kind="request_environment_mismatch")
        with self.assertRaisesRegex(ValueError, "not protocol eligible"):
            self.execute(self.result)
        self.assertFalse((self.wave / "dispatch").exists())

    def test_retry_link_cannot_shorten_registered_wait(self):
        row = self.rows[0]
        self.failure(row)
        retry = executor._clone_retry_row(row, 2)
        archive.archive_retry_link(data_root=self.data,
            original_attempt_id=row["attempt_id"], retry_attempt_id=retry["attempt_id"],
            site_id=row["site_id"], wave_id=row["wave_id"],
            due_at_utc=(self.clock + timedelta(minutes=1)).isoformat(), failure_kind="timeout")
        with self.assertRaisesRegex(ValueError, "violates registered decision"):
            self.execute(self.result)
        self.assertFalse((self.wave / "dispatch").exists())

    def test_partial_raw_without_metadata_blocks_resend(self):
        path = self.wave / "api_raw" / (self.rows[0]["attempt_id"] + ".json")
        path.parent.mkdir(parents=True)
        path.write_text('{"partial":')
        with self.assertRaisesRegex(ValueError, "unlinked raw"):
            self.execute(self.result)

    def test_corrupted_metadata_is_not_silently_skipped(self):
        path = self.wave / "metadata" / (self.rows[0]["attempt_id"] + ".json")
        path.parent.mkdir(parents=True)
        path.write_text("{")
        with self.assertRaisesRegex(ValueError, "unreadable retained record"):
            self.execute(self.result)

    def test_second_executor_cannot_hold_same_wave_version_lock(self):
        with executor._execution_lock(self.data, self.rows):
            with self.assertRaisesRegex(RuntimeError, "another executor"):
                with executor._execution_lock(self.data, self.rows):
                    self.fail("second collector acquired the lock")
        with executor._execution_lock(self.data, self.rows):
            pass

    def test_lineage_lock_blocks_other_version_but_allows_other_lineage(self):
        google = next(r for r in self.rows if r["provider"] == "Google")
        migrated = dict(google, protocol_version="2.0.4")
        other = dict(next(r for r in self.rows if r["provider"] == "OpenAI"), protocol_version="2.0.2")
        with executor._execution_lock(self.data, [google]):
            with self.assertRaisesRegex(RuntimeError, "another executor"):
                with executor._execution_lock(self.data, [migrated]):
                    self.fail("same lineage migrated concurrently")
            with executor._execution_lock(self.data, [other]):
                pass

    def test_same_namespace_other_scope_is_rejected_before_api_dispatch(self):
        google = next(r for r in self.rows if r["provider"] == "Google")
        openai = next(r for r in self.rows if r["provider"] == "OpenAI")
        with executor._execution_lock(self.data, [google]):
            with self.assertRaisesRegex(RuntimeError, "namespace-v2.0"):
                self.execute(self.result, rows=[openai])
        self.assertFalse((self.wave / "dispatch").exists())

    def test_dispatch_survives_interrupt_without_auto_retry(self):
        with self.assertRaises(KeyboardInterrupt):
            self.execute(KeyboardInterrupt())
        self.assertEqual(len(list((self.wave / "dispatch").glob("*.json"))), 1)
        with self.assertRaisesRegex(ValueError, "unresolved dispatch"):
            self.execute(self.result)

    def test_new_dispatch_directory_and_its_parent_are_synchronized(self):
        with mock.patch.object(archive.os, "open", wraps=os.open) as opened:
            archive.archive_dispatch(data_root=self.data, row=self.rows[0])
        directories = {Path(call.args[0]) for call in opened.call_args_list}
        self.assertIn(self.wave / "dispatch", directories)
        self.assertIn(self.wave, directories)
        self.assertIn(self.wave.parent, directories)


class AgentMigrationDispatchTests(unittest.TestCase):
    def test_unresolved_original_dispatch_blocks_agent_namespace_migration(self):
        for folder, filename in (("dispatch", "synthetic-attempt.json"),
                                 ("metadata", "first-dispatch-MIBO-SL-003.json")):
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as d:
                fixture = AgentFixture(Path(d))
                root = archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", "2.0")
                path = root / folder / filename
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"service_lineage_id": "MIBO-SL-003",
                                            "synthetic": True}))
                with mock.patch.object(executor, "call_provider") as call:
                    with self.assertRaisesRegex(ValueError, "no mid-wave amendment"):
                        fixture.check()
                    call.assert_not_called()
                self.assertFalse(archive.wave_root(Path(d) / "data", "JP01", "MIBO2-W01", "2.0.1").exists())


class ScopedRecoveryTests(unittest.TestCase):
    def test_other_scope_records_are_validated_but_never_scheduled(self):
        for mode in ("valid", "valid_without_link", "unknown", "inconsistent"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                root = Path(d)
                helper = admission_fixtures.AdmissionTests()
                _, _, destination, built = helper.fixture(root, stack)
                authorization = helper.authorize(destination, built)
                checked = helper.check(destination, built, authorization, root)
                base = destination / "bundle"
                manifest = base / built["manifest_file"]
                all_rows = runner.read_csv(manifest)
                google = next(r for r in all_rows if r["provider"] == "Google" and r["window_id"] == "STD")
                selected = next(r for r in checked[0] if r["provider"] == "OpenAI" and r["window_id"] == "STD")
                retained = dict(google)
                if mode == "unknown":
                    retained["attempt_id"] += "-UNKNOWN"
                elif mode == "inconsistent":
                    retained["window_id"] = "WA"
                archive.archive_failure(data_root=root / "data", row=retained,
                    failure_kind="timeout", message="SYNTHETIC_OTHER_SCOPE",
                    failed_at_utc="2026-10-06T02:00:00Z")
                if mode == "valid":
                    retry = executor._clone_retry_row(google, 2)
                    archive.archive_retry_link(data_root=root / "data",
                        original_attempt_id=google["attempt_id"], retry_attempt_id=retry["attempt_id"],
                        site_id="JP01", wave_id="MIBO2-W01", protocol_version="2.0.2",
                        due_at_utc="2026-10-06T02:10:00Z", failure_kind="timeout")
                stack.enter_context(mock.patch.object(executor, "preflight", return_value=([selected], *checked[1:])))
                stack.enter_context(mock.patch.dict(os.environ, {"MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}))
                clock = stack.enter_context(mock.patch.object(executor, "datetime", wraps=datetime))
                clock.now.return_value = datetime(2026, 10, 6, 4, 0, tzinfo=timezone.utc)
                called = stack.enter_context(mock.patch.object(executor, "call_provider", side_effect=readiness_fixtures.RecoveryTests().result))
                def run():
                    return executor.execute(protocol_path=base / built["protocol_file"],
                        manifest_path=manifest, freeze_path=base / built["provider_freeze_file"],
                        authorization_path=authorization, data_root=root / "data")
                if mode.startswith("valid"):
                    self.assertEqual(run()["valid"], 1)
                    self.assertEqual(called.call_count, 1)
                    self.assertEqual(called.call_args.kwargs["provider"], "OpenAI")
                    wave = archive.wave_root(root / "data", "JP01", "MIBO2-W01", "2.0.2")
                    retry = executor._clone_retry_row(google, 2)
                    self.assertFalse((wave / "dispatch" / (retry["attempt_id"] + ".json")).exists())
                    if mode == "valid_without_link":
                        self.assertFalse((wave / "metadata" / ("retry-link-" + retry["attempt_id"] + ".json")).exists())
                else:
                    with self.assertRaises(ValueError):
                        run()
                    called.assert_not_called()


if __name__ == "__main__":
    unittest.main()
