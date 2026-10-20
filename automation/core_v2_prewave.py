#!/usr/bin/env python3
"""Offline deployment gates for an authorized Core v2 wave, before its start.

This verifies local files and runtime state only. It never discovers models,
contacts providers, manufactures authorization, or creates observation files.
The same gates are checked again by the waiter immediately before dispatch.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
from typing import Any

import core_v2_archive as archive
import core_v2_executor as executor
import core_v2_runner as runner
import runtime_health

MIN_FREE_BYTES = 2 * 1024 ** 3


def input_hashes(*, protocol_path: Path, manifest_path: Path, freeze_path: Path,
                 authorization_path: Path) -> dict[str, str]:
    return {
        "protocol_file_sha256": runner.sha256_file(protocol_path),
        "manifest_sha256": runner.sha256_file(manifest_path),
        "provider_freeze_sha256": runner.sha256_file(freeze_path),
        "authorization_sha256": runner.sha256_file(authorization_path),
    }


def _regular_input(path: Path) -> None:
    if (not path.is_absolute() or not path.is_file()
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError("prewave inputs must be existing absolute regular files")


def _runtime_gate(*, repo_root: Path, data_root: Path, expected_host: str | None,
                  expected_source_commit: str | None, strict_runtime: bool) -> dict[str, Any]:
    if strict_runtime and (not expected_host or not expected_source_commit):
        raise ValueError("strict runtime validation requires an explicit host and source commit")
    host = socket.gethostname().split(".", 1)[0]
    if expected_host and host != expected_host:
        raise ValueError("controlled runtime hostname mismatch; use the observation VM, not Cloud Shell")
    provenance = None
    if expected_source_commit:
        if not re.fullmatch(r"[0-9a-f]{40}", expected_source_commit):
            raise ValueError("expected source commit must be a full lowercase 40-hex SHA")
        provenance = runtime_health.provenance_state(repo_root)
        if (provenance.get("commit_sha") != expected_source_commit
                or provenance.get("commit_resolved") is not True
                or provenance.get("working_tree_clean") is not True):
            raise ValueError("reviewed source commit or installed source integrity mismatch")
    clock = runtime_health.ntp_state()
    if clock.get("ntp_synchronized") is False:
        raise ValueError("controlled runtime UTC clock is not synchronized")
    if strict_runtime and (clock.get("check_available") is not True
                           or clock.get("ntp_synchronized") is not True):
        raise ValueError("strict runtime validation requires verified UTC clock synchronization")
    free = shutil.disk_usage(data_root).free
    if free < MIN_FREE_BYTES:
        raise ValueError("less than 2 GiB free in configured data store")
    return {"host": host, "expected_host": expected_host,
            "expected_source_commit": expected_source_commit,
            "provenance": provenance, "clock": clock, "free_bytes": free,
            "strict_runtime": strict_runtime,
            "manual_clock_verification_required": clock.get("check_available") is not True}


def _storage_gate(*, data_root: Path, protocol_version: str, site_id: str,
                  wave_id: str, before_start: bool) -> None:
    current_root = archive.wave_root(data_root, site_id, wave_id, protocol_version)
    versions = runner.SUPPORTED_PROTOCOL_VERSIONS if before_start else {protocol_version}
    for version in sorted(versions):
        root = archive.wave_root(data_root, site_id, wave_id, version)
        for component in (root, *root.parents):
            if component == data_root:
                break
            if component.is_symlink():
                raise ValueError("wave namespace contains a symlink alias")
        if not root.resolve().is_relative_to(data_root.resolve()):
            raise ValueError("wave namespace escapes the configured data store")
        if root.exists() and any(path.is_symlink() for path in root.rglob("*")):
            raise ValueError("wave storage contains a symlink alias")
        if (root / "SHA256SUMS.txt").exists() or (root / "closure").exists():
            raise ValueError("wave namespace is already closed or sealed")
        if before_start and any(next((root / folder).glob("*.json"), None) is not None
                                for folder in ("api_raw", "failures")):
            raise ValueError("retained wave attempts exist before the registered start")
    # Check the actual service user's permissions without a root-owned namespace
    # or fixed-name write test. All probe files are removed before returning.
    parent = current_root
    while not parent.exists():
        parent = parent.parent
    if not parent.is_dir():
        raise ValueError("wave namespace ancestor is not a directory")
    with tempfile.TemporaryDirectory(prefix=".mibo-prewave-", dir=parent) as tmp:
        path = Path(tmp) / "write-probe"
        with path.open("xb") as handle:
            handle.write(b"offline deployment write probe\n")
            handle.flush()
            os.fsync(handle.fileno())


def validate_prewave(*, protocol_path: Path, manifest_path: Path, freeze_path: Path,
                     authorization_path: Path, data_root: Path, wave_id: str,
                     site_id: str = "JP01", now: datetime | None = None,
                     repo_root: Path | None = None, expected_host: str | None = None,
                     expected_source_commit: str | None = None,
                     strict_runtime: bool = False) -> dict[str, Any]:
    """Validate the real current prestart/runtime state without provider calls.

    ``now`` is injectable for synthetic tests only; the CLI always uses the real
    clock. This does not authorize calls before the executor's field-window gate.
    """
    for path in (protocol_path, manifest_path, freeze_path, authorization_path):
        _regular_input(path)
    if not data_root.is_absolute() or not data_root.is_dir():
        raise ValueError("configured data root must be an existing absolute directory")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", site_id):
        raise ValueError("invalid expected site identifier")
    if os.environ.get("MIBO_CORE_V2_EXECUTION") != executor.EXECUTION_SENTINEL:
        raise ValueError("Core v2 provider execution sentinel is not enabled")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("prewave clock must be timezone-aware")
    current = current.astimezone(timezone.utc)
    protocol, _ = runner.load_protocol(protocol_path)
    bounds = runner.wave(protocol, wave_id)
    start = runner.parse_aware_utc(bounds["start_utc"])
    close = runner.parse_aware_utc(bounds["close_utc"])
    if current >= close:
        raise ValueError("prospectively registered Core v2 field window has closed")
    rows = runner.read_csv(manifest_path)
    if not rows or any(row.get("wave_id") != wave_id or row.get("site_id") != site_id
                       for row in rows):
        raise ValueError("waiter wave/site does not match the supplied manifest")
    errors = runner.validate_manifest(rows, protocol_path=protocol_path, freeze_path=freeze_path)
    if errors:
        raise ValueError("Core v2 manifest validation failed: " + "; ".join(errors))
    regenerated = runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path,
                                          wave_id=wave_id, site_id=site_id)
    if rows != regenerated:
        raise ValueError("strict deterministic manifest comparison failed")
    freeze, _ = runner.load_freeze(freeze_path, protocol=protocol,
                                  wave_id=wave_id, site_id=site_id)
    auth = executor.load_authorization(authorization_path, protocol_path=protocol_path,
        manifest_path=manifest_path, freeze_path=freeze_path, protocol=protocol,
        wave_id=wave_id, site_id=site_id)
    frozen_at = runner.parse_aware_utc(freeze["frozen_at_utc"])
    authorized_at = runner.parse_aware_utc(auth["authorized_at_utc"])
    if frozen_at > authorized_at or authorized_at > current:
        raise ValueError("freeze/authorization timestamps must precede the real current check")
    admitted = rows
    if protocol["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
        admitted = [row for row in rows if row["service_lineage_id"] in auth["admitted_lineages"]]
    executor._validate_credentials(admitted, freeze)
    runtime = _runtime_gate(repo_root=repo_root or Path(__file__).resolve().parents[1],
        data_root=data_root, expected_host=expected_host,
        expected_source_commit=expected_source_commit, strict_runtime=strict_runtime)
    _storage_gate(data_root=data_root, protocol_version=protocol["protocol_version"],
                  site_id=site_id, wave_id=wave_id, before_start=current < start)
    return {"prewave": "PASS", "checked_at_utc": current.isoformat().replace("+00:00", "Z"),
            "phase": "armed_before_registered_start" if current < start else "within_registered_window",
            "wave_id": wave_id, "site_id": site_id,
            "protocol_version": protocol["protocol_version"],
            "registered_start_utc": bounds["start_utc"], "registered_close_utc": bounds["close_utc"],
            "intended_initial_cells": len(rows), "admitted_initial_cells": len(admitted),
            "intended_cells_by_lineage": dict(Counter(r["service_lineage_id"] for r in rows)),
            "admitted_cells_by_lineage": dict(Counter(r["service_lineage_id"] for r in admitted)),
            "strict_deterministic_manifest_comparison_passed": True,
            "credentials_values_recorded": False, "provider_calls_made": 0,
            "observation_files_created": False, "runtime": runtime,
            "input_hashes": input_hashes(protocol_path=protocol_path, manifest_path=manifest_path,
                freeze_path=freeze_path, authorization_path=authorization_path)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--expected-host")
    p.add_argument("--expected-source-commit")
    p.add_argument("--strict-runtime", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = validate_prewave(protocol_path=args.protocol, manifest_path=args.manifest,
        freeze_path=args.freeze, authorization_path=args.authorization, data_root=args.data_root,
        wave_id=args.wave, site_id=args.site, expected_host=args.expected_host,
        expected_source_commit=args.expected_source_commit, strict_runtime=args.strict_runtime)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
