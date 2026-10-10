#!/usr/bin/env python3
"""Durable, content-blind execution state for the private Core v2 runtime.

An attempt is claimed before the adapter runs. If a process dies before a
terminal capture/failure is durably retained, its lineage stops on restart;
the claim is never treated as permission to send that attempt again.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator

import core_v2_archive as archive
from retry_policy import decide_retry

SUSPENSION_TYPES = {
    "lineage_suspended_after_retry_exhaustion",
    "lineage_suspended_for_environment_mismatch",
    "lineage_suspended_for_uncertain_dispatch",
}


class LegacyCaptureMetadataError(ValueError):
    """Retained bytes exist but their older sidecar cannot prove eligibility."""


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("retained execution state is not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("corrupt retained execution state: " + path.name) from exc
    if not isinstance(value, dict):
        raise ValueError("retained execution state must be an object: " + path.name)
    return value


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("retained execution timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("retained execution timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@contextmanager
def wave_lock(root: Path) -> Iterator[None]:
    """Keep a kernel lock across validation, dispatch, pauses and archiving."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".executor.lock"
    if path.is_symlink():
        raise ValueError("execution lock must not be a symlink")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another Core v2 executor holds this wave lock") from exc
        yield
    finally:
        os.close(fd)  # Closing releases the kernel lock even after an exception.


@contextmanager
def lineage_locks(data_root: Path, site_id: str, wave_id: str,
                  lineages: set[str]) -> Iterator[None]:
    """Serialize the same lineage/site/wave across all protocol namespaces.

    Nonoverlapping authorized scopes can run independently. These empty lock
    files contain neither scientific data nor private credentials.
    """
    if any(not value or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in value)
           for value in (site_id, wave_id, *lineages)):
        raise ValueError("invalid execution lock identity")
    parent = data_root / '.execution-locks' / site_id / wave_id
    for path in (data_root / '.execution-locks', data_root / '.execution-locks' / site_id, parent):
        if path.is_symlink():
            raise ValueError("execution lock namespace must not contain a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    fds: list[int] = []
    try:
        for lineage in sorted(lineages):
            path = parent / (lineage + '.lock')
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            fds.append(fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another Core v2 namespace holds this lineage/wave lock") from exc
        yield
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def processed_attempt_ids(root: Path) -> set[str]:
    """Reject incomplete/corrupt terminal state instead of silently resending."""
    captured: set[str] = set()
    if any((root / folder).is_symlink() for folder in ("metadata", "failures", "api_raw", "dispatch", "deviations")):
        raise ValueError("retained execution folders must not be symlinks")
    for path in (root / "metadata").glob("*.json"):
        data = _read(path)
        if path.name.startswith(("retry-link-", "first-dispatch-")):
            continue
        aid = data.get("attempt_id")
        if not isinstance(aid, str) or path.stem != aid or aid in captured:
            raise ValueError("invalid retained capture identity")
        relative = data.get("raw_file")
        if not isinstance(relative, str):
            raise ValueError("retained capture has no raw file")
        raw = root / relative
        if raw.is_symlink() or not raw.is_file() or not raw.resolve().is_relative_to(root.resolve()):
            raise ValueError("retained capture raw file missing or outside wave")
        if raw.parent != root / "api_raw" or raw.stem != aid:
            raise ValueError("retained capture raw filename differs from Attempt ID")
        if data.get("status") != "valid_confirmatory_api_capture" or _digest(raw) != data.get("raw_file_sha256"):
            raise ValueError("retained capture checksum/status mismatch")
        captured.add(aid)
    failed: set[str] = set()
    for path in (root / "failures").glob("*.json"):
        data = _read(path)
        aid = data.get("attempt_id")
        if not isinstance(aid, str) or path.stem != aid or aid in failed:
            raise ValueError("invalid retained failure identity")
        failed.add(aid)
    if captured & failed:
        raise ValueError("Attempt ID has both capture and failure records")
    return captured | failed


@dataclass
class ResumeState:
    done: set[str] = field(default_factory=set)
    retries: list[tuple[datetime, dict[str, Any]]] = field(default_factory=list)
    pause_until: dict[str, datetime] = field(default_factory=dict)
    suspended: set[str] = field(default_factory=set)
    uncertain: set[str] = field(default_factory=set)
    recovery_attempt: dict[str, str] = field(default_factory=dict)


def _bind_fields(data: dict[str, Any], row: dict[str, Any], keys: tuple[str, ...],
                 label: str) -> None:
    for key in keys:
        expected = row.get(key)
        if key not in data or data[key] != expected or type(data[key]) is not type(expected):
            raise ValueError("retained " + label + " frozen-input identity mismatch: " + key)


def _bind(data: dict[str, Any], row: dict[str, Any], *, claim: bool = False) -> None:
    keys = ("protocol_version", "attempt_id", "service_lineage_id", "window_id",
            "retry_of_attempt_id")
    if claim:
        keys += ("site_id", "wave_id", "model_id", "query_sha256",
                 "protocol_file_sha256", "provider_freeze_sha256")
    _bind_fields(data, row, keys, "dispatch" if claim else "attempt")


def validate_capture(data: dict[str, Any], row: dict[str, Any], *,
                     bounds: tuple[datetime, datetime], current: datetime,
                     retry_due: datetime | None = None,
                     dispatched_at: datetime | None = None) -> tuple[datetime, datetime]:
    """Validate technical evidence only; the restricted raw JSON stays opaque.

    A valid dispatch may finish after the row closes. Its recorded start must
    remain inside that row's registered window and at or after its retry due.
    Older incomplete sidecars remain retained, but cannot be counted or resent.
    """
    if (type(data.get("technical_metadata_version")) is not int or
            data["technical_metadata_version"] != archive.TECHNICAL_CAPTURE_VERSION):
        raise LegacyCaptureMetadataError(
            "legacy capture lacks complete technical metadata; retain without automatic resend")
    _bind_fields(data, row, archive.CAPTURE_IDENTITY_FIELDS, "capture")
    if (data.get("observation_id") != row["attempt_id"] or
            data.get("model_id_requested") != row["model_id"]):
        raise ValueError("retained capture observation/model identity mismatch")
    if type(data.get("http_status")) is not int or not 200 <= data["http_status"] < 300:
        raise ValueError("retained capture HTTP status is not successful")
    started = _utc(data.get("started_at_utc"))
    completed = _utc(data.get("completed_at_utc"))
    start, close = bounds
    if not start <= started < close:
        raise ValueError("retained capture start outside registered row window")
    if completed < started:
        raise ValueError("retained capture completion precedes start")
    if completed > current:
        raise ValueError("retained capture timestamp is in the future")
    if retry_due is not None and started < retry_due:
        raise ValueError("retained retry capture starts before protocol-eligible due")
    if dispatched_at is not None and started < dispatched_at:
        raise ValueError("retained capture start predates dispatch claim")
    return started, completed


def claim_attempt(root: Path, row: dict[str, Any], *, authorization_sha256: str,
                  dispatched_at: datetime) -> None:
    record = {key: row.get(key) for key in (
        "protocol_version", "site_id", "wave_id", "service_lineage_id",
        "attempt_id", "retry_of_attempt_id", "window_id", "model_id",
        "query_sha256", "protocol_file_sha256", "provider_freeze_sha256",
    )}
    record.update(
        type="attempt_dispatch_claim",
        authorization_sha256=authorization_sha256,
        dispatched_at_utc=dispatched_at.isoformat(),
        ambiguity_rule="no automatic resend without a retained terminal record",
    )
    archive._write_exclusive(root / "dispatch" / (row["attempt_id"] + ".json"),
                             archive.canonical_json_bytes(record))


def record_recovery_block(data_root: Path, row: dict[str, Any], *, retry_id: str,
                          due: datetime, http_status: int | None) -> None:
    root = archive.wave_root(data_root, row['site_id'], row['wave_id'], row['protocol_version'])
    deviation_id = 'CORE-V2-RECOVERY-BLOCK-' + row['attempt_id']
    if not (root / 'deviations' / (deviation_id + '.json')).exists():
        archive.write_deviation(data_root=data_root, site_id=row['site_id'],
            wave_id=row['wave_id'], protocol_version=row['protocol_version'],
            deviation_id=deviation_id, record={
                'type': 'lineage_controlled_technical_recovery_block',
                'service_lineage_id': row['service_lineage_id'],
                'trigger_attempt_id': row['attempt_id'], 'http_status': http_status,
                'first_recovery_attempt_id': retry_id, 'first_recovery_due_at_utc': due.isoformat(),
                'rule': 'hold fresh lineage submissions until registered retry succeeds or lineage suspends',
            })


def restore(*, root: Path, initial_rows: list[dict[str, Any]],
            clone_retry: Callable[[dict[str, Any], int], dict[str, Any]],
            row_bounds: Callable[[dict[str, Any]], tuple[datetime, datetime]],
            data_root: Path, authorization_sha256: str | None,
            persist: bool = True, current: datetime | None = None) -> ResumeState:
    """Reconstruct only protocol-eligible retries from retained technical state.

    The failure is the authority. A missing retry link can be written again
    deterministically after a crash between the failure and link writes. A
    malformed/mismatched existing link fails closed and is never overwritten.
    """
    now = current if current is not None else datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("retained-state validation clock must be timezone-aware")
    now = now.astimezone(timezone.utc)
    state = ResumeState(done=processed_attempt_ids(root))
    row_map = {row["attempt_id"]: row for row in initial_rows}
    if len(row_map) != len(initial_rows):
        raise ValueError("duplicate initial Attempt IDs")
    failures = {path.stem: _read(path) for path in (root / "failures").glob("*.json")}
    captures = {path.stem: _read(path) for path in (root / "metadata").glob("*.json")
                if not path.name.startswith(("retry-link-", "first-dispatch-"))}
    links = {path.stem.removeprefix("retry-link-"): _read(path)
             for path in (root / "metadata").glob("retry-link-*.json")}
    claims = {path.stem: _read(path) for path in (root / "dispatch").glob("*.json")}
    raw_paths = list((root / "api_raw").glob("*.json"))
    if any(path.is_symlink() or not path.is_file() for path in raw_paths):
        raise ValueError("retained raw capture must be a regular file")
    raw_only = {path.stem for path in raw_paths} - state.done
    # Build deterministic retry identities only where retained state needs them.
    retained_ids = state.done | set(claims) | raw_only | set(links)
    if retained_ids - set(row_map):
        for row in initial_rows:
            retry_one = clone_retry(row, 2)
            retry_two = clone_retry(retry_one, 3)
            for retry in (retry_one, retry_two):
                row_map[retry["attempt_id"]] = retry
    if retained_ids - set(row_map):
        raise ValueError("retained state contains an unregistered Attempt ID or excess retry")
    capture_times = {}
    for aid, capture in captures.items():
        row = row_map[aid]
        capture_times[aid] = validate_capture(capture, row, bounds=row_bounds(row), current=now)
    for aid, failure in failures.items():
        row = row_map[aid]
        _bind_fields(failure, row, archive.FAILURE_IDENTITY_FIELDS, "failure")
        # Newer technical sidecars may carry additional frozen identity. Never
        # ignore contradictory evidence simply because it is an optional field
        # in the older failure format.
        additional = tuple(key for key in archive.CAPTURE_IDENTITY_FIELDS
                           if key in failure and key not in archive.FAILURE_IDENTITY_FIELDS)
        _bind_fields(failure, row, additional, "failure")
        if "model_id_requested" in failure and failure["model_id_requested"] != row["model_id"]:
            raise ValueError("retained failure frozen model identity mismatch")
    claim_times = {}
    for aid, claim in claims.items():
        if claim.get("type") != "attempt_dispatch_claim":
            raise ValueError("invalid retained dispatch record type")
        _bind(claim, row_map[aid], claim=True)
        if authorization_sha256 is not None and claim.get("authorization_sha256") != authorization_sha256:
            raise ValueError("retained dispatch authorization hash mismatch")
        dispatched = _utc(claim.get("dispatched_at_utc"))
        start, close = row_bounds(row_map[aid])
        if not start <= dispatched < close or dispatched > now:
            raise ValueError("retained dispatch timestamp outside registered/current bounds")
        claim_times[aid] = dispatched
    for path in (root / "deviations").glob("*.json"):
        record = _read(path)
        record_type = str(record.get("type", ""))
        if "suspend" in record_type:
            if record_type not in SUSPENSION_TYPES:
                raise ValueError("unknown retained lineage suspension type")
            sid = record.get("service_lineage_id")
            if sid not in {row["service_lineage_id"] for row in initial_rows}:
                raise ValueError("retained suspension has an unregistered lineage")
            state.suspended.add(sid)
    expected_links: dict[str, tuple[datetime, dict[str, Any], dict[str, Any]]] = {}
    recovery_candidates: dict[str, list[tuple[datetime, int, str]]] = {}
    recovery_blocks = []
    failure_times = {}
    for aid, failure in failures.items():
        row = row_map[aid]
        failed_at = _utc(failure.get("failed_at_utc"))
        start, close = row_bounds(row)
        if failed_at < start:
            raise ValueError("retained failure predates registered row window")
        if failed_at > now:
            raise ValueError("retained failure timestamp is in the future")
        if aid in claim_times and failed_at < claim_times[aid]:
            raise ValueError("retained failure predates dispatch claim")
        failure_times[aid] = failed_at
        kind = failure.get("failure_kind")
        decision = decide_retry(attempt=int(row["attempt"]), failure_kind=kind,
            failed_at=failed_at, provider_retry_after_seconds=failure.get("retry_after_seconds"),
            field_close=close)
        sid = row["service_lineage_id"]
        ancestry = []
        parent: str | None = aid
        while parent is not None and parent in failures:
            ancestry.append(failures[parent].get("http_status"))
            parent = row_map[parent].get("retry_of_attempt_id")
        outage_chain = any(status in {502, 503, 504} for status in ancestry)
        recovery_chain = outage_chain or 429 in ancestry
        if kind == "request_environment_mismatch" or (
                recovery_chain and not decision.retry):
            state.suspended.add(sid)
        if decision.retry:
            retry = clone_retry(row, int(decision.next_attempt))
            row_map[retry["attempt_id"]] = retry
            due = _utc(decision.due_at_utc)
            expected_links[retry["attempt_id"]] = (due, retry, failure)
            if retry["attempt_id"] not in state.done:
                state.retries.append((due, retry))
                if failure.get("http_status") in {429, 502, 503, 504}:
                    state.pause_until[sid] = max(due, state.pause_until.get(sid, due))
                if recovery_chain:
                    recovery_candidates.setdefault(sid, []).append((due, int(retry["execution_order"]), retry["attempt_id"]))
            if (persist and failure.get('http_status') in {429, 502, 503, 504}
                    and not any(status in {429, 502, 503, 504} for status in ancestry[1:])):
                recovery_blocks.append((row, retry['attempt_id'], due, failure.get('http_status')))
    for sid, candidates in recovery_candidates.items():
        state.recovery_attempt[sid] = min(candidates)[2]
    for aid, link in links.items():
        if aid not in expected_links:
            raise ValueError("retained retry link lacks a protocol-eligible failure")
        due, retry, failure = expected_links[aid]
        if (link.get("retry_attempt_id") != aid or
                link.get("original_attempt_id") != retry["retry_of_attempt_id"] or
                link.get("protocol_version") != retry["protocol_version"] or
                link.get("link_type") != "technical_retry" or
                link.get("failure_kind") != failure["failure_kind"] or
                _utc(link.get("due_at_utc")) != due):
            raise ValueError("retained retry link violates frozen retry identity/timing")
    for aid in retained_ids:
        if int(row_map[aid]["attempt"]) > 1 and aid not in expected_links:
            raise ValueError("retained retry attempt lacks a protocol-eligible parent failure")
        if aid in capture_times and aid in claim_times and capture_times[aid][0] < claim_times[aid]:
            raise ValueError("retained capture start predates dispatch claim")
        if int(row_map[aid]["attempt"]) > 1:
            due = expected_links[aid][0]
            if aid in capture_times and capture_times[aid][0] < due:
                raise ValueError("retained retry capture starts before protocol-eligible due")
            if aid in failure_times and failure_times[aid] < due:
                raise ValueError("retained retry failure predates protocol-eligible due")
            if aid in claim_times and claim_times[aid] < due:
                raise ValueError("retained retry dispatch predates protocol-eligible due")
    # Only repair missing append-only technical records after every retained
    # identity and timestamp has passed; corrupt state causes no repair writes.
    for row, retry_id, due, http_status in recovery_blocks:
        record_recovery_block(data_root, row, retry_id=retry_id, due=due, http_status=http_status)
    for aid, (due, retry, failure) in expected_links.items():
        if persist and aid not in links:
            archive.archive_retry_link(data_root=data_root,
                original_attempt_id=retry["retry_of_attempt_id"], retry_attempt_id=aid,
                site_id=retry["site_id"], wave_id=retry["wave_id"],
                due_at_utc=due.isoformat().replace("+00:00", "Z"),
                failure_kind=failure["failure_kind"],
                protocol_version=retry["protocol_version"])
    state.uncertain = (set(claims) | raw_only) - state.done
    for aid in state.uncertain:
        row = row_map[aid]
        sid = row["service_lineage_id"]
        state.suspended.add(sid)
        deviation_id = "CORE-V2-UNCERTAIN-DISPATCH-" + aid
        if persist and not (root / "deviations" / (deviation_id + ".json")).exists():
            archive.write_deviation(data_root=data_root, site_id=row["site_id"],
                wave_id=row["wave_id"], protocol_version=row["protocol_version"],
                deviation_id=deviation_id, record={
                    "type": "lineage_suspended_for_uncertain_dispatch",
                    "service_lineage_id": sid, "trigger_attempt_id": aid,
                    "rule": "retain ambiguity/missingness; no automatic resend or recovery",
                })
    return state
