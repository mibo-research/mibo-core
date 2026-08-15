#!/usr/bin/env python3
"""Freeze the exploratory MIBO API Shadow wave after the registered field closes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import mibo_runner as core
from raw_archive import canonical_json_bytes
import shadow_archive
import shadow_qc


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)


def freeze_wave(*, data_root: Path, manifest_path: Path, freeze_path: Path,
                now: datetime | None = None) -> dict:
    rows = __import__("shadow_runner").read_csv(manifest_path)
    if not rows:
        raise ValueError("shadow manifest is empty")
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    wave = core._wave(wave_id)
    close = parse_utc(wave["close_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current < close:
        raise ValueError("API Shadow wave cannot be frozen before the registered field closes")

    root = shadow_archive.shadow_wave_root(data_root, site_id, wave_id)
    release = root / "release"
    record_path = release / "SHADOW_FREEZE_RECORD.json"
    if record_path.exists():
        raise FileExistsError("API Shadow wave is already frozen")

    qc = shadow_qc.build_qc(data_root=data_root, manifest_path=manifest_path, freeze_path=freeze_path)
    if not qc["structural_qc_pass"]:
        raise ValueError("API Shadow structural QC failed; correct/archive the structural defect before freeze")
    qc_path = release / "SHADOW_QC_REPORT.json"
    _write_exclusive(qc_path, canonical_json_bytes(qc))

    record = {
        "schema_version": "0.1",
        "archive_name": "MIBO API Shadow Archive",
        "archive_class": "exploratory_auxiliary",
        "confirmatory_use": "prohibited",
        "protocol_doi": rows[0]["protocol_doi"],
        "wave_id": wave_id,
        "site_id": site_id,
        "field_close_utc": wave["close_utc"],
        "frozen_at_utc": current.isoformat().replace("+00:00", "Z"),
        "manifest_sha256": shadow_qc.sha256_file(manifest_path),
        "shadow_freeze_sha256": shadow_qc.sha256_file(freeze_path),
        "shadow_qc_report_sha256": shadow_qc.sha256_file(qc_path),
        "valid_initial_observations": qc["valid_initial_observations"],
        "missing_initial_observations": qc["missing_initial_observations"],
        "substantive_coding_performed_before_freeze": False,
        "note": "Exploratory auxiliary archive only. This freeze does not alter MIBO Core v1.0 confirmatory data or claims.",
    }
    _write_exclusive(record_path, canonical_json_bytes(record))
    sums_path, sums_sha = shadow_archive.build_shadow_hash_manifest(
        data_root=data_root, site_id=site_id, wave_id=wave_id
    )
    return {
        **record,
        "sha256s_file": str(sums_path.relative_to(root)),
        "sha256s_sha256": sums_sha,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(freeze_wave(
        data_root=args.data_root, manifest_path=args.manifest, freeze_path=args.freeze
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
