#!/usr/bin/env python3
"""Append-only raw API capture and integrity utilities for MIBO Core."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return _sha256_bytes(data)


def canonical_json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def wave_root(data_root: Path, site_id: str, wave_id: str) -> Path:
    return data_root / "v1.0" / site_id / wave_id


def archive_success(*, data_root: Path, row: dict, request_payload: dict, response_json: dict, raw_response_text: str, http_status: int, returned_model: str | None, usage: Any, started_at_utc: str, completed_at_utc: str, duration_ms: int) -> dict:
    root = wave_root(data_root, row["site_id"], row["wave_id"])
    observation_id = row["attempt_id"]
    envelope = {
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "protocol_doi": row["protocol_doi"],
        "wave_id": row["wave_id"],
        "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"],
        "provider": row["provider"],
        "line_id": row["line_id"],
        "query_form_id": row["query_form_id"],
        "replication": row["replication"],
        "attempt": row["attempt"],
        "configuration_freeze_sha256": row.get("configuration_freeze_sha256", ""),
        "model_id_requested": row.get("model_id", ""),
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
        "observation_id": observation_id,
        "attempt_id": row["attempt_id"],
        "raw_file": str(raw_path.relative_to(root)),
        "raw_file_sha256": raw_hash,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "valid_technical_capture",
    }
    meta_path = root / "metadata" / f"{observation_id}.json"
    meta_hash = _write_exclusive(meta_path, canonical_json_bytes(metadata))
    return {**metadata, "metadata_file_sha256": meta_hash}


def archive_failure(*, data_root: Path, row: dict, failure_kind: str, message: str, failed_at_utc: str, http_status: int | None = None, retry_after_seconds: int | None = None, response_body: str | None = None) -> dict:
    root = wave_root(data_root, row["site_id"], row["wave_id"])
    failure = {
        "attempt_id": row["attempt_id"],
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
    digest = _write_exclusive(path, canonical_json_bytes(failure))
    return {"attempt_id": row["attempt_id"], "failure_file": str(path.relative_to(root)), "failure_file_sha256": digest}


def write_deviation(*, data_root: Path, site_id: str, wave_id: str, deviation_id: str, record: dict) -> str:
    root = wave_root(data_root, site_id, wave_id)
    path = root / "deviations" / f"{deviation_id}.json"
    return _write_exclusive(path, canonical_json_bytes(record))


def build_wave_hash_manifest(*, data_root: Path, site_id: str, wave_id: str) -> tuple[Path, str]:
    root = wave_root(data_root, site_id, wave_id)
    release = root / "release"
    release.mkdir(parents=True, exist_ok=True)
    manifest_path = release / "SHA256SUMS.txt"
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(root).as_posix()}")
    data = ("\n".join(entries) + "\n").encode("utf-8")
    digest = _write_exclusive(manifest_path, data)
    return manifest_path, digest
