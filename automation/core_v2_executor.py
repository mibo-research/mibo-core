#!/usr/bin/env python3
"""Fail-closed executor for prospectively registered API-only MIBO Core v2.0."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import core_v2_archive as archive
import core_v2_execution_state as execution_state
import core_v2_runner as runner
import mibo_runner as v1
from provider_adapters import AdapterFailure, call_provider
from retry_policy import decide_retry

EXECUTION_SENTINEL = "ENABLED_AFTER_CORE_V2_GATE"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_authorization(path: Path, *, protocol_path: Path, manifest_path: Path,
                       freeze_path: Path, protocol: dict[str, Any], wave_id: str,
                       site_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = protocol["protocol_version"]
    if data.get("schema_version") != version or data.get("protocol_version") != version:
        raise ValueError("Core v2 authorization schema/protocol version mismatch")
    if data.get("protocol_registration_id") != protocol.get("protocol_registration_id"):
        raise ValueError("Core v2 authorization registration ID mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("Core v2 authorization wave/site mismatch")
    for field in (
        "authorized", "protocol_finalized", "prospective_registration_complete",
        "terms_review_complete", "model_freeze_complete",
        "synthetic_dry_run_complete", "authorize_confirmatory_api_core",
    ):
        if data.get(field) is not True:
            raise ValueError(f"Core v2 authorization gate {field} is not true")
    if not data.get("operations_lead") or not data.get("authorized_at_utc"):
        raise ValueError("Core v2 authorization requires operations_lead and authorized_at_utc")
    if version in runner.AGENT_PROTOCOL_VERSIONS:
        for field in ("prospective_agent_amendment_reviewed", "late_activation_with_original_windows_approved"):
            if data.get(field) is not True:
                raise ValueError(f"Core v2 authorization gate {field} is not true")
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        authorized_at = runner.parse_aware_utc(data["authorized_at_utc"])
        if authorized_at < runner.parse_aware_utc(freeze["frozen_at_utc"]):
            raise ValueError("Agent authorization cannot predate the new freeze")
    expected_hashes = {
        "protocol_file_sha256": sha256_file(protocol_path),
        "manifest_sha256": sha256_file(manifest_path),
        "provider_freeze_sha256": sha256_file(freeze_path),
    }
    for field, expected in expected_hashes.items():
        if data.get(field) != expected:
            raise ValueError(f"Core v2 authorization {field} mismatch")
    if version in runner.SCOPED_PROTOCOL_VERSIONS:
        import core_v2_admission as admission
        admission.validate_authorization(data, protocol_path=protocol_path,
            freeze_path=freeze_path, protocol=protocol,
            freeze=json.loads(freeze_path.read_text()))
    return data


def _validate_credentials(rows: list[dict[str, Any]], freeze: dict[str, Any]) -> None:
    for row in rows:
        profile = freeze["core_api"][row["service_lineage_id"]]["request_profile"]
        env_name = profile["api_key_env"]
        if not os.environ.get(env_name):
            raise ValueError(f"required credential environment variable {env_name} is not set")


def preflight(*, protocol_path: Path, manifest_path: Path, freeze_path: Path,
              authorization_path: Path, data_root: Path,
              now: datetime | None = None, require_credentials: bool = False
              ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], datetime, datetime]:
    validated_hashes = {path: sha256_file(path) for path in (
        protocol_path, manifest_path, freeze_path, authorization_path)}
    protocol, _ = runner.load_protocol(protocol_path)
    rows = runner.read_csv(manifest_path)
    errors = runner.validate_manifest(rows, protocol_path=protocol_path, freeze_path=freeze_path)
    if errors:
        raise ValueError("Core v2 manifest validation failed: " + "; ".join(errors))
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    freeze, _ = runner.load_freeze(
        freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id,
    )
    authorization = load_authorization(
        authorization_path, protocol_path=protocol_path,
        manifest_path=manifest_path, freeze_path=freeze_path,
        protocol=protocol, wave_id=wave_id, site_id=site_id,
    )
    if protocol["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
        rows = [r for r in rows if r["service_lineage_id"] in authorization["admitted_lineages"]]
    if require_credentials:
        _validate_credentials(rows, freeze)
    wave_cfg = runner.wave(protocol, wave_id)
    start = parse_utc(wave_cfg["start_utc"])
    close = parse_utc(wave_cfg["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not (start <= current < close):
        raise ValueError("current time is outside the prospectively registered Core v2 field window")
    if current < runner.parse_aware_utc(authorization["authorized_at_utc"]):
        raise ValueError("Core v2 execution cannot precede human authorization")
    version = protocol["protocol_version"]
    if version in runner.AGENT_PROTOCOL_VERSIONS:
        prior_versions = [runner.PROTOCOL_VERSION]
        if version in runner.SCOPED_PROTOCOL_VERSIONS:
            prior_versions.append(runner.AGENT_PROTOCOL_VERSION)
        for prior in prior_versions:
            legacy_root = archive.wave_root(data_root, site_id, wave_id, prior)
            if version == runner.STANDARD_PROTOCOL_VERSION:
                import core_v2_standard
                core_v2_standard.block_prior_google_attempts(data_root, site_id, wave_id)
                break
            if version == runner.PRIORITY_PROTOCOL_VERSION:
                import core_v2_priority
                core_v2_priority.block_prior_google_attempts(data_root, site_id, wave_id)
                break
            if any(next((legacy_root / folder).glob("*.json"), None) is not None
                   for folder in ("api_raw", "failures")):
                raise ValueError("prior wave already has retained attempts; no mid-wave amendment")
    root = archive.wave_root(data_root, site_id, wave_id, version)
    root.mkdir(parents=True, exist_ok=True)
    probe = root / ".write-test"
    with probe.open("x", encoding="utf-8") as fh:
        fh.write("ok")
    probe.unlink()
    if any(sha256_file(path) != digest for path, digest in validated_hashes.items()):
        raise ValueError("frozen execution input changed during preflight")
    authorization["_validated_authorization_sha256"] = validated_hashes[authorization_path]
    return rows, freeze, authorization, start, close


def _prompt_map() -> dict[str, str]:
    return {f["query_form_id"]: f["text"] for f in v1._forms()}


def _row_bounds(protocol: dict[str, Any], row: dict[str, Any]) -> tuple[datetime, datetime]:
    wave_cfg = runner.wave(protocol, row["wave_id"])
    field_start = parse_utc(wave_cfg["start_utc"])
    field_close = parse_utc(wave_cfg["close_utc"])
    window_id = row["window_id"]
    if window_id == "STD":
        return field_start, field_close
    key = {"WA": "window_a", "WB": "window_b"}.get(window_id)
    window = wave_cfg.get(key) if key else None
    if not isinstance(window, dict):
        raise ValueError(f"Core v2 row uses unavailable window {window_id}")
    return (
        field_start + timedelta(hours=int(window["start_offset_hours"])),
        field_start + timedelta(hours=int(window["end_offset_hours"])),
    )


def _clone_retry_row(row: dict[str, Any], next_attempt: int) -> dict[str, Any]:
    service = next(s for s in v1._services() if s["service_lineage_id"] == row["service_lineage_id"])
    clone = dict(row)
    clone["retry_of_attempt_id"] = row["attempt_id"]
    clone["attempt"] = next_attempt
    clone["attempt_id"] = runner.attempt_id(
        row["site_id"], row["wave_id"], service["short_id"], row["item_id"],
        row["language"], row["window_id"], int(row["replication"]), next_attempt,
    )
    clone["status"] = "retry_intended_confirmatory_api"
    return clone


def _processed_attempt_ids(data_root: Path, site_id: str, wave_id: str,
                           protocol_version: str = runner.PROTOCOL_VERSION) -> set[str]:
    root = archive.wave_root(data_root, site_id, wave_id, protocol_version)
    return execution_state.processed_attempt_ids(root)


def _existing_retry_rows(data_root: Path, initial_rows: list[dict[str, Any]]) -> list[tuple[datetime, dict[str, Any]]]:
    site_id = initial_rows[0]["site_id"]
    wave_id = initial_rows[0]["wave_id"]
    version = initial_rows[0]["protocol_version"]
    metadata = archive.wave_root(data_root, site_id, wave_id, version) / "metadata"
    if not metadata.exists():
        return []
    row_map = {r["attempt_id"]: r for r in initial_rows}
    links: list[dict[str, Any]] = []
    for path in metadata.glob("retry-link-*.json"):
        links.append(execution_state._read(path))
    for _ in range(3):
        changed = False
        for link in links:
            original = row_map.get(link.get("original_attempt_id"))
            target = link.get("retry_attempt_id")
            if original is None or not target or target in row_map:
                continue
            if int(original["attempt"]) >= 3:
                raise ValueError("stored Core v2 retry exceeds maximum of two retries")
            clone = _clone_retry_row(original, int(original["attempt"]) + 1)
            if clone["attempt_id"] != target:
                raise ValueError("stored Core v2 retry link does not match deterministic Attempt ID")
            row_map[target] = clone
            changed = True
        if not changed:
            break
    done = _processed_attempt_ids(data_root, site_id, wave_id, version)
    if any(link.get("retry_attempt_id") not in row_map for link in links):
        raise ValueError("stored Core v2 retry link has an unregistered or cyclic parent")
    return [
        (parse_utc(link["due_at_utc"]), row_map[link["retry_attempt_id"]])
        for link in links
        if link.get("retry_attempt_id") in row_map and link["retry_attempt_id"] not in done
    ]


def execute(*, protocol_path: Path, manifest_path: Path, freeze_path: Path,
            authorization_path: Path, data_root: Path,
            timeout_s: int = 180) -> dict[str, int]:
    if os.environ.get("MIBO_CORE_V2_EXECUTION") != EXECUTION_SENTINEL:
        raise RuntimeError("Core v2 provider execution sentinel is not enabled")
    rows, freeze, _auth, _start, field_close = preflight(
        protocol_path=protocol_path, manifest_path=manifest_path,
        freeze_path=freeze_path, authorization_path=authorization_path,
        data_root=data_root, require_credentials=True,
    )
    root = archive.wave_root(data_root, rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"])
    locked_identity = (rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"],
                       {row["attempt_id"] for row in rows})
    with execution_state.lineage_locks(data_root, rows[0]["site_id"], rows[0]["wave_id"],
                                       {row["service_lineage_id"] for row in rows}):
        with execution_state.wave_lock(root):
            # A different namespace can retain an attempt while this process
            # waits for a lock. Re-run the frozen gates inside both locks.
            rows, freeze, _auth, _start, field_close = preflight(
                protocol_path=protocol_path, manifest_path=manifest_path,
                freeze_path=freeze_path, authorization_path=authorization_path,
                data_root=data_root, require_credentials=True)
            identity = (rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"],
                        {row["attempt_id"] for row in rows})
            if identity != locked_identity:
                raise ValueError("execution scope changed while acquiring durable locks")
            _block_other_namespace_attempts(data_root, rows)
            return _execute_locked(protocol_path=protocol_path, manifest_path=manifest_path,
                freeze_path=freeze_path, authorization_path=authorization_path,
                data_root=data_root, timeout_s=timeout_s,
                rows=rows, freeze=freeze, authorization=_auth, field_close=field_close)


def _block_other_namespace_attempts(data_root: Path, rows: list[dict[str, Any]]) -> None:
    site, wave, version = (rows[0][key] for key in ("site_id", "wave_id", "protocol_version"))
    lineages = {row["service_lineage_id"] for row in rows}
    services = v1._services()
    prefixes = {f"MIBO2-SITE-{site}-{wave.replace('MIBO2-', '')}-{service['short_id']}-{runner.LINE_ID}-":
                service['service_lineage_id'] for service in services}
    known_attempt_lineages = {}
    for row in rows:
        for attempt in (row, _clone_retry_row(row, 2), _clone_retry_row(_clone_retry_row(row, 2), 3)):
            known_attempt_lineages[attempt['attempt_id']] = attempt['service_lineage_id']
    for other_version in sorted(runner.SUPPORTED_PROTOCOL_VERSIONS - {version}):
        other = archive.wave_root(data_root, site, wave, other_version)
        for lineage in lineages:
            if (other / 'metadata' / ('first-dispatch-' + lineage + '.json')).exists():
                raise ValueError("another protocol namespace has retained lineage dispatch; no replay")
        for folder in ('api_raw', 'metadata', 'failures', 'dispatch'):
            if (other / folder).is_symlink():
                raise ValueError("other namespace state folder must not be a symlink")
            for path in (other / folder).glob('*.json'):
                if folder == 'metadata' and path.name.startswith(('retry-link-', 'first-dispatch-')):
                    continue
                filename_sid = known_attempt_lineages.get(path.stem) or next(
                    (sid for prefix, sid in prefixes.items() if path.stem.startswith(prefix)), None)
                if folder == 'api_raw':
                    sid = filename_sid
                else:
                    record = execution_state._read(path)
                    if record.get('attempt_id') != path.stem:
                        raise ValueError("other namespace retained attempt filename/identity conflict")
                    embedded_sid = record.get('service_lineage_id')
                    if embedded_sid is not None and embedded_sid != filename_sid:
                        raise ValueError("other namespace retained attempt filename/lineage conflict")
                    sid = filename_sid
                if sid is None:
                    raise ValueError("other namespace retained attempt cannot be classified by lineage")
                if sid in lineages:
                    raise ValueError("another protocol namespace has retained lineage attempt; no replay")


def _execute_locked(*, protocol_path: Path, manifest_path: Path,
                    freeze_path: Path,
                    authorization_path: Path, data_root: Path, timeout_s: int,
                    rows: list[dict[str, Any]], freeze: dict[str, Any],
                    authorization: dict[str, Any], field_close: datetime) -> dict[str, int]:
    _auth = authorization
    root = archive.wave_root(data_root, rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"])
    authorization_digest = sha256_file(authorization_path)
    if ("_validated_authorization_sha256" in _auth and
            _auth["_validated_authorization_sha256"] != authorization_digest):
        raise ValueError("authorization changed after validated preflight")
    pinned_inputs = {path: sha256_file(path) for path in (
        protocol_path, manifest_path, freeze_path, authorization_path)}
    for field, path in (("protocol_file_sha256", protocol_path),
                        ("manifest_sha256", manifest_path),
                        ("provider_freeze_sha256", freeze_path)):
        if field in _auth and _auth[field] != pinned_inputs[path]:
            raise ValueError("frozen input changed after validated authorization")
    if rows[0]["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
        digest = sha256_file(authorization_path)
        record_path = archive.wave_root(data_root, rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"]) / "deviations" / ("ADMISSION-" + digest + ".json")
        if not record_path.exists():
            archive.write_deviation(data_root=data_root, site_id=rows[0]["site_id"],
                wave_id=rows[0]["wave_id"], protocol_version=rows[0]["protocol_version"],
                deviation_id="ADMISSION-" + digest, record={
                    "type": "human_authorized_lineage_admission",
                    "admitted_lineages": _auth["admitted_lineages"],
                    "authorization_sha256": digest,
                    "authorized_at_utc": _auth["authorized_at_utc"],
                    "executor_activated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "intended_manifest_rows": len(runner.read_csv(manifest_path)),
                    "authorized_manifest_rows": len(rows),
                    "readiness_report_sha256": _auth["readiness_report_sha256"]})
    prompts = _prompt_map()
    protocol, _ = runner.load_protocol(protocol_path)
    restored = execution_state.restore(root=root, initial_rows=rows,
        clone_retry=_clone_retry_row, row_bounds=lambda row: _row_bounds(protocol, row),
        data_root=data_root, authorization_sha256=authorization_digest,
        current=datetime.now(timezone.utc))
    done = restored.done
    now = datetime.now(timezone.utc)
    queue: list[tuple[datetime, int, str, dict[str, Any]]] = [
        (max(now, _row_bounds(protocol, row)[0]), int(row["execution_order"]), row["attempt_id"], row)
        for row in rows if row["attempt_id"] not in done
    ]
    for due, retry_row in restored.retries:
        queue.append((due, int(retry_row["execution_order"]), retry_row["attempt_id"], retry_row))
    summary = {
        "valid": 0, "already_processed": len(done), "failed_attempts": 0,
        "retries_scheduled": 0, "rate_limit_pauses": 0, "outage_pauses": 0,
        "lineage_suspensions": 0, "skipped_after_suspension": 0,
        "retained_lineage_suspensions": len(restored.suspended),
        "uncertain_dispatches": len(restored.uncertain),
    }
    pause_until: dict[str, datetime] = dict(restored.pause_until)
    suspended: set[str] = set(restored.suspended)
    recovery_attempt = dict(restored.recovery_attempt)
    def retain_expired(row: dict[str, Any], current: datetime, message: str) -> None:
        archive.archive_failure(data_root=data_root, row=row,
            failure_kind="window_expired_before_attempt", message=message,
            failed_at_utc=current.isoformat().replace("+00:00", "Z"))
        summary["failed_attempts"] += 1
        sid = row["service_lineage_id"]
        if recovery_attempt.get(sid) == row["attempt_id"]:
            suspended.add(sid)
            summary["lineage_suspensions"] += 1
            archive.write_deviation(data_root=data_root, site_id=row["site_id"],
                wave_id=row["wave_id"], protocol_version=row["protocol_version"],
                deviation_id="CORE-V2-RECOVERY-WINDOW-CLOSED-" + row["attempt_id"],
                record={"type": "lineage_suspended_after_retry_exhaustion",
                        "service_lineage_id": sid, "trigger_attempt_id": row["attempt_id"],
                        "rule": "registered recovery window closed; retain missingness; no blind queue submission"})
    while queue:
        queue.sort(key=lambda item: (item[0],
            0 if recovery_attempt.get(item[3]["service_lineage_id"]) == item[2] else 1,
            item[1], item[2]))
        due, order, _aid, row = queue.pop(0)
        lineage = row["service_lineage_id"]
        if lineage in suspended:
            summary["skipped_after_suspension"] += 1
            continue
        if lineage in recovery_attempt and row["attempt_id"] != recovery_attempt[lineage]:
            recovery_due = next((item[0] for item in queue if item[2] == recovery_attempt[lineage]), None)
            if recovery_due is None:
                raise ValueError("controlled lineage recovery has no queued retry")
            queue.append((max(due, recovery_due), order, row["attempt_id"], row))
            continue
        if pause_until.get(lineage) and due < pause_until[lineage]:
            queue.append((pause_until[lineage], order, row["attempt_id"], row))
            continue
        current = datetime.now(timezone.utc)
        _row_start, row_close = _row_bounds(protocol, row)
        if current >= field_close:
            break
        if current >= row_close:
            retain_expired(row, current, "registered row window closed before this attempt could start")
            continue
        if due > current:
            time.sleep(min((due - current).total_seconds(), max(0.0, (row_close - current).total_seconds())))
            current = datetime.now(timezone.utc)
            if current < max(due, _row_start):
                # Wall UTC can move backwards while monotonic sleep completes.
                # Recheck the registered lower bound instead of sending early.
                queue.append((max(due, _row_start), order, row["attempt_id"], row))
                continue
            if current >= row_close:
                retain_expired(row, current, "registered row window closed while the attempt was waiting")
                continue
        cfg = freeze["core_api"][lineage]
        if row["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
            dispatch = archive.wave_root(data_root, row["site_id"], row["wave_id"], row["protocol_version"]) / "metadata" / ("first-dispatch-" + lineage + ".json")
            if not dispatch.exists():
                archive._write_exclusive(dispatch, archive.canonical_json_bytes({
                    "protocol_version": row["protocol_version"],
                    "service_lineage_id": lineage,
                    "initial_attempt_id": row["attempt_id"],
                    "actual_observation_start_at_utc": datetime.now(timezone.utc).isoformat(),
                    "timestamp_kind": "collector_dispatch_to_provider_adapter",
                    "authorization_sha256": sha256_file(authorization_path)}))
        current = datetime.now(timezone.utc)
        if current < max(due, _row_start):
            queue.append((max(due, _row_start), order, row["attempt_id"], row))
            continue
        if current >= field_close:
            break
        if current >= row_close:
            retain_expired(row, current, "registered row window closed before durable dispatch claim")
            continue
        if any(sha256_file(path) != digest for path, digest in pinned_inputs.items()):
            raise ValueError("frozen execution input changed before dispatch")
        dispatched_at = current
        execution_state.claim_attempt(root, row,
            authorization_sha256=authorization_digest,
            dispatched_at=current)
        current = datetime.now(timezone.utc)
        if any(sha256_file(path) != digest for path, digest in pinned_inputs.items()):
            raise ValueError("frozen execution input changed during durable dispatch claim")
        if current < max(due, _row_start) or current >= min(row_close, field_close):
            # A clock step during durable filesystem I/O leaves an ambiguous
            # dispatch claim. Stop the lineage; never resend the claimed ID.
            suspended.add(lineage)
            summary["lineage_suspensions"] += 1
            summary["uncertain_dispatches"] += 1
            archive.write_deviation(data_root=data_root, site_id=row["site_id"],
                wave_id=row["wave_id"], protocol_version=row["protocol_version"],
                deviation_id="CORE-V2-UNCERTAIN-DISPATCH-" + row["attempt_id"],
                record={"type": "lineage_suspended_for_uncertain_dispatch",
                        "service_lineage_id": lineage,
                        "trigger_attempt_id": row["attempt_id"],
                        "rule": "clock left registered dispatch bounds; retain claim; no automatic resend"})
            continue
        try:
            result = call_provider(
                provider=row["provider"], model_id=row["model_id"],
                prompt=prompts[row["query_form_id"]],
                profile=cfg["request_profile"], timeout_s=timeout_s,
                **({"capture_response_metadata": True} if row["provider"] == "Google" else {}),
            )
        except AdapterFailure as exc:
            failed_at = datetime.now(timezone.utc)
            archive.archive_failure(
                data_root=data_root, row=row, failure_kind=exc.kind,
                message=exc.message, failed_at_utc=failed_at.isoformat().replace("+00:00", "Z"),
                http_status=exc.http_status, retry_after_seconds=exc.retry_after_seconds,
                response_body=exc.response_body, response_metadata=exc.response_metadata,
            )
            summary["failed_attempts"] += 1
            decision = decide_retry(
                attempt=int(row["attempt"]), failure_kind=exc.kind,
                failed_at=failed_at, provider_retry_after_seconds=exc.retry_after_seconds,
                field_close=row_close,
            )
            retry_due: datetime | None = None
            if decision.retry:
                retry_row = _clone_retry_row(row, int(decision.next_attempt))
                archive.archive_retry_link(
                    data_root=data_root, original_attempt_id=row["attempt_id"],
                    retry_attempt_id=retry_row["attempt_id"], site_id=row["site_id"],
                    wave_id=row["wave_id"], due_at_utc=str(decision.due_at_utc),
                    failure_kind=exc.kind,
                    protocol_version=row["protocol_version"],
                )
                retry_due = parse_utc(str(decision.due_at_utc))
                queue.append((retry_due, order, retry_row["attempt_id"], retry_row))
                summary["retries_scheduled"] += 1
                if lineage not in recovery_attempt and exc.http_status in {429, 502, 503, 504}:
                    execution_state.record_recovery_block(data_root, row,
                        retry_id=retry_row["attempt_id"], due=retry_due, http_status=exc.http_status)
                if lineage in recovery_attempt or exc.http_status in {429, 502, 503, 504}:
                    recovery_attempt[lineage] = retry_row["attempt_id"]
            if exc.http_status == 429 and retry_due is not None:
                pause_until[lineage] = retry_due
                summary["rate_limit_pauses"] += 1
            if exc.http_status in {502, 503, 504} or (
                    retry_due is None and (exc.http_status == 429 or lineage in recovery_attempt)):
                if retry_due is not None:
                    pause_until[lineage] = retry_due
                    summary["outage_pauses"] += 1
                else:
                    suspended.add(lineage)
                    summary["lineage_suspensions"] += 1
                    deviation_id = f"CORE-V2-LINEAGE-SUSPEND-{lineage}-{int(failed_at.timestamp())}"
                    archive.write_deviation(
                        data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"],
                        deviation_id=deviation_id,
                        record={"deviation_id": deviation_id,
                                "type": "lineage_suspended_after_retry_exhaustion",
                                "service_lineage_id": lineage,
                                "trigger_attempt_id": row["attempt_id"],
                                "rule": "retain missingness; do not substitute provider or model"},
                        protocol_version=row["protocol_version"],
                    )
            if exc.kind == "request_environment_mismatch":
                suspended.add(lineage)
                summary["lineage_suspensions"] += 1
                archive.write_deviation(
                    data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"],
                    deviation_id=f"CORE-V2-ENVIRONMENT-MISMATCH-{row['attempt_id']}",
                    record={"type": "lineage_suspended_for_environment_mismatch",
                            "service_lineage_id": lineage, "trigger_attempt_id": row["attempt_id"],
                            "rule": "retain response; no retry, model substitution, or blind queue submission"},
                    protocol_version=row["protocol_version"],
                )
            continue
        capture = archive.archive_success(
            data_root=data_root, row=row, request_payload=result.request_payload,
            response_json=result.response_json, raw_response_text=result.raw_response_text,
            http_status=result.http_status, returned_model=result.returned_model,
            usage=result.usage, started_at_utc=result.started_at_utc,
            completed_at_utc=result.completed_at_utc, duration_ms=result.duration_ms,
            response_metadata=result.response_metadata,
        )
        # Retain the provider bytes first, then stop before another request if
        # their technical sidecar cannot prove a protocol-eligible capture.
        execution_state.validate_capture(capture, row,
            bounds=_row_bounds(protocol, row), current=datetime.now(timezone.utc),
            retry_due=due if int(row["attempt"]) > 1 else None,
            dispatched_at=dispatched_at)
        if recovery_attempt.get(lineage) == row["attempt_id"]:
            recovery_attempt.pop(lineage)
        summary["valid"] += 1
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if not args.execute:
        rows, _freeze, _auth, start, close = preflight(
            protocol_path=args.protocol, manifest_path=args.manifest,
            freeze_path=args.freeze, authorization_path=args.authorization,
            data_root=args.data_root, require_credentials=False,
        )
        print(json.dumps({
            "preflight": "PASS", "protocol_version": rows[0]["protocol_version"],
            "scientific_class": runner.SCIENTIFIC_CLASS, "rows": len(rows),
            "field_start": start.isoformat(), "field_close": close.isoformat(),
        }, indent=2))
        return 0
    summary = execute(
        protocol_path=args.protocol, manifest_path=args.manifest,
        freeze_path=args.freeze, authorization_path=args.authorization,
        data_root=args.data_root, timeout_s=args.timeout,
    )
    # A normal process exit does not certify that all planned observations were
    # captured. Incomplete scientific collection remains visible to systemd.
    from core_v2_status import build_report
    try:
        report = build_report(protocol_path=args.protocol, manifest_path=args.manifest,
            freeze_path=args.freeze, data_root=args.data_root,
            authorization_path=args.authorization)
        report.pop("cells", None)
        report.pop("dimension_counts", None)
        print(json.dumps({"execution": summary, "completion": report}, indent=2))
        return 1 if not report["integrity_pass"] else 0 if report["scientific_collection_complete"] else 2
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"execution": summary, "completion": {
            "status": "INTEGRITY_ERROR", "scientific_collection_complete": False,
            "error": "completion state could not be verified"}}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
