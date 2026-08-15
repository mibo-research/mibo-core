#!/usr/bin/env python3
"""Fail-closed paired API executor for MIBO Core v1.0.

Provider calls are impossible unless the manifest, Configuration Freeze Record,
private human authorization record, registered field window, and explicit
runtime execution sentinel all agree.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import manifest_integrity
import mibo_runner as core
from provider_adapters import AdapterFailure, call_provider
from raw_archive import archive_failure, archive_retry_link, archive_success, write_deviation
from retry_policy import decide_retry

PROTOCOL_DOI = "10.5281/zenodo.21936410"
EXECUTION_SENTINEL = "ENABLED_AFTER_PREWAVE_GATE"
EXPECTED_ADAPTER = {
    "OpenAI": "openai_responses",
    "Anthropic": "anthropic_messages",
    "Google": "gemini_generate_content",
}
FORBIDDEN_PROFILE_KEYS = {
    "tools", "tool_choice", "instructions", "system", "system_instruction",
    "web_search", "file_search", "google_search", "url_context", "files",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_authorization(path: Path, *, manifest_path: Path, freeze_path: Path, wave_id: str, site_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required_true = ("authorized", "terms_review_complete", "institutional_process_checked", "dry_run_complete")
    if data.get("protocol_doi") != PROTOCOL_DOI:
        raise ValueError("authorization protocol DOI mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("authorization wave/site mismatch")
    for field in required_true:
        if data.get(field) is not True:
            raise ValueError(f"authorization gate {field} is not true")
    if not data.get("operations_lead") or not data.get("authorized_at_utc"):
        raise ValueError("authorization requires operations_lead and authorized_at_utc")
    if data.get("manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("authorization manifest SHA-256 does not match")
    if data.get("provider_freeze_sha256") != sha256_file(freeze_path):
        raise ValueError("authorization provider-freeze SHA-256 does not match")
    return data


def _freeze_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("paired_api", {})


def _validate_freeze_binding(rows: list[dict], freeze_path: Path, *, require_credentials: bool) -> None:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    paired = freeze.get("paired_api", {})
    freeze_sha = sha256_file(freeze_path)
    for i, row in enumerate(rows, 1):
        sid = row["service_lineage_id"]
        cfg = paired.get(sid)
        if not isinstance(cfg, dict):
            raise ValueError(f"row {i}: lineage missing from provider freeze")
        if cfg.get("status") != "eligible":
            raise ValueError(f"row {i}: lineage is not eligible in provider freeze")
        if cfg.get("comparability_class") not in core.ELIGIBLE_COMPARABILITY_CLASSES:
            raise ValueError(f"row {i}: invalid provider-freeze comparability class")
        if row.get("comparability_class") != cfg.get("comparability_class"):
            raise ValueError(f"row {i}: comparability class does not match provider freeze")
        expected_model = cfg.get("live_model_id") if row["line_id"] == "PLR" else cfg.get("frozen_model_id")
        if row.get("model_id") != expected_model:
            raise ValueError(f"row {i}: model_id does not match provider freeze")
        if row.get("configuration_freeze_sha256") != freeze_sha:
            raise ValueError(f"row {i}: provider-freeze SHA-256 mismatch")
        profile = cfg.get("request_profile")
        if not isinstance(profile, dict):
            raise ValueError(f"row {i}: provider freeze lacks a request_profile")
        expected_adapter = EXPECTED_ADAPTER.get(row["provider"])
        if expected_adapter is None or profile.get("adapter") != expected_adapter:
            raise ValueError(f"row {i}: request_profile adapter mismatch")
        forbidden = FORBIDDEN_PROFILE_KEYS.intersection(profile)
        if forbidden:
            raise ValueError(f"row {i}: request_profile contains forbidden capability keys: {sorted(forbidden)}")
        if row["provider"] == "Anthropic" and profile.get("max_output_tokens") is None:
            raise ValueError(f"row {i}: Anthropic request_profile requires max_output_tokens")
        key_env = profile.get("api_key_env")
        if not isinstance(key_env, str) or not key_env:
            raise ValueError(f"row {i}: request_profile requires api_key_env")
        if require_credentials and not os.environ.get(key_env):
            raise ValueError(f"row {i}: required credential environment variable {key_env} is not set")


def preflight(*, manifest_path: Path, freeze_path: Path, authorization_path: Path, data_root: Path, now: datetime | None = None, require_credentials: bool = False) -> tuple[list[dict], dict, datetime, datetime]:
    rows = core.read_csv(manifest_path)
    errors = manifest_integrity.strict_validate_manifest(rows)
    if errors:
        raise ValueError("manifest validation failed: " + "; ".join(errors))
    if not rows or any(r["line_id"] not in {"PLR", "FRZ"} for r in rows):
        raise ValueError("paired executor accepts paired API manifests only")
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    _validate_freeze_binding(rows, freeze_path, require_credentials=require_credentials)
    auth = load_authorization(authorization_path, manifest_path=manifest_path, freeze_path=freeze_path, wave_id=wave_id, site_id=site_id)
    wave = core._wave(wave_id)
    field_start = parse_utc(wave["start_utc"])
    field_close = parse_utc(wave["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not (field_start <= current < field_close):
        raise ValueError("current time is outside the registered primary field window")
    data_root.mkdir(parents=True, exist_ok=True)
    probe = data_root / ".mibo-write-test"
    with probe.open("w", encoding="utf-8") as fh:
        fh.write("ok")
    probe.unlink()
    return rows, auth, field_start, field_close


def _prompt_map() -> dict[str, str]:
    return {f["query_form_id"]: f["text"] for f in core._forms()}


def _clone_retry_row(row: dict, next_attempt: int) -> dict:
    service = next(s for s in core._services() if s["service_lineage_id"] == row["service_lineage_id"])
    clone = dict(row)
    clone["retry_of_attempt_id"] = row["attempt_id"]
    clone["attempt"] = next_attempt
    clone["attempt_id"] = core.attempt_id(
        row["site_id"], row["wave_id"], service["short_id"], row["line_id"],
        row["item_id"], row["language"], row["window_id"], int(row["replication"]), next_attempt,
    )
    clone["status"] = "retry_intended"
    return clone


def execute(*, manifest_path: Path, freeze_path: Path, authorization_path: Path, data_root: Path, timeout_s: int = 180) -> dict[str, int]:
    if os.environ.get("MIBO_PROVIDER_EXECUTION") != EXECUTION_SENTINEL:
        raise RuntimeError("provider execution sentinel is not enabled")
    rows, _auth, _field_start, field_close = preflight(
        manifest_path=manifest_path, freeze_path=freeze_path, authorization_path=authorization_path,
        data_root=data_root, require_credentials=True,
    )
    profiles = _freeze_profiles(freeze_path)
    prompts = _prompt_map()
    summary = {"valid": 0, "failed_attempts": 0, "retries_scheduled": 0, "timing_deviations": 0, "outage_pauses": 0}
    paused_lineages: set[str] = set()

    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in sorted(rows, key=lambda r: int(r["execution_order"])):
        grouped.setdefault((row["service_lineage_id"], row["item_id"]), []).append(row)

    for (lineage, item_id), block in grouped.items():
        if lineage in paused_lineages:
            continue
        block_start = datetime.now(timezone.utc)
        queue: list[tuple[datetime, dict]] = [(block_start, row) for row in block]
        while queue:
            queue.sort(key=lambda pair: pair[0])
            due, row = queue.pop(0)
            now = datetime.now(timezone.utc)
            if due > now:
                time.sleep((due - now).total_seconds())
            cfg = profiles[lineage]
            profile = cfg["request_profile"]
            try:
                result = call_provider(
                    provider=row["provider"], model_id=row["model_id"], prompt=prompts[row["query_form_id"]],
                    profile=profile, timeout_s=timeout_s,
                )
            except AdapterFailure as exc:
                failed_at = datetime.now(timezone.utc)
                archive_failure(
                    data_root=data_root, row=row, failure_kind=exc.kind, message=exc.message,
                    failed_at_utc=failed_at.isoformat().replace("+00:00", "Z"), http_status=exc.http_status,
                    retry_after_seconds=exc.retry_after_seconds, response_body=exc.response_body,
                )
                summary["failed_attempts"] += 1

                # Explicit gateway/service-unavailable signals are treated as an apparent
                # service-wide outage: stop hammering that lineage and require the
                # Operations Lead to schedule a documented recovery block.
                if exc.http_status in {502, 503, 504}:
                    paused_lineages.add(lineage)
                    deviation_id = f"OUTAGE-PAUSE-{lineage}-{int(failed_at.timestamp())}"
                    write_deviation(
                        data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"], deviation_id=deviation_id,
                        record={
                            "deviation_id": deviation_id,
                            "type": "apparent_service_wide_outage_pause",
                            "service_lineage_id": lineage,
                            "trigger_http_status": exc.http_status,
                            "trigger_attempt_id": row["attempt_id"],
                            "paused_at_utc": failed_at.isoformat().replace("+00:00", "Z"),
                            "rule": "pause affected lineage; Operations Lead schedules a documented recovery block",
                        },
                    )
                    summary["outage_pauses"] += 1
                    queue.clear()
                    break

                decision = decide_retry(
                    attempt=int(row["attempt"]), failure_kind=exc.kind, failed_at=failed_at,
                    provider_retry_after_seconds=exc.retry_after_seconds, field_close=field_close,
                )
                if decision.retry:
                    retry_row = _clone_retry_row(row, int(decision.next_attempt))
                    archive_retry_link(
                        data_root=data_root, original_attempt_id=row["attempt_id"], retry_attempt_id=retry_row["attempt_id"],
                        site_id=row["site_id"], wave_id=row["wave_id"], due_at_utc=decision.due_at_utc,
                        failure_kind=exc.kind,
                    )
                    queue.append((parse_utc(decision.due_at_utc), retry_row))
                    summary["retries_scheduled"] += 1
                continue

            archive_success(
                data_root=data_root, row=row, request_payload=result.request_payload,
                response_json=result.response_json, raw_response_text=result.raw_response_text,
                http_status=result.http_status, returned_model=result.returned_model, usage=result.usage,
                started_at_utc=result.started_at_utc, completed_at_utc=result.completed_at_utc,
                duration_ms=result.duration_ms,
            )
            summary["valid"] += 1

        elapsed = (datetime.now(timezone.utc) - block_start).total_seconds()
        if elapsed > 7200:
            deviation_id = f"PAIRED-TIMING-{lineage}-{item_id}-{int(block_start.timestamp())}"
            write_deviation(
                data_root=data_root, site_id=block[0]["site_id"], wave_id=block[0]["wave_id"], deviation_id=deviation_id,
                record={
                    "deviation_id": deviation_id,
                    "type": "paired_block_exceeded_two_hours",
                    "service_lineage_id": lineage,
                    "item_id": item_id,
                    "elapsed_seconds": elapsed,
                    "rule": "retain valid calls, flag timing deviation, evaluate primary-comparison eligibility",
                },
            )
            summary["timing_deviations"] += 1
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if not args.execute:
        rows, _, start, close = preflight(
            manifest_path=args.manifest, freeze_path=args.freeze, authorization_path=args.authorization,
            data_root=args.data_root, require_credentials=False,
        )
        print(json.dumps({"preflight": "PASS", "rows": len(rows), "field_start": start.isoformat(), "field_close": close.isoformat()}, indent=2))
        return 0
    print(json.dumps(execute(
        manifest_path=args.manifest, freeze_path=args.freeze, authorization_path=args.authorization,
        data_root=args.data_root, timeout_s=args.timeout
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
