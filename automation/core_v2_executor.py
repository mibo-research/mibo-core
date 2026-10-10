#!/usr/bin/env python3
"""Fail-closed executor for prospectively registered API-only MIBO Core v2.0."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import core_v2_archive as archive
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
    version = protocol["protocol_version"]
    if version in runner.AGENT_PROTOCOL_VERSIONS:
        if current < runner.parse_aware_utc(authorization["authorized_at_utc"]):
            raise ValueError("Agent execution cannot precede human authorization")
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
                   for folder in ("api_raw", "failures", "dispatch")) or next(
                       (legacy_root / "metadata").glob("first-dispatch-*.json"), None) is not None:
                raise ValueError("prior wave already has retained attempts; no mid-wave amendment")
    root = archive.wave_root(data_root, site_id, wave_id, version)
    archive._mkdir_durable(root)
    probe = root / ".write-test"
    with probe.open("x", encoding="utf-8") as fh:
        fh.write("ok")
    probe.unlink()
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
    done: set[str] = set()
    metadata = root / "metadata"
    failures = root / "failures"
    if metadata.exists():
        for path in metadata.glob("*.json"):
            if path.name.startswith("retry-link-"):
                continue
            data = _read_record(path)
            if data.get("attempt_id"):
                aid = data["attempt_id"]
                if path.stem != aid or data.get("status") != "valid_confirmatory_api_capture":
                    raise ValueError("invalid retained capture identity/status: " + path.name)
                raw = root / data.get("raw_file", "")
                if (raw.is_symlink() or not raw.is_file() or
                        not raw.resolve().is_relative_to(root.resolve()) or
                        sha256_file(raw) != data.get("raw_file_sha256")):
                    raise ValueError("retained capture integrity mismatch: " + path.name)
                envelope = _read_record(raw)
                if envelope.get("attempt_id") != aid:
                    raise ValueError("retained raw attempt identity mismatch: " + path.name)
                done.add(data["attempt_id"])
    if failures.exists():
        for path in failures.glob("*.json"):
            record = _read_record(path)
            if record.get("attempt_id") != path.stem or path.stem in done:
                raise ValueError("invalid or conflicting retained failure: " + path.name)
            done.add(path.stem)
    retained_raw = {p.resolve() for p in (root / "api_raw").glob("*.json")}
    linked_raw = { (root / _read_record(p)["raw_file"]).resolve()
                   for p in metadata.glob("*.json")
                   if not p.name.startswith("retry-link-") and _read_record(p).get("attempt_id") }
    if retained_raw != linked_raw:
        raise ValueError("unlinked raw capture; stop without resending")
    for path in (root / "dispatch").glob("*.json"):
        dispatch = _read_record(path)
        if dispatch.get("attempt_id") != path.stem:
            raise ValueError("invalid dispatch journal identity: " + path.name)
        if path.stem not in done:
            raise ValueError("unresolved dispatch; stop without resending: " + path.name)
    return done


def _read_record(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("unexpected symlink in retained record: " + path.name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("unreadable retained record: " + path.name) from exc
    if not isinstance(value, dict):
        raise ValueError("retained record must be an object: " + path.name)
    return value


@contextmanager
def _execution_lock(data_root: Path, rows: list[dict[str, Any]]):
    """Serialize each namespace and lock admitted lineages across versions."""
    row = rows[0]
    root = data_root / ".execution-locks" / row["site_id"] / row["wave_id"]
    root.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        names = ["namespace-v" + row["protocol_version"]]
        names += sorted({r["service_lineage_id"] for r in rows})
        for name in names:
            lock = stack.enter_context((root / (name + ".lock")).open("a+b"))
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another executor holds this wave execution lock: " + name) from exc
            stack.callback(fcntl.flock, lock.fileno(), fcntl.LOCK_UN)
        yield


def _restore_runtime_state(data_root: Path, rows: list[dict[str, Any]],
                           protocol: dict[str, Any],
                           admitted_lineages: set[str] | None = None
                           ) -> tuple[dict[str, datetime], set[str]]:
    """Reconstruct registered waits/retries and stops solely from retained logs."""
    first = rows[0]
    root = archive.wave_root(data_root, first["site_id"], first["wave_id"], first["protocol_version"])
    row_map = {r["attempt_id"]: r for r in rows}
    failures = {_read_record(p)["attempt_id"]: _read_record(p)
                for p in (root / "failures").glob("*.json")}
    stored_links = {p.name: _read_record(p)
                    for p in (root / "metadata").glob("retry-link-*.json")}
    for name, link in stored_links.items():
        if link.get("original_attempt_id") not in failures:
            raise ValueError("retained retry link has no parent technical failure: " + name)
        if name != "retry-link-" + str(link.get("retry_attempt_id")) + ".json":
            raise ValueError("retained retry link filename/identity mismatch: " + name)
    validated_links: set[str] = set()
    pause_until: dict[str, datetime] = {}
    suspended: set[str] = set()
    for path in (root / "deviations").glob("*.json"):
        record = _read_record(path)
        if record.get("type") in {"lineage_suspended_after_retry_exhaustion",
                                  "lineage_suspended_for_environment_mismatch"}:
            suspended.add(record["service_lineage_id"])
    for _ in range(3):
        for aid, failure in failures.items():
            row = row_map.get(aid)
            if row is None:
                continue
            failed_at = parse_utc(failure["failed_at_utc"])
            _start, close = _row_bounds(protocol, row)
            decision = decide_retry(attempt=int(row["attempt"]),
                failure_kind=failure["failure_kind"], failed_at=failed_at,
                provider_retry_after_seconds=failure.get("retry_after_seconds"),
                field_close=close)
            child_links = {name: link for name, link in stored_links.items()
                           if link.get("original_attempt_id") == aid}
            if child_links and not decision.retry:
                raise ValueError("retained retry link is not protocol eligible: " + aid)
            lineage = row["service_lineage_id"]
            if failure["failure_kind"] == "request_environment_mismatch":
                suspended.add(lineage)
            if decision.retry:
                retry = _clone_retry_row(row, int(decision.next_attempt))
                row_map[retry["attempt_id"]] = retry
                link_path = root / "metadata" / ("retry-link-" + retry["attempt_id"] + ".json")
                expected = dict(original_attempt_id=aid, retry_attempt_id=retry["attempt_id"],
                    due_at_utc=decision.due_at_utc, failure_kind=failure["failure_kind"])
                if child_links and set(child_links) != {link_path.name}:
                    raise ValueError("retained retry link does not match deterministic next attempt: " + aid)
                if link_path.exists():
                    link = _read_record(link_path)
                    identity = {**expected, "protocol_version": row["protocol_version"],
                                "scientific_class": runner.SCIENTIFIC_CLASS,
                                "link_type": "technical_retry"}
                    if any(link.get(k) != v for k, v in identity.items()):
                        raise ValueError("retained retry link violates registered decision: " + link_path.name)
                    validated_links.add(link_path.name)
                elif admitted_lineages is None or lineage in admitted_lineages:
                    archive.archive_retry_link(data_root=data_root, site_id=row["site_id"],
                        wave_id=row["wave_id"], protocol_version=row["protocol_version"], **expected)
                if failure.get("http_status") in {429, 502, 503, 504}:
                    due = parse_utc(str(decision.due_at_utc))
                    pause_until[lineage] = max(pause_until.get(lineage, due), due)
            elif failure.get("http_status") in {502, 503, 504}:
                suspended.add(lineage)
    if set(failures) - set(row_map):
        raise ValueError("retained failure is not linked to the authorized manifest")
    if set(stored_links) - validated_links:
        raise ValueError("retained retry link has no validated registered decision")
    identity_fields = ("protocol_version", "wave_id", "site_id", "service_lineage_id",
                       "provider", "query_form_id", "query_sha256", "window_id",
                       "replication", "attempt")
    for aid, failure in failures.items():
        if any(failure.get(field) != row_map[aid].get(field) for field in identity_fields):
            raise ValueError("retained failure identity differs from the full manifest: " + aid)
    for path in (root / "metadata").glob("*.json"):
        record = _read_record(path)
        aid = record.get("attempt_id")
        if not aid:
            continue
        if aid not in row_map:
            raise ValueError("retained capture is not linked to the full manifest: " + aid)
        envelope = _read_record(root / record["raw_file"])
        if any(envelope.get(field) != row_map[aid].get(field) for field in identity_fields):
            raise ValueError("retained capture identity differs from the full manifest: " + aid)
    return pause_until, suspended


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
        links.append(_read_record(path))
    for _ in range(3):
        changed = False
        for link in links:
            original = row_map.get(link.get("original_attempt_id"))
            target = link.get("retry_attempt_id")
            if original is None or not target or target in row_map:
                continue
            clone = _clone_retry_row(original, int(original["attempt"]) + 1)
            if clone["attempt_id"] != target:
                raise ValueError("stored Core v2 retry link does not match deterministic Attempt ID")
            row_map[target] = clone
            changed = True
        if not changed:
            break
    if any(link.get("original_attempt_id") not in row_map or
           link.get("retry_attempt_id") not in row_map for link in links):
        raise ValueError("retained retry link is not linked to the authorized manifest")
    done = _processed_attempt_ids(data_root, site_id, wave_id, version)
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
    with _execution_lock(data_root, rows):
        return _execute_locked(protocol_path=protocol_path, manifest_path=manifest_path,
            authorization_path=authorization_path, data_root=data_root, timeout_s=timeout_s,
            rows=rows, freeze=freeze, _auth=_auth, field_close=field_close)


def _execute_locked(*, protocol_path: Path, manifest_path: Path,
                    authorization_path: Path, data_root: Path, timeout_s: int,
                    rows: list[dict[str, Any]], freeze: dict[str, Any],
                    _auth: dict[str, Any], field_close: datetime) -> dict[str, int]:
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
    done = _processed_attempt_ids(data_root, rows[0]["site_id"], rows[0]["wave_id"], rows[0]["protocol_version"])
    protocol, _ = runner.load_protocol(protocol_path)
    all_rows = runner.read_csv(manifest_path) if rows[0]["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS else rows
    admitted = {row["service_lineage_id"] for row in rows}
    pause_until, suspended = _restore_runtime_state(data_root, all_rows, protocol, admitted)
    now = datetime.now(timezone.utc)
    queue: list[tuple[datetime, int, str, dict[str, Any]]] = [
        (max(now, _row_bounds(protocol, row)[0]), int(row["execution_order"]), row["attempt_id"], row)
        for row in rows if row["attempt_id"] not in done
    ]
    for due, retry_row in _existing_retry_rows(data_root, all_rows):
        if retry_row["service_lineage_id"] in admitted:
            queue.append((due, int(retry_row["execution_order"]), retry_row["attempt_id"], retry_row))
    summary = {
        "valid": 0, "already_processed": len(done), "failed_attempts": 0,
        "retries_scheduled": 0, "rate_limit_pauses": 0, "outage_pauses": 0,
        "lineage_suspensions": 0, "skipped_after_suspension": 0,
    }
    while queue:
        queue.sort(key=lambda item: (item[0], item[1], item[2]))
        due, order, _aid, row = queue.pop(0)
        lineage = row["service_lineage_id"]
        if lineage in suspended:
            summary["skipped_after_suspension"] += 1
            continue
        if pause_until.get(lineage) and due < pause_until[lineage]:
            queue.append((pause_until[lineage], order, row["attempt_id"], row))
            continue
        current = datetime.now(timezone.utc)
        _row_start, row_close = _row_bounds(protocol, row)
        if current >= field_close:
            break
        if current >= row_close:
            archive.archive_failure(
                data_root=data_root, row=row,
                failure_kind="window_expired_before_attempt",
                message="registered row window closed before this attempt could start",
                failed_at_utc=current.isoformat().replace("+00:00", "Z"),
            )
            summary["failed_attempts"] += 1
            continue
        if due > current:
            time.sleep(min((due - current).total_seconds(), max(0.0, (row_close - current).total_seconds())))
            current = datetime.now(timezone.utc)
            if current >= row_close:
                archive.archive_failure(
                    data_root=data_root, row=row,
                    failure_kind="window_expired_before_attempt",
                    message="registered row window closed while the attempt was waiting",
                    failed_at_utc=current.isoformat().replace("+00:00", "Z"),
                )
                summary["failed_attempts"] += 1
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
        try:
            archive.archive_dispatch(data_root=data_root, row=row)
            result = call_provider(
                provider=row["provider"], model_id=row["model_id"],
                prompt=prompts[row["query_form_id"]],
                profile=cfg["request_profile"], timeout_s=timeout_s,
                **({"capture_response_metadata": True} if row["protocol_version"] == runner.STANDARD_PROTOCOL_VERSION
                   and row["provider"] == "Google" else {}),
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
            if exc.http_status == 429 and retry_due is not None:
                pause_until[lineage] = retry_due
                summary["rate_limit_pauses"] += 1
            if exc.http_status in {502, 503, 504}:
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
        archive.archive_success(
            data_root=data_root, row=row, request_payload=result.request_payload,
            response_json=result.response_json, raw_response_text=result.raw_response_text,
            http_status=result.http_status, returned_model=result.returned_model,
            usage=result.usage, started_at_utc=result.started_at_utc,
            completed_at_utc=result.completed_at_utc, duration_ms=result.duration_ms,
            response_metadata=result.response_metadata,
        )
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
    print(json.dumps(execute(
        protocol_path=args.protocol, manifest_path=args.manifest,
        freeze_path=args.freeze, authorization_path=args.authorization,
        data_root=args.data_root, timeout_s=args.timeout,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
