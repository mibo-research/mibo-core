#!/usr/bin/env python3
"""Structural QC for the exploratory MIBO API Shadow Archive v0.1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import shadow_archive
import shadow_runner


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def initial_attempt_id(attempt_id: str) -> str:
    return re.sub(r"-A\d{2}$", "-A01", attempt_id)


def build_qc(*, data_root: Path, manifest_path: Path, freeze_path: Path) -> dict[str, Any]:
    rows = shadow_runner.read_csv(manifest_path)
    manifest_errors = shadow_runner.validate_shadow_manifest(rows, freeze_path)
    if manifest_errors:
        raise ValueError("shadow manifest invalid: " + "; ".join(manifest_errors))
    wave_id = rows[0]["wave_id"]
    site_id = rows[0]["site_id"]
    root = shadow_archive.shadow_wave_root(data_root, site_id, wave_id)
    intended = {r["attempt_id"]: r for r in rows}
    valid_initial: set[str] = set()
    structural_errors: list[str] = []
    success_attempts = 0

    metadata_dir = root / "metadata"
    if metadata_dir.exists():
        for path in sorted(metadata_dir.glob("*.json")):
            if path.name.startswith("retry-link-"):
                continue
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                structural_errors.append(f"invalid metadata JSON: {path.name}")
                continue
            if meta.get("archive_class") != shadow_runner.ARCHIVE_CLASS:
                structural_errors.append(f"wrong archive_class in {path.name}")
            if meta.get("confirmatory_use") != shadow_runner.CONFIRMATORY_USE:
                structural_errors.append(f"wrong confirmatory_use in {path.name}")
            attempt_id = meta.get("attempt_id")
            if not isinstance(attempt_id, str):
                structural_errors.append(f"missing attempt_id in {path.name}")
                continue
            base = initial_attempt_id(attempt_id)
            if base not in intended:
                structural_errors.append(f"metadata attempt not represented in shadow manifest: {attempt_id}")
                continue
            raw_rel = meta.get("raw_file")
            raw_hash = meta.get("raw_file_sha256")
            if not isinstance(raw_rel, str) or not isinstance(raw_hash, str):
                structural_errors.append(f"missing raw file/hash in {path.name}")
                continue
            raw_path = root / raw_rel
            if not raw_path.is_file():
                structural_errors.append(f"missing raw file for {attempt_id}")
                continue
            if sha256_file(raw_path) != raw_hash:
                structural_errors.append(f"raw file hash mismatch for {attempt_id}")
                continue
            valid_initial.add(base)
            success_attempts += 1

    by_lineage: dict[str, dict[str, Any]] = {}
    cells: list[dict[str, Any]] = []
    for sid in sorted({r["service_lineage_id"] for r in rows}):
        sr = [r for r in rows if r["service_lineage_id"] == sid]
        valid = sum(r["attempt_id"] in valid_initial for r in sr)
        by_lineage[sid] = {
            "intended": len(sr),
            "valid": valid,
            "missing": len(sr) - valid,
            "completion_rate": valid / len(sr) if sr else 0.0,
        }
        for qid in sorted({r["query_form_id"] for r in sr}):
            qr = [r for r in sr if r["query_form_id"] == qid]
            qvalid = sum(r["attempt_id"] in valid_initial for r in qr)
            cells.append({
                "service_lineage_id": sid,
                "query_form_id": qid,
                "intended": len(qr),
                "valid": qvalid,
                "missing": len(qr) - qvalid,
                "completion_state": "complete" if qvalid == len(qr) else ("partial" if qvalid else "missing"),
            })

    valid_count = len(valid_initial)
    return {
        "schema_version": "0.1",
        "archive_name": "MIBO API Shadow Archive",
        "archive_class": shadow_runner.ARCHIVE_CLASS,
        "confirmatory_use": shadow_runner.CONFIRMATORY_USE,
        "protocol_doi": rows[0]["protocol_doi"],
        "wave_id": wave_id,
        "site_id": site_id,
        "manifest_sha256": sha256_file(manifest_path),
        "shadow_freeze_sha256": sha256_file(freeze_path),
        "expected_initial_observations": len(rows),
        "valid_initial_observations": valid_count,
        "missing_initial_observations": len(rows) - valid_count,
        "successful_attempt_files": success_attempts,
        "completion_rate": valid_count / len(rows),
        "by_lineage": by_lineage,
        "cells": cells,
        "structural_errors": structural_errors,
        "structural_qc_pass": not structural_errors,
        "note": "Missing shadow observations are retained as missing; no imputation. This report is exploratory auxiliary QC only.",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    args = p.parse_args()
    report = build_qc(data_root=args.data_root, manifest_path=args.manifest, freeze_path=args.freeze)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["structural_qc_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
