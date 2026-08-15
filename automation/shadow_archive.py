#!/usr/bin/env python3
"""Append-only storage utilities for the exploratory MIBO API Shadow Archive."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from raw_archive import canonical_json_bytes

ARCHIVE_VERSION = "0.1"
ARCHIVE_CLASS = "exploratory_auxiliary"


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def shadow_wave_root(data_root: Path, site_id: str, wave_id: str) -> Path:
    return data_root / "auxiliary" / f"api-shadow-v{ARCHIVE_VERSION}" / site_id / wave_id


def archive_success(*, data_root: Path, row: dict, request_payload: dict,
                    response_json: dict, raw_response_text: str, http_status: int,
                    returned_model: str | None, usage: Any,
                    started_at_utc: str, completed_at_utc: str,
                    duration_ms: int) -> dict:
    root = shadow_wave_root(data_root, row["site_id"], row["wave_id"])
    observation_id = row["attempt_id"]
    envelope = {
        "archive_version": ARCHIVE_VERSION,
        "archive_class": ARCHIVE_CLASS,
        "confirmatory_use": "prohibited",
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "protocol_doi": row["protocol_doi"],
        "wave_id": row["wave_id"],
        "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"],
        "service_name": row["service_name"],
        "provider": row["provider"],
        "line_id": row["line_id"],
        "environment_class": row["environment_class"],
        "query_form_id": row["query_form_id"],
        "item_id": row["item_id"],
        "language": row["language"],
        "replication": row["replication"],
        "attempt": row["attempt"],
        "shadow_freeze_sha256": row["shadow_freeze_sha256"],
        "model_id_requested": row["model_id"],
        "model_id_returned": returned_model,
        "request_payload": request_payload,
        "http_status": http_status,
        "raw_response": response_json,
        "raw_response_text": raw_response_text,
        "usage": usage,
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "duration_ms": duration_ms,
    }
    raw_path = root / "api_raw" / f"{observation_id}.json"
    raw_hash = _write_exclusive(raw_path, canonical_json_bytes(envelope))
    metadata = {
        "archive_class": ARCHIVE_CLASS,
        "confirmatory_use": "prohibited",
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "raw_file": str(raw_path.relative_to(root)),
        "raw_file_sha256": raw_hash,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "valid_exploratory_capture",
    }
    meta_path = root / "metadata" / f"{observation_id}.json"
    meta_hash = _write_exclusive(meta_path, canonical_json_bytes(metadata))
    return {**metadata, "metadata_file_sha256": meta_hash}


def archive_failure(*, data_root: Path, row: dict, failure_kind: str, message: str,
                    failed_at_utc: str, http_status: int | None = None,
                    retry_after_seconds: int | None = None,
                    response_body: str | None = None) -> dict:
    root = shadow_wave_root(data_root, row["site_id"], row["wave_id"])
    record = {
        "archive_class": ARCHIVE_CLASS,
        "confirmatory_use": "prohibited",
        "attempt_id": row["attempt_id"],
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "protocol_doi": row["protocol_doi"],
        "wave_id": row["wave_id"],
        "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"],
        "provider": row["provider"],
        "line_id": row["line_id"],
        "query_form_id": row["query_form_id"],
        "replication": row["replication"],
        "attempt": row["attempt"],
        "failure_kind": failure_kind,
        "message": message,
        "http_status": http_status,
        "retry_after_seconds": retry_after_seconds,
        "provider_response_body": response_body,
        "failed_at_utc": failed_at_utc,
    }
    path = root / "failures" / f"{row['attempt_id']}.json"
    digest = _write_exclusive(path, canonical_json_bytes(record))
    return {"failure_file": str(path.relative_to(root)), "failure_file_sha256": digest}


def archive_retry_link(*, data_root: Path, original_attempt_id: str,
                       retry_attempt_id: str, site_id: str, wave_id: str,
                       due_at_utc: str, failure_kind: str) -> dict:
    root = shadow_wave_root(data_root, site_id, wave_id)
    record = {
        "archive_class": ARCHIVE_CLASS,
        "original_attempt_id": original_attempt_id,
        "retry_attempt_id": retry_attempt_id,
        "due_at_utc": due_at_utc,
        "failure_kind": failure_kind,
        "link_type": "technical_retry",
    }
    path = root / "metadata" / f"retry-link-{retry_attempt_id}.json"
    digest = _write_exclusive(path, canonical_json_bytes(record))
    return {"retry_link_file": str(path.relative_to(root)), "retry_link_sha256": digest}


def write_deviation(*, data_root: Path, site_id: str, wave_id: str,
                    deviation_id: str, record: dict) -> str:
    root = shadow_wave_root(data_root, site_id, wave_id)
    path = root / "deviations" / f"{deviation_id}.json"
    return _write_exclusive(path, canonical_json_bytes({
        "archive_class": ARCHIVE_CLASS,
        "confirmatory_use": "prohibited",
        **record,
    }))


def build_shadow_hash_manifest(*, data_root: Path, site_id: str, wave_id: str) -> tuple[Path, str]:
    root = shadow_wave_root(data_root, site_id, wave_id)
    release = root / "release"
    release.mkdir(parents=True, exist_ok=True)
    manifest_path = release / "SHA256SUMS.txt"
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    digest = _write_exclusive(manifest_path, ("\n".join(entries) + "\n").encode("utf-8"))
    return manifest_path, digest
