#!/usr/bin/env python3
"""Model-catalog and synthetic readiness evidence for API-only MIBO Core v2.0."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import api_preflight as api
import core_v2_runner as runner
from provider_adapters import AdapterFailure, call_provider
from raw_archive import canonical_json_bytes

SMOKE_SENTINEL = "ENABLED_AFTER_TERMS_REVIEW"
SYNTHETIC_PROMPT = (
    "MIBO Core v2 non-confirmatory technical readiness check. "
    "Return a short plain-text acknowledgement."
)


def _api_provider(provider: str) -> str:
    return "Perplexity" if provider == "Perplexity AI" else provider


def _safe_name(value: str) -> str:
    return value.lower().replace(" ", "-").replace("/", "_")


def _write_exclusive(path: Path, obj: Any) -> str:
    data = canonical_json_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def run_preflight(*, protocol_path: Path, freeze_path: Path, out_dir: Path,
                  smoke: bool = False, timeout_s: int = 30) -> dict[str, Any]:
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    raw = json.loads(freeze_path.read_text(encoding="utf-8"))
    wave_id, site_id = raw.get("wave_id"), raw.get("site_id")
    if not isinstance(wave_id, str) or not isinstance(site_id, str):
        raise ValueError("Core v2 provider freeze requires wave_id and site_id")
    freeze, freeze_sha = runner.load_freeze(
        freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id,
    )
    if out_dir.exists():
        raise FileExistsError(f"Core v2 preflight evidence already exists: {out_dir}")
    out_dir.mkdir(parents=True)
    services = {s["service_lineage_id"]: s for s in __import__("mibo_runner")._services()}
    catalogs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for service in services.values():
        label = service["provider"]
        provider = _api_provider(label)
        result, ids = api.fetch_catalog(provider, timeout_s=timeout_s)
        evidence = {
            "service_provider_label": label, "api_provider": provider,
            "endpoint": result.endpoint, "http_status": result.status,
            "started_at_utc": result.started_at_utc,
            "completed_at_utc": result.completed_at_utc,
            "duration_ms": result.duration_ms, "response": result.data,
            "normalized_model_ids": ids, "credential_value_recorded": False,
        }
        path = out_dir / "catalogs" / f"{_safe_name(label)}.json"
        catalogs[label] = {
            "file": str(path.relative_to(out_dir)),
            "sha256": _write_exclusive(path, evidence),
            "model_ids": ids, "model_count_in_response": len(ids),
        }
    checks: list[dict[str, Any]] = []
    smoke_checks: list[dict[str, Any]] = []
    for sid, service in services.items():
        label = service["provider"]
        provider = _api_provider(label)
        cfg = freeze["core_api"][sid]
        model_id = cfg["model_id"]
        listed = model_id in catalogs[label]["model_ids"]
        exact = api.fetch_exact_model(provider, model_id, timeout_s=timeout_s)
        returned_id = None
        verified = listed
        metadata_file = None
        metadata_sha = None
        if exact is not None:
            returned_id = api.returned_metadata_model_id(provider, exact.data)
            verified = returned_id == model_id
            record = {
                "service_provider_label": label, "api_provider": provider,
                "endpoint": exact.endpoint, "http_status": exact.status,
                "started_at_utc": exact.started_at_utc,
                "completed_at_utc": exact.completed_at_utc,
                "duration_ms": exact.duration_ms, "response": exact.data,
                "credential_value_recorded": False,
            }
            path = out_dir / "models" / _safe_name(label) / f"{model_id.replace('/', '_')}.json"
            metadata_file = str(path.relative_to(out_dir))
            metadata_sha = _write_exclusive(path, record)
        checks.append({
            "service_lineage_id": sid, "provider": label, "model_id": model_id,
            "listed_in_catalog_response": listed, "exact_metadata_verified": verified,
            "metadata_returned_model_id": returned_id,
            "metadata_file": metadata_file, "metadata_sha256": metadata_sha,
        })
        if not verified:
            errors.append(f"{label} Core v2 model was not verified: {model_id}")
        if smoke:
            if os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != SMOKE_SENTINEL:
                raise ValueError(f"Core v2 smoke requires MIBO_CORE_V2_SMOKE_TEST={SMOKE_SENTINEL}")
            try:
                result = call_provider(
                    provider=label, model_id=model_id, prompt=SYNTHETIC_PROMPT,
                    profile=cfg["request_profile"], timeout_s=max(timeout_s, 60),
                )
            except AdapterFailure as exc:
                errors.append(f"{label} Core v2 smoke failed for {model_id}: {exc.kind}")
                smoke_checks.append({
                    "service_lineage_id": sid, "provider": label, "model_id": model_id,
                    "pass": False, "failure_kind": exc.kind, "http_status": exc.http_status,
                })
            else:
                record = {
                    "protocol_version": runner.PROTOCOL_VERSION,
                    "scientific_class": runner.SCIENTIFIC_CLASS,
                    "readiness_only": True, "service_lineage_id": sid,
                    "provider": label, "requested_model": model_id,
                    "returned_model": result.returned_model, "http_status": result.http_status,
                    "started_at_utc": result.started_at_utc,
                    "completed_at_utc": result.completed_at_utc,
                    "duration_ms": result.duration_ms, "usage": result.usage,
                    "request_payload": result.request_payload, "response": result.response_json,
                    "synthetic_prompt_sha256": hashlib.sha256(SYNTHETIC_PROMPT.encode("utf-8")).hexdigest(),
                    "registered_mibo_prompt_used": False,
                    "pass": 200 <= result.http_status < 300,
                }
                path = out_dir / "smoke" / _safe_name(label) / f"{model_id.replace('/', '_')}.json"
                smoke_checks.append({
                    "service_lineage_id": sid, "provider": label, "model_id": model_id,
                    "pass": record["pass"], "file": str(path.relative_to(out_dir)),
                    "sha256": _write_exclusive(path, record),
                })
    report = {
        "schema_version": runner.PROTOCOL_VERSION,
        "protocol_version": runner.PROTOCOL_VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha,
        "scientific_class": runner.SCIENTIFIC_CLASS,
        "wave_id": wave_id, "site_id": site_id,
        "provider_freeze_sha256": freeze_sha,
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "catalogs": catalogs, "model_checks": checks,
        "synthetic_smoke_requested": smoke, "synthetic_smoke_checks": smoke_checks,
        "automatic_model_selection": False, "automatic_provider_substitution": False,
        "provider_freeze_modified": False, "registered_mibo_prompts_used": False,
        "errors": errors, "pass": not errors,
    }
    path = out_dir / "CORE_V2_API_PREFLIGHT_REPORT.json"
    report_sha = _write_exclusive(path, report)
    entries = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out_dir).as_posix()}"
        for p in sorted(out_dir.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.txt"
    ]
    sums = out_dir / "SHA256SUMS.txt"
    with sums.open("x", encoding="utf-8") as fh:
        fh.write("\n".join(entries) + "\n")
    return {**report, "report_sha256": report_sha,
            "sha256s_sha256": hashlib.sha256(sums.read_bytes()).hexdigest()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    report = run_preflight(
        protocol_path=args.protocol, freeze_path=args.freeze,
        out_dir=args.out_dir, smoke=args.smoke, timeout_s=args.timeout,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
