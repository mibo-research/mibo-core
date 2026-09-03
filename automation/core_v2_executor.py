#!/usr/bin/env python3
"""Fail-closed executor for prospectively registered API-only MIBO Core v2.0."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
    if data.get("schema_version") != runner.PROTOCOL_VERSION or data.get("protocol_version") != runner.PROTOCOL_VERSION:
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
    expected_hashes = {
        "protocol_file_sha256": sha256_file(protocol_path),
        "manifest_sha256": sha256_file(manifest_path),
        "provider_freeze_sha256": sha256_file(freeze_path),
    }
    for field, expected in expected_hashes.items():
        if data.get(field) != expected:
            raise ValueError(f"Core v2 authorization {field} mismatch")
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
    if require_credentials:
        _validate_credentials(rows, freeze)
    wave_cfg = runner.wave(protocol, wave_id)
    start = parse_utc(wave_cfg["start_utc"])
    close = parse_utc(wave_cfg["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not (start <= current < close):
        raise ValueError("current time is outside the prospectively registered Core v2 field window")
    root = archive.wave_root(data_root, site_id, wave_id)
    root.mkdir(parents=True, exist_ok=True)
    probe = root / ".write-test"
    with probe.open("x", encoding="utf-8") as fh:
        fh.write("ok")
    probe.unlink()
    return rows, freeze, authorization, start, close


def _prompt_map() -> dict[str, str]:
    return {f["query_form_id"]: f["text"] for f in v1._forms()}


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


def _processed_attempt_ids(data_root: Path, site_id: str, wave_id: str) -> set[str]:
    root = archive.wave_root(data_root, site_id, wave_id)
    done: set[str] = set()
    metadata = root / "metadata"
    failures = root / "failures"
    if metadata.exists():
        for path in metadata.glob("*.json"):
            if path.name.startswith("retry-link-"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("attempt_id"):
                done.add(data["attempt_id"])
    if failures.exists():
        done |= {p.stem for p in failures.glob("*.json")}
    return done


def _existing_retry_rows(data_root: Path, initial_rows: list[dict[str, Any]]) -> list[tuple[datetime, dict[str, Any]]]:
    site_id = initial_rows[0]["site_id"]
    wave_id = initial_rows[0]["wave_id"]
    metadata = archive.wave_root(data_root, site_id, wave_id) / "metadata"
    if not metadata.exists():
        return []
    row_map = {r["attempt_id"]: r for r in initial_rows}
    links: list[dict[str, Any]] = []
    for path in metadata.glob("retry-link-*.json"):
        try:
            links.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
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
    done = _processed_attempt_ids(data_root, site_id, wave_id)
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
    prompts = _prompt_map()
    done = _processed_attempt_ids(data_root, rows[0]["site_id"], rows[0]["wave_id"])
    now = datetime.now(timezone.utc)
    queue: list[tuple[datetime, int, str, dict[str, Any]]] = [
        (now, int(row["execution_order"]), row["attempt_id"], row)
        for row in rows if row["attempt_id"] not in done
    ]
    for due, retry_row in _existing_retry_rows(data_root, rows):
        queue.append((due, int(retry_row["execution_order"]), retry_row["attempt_id"], retry_row))
    summary = {
        "valid": 0, "already_processed": len(done), "failed_attempts": 0,
        "retries_scheduled": 0, "rate_limit_pauses": 0, "outage_pauses": 0,
        "lineage_suspensions": 0, "skipped_after_suspension": 0,
    }
    pause_until: dict[str, datetime] = {}
    suspended: set[str] = set()
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
        if current >= field_close:
            break
        if due > current:
            time.sleep(min((due - current).total_seconds(), max(0.0, (field_close - current).total_seconds())))
            if datetime.now(timezone.utc) >= field_close:
                break
        cfg = freeze["core_api"][lineage]
        try:
            result = call_provider(
                provider=row["provider"], model_id=row["model_id"],
                prompt=prompts[row["query_form_id"]],
                profile=cfg["request_profile"], timeout_s=timeout_s,
            )
        except AdapterFailure as exc:
            failed_at = datetime.now(timezone.utc)
            archive.archive_failure(
                data_root=data_root, row=row, failure_kind=exc.kind,
                message=exc.message, failed_at_utc=failed_at.isoformat().replace("+00:00", "Z"),
                http_status=exc.http_status, retry_after_seconds=exc.retry_after_seconds,
                response_body=exc.response_body,
            )
            summary["failed_attempts"] += 1
            decision = decide_retry(
                attempt=int(row["attempt"]), failure_kind=exc.kind,
                failed_at=failed_at, provider_retry_after_seconds=exc.retry_after_seconds,
                field_close=field_close,
            )
            retry_due: datetime | None = None
            if decision.retry:
                retry_row = _clone_retry_row(row, int(decision.next_attempt))
                archive.archive_retry_link(
                    data_root=data_root, original_attempt_id=row["attempt_id"],
                    retry_attempt_id=retry_row["attempt_id"], site_id=row["site_id"],
                    wave_id=row["wave_id"], due_at_utc=str(decision.due_at_utc),
                    failure_kind=exc.kind,
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
                    )
            continue
        archive.archive_success(
            data_root=data_root, row=row, request_payload=result.request_payload,
            response_json=result.response_json, raw_response_text=result.raw_response_text,
            http_status=result.http_status, returned_model=result.returned_model,
            usage=result.usage, started_at_utc=result.started_at_utc,
            completed_at_utc=result.completed_at_utc, duration_ms=result.duration_ms,
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
            "preflight": "PASS", "protocol_version": runner.PROTOCOL_VERSION,
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
