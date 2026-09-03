#!/usr/bin/env python3
"""Build a private hash-bound bundle for API-only MIBO Core v2.0."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import core_v2_runner as runner
from raw_archive import canonical_json_bytes


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def build_bundle(*, protocol_path: Path, wave_id: str, site_id: str,
                 freeze_path: Path, preflight_report_path: Path,
                 out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise FileExistsError(f"Core v2 bundle already exists: {out_dir}")
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    freeze, freeze_sha = runner.load_freeze(
        freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id,
    )
    preflight = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    expected = {
        "protocol_version": runner.PROTOCOL_VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha,
        "scientific_class": runner.SCIENTIFIC_CLASS,
        "wave_id": wave_id, "site_id": site_id,
        "provider_freeze_sha256": freeze_sha,
        "pass": True,
    }
    for field, value in expected.items():
        if preflight.get(field) != value:
            raise ValueError(f"Core v2 preflight {field} mismatch")
    if preflight.get("synthetic_smoke_requested") is not True:
        raise ValueError("Core v2 bundle requires a completed synthetic smoke preflight")
    smoke = preflight.get("synthetic_smoke_checks")
    if not isinstance(smoke, list) or len(smoke) != 4 or not all(c.get("pass") is True for c in smoke):
        raise ValueError("Core v2 bundle requires four passing synthetic smoke checks")
    rows = runner.generate_manifest(
        protocol_path=protocol_path, freeze_path=freeze_path,
        wave_id=wave_id, site_id=site_id,
    )
    errors = runner.validate_manifest(rows, protocol_path=protocol_path, freeze_path=freeze_path)
    if errors:
        raise ValueError("Core v2 manifest invalid: " + "; ".join(errors))
    out_dir.mkdir(parents=True)
    config = out_dir / "configuration"
    manifests = out_dir / "manifests"
    protocol_copy = config / "core_v2_protocol.final.json"
    freeze_copy = config / "core_v2_provider_freeze.json"
    preflight_copy = config / "CORE_V2_API_PREFLIGHT_REPORT.json"
    _write_exclusive(protocol_copy, protocol_path.read_bytes())
    _write_exclusive(freeze_copy, freeze_path.read_bytes())
    _write_exclusive(preflight_copy, preflight_report_path.read_bytes())
    manifest_path = manifests / f"{wave_id}-{site_id}-API-CORE.csv"
    runner.write_csv(rows, manifest_path)
    manifest_sha = sha256_file(manifest_path)
    report = {
        "schema_version": runner.PROTOCOL_VERSION,
        "protocol_version": runner.PROTOCOL_VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "scientific_class": runner.SCIENTIFIC_CLASS,
        "observation_surface": runner.OBSERVATION_SURFACE,
        "wave_id": wave_id, "site_id": site_id,
        "built_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "service_lineages": list(freeze["core_api"]),
        "initial_request_count": len(rows),
        "protocol_file": str(protocol_copy.relative_to(out_dir)),
        "protocol_file_sha256": protocol_sha,
        "manifest_file": str(manifest_path.relative_to(out_dir)),
        "manifest_sha256": manifest_sha,
        "provider_freeze_file": str(freeze_copy.relative_to(out_dir)),
        "provider_freeze_sha256": freeze_sha,
        "provider_preflight_report_file": str(preflight_copy.relative_to(out_dir)),
        "provider_preflight_report_sha256": sha256_file(preflight_copy),
        "authorization_status": "NOT_AUTHORIZED_BY_BUNDLE_BUILDER",
    }
    report_path = out_dir / "CORE_V2_BUNDLE_REPORT.json"
    report_sha = _write_exclusive(report_path, canonical_json_bytes(report))
    authorization = {
        "schema_version": runner.PROTOCOL_VERSION,
        "protocol_version": runner.PROTOCOL_VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "wave_id": wave_id, "site_id": site_id,
        "authorized": False, "authorized_at_utc": None, "operations_lead": None,
        "protocol_finalized": True, "prospective_registration_complete": True,
        "terms_review_complete": False, "model_freeze_complete": True,
        "synthetic_dry_run_complete": True,
        "authorize_confirmatory_api_core": False,
        "protocol_file_sha256": protocol_sha, "manifest_sha256": manifest_sha,
        "provider_freeze_sha256": freeze_sha,
        "bundle_report_sha256": report_sha,
        "note": "Human authorization template. The bundle builder never authorizes execution.",
    }
    _write_exclusive(
        out_dir / "core_v2_execution_authorization.template.json",
        canonical_json_bytes(authorization),
    )
    entries = [
        f"{sha256_file(p)}  {p.relative_to(out_dir).as_posix()}"
        for p in sorted(out_dir.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.txt"
    ]
    sums = out_dir / "SHA256SUMS.txt"
    sums_sha = _write_exclusive(sums, ("\n".join(entries) + "\n").encode("utf-8"))
    return {**report, "bundle_report_sha256": report_sha,
            "sha256s_sha256": sums_sha}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--preflight-report", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(build_bundle(
        protocol_path=args.protocol, wave_id=args.wave, site_id=args.site,
        freeze_path=args.freeze, preflight_report_path=args.preflight_report,
        out_dir=args.out_dir,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
