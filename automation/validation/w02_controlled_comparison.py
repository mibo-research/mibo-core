"""Disclosure-safe software control: identical synthetic public entry points.

No network calls: credential/preflight checks and provider adapters are mocked.
This compares engineering safeguards only, not live readiness or W01 causes.
"""
from contextlib import ExitStack
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo / "automation"), str(repo / "automation/tests")]
import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_runner as runner
import core_v2_priority as priority
import core_v2_standard as standard
from provider_adapters import AdapterFailure
from test_core_v2_api import CoreV2Fixture

results = {"network": "disabled by mocked provider adapter", "cases": {}}

class Fixture:
    def __init__(self, base):
        self.base = Path(base)
        self.fixture = CoreV2Fixture(self.base)
        self.freeze = json.loads(self.fixture.freeze.read_text())
        self.freeze["wave_id"] = "MIBO2-W02"
        self.fixture.freeze.write_text(json.dumps(self.freeze))
        self.rows = runner.generate_manifest(protocol_path=self.fixture.protocol,
            freeze_path=self.fixture.freeze, wave_id="MIBO2-W02", site_id="JP01")
        self.selected = [r for r in self.rows if r["provider"] == "Google"][:2]
        self.start = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.clock = self.start
        self.close = self.start + timedelta(hours=48)
        self.data = self.base / "data"
        self.root = archive.wave_root(self.data, "JP01", "MIBO2-W02")
        self.calls = []

    def success(self, **kwargs):
        self.calls.append(kwargs["provider"])
        stamp = self.clock.isoformat()
        return SimpleNamespace(request_payload={"model": kwargs["model_id"]},
            response_json={"synthetic": True}, raw_response_text='{"synthetic":true}',
            http_status=200, returned_model=kwargs["model_id"], usage={},
            started_at_utc=stamp, completed_at_utc=stamp, duration_ms=0,
            response_metadata=None)

    def execute(self, callback=None):
        owner = self
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return owner.clock
        def sleep(seconds):
            owner.clock += timedelta(seconds=seconds)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, {
                "MIBO_CORE_V2_EXECUTION": executor.EXECUTION_SENTINEL}))
            stack.enter_context(mock.patch.object(executor, "datetime", Clock))
            stack.enter_context(mock.patch.object(archive, "datetime", Clock))
            stack.enter_context(mock.patch.object(executor.time, "sleep", side_effect=sleep))
            stack.enter_context(mock.patch.object(executor, "preflight", return_value=(
                self.selected, self.freeze, {}, self.start, self.close)))
            stack.enter_context(mock.patch.object(executor, "_prompt_map", return_value={
                row["query_form_id"]: "SYNTHETIC" for row in self.selected}))
            stack.enter_context(mock.patch.object(executor, "call_provider",
                side_effect=callback or self.success))
            return executor.execute(protocol_path=self.fixture.protocol,
                manifest_path=self.fixture.manifest, freeze_path=self.fixture.freeze,
                authorization_path=self.fixture.authorization, data_root=self.data)

for case in ("deterministic_order", "ambiguous_prior_namespace_dispatch", "retained_environment_mismatch", "contradictory_prior_failure_sid"):
    with tempfile.TemporaryDirectory() as td:
        f = Fixture(td)
        if case == "deterministic_order":
            changed = copy.deepcopy(f.rows)
            changed[0]["execution_order"], changed[1]["execution_order"] = (
                changed[1]["execution_order"], changed[0]["execution_order"])
            errors = runner.validate_manifest(changed,
                protocol_path=f.fixture.protocol, freeze_path=f.fixture.freeze)
            results["cases"][case] = {"rejected": bool(errors), "errors": errors}
        elif case == "ambiguous_prior_namespace_dispatch":
            path = archive.wave_root(f.data, "JP01", "MIBO2-W02", "2.0.4") / "dispatch" / (f.selected[0]["attempt_id"] + ".json")
            path.parent.mkdir(parents=True)
            row = f.selected[0]
            path.write_text(json.dumps({**row, "protocol_version": "2.0.4",
                "type": "attempt_dispatch_claim", "dispatched_at_utc": f.start.isoformat()}))
            error = None
            try:
                f.execute()
            except (ValueError, RuntimeError) as exc:
                error = str(exc)
            results["cases"][case] = {"blocked": error is not None,
                "mock_adapter_calls": len(f.calls), "error": error}
        elif case == "retained_environment_mismatch":
            def mismatch(**kwargs):
                f.calls.append(kwargs["provider"])
                raise AdapterFailure(kind="request_environment_mismatch", message="SYNTHETIC")
            f.execute(mismatch)
            first_calls = len(f.calls)
            error = None
            try:
                f.execute()
            except (ValueError, RuntimeError) as exc:
                error = str(exc)
            results["cases"][case] = {"first_mock_adapter_calls": first_calls,
                "restart_mock_adapter_calls": len(f.calls) - first_calls, "error": error}
        else:
            row = f.selected[0]
            path = archive.wave_root(f.data, "JP01", "MIBO2-W02", "2.0.4") / "failures" / (row["attempt_id"] + ".json")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({**row, "protocol_version": "2.0.4",
                "service_lineage_id": "MIBO-SL-001", "failure_kind": "timeout",
                "failed_at_utc": f.start.isoformat()}))
            error = None
            try:
                f.execute()
            except (ValueError, RuntimeError) as exc:
                error = str(exc)
            results["cases"][case] = {"blocked": error is not None,
                "mock_adapter_calls": len(f.calls), "error": error}

print(json.dumps(results, indent=2, sort_keys=True))
