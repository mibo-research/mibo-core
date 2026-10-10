#!/usr/bin/env python3
"""Local technical monitoring for one authorized collector; no provider calls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import core_v2_runner as runner
from core_v2_status import build_report, service_states
import runtime_health


def assess(*, completion: dict, services: dict, before_close: bool,
           free_bytes: int, clock: dict) -> dict:
    """Operational attention is independent of whether the process exited 0."""
    reasons = []
    if not completion["integrity_pass"]:
        reasons.append("retained_state_integrity_failed")
    if completion["status"] == "SUSPENDED":
        reasons.append("lineage_suspended_or_dispatch_uncertain")
    if free_bytes < 2 * 1024 ** 3:
        reasons.append("data_store_free_space_below_2_GiB")
    if clock.get("check_available") is not True or clock.get("ntp_synchronized") is not True:
        reasons.append("UTC_clock_synchronization_unverified")
    if not completion["scientific_collection_complete"]:
        if not before_close:
            reasons.append("registered_window_closed_with_missing_cells")
        for state in services.values():
            if not state.get("available"):
                reasons.append("collector_service_state_unavailable")
            elif before_close and (state.get("ActiveState") != "active"
                                   or state.get("MainPID") in {None, "", "0"}):
                reasons.append("collector_not_running_with_missing_cells")
    return {"monitor_status": "ATTENTION_REQUIRED" if reasons else "OK",
            "attention_reasons": sorted(set(reasons)), "completion": completion,
            "services": services, "data_store_free_bytes": free_bytes,
            "clock_synchronized": clock.get("ntp_synchronized") is True,
            "automatic_recovery_performed": False, "provider_calls_made": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("protocol", "manifest", "freeze", "authorization", "data-root"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--site", default="JP01")
    parser.add_argument("--unit", required=True, action="append")
    args = parser.parse_args()
    try:
        now = datetime.now(timezone.utc)
        completion = build_report(protocol_path=args.protocol, manifest_path=args.manifest,
            freeze_path=args.freeze, authorization_path=args.authorization, data_root=args.data_root,
            current=now, expected_wave=args.wave, expected_site=args.site)
        completion.pop("cells")
        completion.pop("dimension_counts")
        protocol, _ = runner.load_protocol(args.protocol)
        close = runner.parse_aware_utc(runner.wave(protocol, args.wave)["close_utc"])
        report = assess(completion=completion, services=service_states(args.unit),
                        before_close=now < close, free_bytes=shutil.disk_usage(args.data_root).free,
                        clock=runtime_health.ntp_state())
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0 if report["monitor_status"] == "OK" else 1
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"monitor_status": "ATTENTION_REQUIRED",
            "attention_reasons": ["monitor_inputs_could_not_be_verified"],
            "automatic_recovery_performed": False, "provider_calls_made": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
