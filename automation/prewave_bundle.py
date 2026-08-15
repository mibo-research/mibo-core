#!/usr/bin/env python3
"""Build a private, hash-bound MIBO W01 execution bundle before collection.

The builder never authorizes collection, never changes scientific parameters,
and never makes provider or UI calls. It verifies prospectively completed
configuration records, generates deterministic manifests, validates them, and
writes an integrity manifest plus a still-disabled authorization template.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import manifest_integrity
import mibo_runner as core
import ui_capture
from raw_archive import canonical_json_bytes

PROTOCOL_DOI = "10.5281/zenodo.21936410"


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
    data = src.read_bytes()
    _write_exclusive(dst, data)
    return hashlib.sha256(data).hexdigest()


def _validate_ui_config(path: Path, wave_id: str, site_id: str) -> tuple[dict[str, Any], str]:
    config, digest = ui_capture.load_ui_configuration(path, wave_id=wave_id, site_id=site_id)
    expected = {s["service_lineage_id"] for s in core._services()}
    actual = set((config.get("ecological_live") or {}).keys())
    if actual != expected:
        raise ValueError(f"Ecological Live config lineage set mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    for sid in sorted(expected):
        entry = ui_capture.validate_ui_service_configuration(config, sid)
        for field in (
            "account_tier", "mode", "search_tools_state", "memory_personalization_state",
            "locale", "terms_review_date", "terms_review_source",
        ):
            if not entry.get(field):
                raise ValueError(f"{sid} UI configuration requires {field}")
    return config, digest


def _validate_provider_freeze(path: Path, wave_id: str, site_id: str) -> tuple[dict[str, Any], str, list[str]]:
    freeze, digest = core.load_provider_freeze(path, wave_id, site_id)
    paired = freeze.get("paired_api") or {}
    eligible: list[str] = []
    for service in core._services():
        sid = service["service_lineage_id"]
        cfg = paired.get(sid)
        if not isinstance(cfg, dict):
            raise ValueError(f"{sid} missing from paired provider freeze")
        if cfg.get("status") == "eligible":
            if service.get("paired_candidate") == "no":
                raise ValueError(f"{sid} cannot be eligible under v1.0")
            if cfg.get("comparability_class") not in core.ELIGIBLE_COMPARABILITY_CLASSES:
                raise ValueError(f"{sid} eligible status requires comparability Class A or B")
            for field in (
                "live_model_id", "frozen_model_id", "provider_evidence", "terms_review_date",
                "terms_review_source", "verified_at_utc", "request_profile",
            ):
                if not cfg.get(field):
                    raise ValueError(f"{sid} eligible paired freeze requires {field}")
            eligible.append(sid)
        elif cfg.get("status") not in {"pending", "not_admissible_v1", "ineligible"}:
            raise ValueError(f"{sid} has unknown paired status {cfg.get('status')!r}")
    return freeze, digest, eligible


def _write_csv_exclusive(rows: list[dict], path: Path) -> str:
    if path.exists():
        raise FileExistsError(path)
    core.write_csv(rows, path)
    return sha256_file(path)


def build_bundle(*, wave_id: str, site_id: str, ui_configuration: Path,
                 provider_freeze: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise FileExistsError(f"bundle directory already exists: {out_dir}")
    config_errors = core.verify_frozen_config()
    if config_errors:
        raise ValueError("frozen config invalid: " + "; ".join(config_errors))

    ui_config, ui_config_sha = _validate_ui_config(ui_configuration, wave_id, site_id)
    freeze, freeze_sha, eligible = _validate_provider_freeze(provider_freeze, wave_id, site_id)

    out_dir.mkdir(parents=True)
    configuration_dir = out_dir / "configuration"
    manifests_dir = out_dir / "manifests"
    ui_copy = configuration_dir / "ui_configuration.json"
    paired_copy = configuration_dir / "provider_freeze.json"
    _copy_exclusive(ui_configuration, ui_copy)
    _copy_exclusive(provider_freeze, paired_copy)

    ui_rows = core.generate_ui_manifest(wave_id, site_id)
    ui_errors = core.validate_manifest(ui_rows) + manifest_integrity.strict_validate_manifest(ui_rows)
    if ui_errors:
        raise ValueError("UI manifest invalid: " + "; ".join(ui_errors))
    ui_manifest = manifests_dir / f"{wave_id}-{site_id}-LUI.csv"
    ui_manifest_sha = _write_csv_exclusive(ui_rows, ui_manifest)

    paired_manifest: Path | None = None
    paired_manifest_sha: str | None = None
    paired_rows = 0
    if eligible:
        rows = core.generate_paired_manifest(wave_id, eligible, paired_copy, site_id)
        errors = core.validate_manifest(rows) + manifest_integrity.strict_validate_manifest(rows)
        if errors:
            raise ValueError("paired manifest invalid: " + "; ".join(errors))
        paired_manifest = manifests_dir / f"{wave_id}-{site_id}-PAIRED.csv"
        paired_manifest_sha = _write_csv_exclusive(rows, paired_manifest)
        paired_rows = len(rows)

    primary_paired_ready = len(eligible) >= 2
    report = {
        "schema_version": "1.0",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        "built_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scientific_config_valid": True,
        "ui": {
            "configuration_file": str(ui_copy.relative_to(out_dir)),
            "configuration_sha256": ui_config_sha,
            "manifest_file": str(ui_manifest.relative_to(out_dir)),
            "manifest_sha256": ui_manifest_sha,
            "rows": len(ui_rows),
            "all_lineages_ready_human_operated": True,
        },
        "paired": {
            "configuration_file": str(paired_copy.relative_to(out_dir)),
            "configuration_sha256": freeze_sha,
            "eligible_lineages": eligible,
            "eligible_lineage_count": len(eligible),
            "primary_paired_ready": primary_paired_ready,
            "manifest_file": str(paired_manifest.relative_to(out_dir)) if paired_manifest else None,
            "manifest_sha256": paired_manifest_sha,
            "rows": paired_rows,
        },
        "authorization_status": "NOT_AUTHORIZED_BY_BUNDLE_BUILDER",
    }
    report_path = out_dir / "PREWAVE_BUNDLE_REPORT.json"
    report_sha = _write_exclusive(report_path, canonical_json_bytes(report))

    authorization = {
        "schema_version": "1.0",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        "authorized": False,
        "authorized_at_utc": None,
        "operations_lead": None,
        "terms_review_complete": False,
        "institutional_process_checked": False,
        "dry_run_complete": False,
        "manifest_sha256": paired_manifest_sha,
        "provider_freeze_sha256": freeze_sha,
        "prewave_bundle_report_sha256": report_sha,
        "note": "Human sign-off template only. Set gates true prospectively after completing the Pre-Wave-1 Execution Gate; this builder never authorizes collection."
    }
    authorization_path = out_dir / "execution_authorization.PAIRED.template.json"
    _write_exclusive(authorization_path, canonical_json_bytes(authorization))

    integrity_entries: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            integrity_entries.append(f"{sha256_file(path)}  {path.relative_to(out_dir).as_posix()}")
    sums_path = out_dir / "SHA256SUMS.txt"
    sums_sha = _write_exclusive(sums_path, ("\n".join(integrity_entries) + "\n").encode("utf-8"))

    return {
        **report,
        "prewave_bundle_report_sha256": report_sha,
        "bundle_sha256s_file": str(sums_path),
        "bundle_sha256s_sha256": sums_sha,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--ui-configuration", required=True, type=Path)
    p.add_argument("--provider-freeze", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    result = build_bundle(
        wave_id=args.wave,
        site_id=args.site,
        ui_configuration=args.ui_configuration,
        provider_freeze=args.provider_freeze,
        out_dir=args.out_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["paired"]["primary_paired_ready"]:
        print("WARNING: fewer than two eligible paired lineages; paired primary hypothesis set must be prospectively reduced/classified under the SAP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
