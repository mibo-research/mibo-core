#!/usr/bin/env python3
"""Provider-model readiness evidence for the exploratory API Shadow Archive."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import api_preflight as api
from provider_adapters import AdapterFailure, call_provider
from raw_archive import canonical_json_bytes
import shadow_runner

SMOKE_SENTINEL = "ENABLED_AFTER_TERMS_REVIEW"
SYNTHETIC_PROMPT = (
    "MIBO API Shadow non-confirmatory technical readiness check. "
    "Return a short plain-text acknowledgement."
)


def _write_exclusive(path: Path, obj: Any) -> str:
    data = canonical_json_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def run_preflight(*, freeze_path: Path, out_dir: Path, smoke: bool = False,
                  timeout_s: int = 30) -> dict[str, Any]:
    raw = json.loads(freeze_path.read_text(encoding="utf-8"))
    wave_id = raw.get("wave_id")
    site_id = raw.get("site_id")
    if not isinstance(wave_id, str) or not isinstance(site_id, str):
        raise ValueError("shadow freeze requires wave_id and site_id")
    freeze, freeze_sha = shadow_runner.load_shadow_freeze(freeze_path, wave_id, site_id)
    if out_dir.exists():
        raise FileExistsError(f"shadow preflight evidence directory already exists: {out_dir}")
    out_dir.mkdir(parents=True)

    services = {s["service_lineage_id"]: s for s in __import__("mibo_runner")._services()}
    eligible = shadow_runner.eligible_lineages(freeze)
    providers = sorted({services[sid]["provider"] for sid in eligible})
    catalogs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for provider in providers:
        result, ids = api.fetch_catalog(provider, timeout_s=timeout_s)
        evidence = {
            "provider": provider,
            "endpoint": result.endpoint,
            "http_status": result.status,
            "started_at_utc": result.started_at_utc,
            "completed_at_utc": result.completed_at_utc,
            "duration_ms": result.duration_ms,
            "response": result.data,
            "normalized_model_ids": ids,
            "credential_value_recorded": False,
        }
        path = out_dir / "catalogs" / f"{provider.lower()}.json"
        digest = _write_exclusive(path, evidence)
        catalogs[provider] = {
            "file": str(path.relative_to(out_dir)),
            "sha256": digest,
            "model_ids": ids,
            "model_count_in_response": len(ids),
        }

    model_checks: list[dict[str, Any]] = []
    smoke_checks: list[dict[str, Any]] = []
    for sid in eligible:
        service = services[sid]
        provider = service["provider"]
        cfg = freeze["shadow_api"][sid]
        model_id = cfg["model_id"]
        listed = model_id in catalogs[provider]["model_ids"]
        exact = api.fetch_exact_model(provider, model_id, timeout_s=timeout_s)
        returned_id = None
        exact_ok = listed
        metadata_file = None
        metadata_sha = None
        if exact is not None:
            returned_id = api.returned_metadata_model_id(provider, exact.data)
            exact_ok = returned_id == model_id
            record = {
                "provider": provider,
                "endpoint": exact.endpoint,
                "http_status": exact.status,
                "started_at_utc": exact.started_at_utc,
                "completed_at_utc": exact.completed_at_utc,
                "duration_ms": exact.duration_ms,
                "response": exact.data,
                "credential_value_recorded": False,
            }
            path = out_dir / "models" / provider.lower() / f"{model_id.replace('/', '_')}.json"
            metadata_sha = _write_exclusive(path, record)
            metadata_file = str(path.relative_to(out_dir))
        check = {
            "service_lineage_id": sid,
            "provider": provider,
            "model_id": model_id,
            "listed_in_catalog_response": listed,
            "exact_metadata_verified": exact_ok,
            "metadata_returned_model_id": returned_id,
            "metadata_file": metadata_file,
            "metadata_sha256": metadata_sha,
        }
        model_checks.append(check)
        if not exact_ok:
            errors.append(f"{provider} shadow model was not verified: {model_id}")

        if smoke:
            if os.environ.get("MIBO_API_SHADOW_SMOKE_TEST") != SMOKE_SENTINEL:
                raise ValueError(
                    f"shadow smoke test requires MIBO_API_SHADOW_SMOKE_TEST={SMOKE_SENTINEL}"
                )
            try:
                result = call_provider(
                    provider=provider, model_id=model_id,
                    prompt=SYNTHETIC_PROMPT, profile=cfg["request_profile"],
                    timeout_s=max(timeout_s, 60),
                )
            except AdapterFailure as exc:
                errors.append(f"{provider} shadow smoke failed for {model_id}: {exc.kind}")
                smoke_checks.append({
                    "service_lineage_id": sid,
                    "provider": provider,
                    "model_id": model_id,
                    "pass": False,
                    "failure_kind": exc.kind,
                    "http_status": exc.http_status,
                })
            else:
                smoke_record = {
                    "archive_class": shadow_runner.ARCHIVE_CLASS,
                    "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
                    "service_lineage_id": sid,
                    "provider": provider,
                    "requested_model": model_id,
                    "returned_model": result.returned_model,
                    "http_status": result.http_status,
                    "started_at_utc": result.started_at_utc,
                    "completed_at_utc": result.completed_at_utc,
                    "duration_ms": result.duration_ms,
                    "usage": result.usage,
                    "request_payload": result.request_payload,
                    "response": result.response_json,
                    "synthetic_prompt_sha256": hashlib.sha256(SYNTHETIC_PROMPT.encode("utf-8")).hexdigest(),
                    "registered_mibo_prompt_used": False,
                    "pass": 200 <= result.http_status < 300,
                }
                path = out_dir / "smoke" / provider.lower() / f"{model_id.replace('/', '_')}.json"
                digest = _write_exclusive(path, smoke_record)
                smoke_checks.append({
                    "service_lineage_id": sid,
                    "provider": provider,
                    "model_id": model_id,
                    "pass": smoke_record["pass"],
                    "file": str(path.relative_to(out_dir)),
                    "sha256": digest,
                })

    report = {
        "schema_version": "0.1",
        "archive_name": "MIBO API Shadow Archive",
        "archive_class": shadow_runner.ARCHIVE_CLASS,
        "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
        "protocol_doi": freeze["protocol_doi"],
        "wave_id": wave_id,
        "site_id": site_id,
        "shadow_freeze_sha256": freeze_sha,
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "eligible_lineages": eligible,
        "catalogs": catalogs,
        "model_checks": model_checks,
        "synthetic_smoke_requested": smoke,
        "synthetic_smoke_checks": smoke_checks,
        "automatic_model_selection": False,
        "shadow_freeze_modified": False,
        "registered_mibo_prompts_used": False,
        "errors": errors,
        "pass": not errors,
    }
    report_path = out_dir / "API_SHADOW_PREFLIGHT_REPORT.json"
    report_sha = _write_exclusive(report_path, report)
    sums: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(out_dir).as_posix()}")
    sums_path = out_dir / "SHA256SUMS.txt"
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")
    return {**report, "report_sha256": report_sha, "sha256s_sha256": hashlib.sha256(sums_path.read_bytes()).hexdigest()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    report = run_preflight(
        freeze_path=args.freeze, out_dir=args.out_dir,
        smoke=args.smoke, timeout_s=args.timeout,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
