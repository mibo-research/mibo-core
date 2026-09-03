#!/usr/bin/env python3
"""Append-only storage for prospectively registered MIBO Core v2.0 API observations."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from raw_archive import canonical_json_bytes

PROTOCOL_VERSION = "2.0"
SCIENTIFIC_CLASS = "confirmatory_primary"


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def wave_root(data_root: Path, site_id: str, wave_id: str) -> Path:
    return data_root / "v2.0" / site_id / wave_id


def archive_success(*, data_root: Path, row: dict[str, Any], request_payload: dict[str, Any],
                    response_json: dict[str, Any], raw_response_text: str, http_status: int,
                    returned_model: str | None, usage: Any, started_at_utc: str,
                    completed_at_utc: str, duration_ms: int) -> dict[str, Any]:
    root = wave_root(data_root, row["site_id"], row["wave_id"])
    observation_id = row["attempt_id"]
    envelope = {
        "protocol_version": PROTOCOL_VERSION,
        "protocol_registration_id": row["protocol_registration_id"],
        "scientific_class": SCIENTIFIC_CLASS,
        "observation_surface": "provider_api",
        "environment_class": "CLOSED",
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "wave_id": row["wave_id"], "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"],
        "service_name": row["service_name"], "provider": row["provider"],
        "line_id": row["line_id"], "query_form_id": row["query_form_id"],
        "item_id": row["item_id"], "language": row["language"],
        "replication": row["replication"], "attempt": row["attempt"],
        "protocol_file_sha256": row["protocol_file_sha256"],
        "provider_freeze_sha256": row["provider_freeze_sha256"],
        "model_id_requested": row["model_id"], "model_id_returned": returned_model,
        "request_payload": request_payload, "http_status": http_status,
        "raw_response": response_json, "raw_response_text": raw_response_text,
        "usage": usage, "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc, "duration_ms": duration_ms,
    }
    raw_path = root / "api_raw" / f"{observation_id}.json"
    raw_hash = _write_exclusive(raw_path, canonical_json_bytes(envelope))
    metadata = {
        "protocol_version": PROTOCOL_VERSION,
        "scientific_class": SCIENTIFIC_CLASS,
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "raw_file": str(raw_path.relative_to(root)),
        "raw_file_sha256": raw_hash,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "valid_confirmatory_api_capture",
    }
    meta_path = root / "metadata" / f"{observation_id}.json"
    meta_hash = _write_exclusive(meta_path, canonical_json_bytes(metadata))
    return {**metadata, "metadata_file_sha256": meta_hash}


def archive_failure(*, data_root: Path, row: dict[str, Any], failure_kind: str,
                    message: str, failed_at_utc: str, http_status: int | None = None,
                    retry_after_seconds: int | None = None,
                    response_body: str | None = None) -> dict[str, Any]:
    root = wave_root(data_root, row["site_id"], row["wave_id"])
    record = {
        "protocol_version": PROTOCOL_VERSION, "scientific_class": SCIENTIFIC_CLASS,
        "attempt_id": row["attempt_id"], "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "protocol_registration_id": row["protocol_registration_id"],
        "wave_id": row["wave_id"], "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"], "provider": row["provider"],
        "line_id": row["line_id"], "query_form_id": row["query_form_id"],
        "replication": row["replication"], "attempt": row["attempt"],
        "failure_kind": failure_kind, "message": message, "http_status": http_status,
        "retry_after_seconds": retry_after_seconds,
        "provider_response_body": response_body, "failed_at_utc": failed_at_utc,
    }
    path = root / "failures" / f"{row['attempt_id']}.json"
    digest = _write_exclusive(path, canonical_json_bytes(record))
    return {"failure_file": str(path.relative_to(root)), "failure_file_sha256": digest}


def archive_retry_link(*, data_root: Path, original_attempt_id: str,
                       retry_attempt_id: str, site_id: str, wave_id: str,
                       due_at_utc: str, failure_kind: str) -> dict[str, Any]:
    root = wave_root(data_root, site_id, wave_id)
    record = {
        "protocol_version": PROTOCOL_VERSION, "scientific_class": SCIENTIFIC_CLASS,
        "original_attempt_id": original_attempt_id, "retry_attempt_id": retry_attempt_id,
        "due_at_utc": due_at_utc, "failure_kind": failure_kind,
        "link_type": "technical_retry",
    }
    path = root / "metadata" / f"retry-link-{retry_attempt_id}.json"
    digest = _write_exclusive(path, canonical_json_bytes(record))
    return {"retry_link_file": str(path.relative_to(root)), "retry_link_sha256": digest}


def write_deviation(*, data_root: Path, site_id: str, wave_id: str,
                    deviation_id: str, record: dict[str, Any]) -> str:
    path = wave_root(data_root, site_id, wave_id) / "deviations" / f"{deviation_id}.json"
    return _write_exclusive(path, canonical_json_bytes({
        "protocol_version": PROTOCOL_VERSION,
        "scientific_class": SCIENTIFIC_CLASS,
        **record,
    }))
