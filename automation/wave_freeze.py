#!/usr/bin/env python3
"""Freeze a MIBO Core raw wave package after the registered field closes.

The freeze is structural only: no substantive coding, no imputation, and no
outcome-dependent exclusion. It runs QC, records cell eligibility/missingness,
selects the registered 5% operational audit sample, and hashes the entire raw
wave package before substantive analysis.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import mibo_runner as core
from raw_archive import build_wave_hash_manifest, canonical_json_bytes, wave_root
import ui_capture
import wave_qc

PROTOCOL_DOI = "10.5281/zenodo.21936410"


def _write_exclusive(path: Path, obj: Any) -> str:
    data = canonical_json_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()


def _git_commit(repo_root: Path) -> str | None:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def freeze_wave(*, data_root: Path, ui_manifest: Path, ui_configuration: Path,
                operator_roster: Path, paired_manifest: Path | None = None,
                provider_freeze: Path | None = None,
                repo_root: Path | None = None,
                now: datetime | None = None) -> dict[str, Any]:
    ui_rows = core.read_csv(ui_manifest)
    if not ui_rows:
        raise ValueError("UI manifest is empty")
    wave_id = ui_rows[0]["wave_id"]
    site_id = ui_rows[0]["site_id"]
    wave = core._wave(wave_id)
    close = ui_capture.parse_utc(wave["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current < close:
        raise ValueError(f"cannot freeze {wave_id} before registered field close {close.isoformat()}")

    root = wave_root(data_root, site_id, wave_id)
    release_dir = root / "release"
    if (release_dir / "SHA256SUMS.txt").exists():
        raise FileExistsError("wave has already been frozen: SHA256SUMS.txt exists")

    qc = wave_qc.run_qc(
        data_root=data_root,
        ui_manifest=ui_manifest,
        ui_configuration=ui_configuration,
        operator_roster_path=operator_roster,
        paired_manifest=paired_manifest,
        provider_freeze=provider_freeze,
    )
    if not qc["integrity_pass"]:
        raise ValueError("wave integrity QC failed; fix/record the technical issue before freeze")

    qc_path = release_dir / "WAVE_QC_REPORT.json"
    qc_sha = _write_exclusive(qc_path, qc)
    audit = {
        "schema_version": "1.0",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        **qc["operational_audit"],
        "substantive_response_content_used_for_sampling": False,
    }
    audit_path = release_dir / "OPERATIONAL_AUDIT_SAMPLE.json"
    audit_sha = _write_exclusive(audit_path, audit)

    repo_root = repo_root or Path(__file__).resolve().parents[1]
    record = {
        "schema_version": "1.0",
        "status": "WAVE_FROZEN_BEFORE_SUBSTANTIVE_CODING",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        "registered_field_close_utc": wave["close_utc"],
        "frozen_at_utc": current.isoformat().replace("+00:00", "Z"),
        "software_commit_sha": _git_commit(repo_root),
        "ui_manifest_sha256": wave_qc.sha256_file(ui_manifest),
        "ui_configuration_sha256": wave_qc.sha256_file(ui_configuration),
        "operator_roster_sha256": wave_qc.sha256_file(operator_roster),
        "paired_manifest_sha256": wave_qc.sha256_file(paired_manifest) if paired_manifest else None,
        "provider_freeze_sha256": wave_qc.sha256_file(provider_freeze) if provider_freeze else None,
        "wave_qc_report_sha256": qc_sha,
        "operational_audit_sample_sha256": audit_sha,
        "registered_rows": qc["registered"],
        "observed": qc["observed"],
        "cell_eligibility_counts": qc["cell_eligibility_counts"],
        "imputation_performed": False,
        "substantive_response_content_inspected_by_freezer": False,
        "note": "Low-validity cells are retained and classified by the frozen >=8 / 5-7 / <5 rules; they are not imputed or silently dropped.",
    }
    record_path = release_dir / "WAVE_FREEZE_RECORD.json"
    record_sha = _write_exclusive(record_path, record)

    sums_path, sums_sha = build_wave_hash_manifest(
        data_root=data_root, site_id=site_id, wave_id=wave_id
    )
    return {
        **record,
        "wave_freeze_record_sha256": record_sha,
        "sha256s_file": str(sums_path.relative_to(root)),
        "sha256s_sha256": sums_sha,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--ui-manifest", required=True, type=Path)
    p.add_argument("--ui-configuration", required=True, type=Path)
    p.add_argument("--operator-roster", required=True, type=Path)
    p.add_argument("--paired-manifest", type=Path)
    p.add_argument("--provider-freeze", type=Path)
    p.add_argument("--repo-root", type=Path)
    args = p.parse_args()
    result = freeze_wave(
        data_root=args.data_root,
        ui_manifest=args.ui_manifest,
        ui_configuration=args.ui_configuration,
        operator_roster=args.operator_roster,
        paired_manifest=args.paired_manifest,
        provider_freeze=args.provider_freeze,
        repo_root=args.repo_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
