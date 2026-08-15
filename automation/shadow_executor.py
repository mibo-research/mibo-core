#!/usr/bin/env python3
"""Fail-closed executor for the exploratory MIBO API Shadow Archive v0.1.

The shadow archive is fully separated from MIBO Core confirmatory data. Real
provider calls require a finalized shadow freeze, exact manifest binding,
private human authorization, the registered field window, credentials, and a
separate execution sentinel.
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

import mibo_runner as core
from provider_adapters import AdapterFailure, call_provider
from retry_policy import decide_retry
import shadow_archive
import shadow_runner

EXECUTION_SENTINEL = "ENABLED_AFTER_SHADOW_GATE"
EXPECTED_ADAPTER = shadow_runner.EXPECTED_ADAPTER


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_authorization(path: Path, *, manifest_path: Path, freeze_path: Path,
                       wave_id: str, site_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("archive_class") != shadow_runner.ARCHIVE_CLASS:
        raise ValueError("shadow authorization archive_class mismatch")
    if data.get("confirmatory_use") != shadow_runner.CONFIRMATORY_USE:
        raise ValueError("shadow authorization must prohibit confirmatory use")
    if data.get("protocol_doi") != core.PROTOCOL_DOI:
        raise ValueError("shadow authorization protocol DOI mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("shadow authorization wave/site mismatch")
    for field in (
        "authorized", "terms_review_complete", "institutional_process_checked",
        "dry_run_complete", "acknowledge_exploratory_only",
    ):
        if data.get(field) is not True:
            raise ValueError(f"shadow authorization gate {field} is not true")
    if not data.get("operations_lead") or not data.get("authorized_at_utc"):
        raise ValueError("shadow authorization requires operations_lead and authorized_at_utc")
    if data.get("manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("shadow authorization manifest SHA-256 mismatch")
    if data.get("shadow_freeze_sha256") != sha256_file(freeze_path):
        raise ValueError("shadow authorization freeze SHA-256 mismatch")
    return data


def _validate_binding(rows: list[dict], freeze_path: Path,
                      *, require_credentials: bool) -> dict[str, Any]:
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    freeze, freeze_sha = shadow_runner.load_shadow_freeze(freeze_path, wave_id, site_id)
    for i, row in enumerate(rows, 1):
        sid = row["service_lineage_id"]
        cfg = freeze["shadow_api"].get(sid)
        if not isinstance(cfg, dict) or cfg.get("status") != "eligible":
            raise ValueError(f"row {i}: lineage is not eligible in API Shadow freeze")
        if row.get("model_id") != cfg.get("model_id"):
            raise ValueError(f"row {i}: model_id does not match API Shadow freeze")
        if row.get("shadow_freeze_sha256") != freeze_sha:
            raise ValueError(f"row {i}: API Shadow freeze SHA-256 mismatch")
        profile = cfg.get("request_profile")
        if not isinstance(profile, dict):
            raise ValueError(f"row {i}: missing request_profile")
        expected = EXPECTED_ADAPTER.get(row["provider"])
        if profile.get("adapter") != expected:
            raise ValueError(f"row {i}: request_profile adapter mismatch")
        if shadow_runner.FORBIDDEN_PROFILE_KEYS.intersection(profile):
            raise ValueError(f"row {i}: closed shadow profile contains forbidden capability keys")
        if row["provider"] == "Perplexity" and profile.get("disable_search") is not True:
            raise ValueError(f"row {i}: Perplexity closed shadow requires disable_search=true")
        key_env = profile.get("api_key_env")
        if not isinstance(key_env, str) or not key_env:
            raise ValueError(f"row {i}: request_profile requires api_key_env")
        if require_credentials and not os.environ.get(key_env):
            raise ValueError(f"row {i}: required credential environment variable {key_env} is not set")
    return freeze


def preflight(*, manifest_path: Path, freeze_path: Path, authorization_path: Path,
              data_root: Path, now: datetime | None = None,
              require_credentials: bool = False) -> tuple[list[dict], dict, dict, datetime, datetime]:
    rows = shadow_runner.read_csv(manifest_path)
    errors = shadow_runner.validate_shadow_manifest(rows, freeze_path)
    if errors:
        raise ValueError("shadow manifest validation failed: " + "; ".join(errors))
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    freeze = _validate_binding(rows, freeze_path, require_credentials=require_credentials)
    auth = load_authorization(
        authorization_path, manifest_path=manifest_path, freeze_path=freeze_path,
        wave_id=wave_id, site_id=site_id,
    )
    wave = core._wave(wave_id)
    field_start = parse_utc(wave["start_utc"])
    field_close = parse_utc(wave["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not (field_start <= current < field_close):
        raise ValueError("current time is outside the registered primary field window")
    root = shadow_archive.shadow_wave_root(data_root, site_id, wave_id)
    root.mkdir(parents=True, exist_ok=True)
    probe = root / ".write-test"
    with probe.open("w", encoding="utf-8") as fh:
        fh.write("ok")
    probe.unlink()
    return rows, freeze, auth, field_start, field_close


def _prompt_map() -> dict[str, str]:
    return {f["query_form_id"]: f["text"] for f in core._forms()}


def _clone_retry_row(row: dict, next_attempt: int) -> dict:
    service = next(s for s in core._services() if s["service_lineage_id"] == row["service_lineage_id"])
    clone = dict(row)
    clone["retry_of_attempt_id"] = row["attempt_id"]
    clone["attempt"] = next_attempt
    clone["attempt_id"] = core.attempt_id(
        row["site_id"], row["wave_id"], service["short_id"], row["line_id"],
        row["item_id"], row["language"], row["window_id"],
        int(row["replication"]), next_attempt,
    )
    clone["status"] = "retry_intended_exploratory"
    return clone


def _processed_attempt_ids(data_root: Path, site_id: str, wave_id: str) -> set[str]:
    root = shadow_archive.shadow_wave_root(data_root, site_id, wave_id)
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


def _existing_retry_rows(data_root: Path, initial_rows: list[dict]) -> list[tuple[datetime, dict]]:
    site_id = initial_rows[0]["site_id"]
    wave_id = initial_rows[0]["wave_id"]
    root = shadow_archive.shadow_wave_root(data_root, site_id, wave_id) / "metadata"
    if not root.exists():
        return []
    row_map = {r["attempt_id"]: r for r in initial_rows}
    pending_links: list[dict] = []
    for path in root.glob("retry-link-*.json"):
        try:
            pending_links.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    # At most two retry generations exist, so repeated passes are sufficient and deterministic.
    for _ in range(3):
        changed = False
        for link in pending_links:
            original = row_map.get(link.get("original_attempt_id"))
            target = link.get("retry_attempt_id")
            if original is None or not target or target in row_map:
                continue
            next_attempt = int(original["attempt"]) + 1
            clone = _clone_retry_row(original, next_attempt)
            if clone["attempt_id"] != target:
                raise ValueError("stored shadow retry link does not match deterministic Attempt ID")
            row_map[target] = clone
            changed = True
        if not changed:
            break
    done = _processed_attempt_ids(data_root, site_id, wave_id)
    queue: list[tuple[datetime, dict]] = []
    for link in pending_links:
        target = link.get("retry_attempt_id")
        if target in row_map and target not in done:
            queue.append((parse_utc(link["due_at_utc"]), row_map[target]))
    return queue


def execute(*, manifest_path: Path, freeze_path: Path, authorization_path: Path,
            data_root: Path, timeout_s: int = 180) -> dict[str, int]:
    if os.environ.get("MIBO_API_SHADOW_EXECUTION") != EXECUTION_SENTINEL:
        raise RuntimeError("API Shadow execution sentinel is not enabled")
    rows, freeze, _auth, _field_start, field_close = preflight(
        manifest_path=manifest_path, freeze_path=freeze_path,
        authorization_path=authorization_path, data_root=data_root,
        require_credentials=True,
    )
    prompts = _prompt_map()
    done = _processed_attempt_ids(data_root, rows[0]["site_id"], rows[0]["wave_id"])
    now = datetime.now(timezone.utc)
    queue: list[tuple[datetime, int, str, dict]] = []
    for row in sorted(rows, key=lambda r: int(r["execution_order"])):
        if row["attempt_id"] not in done:
            queue.append((now, int(row["execution_order"]), row["attempt_id"], row))
    for due, retry_row in _existing_retry_rows(data_root, rows):
        queue.append((due, int(retry_row["execution_order"]), retry_row["attempt_id"], retry_row))

    summary = {
        "valid": 0,
        "already_processed": len(done),
        "failed_attempts": 0,
        "retries_scheduled": 0,
        "rate_limit_pauses": 0,
        "outage_pauses": 0,
        "lineage_suspensions": 0,
        "skipped_after_suspension": 0,
    }
    pause_until: dict[str, datetime] = {}
    suspended: set[str] = set()

    while queue:
        queue.sort(key=lambda x: (x[0], x[1], x[2]))
        due, order, aid, row = queue.pop(0)
        lineage = row["service_lineage_id"]
        if lineage in suspended:
            summary["skipped_after_suspension"] += 1
            continue
        pause = pause_until.get(lineage)
        if pause and due < pause:
            queue.append((pause, order, aid, row))
            continue
        current = datetime.now(timezone.utc)
        if current >= field_close:
            break
        if due > current:
            time.sleep(min((due - current).total_seconds(), max(0.0, (field_close - current).total_seconds())))
            current = datetime.now(timezone.utc)
            if current >= field_close:
                break

        cfg = freeze["shadow_api"][lineage]
        profile = cfg["request_profile"]
        try:
            result = call_provider(
                provider=row["provider"], model_id=row["model_id"],
                prompt=prompts[row["query_form_id"]], profile=profile,
                timeout_s=timeout_s,
            )
        except AdapterFailure as exc:
            failed_at = datetime.now(timezone.utc)
            shadow_archive.archive_failure(
                data_root=data_root, row=row, failure_kind=exc.kind,
                message=exc.message,
                failed_at_utc=failed_at.isoformat().replace("+00:00", "Z"),
                http_status=exc.http_status,
                retry_after_seconds=exc.retry_after_seconds,
                response_body=exc.response_body,
            )
            summary["failed_attempts"] += 1
            decision = decide_retry(
                attempt=int(row["attempt"]), failure_kind=exc.kind,
                failed_at=failed_at,
                provider_retry_after_seconds=exc.retry_after_seconds,
                field_close=field_close,
            )
            retry_due: datetime | None = None
            if decision.retry:
                retry_row = _clone_retry_row(row, int(decision.next_attempt))
                shadow_archive.archive_retry_link(
                    data_root=data_root,
                    original_attempt_id=row["attempt_id"],
                    retry_attempt_id=retry_row["attempt_id"],
                    site_id=row["site_id"], wave_id=row["wave_id"],
                    due_at_utc=decision.due_at_utc,
                    failure_kind=exc.kind,
                )
                retry_due = parse_utc(decision.due_at_utc)
                queue.append((retry_due, order, retry_row["attempt_id"], retry_row))
                summary["retries_scheduled"] += 1

            if exc.http_status == 429 and retry_due is not None:
                pause_until[lineage] = retry_due
                summary["rate_limit_pauses"] += 1
            if exc.http_status in {502, 503, 504}:
                if retry_due is not None:
                    pause_until[lineage] = retry_due
                    summary["outage_pauses"] += 1
                    deviation_id = f"SHADOW-OUTAGE-PAUSE-{lineage}-{int(failed_at.timestamp())}"
                    shadow_archive.write_deviation(
                        data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"],
                        deviation_id=deviation_id,
                        record={
                            "deviation_id": deviation_id,
                            "type": "api_shadow_service_pause",
                            "service_lineage_id": lineage,
                            "trigger_attempt_id": row["attempt_id"],
                            "trigger_http_status": exc.http_status,
                            "resume_after_utc": decision.due_at_utc,
                        },
                    )
                else:
                    suspended.add(lineage)
                    summary["lineage_suspensions"] += 1
                    deviation_id = f"SHADOW-LINEAGE-SUSPEND-{lineage}-{int(failed_at.timestamp())}"
                    shadow_archive.write_deviation(
                        data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"],
                        deviation_id=deviation_id,
                        record={
                            "deviation_id": deviation_id,
                            "type": "api_shadow_lineage_suspended_after_retry_exhaustion",
                            "service_lineage_id": lineage,
                            "trigger_attempt_id": row["attempt_id"],
                            "trigger_http_status": exc.http_status,
                            "rule": "retain missingness; do not substitute another model",
                        },
                    )
            continue

        shadow_archive.archive_success(
            data_root=data_root, row=row,
            request_payload=result.request_payload,
            response_json=result.response_json,
            raw_response_text=result.raw_response_text,
            http_status=result.http_status,
            returned_model=result.returned_model,
            usage=result.usage,
            started_at_utc=result.started_at_utc,
            completed_at_utc=result.completed_at_utc,
            duration_ms=result.duration_ms,
        )
        summary["valid"] += 1

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
        rows, _, _, start, close = preflight(
            manifest_path=args.manifest, freeze_path=args.freeze,
            authorization_path=args.authorization, data_root=args.data_root,
            require_credentials=False,
        )
        print(json.dumps({
            "preflight": "PASS",
            "archive_class": shadow_runner.ARCHIVE_CLASS,
            "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
            "rows": len(rows),
            "field_start": start.isoformat(),
            "field_close": close.isoformat(),
        }, indent=2))
        return 0

    print(json.dumps(execute(
        manifest_path=args.manifest, freeze_path=args.freeze,
        authorization_path=args.authorization, data_root=args.data_root,
        timeout_s=args.timeout,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
