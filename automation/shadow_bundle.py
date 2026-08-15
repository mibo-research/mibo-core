#!/usr/bin/env python3
"""Build a private hash-bound execution bundle for MIBO API Shadow v0.1."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from raw_archive import canonical_json_bytes
import shadow_runner


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def _copy_exclusive(src: Path, dst: Path) -> str:
    return _write_exclusive(dst, src.read_bytes())


def build_bundle(*, wave_id: str, site_id: str, freeze_path: Path,
                 preflight_report_path: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise FileExistsError(f"shadow bundle already exists: {out_dir}")
    freeze, freeze_sha = shadow_runner.load_shadow_freeze(freeze_path, wave_id, site_id)
    preflight = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    if preflight.get("archive_class") != shadow_runner.ARCHIVE_CLASS:
        raise ValueError("shadow preflight report archive_class mismatch")
    if preflight.get("confirmatory_use") != shadow_runner.CONFIRMATORY_USE:
        raise ValueError("shadow preflight report confirmatory_use mismatch")
    if preflight.get("wave_id") != wave_id or preflight.get("site_id") != site_id:
        raise ValueError("shadow preflight report wave/site mismatch")
    if preflight.get("shadow_freeze_sha256") != freeze_sha:
        raise ValueError("shadow preflight report does not bind the exact freeze file")
    if preflight.get("pass") is not True:
        raise ValueError("shadow provider preflight did not pass")

    rows = shadow_runner.generate_shadow_manifest(wave_id, freeze_path, site_id)
    errors = shadow_runner.validate_shadow_manifest(rows, freeze_path)
    if errors:
        raise ValueError("shadow manifest invalid: " + "; ".join(errors))

    out_dir.mkdir(parents=True)
    config_dir = out_dir / "configuration"
    manifest_dir = out_dir / "manifests"
    freeze_copy = config_dir / "api_shadow_freeze.json"
    preflight_copy = config_dir / "API_SHADOW_PREFLIGHT_REPORT.json"
    _copy_exclusive(freeze_path, freeze_copy)
    _copy_exclusive(preflight_report_path, preflight_copy)
    manifest_path = manifest_dir / f"{wave_id}-{site_id}-API-SHADOW.csv"
    shadow_runner.write_csv(rows, manifest_path)
    manifest_sha = sha256_file(manifest_path)

    report = {
        "schema_version": "0.1",
        "archive_name": "MIBO API Shadow Archive",
        "archive_class": shadow_runner.ARCHIVE_CLASS,
        "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
        "protocol_doi": freeze["protocol_doi"],
        "wave_id": wave_id,
        "site_id": site_id,
        "built_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "eligible_lineages": shadow_runner.eligible_lineages(freeze),
        "initial_request_count": len(rows),
        "manifest_file": str(manifest_path.relative_to(out_dir)),
        "manifest_sha256": manifest_sha,
        "shadow_freeze_file": str(freeze_copy.relative_to(out_dir)),
        "shadow_freeze_sha256": freeze_sha,
        "provider_preflight_report_file": str(preflight_copy.relative_to(out_dir)),
        "provider_preflight_report_sha256": sha256_file(preflight_copy),
        "authorization_status": "NOT_AUTHORIZED_BY_BUNDLE_BUILDER",
    }
    report_path = out_dir / "API_SHADOW_BUNDLE_REPORT.json"
    report_sha = _write_exclusive(report_path, canonical_json_bytes(report))

    authorization = {
        "schema_version": "0.1",
        "archive_name": "MIBO API Shadow Archive",
        "archive_class": shadow_runner.ARCHIVE_CLASS,
        "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
        "protocol_doi": freeze["protocol_doi"],
        "wave_id": wave_id,
        "site_id": site_id,
        "authorized": False,
        "authorized_at_utc": None,
        "operations_lead": None,
        "terms_review_complete": False,
        "institutional_process_checked": False,
        "dry_run_complete": False,
        "acknowledge_exploratory_only": False,
        "manifest_sha256": manifest_sha,
        "shadow_freeze_sha256": freeze_sha,
        "shadow_bundle_report_sha256": report_sha,
        "note": "Human authorization template. The builder never enables API Shadow execution."
    }
    auth_path = out_dir / "execution_authorization.SHADOW.template.json"
    _write_exclusive(auth_path, canonical_json_bytes(authorization))

    entries: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            entries.append(f"{sha256_file(path)}  {path.relative_to(out_dir).as_posix()}")
    sums_path = out_dir / "SHA256SUMS.txt"
    sums_sha = _write_exclusive(sums_path, ("\n".join(entries) + "\n").encode("utf-8"))
    return {
        **report,
        "shadow_bundle_report_sha256": report_sha,
        "sha256s_file": str(sums_path.relative_to(out_dir)),
        "sha256s_sha256": sums_sha,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--preflight-report", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    result = build_bundle(
        wave_id=args.wave, site_id=args.site, freeze_path=args.freeze,
        preflight_report_path=args.preflight_report, out_dir=args.out_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
