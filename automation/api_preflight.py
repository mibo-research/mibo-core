#!/usr/bin/env python3
"""Non-confirmatory API discovery and readiness evidence for MIBO Core v1.0.

This module maximizes automation around the paired API condition without
changing the frozen scientific design. It can:

1. inventory model catalogs exposed by official provider APIs;
2. verify exact prospectively frozen Live/Frozen model IDs via provider model
   metadata endpoints where available;
3. optionally make one synthetic smoke-test generation per frozen model; and
4. write append-only, hash-bound private readiness evidence.

It never chooses a model, promotes a provider, rewrites a Configuration Freeze
Record, uses a confirmatory MIBO prompt, or falls back to another model.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import mibo_runner as core
from provider_adapters import AdapterFailure, call_provider
from raw_archive import canonical_json_bytes

PROTOCOL_DOI = "10.5281/zenodo.21936410"
SMOKE_SENTINEL = "ENABLED_AFTER_TERMS_REVIEW"
SYNTHETIC_SMOKE_PROMPT = (
    "MIBO non-confirmatory technical readiness check. "
    "Return a short plain-text acknowledgement."
)

PROVIDER_SPECS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "credential_env": "OPENAI_API_KEY",
        "catalog_url": "https://api.openai.com/v1/models",
        "model_url": "https://api.openai.com/v1/models/{model}",
    },
    "Anthropic": {
        "credential_env": "ANTHROPIC_API_KEY",
        "catalog_url": "https://api.anthropic.com/v1/models",
        "model_url": "https://api.anthropic.com/v1/models/{model}",
    },
    "Google": {
        "credential_env": "GEMINI_API_KEY",
        "catalog_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "model_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}",
    },
    "Perplexity": {
        "credential_env": "PERPLEXITY_API_KEY",
        "catalog_url": "https://api.perplexity.ai/v1/models",
        "model_url": "",
    },
}


@dataclass(frozen=True)
class HTTPResult:
    provider: str
    endpoint: str
    status: int
    started_at_utc: str
    completed_at_utc: str
    duration_ms: int
    raw_text: str
    data: dict[str, Any]


class APIPreflightFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_exclusive(path: Path, obj: Any) -> str:
    data = canonical_json_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def _credential(provider: str) -> tuple[str, str]:
    spec = PROVIDER_SPECS[provider]
    env_name = spec["credential_env"]
    value = os.environ.get(env_name)
    if not value:
        raise APIPreflightFailure(f"{provider} credential {env_name} is not set")
    return env_name, value


def _headers(provider: str) -> dict[str, str]:
    _env, token = _credential(provider)
    if provider in {"OpenAI", "Perplexity"}:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if provider == "Anthropic":
        return {
            "x-api-key": token,
            "anthropic-version": "2023-06-01",
            "Accept": "application/json",
        }
    if provider == "Google":
        return {"x-goog-api-key": token, "Accept": "application/json"}
    raise APIPreflightFailure(f"unsupported provider {provider}")


def _get_json(*, provider: str, url: str, timeout_s: int = 30) -> HTTPResult:
    req = Request(url, headers=_headers(provider), method="GET")
    started = utc_now()
    t0 = time.monotonic()
    try:
        with urlopen(req, timeout=timeout_s) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise APIPreflightFailure(f"{provider} GET {url} returned HTTP {exc.code}: {raw[:500]}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise APIPreflightFailure(f"{provider} GET {url} timed out") from exc
    except URLError as exc:
        raise APIPreflightFailure(f"{provider} GET {url} failed: {exc.reason}") from exc
    completed = utc_now()
    duration_ms = int((time.monotonic() - t0) * 1000)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise APIPreflightFailure(f"{provider} GET {url} returned non-JSON data") from exc
    if not isinstance(parsed, dict):
        raise APIPreflightFailure(f"{provider} GET {url} returned a non-object JSON root")
    return HTTPResult(
        provider=provider, endpoint=url, status=status,
        started_at_utc=started, completed_at_utc=completed,
        duration_ms=duration_ms, raw_text=raw, data=parsed,
    )


def normalize_model_id(provider: str, value: str) -> str:
    if provider == "Google" and value.startswith("models/"):
        return value.split("/", 1)[1]
    return value


def catalog_model_ids(provider: str, data: dict[str, Any]) -> list[str]:
    if provider in {"OpenAI", "Anthropic", "Perplexity"}:
        items = data.get("data") or []
        ids = [item.get("id") for item in items if isinstance(item, dict)]
    elif provider == "Google":
        items = data.get("models") or []
        ids = [item.get("name") for item in items if isinstance(item, dict)]
    else:
        ids = []
    return sorted({normalize_model_id(provider, value) for value in ids if isinstance(value, str) and value})


def fetch_catalog(provider: str, timeout_s: int = 30) -> tuple[HTTPResult, list[str]]:
    spec = PROVIDER_SPECS[provider]
    result = _get_json(provider=provider, url=spec["catalog_url"], timeout_s=timeout_s)
    return result, catalog_model_ids(provider, result.data)


def fetch_exact_model(provider: str, model_id: str, timeout_s: int = 30) -> HTTPResult | None:
    template = PROVIDER_SPECS[provider]["model_url"]
    if not template:
        return None
    endpoint = template.format(model=quote(model_id, safe=""))
    return _get_json(provider=provider, url=endpoint, timeout_s=timeout_s)


def returned_metadata_model_id(provider: str, data: dict[str, Any]) -> str | None:
    if provider in {"OpenAI", "Anthropic"}:
        value = data.get("id")
    elif provider == "Google":
        value = data.get("name")
    else:
        value = None
    if not isinstance(value, str) or not value:
        return None
    return normalize_model_id(provider, value)


def eligible_entries(freeze_path: Path) -> tuple[dict[str, Any], str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    raw = json.loads(freeze_path.read_text(encoding="utf-8"))
    wave_id = raw.get("wave_id")
    site_id = raw.get("site_id")
    if not isinstance(wave_id, str) or not isinstance(site_id, str):
        raise APIPreflightFailure("provider freeze requires wave_id and site_id")
    freeze, freeze_sha = core.load_provider_freeze(freeze_path, wave_id, site_id)
    paired = freeze.get("paired_api") or {}
    entries: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for service in core._services():
        cfg = paired.get(service["service_lineage_id"])
        if not isinstance(cfg, dict) or cfg.get("status") != "eligible":
            continue
        for field in (
            "live_model_id", "frozen_model_id", "comparability_class", "request_profile",
            "terms_review_date", "terms_review_source",
        ):
            if not cfg.get(field):
                raise APIPreflightFailure(
                    f"{service['service_lineage_id']} eligible freeze missing {field}"
                )
        entries.append((service, cfg))
    return freeze, freeze_sha, entries


def _http_evidence(result: HTTPResult, model_ids: list[str] | None = None) -> dict[str, Any]:
    evidence = {
        "provider": result.provider,
        "endpoint": result.endpoint,
        "http_status": result.status,
        "started_at_utc": result.started_at_utc,
        "completed_at_utc": result.completed_at_utc,
        "duration_ms": result.duration_ms,
        "response": result.data,
        "credential_value_recorded": False,
    }
    if model_ids is not None:
        evidence["normalized_model_ids"] = model_ids
    return evidence


def run_preflight(*, freeze_path: Path, out_dir: Path, smoke: bool = False,
                  catalog_all_present: bool = False, timeout_s: int = 30) -> dict[str, Any]:
    if out_dir.exists():
        raise FileExistsError(f"API preflight evidence directory already exists: {out_dir}")
    freeze, freeze_sha, entries = eligible_entries(freeze_path)
    out_dir.mkdir(parents=True)

    required_providers = sorted({service["provider"] for service, _cfg in entries})
    catalog_providers = set(required_providers)
    if catalog_all_present:
        for provider, spec in PROVIDER_SPECS.items():
            if os.environ.get(spec["credential_env"]):
                catalog_providers.add(provider)

    catalogs: dict[str, dict[str, Any]] = {}
    for provider in sorted(catalog_providers):
        result, ids = fetch_catalog(provider, timeout_s=timeout_s)
        path = out_dir / "catalogs" / f"{provider.lower()}.json"
        digest = _write_exclusive(path, _http_evidence(result, ids))
        catalogs[provider] = {
            "file": str(path.relative_to(out_dir)),
            "sha256": digest,
            "model_count_in_response": len(ids),
            "model_ids": ids,
        }

    exact_checks: list[dict[str, Any]] = []
    smoke_checks: list[dict[str, Any]] = []
    errors: list[str] = []

    for service, cfg in entries:
        provider = service["provider"]
        profile = cfg["request_profile"]
        for role, field in (("paired_live_reference", "live_model_id"), ("frozen_reference", "frozen_model_id")):
            model_id = str(cfg[field])
            catalog_ids = catalogs[provider]["model_ids"]
            listed = model_id in catalog_ids
            detail = fetch_exact_model(provider, model_id, timeout_s=timeout_s)
            metadata_ok = False
            metadata_path = None
            metadata_sha = None
            returned_id = None
            if detail is not None:
                returned_id = returned_metadata_model_id(provider, detail.data)
                metadata_ok = returned_id == model_id
                metadata_path_obj = out_dir / "models" / provider.lower() / f"{role}-{model_id.replace('/', '_')}.json"
                metadata_sha = _write_exclusive(metadata_path_obj, _http_evidence(detail))
                metadata_path = str(metadata_path_obj.relative_to(out_dir))
            else:
                metadata_ok = listed
            check = {
                "service_lineage_id": service["service_lineage_id"],
                "provider": provider,
                "role": role,
                "model_id": model_id,
                "listed_in_catalog_response": listed,
                "exact_metadata_verified": metadata_ok,
                "metadata_returned_model_id": returned_id,
                "metadata_file": metadata_path,
                "metadata_sha256": metadata_sha,
            }
            exact_checks.append(check)
            if not metadata_ok:
                errors.append(f"{provider} {role} model metadata not verified for {model_id}")

            if smoke:
                if os.environ.get("MIBO_API_SMOKE_TEST") != SMOKE_SENTINEL:
                    raise APIPreflightFailure(
                        f"synthetic smoke test requires MIBO_API_SMOKE_TEST={SMOKE_SENTINEL}"
                    )
                try:
                    result = call_provider(
                        provider=provider, model_id=model_id,
                        prompt=SYNTHETIC_SMOKE_PROMPT, profile=profile,
                        timeout_s=max(timeout_s, 60),
                    )
                except AdapterFailure as exc:
                    errors.append(f"{provider} synthetic smoke failed for {model_id}: {exc.kind}")
                    smoke_checks.append({
                        "service_lineage_id": service["service_lineage_id"],
                        "provider": provider,
                        "role": role,
                        "model_id": model_id,
                        "pass": False,
                        "failure_kind": exc.kind,
                        "http_status": exc.http_status,
                    })
                else:
                    smoke_record = {
                        "service_lineage_id": service["service_lineage_id"],
                        "provider": provider,
                        "role": role,
                        "requested_model": model_id,
                        "returned_model": result.returned_model,
                        "http_status": result.http_status,
                        "started_at_utc": result.started_at_utc,
                        "completed_at_utc": result.completed_at_utc,
                        "duration_ms": result.duration_ms,
                        "usage": result.usage,
                        "request_payload": result.request_payload,
                        "response": result.response_json,
                        "synthetic_prompt_sha256": hashlib.sha256(SYNTHETIC_SMOKE_PROMPT.encode("utf-8")).hexdigest(),
                        "confirmatory_prompt_used": False,
                        "pass": 200 <= result.http_status < 300,
                    }
                    smoke_path = out_dir / "smoke" / provider.lower() / f"{role}-{model_id.replace('/', '_')}.json"
                    smoke_sha = _write_exclusive(smoke_path, smoke_record)
                    smoke_checks.append({
                        "service_lineage_id": service["service_lineage_id"],
                        "provider": provider,
                        "role": role,
                        "model_id": model_id,
                        "pass": smoke_record["pass"],
                        "file": str(smoke_path.relative_to(out_dir)),
                        "sha256": smoke_sha,
                    })

    report = {
        "schema_version": "1.0",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": freeze["wave_id"],
        "site_id": freeze["site_id"],
        "provider_freeze_sha256": freeze_sha,
        "checked_at_utc": utc_now(),
        "eligible_lineage_count": len(entries),
        "required_providers": required_providers,
        "catalog_providers": sorted(catalog_providers),
        "catalogs": catalogs,
        "exact_model_checks": exact_checks,
        "synthetic_smoke_requested": smoke,
        "synthetic_smoke_checks": smoke_checks,
        "automatic_model_selection": False,
        "automatic_provider_promotion": False,
        "configuration_freeze_modified": False,
        "confirmatory_prompts_used": False,
        "errors": errors,
        "pass": not errors,
    }
    report_path = out_dir / "API_PREFLIGHT_REPORT.json"
    report_sha = _write_exclusive(report_path, report)

    sums: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            sums.append(f"{sha256_file(path)}  {path.relative_to(out_dir).as_posix()}")
    sums_path = out_dir / "SHA256SUMS.txt"
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")
    return {
        **report,
        "report_file": str(report_path),
        "report_sha256": report_sha,
        "sha256s_file": str(sums_path),
        "sha256s_sha256": sha256_file(sums_path),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--catalog-all-present", action="store_true")
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()
    result = run_preflight(
        freeze_path=args.freeze,
        out_dir=args.out_dir,
        smoke=args.smoke,
        catalog_all_present=args.catalog_all_present,
        timeout_s=args.timeout,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
