#!/usr/bin/env python3
"""Structural, provenance, missingness, and operational QC for MIBO Core waves.

This module does not inspect substantive response meaning and performs no
imputation. It classifies each registered 10-replication cell using the frozen
valid-count rules: >=8 primary, 5-7 sensitivity, <5 descriptive only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import manifest_integrity
import mibo_runner as core
import operator_roster
import paired_executor
import ui_capture
from raw_archive import wave_root

PROTOCOL_DOI = "10.5281/zenodo.21936410"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def attempt_base(attempt_id: str) -> str:
    if "-A" not in attempt_id:
        raise ValueError(f"attempt ID lacks attempt suffix: {attempt_id}")
    return attempt_id.rsplit("-A", 1)[0]


def attempt_number(attempt_id: str) -> int:
    try:
        return int(attempt_id.rsplit("-A", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"invalid attempt suffix: {attempt_id}") from exc


def cell_key(row: dict) -> tuple[str, str, str, str]:
    return (
        row["service_lineage_id"],
        row["line_id"],
        row["query_form_id"],
        row["window_id"],
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_file_hash(root: Path, relative: str | None, expected: str | None,
                      label: str, errors: list[str]) -> None:
    if not relative or not expected:
        errors.append(f"{label}: missing file path or SHA-256")
        return
    path = root / relative
    if not path.is_file():
        errors.append(f"{label}: referenced file does not exist: {relative}")
        return
    actual = sha256_file(path)
    if actual != expected:
        errors.append(f"{label}: SHA-256 mismatch for {relative}")


def _registered_row_by_base(rows: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        base = attempt_base(row["attempt_id"])
        if base in result:
            raise ValueError(f"duplicate registered replication base: {base}")
        result[base] = row
    return result


def _load_success_metadata(root: Path) -> tuple[dict[str, dict], list[str]]:
    successes: dict[str, dict] = {}
    errors: list[str] = []
    metadata_dir = root / "metadata"
    if not metadata_dir.exists():
        return successes, errors
    for path in sorted(metadata_dir.glob("*.ui.json")):
        try:
            data = _load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"cannot read UI metadata {path.name}: {exc}")
            continue
        aid = data.get("attempt_id")
        if not aid or path.name != f"{aid}.ui.json":
            errors.append(f"UI metadata filename/attempt mismatch: {path.name}")
            continue
        if aid in successes:
            errors.append(f"duplicate success metadata for {aid}")
            continue
        data["_kind"] = "ui"
        data["_metadata_path"] = path
        successes[aid] = data
    for path in sorted(metadata_dir.glob("*.json")):
        if path.name.endswith(".ui.json") or path.name.startswith("retry-link-"):
            continue
        try:
            data = _load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"cannot read API metadata {path.name}: {exc}")
            continue
        if data.get("status") != "valid_technical_capture":
            continue
        aid = data.get("attempt_id")
        if not aid or path.name != f"{aid}.json":
            errors.append(f"API metadata filename/attempt mismatch: {path.name}")
            continue
        if aid in successes:
            errors.append(f"duplicate success metadata for {aid}")
            continue
        data["_kind"] = "api"
        data["_metadata_path"] = path
        successes[aid] = data
    return successes, errors


def _load_failures(root: Path) -> tuple[dict[str, dict], list[str]]:
    failures: dict[str, dict] = {}
    errors: list[str] = []
    failure_dir = root / "failures"
    if not failure_dir.exists():
        return failures, errors
    for path in sorted(failure_dir.glob("*.json")):
        try:
            data = _load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"cannot read failure record {path.name}: {exc}")
            continue
        aid = data.get("attempt_id")
        if not aid or path.name != f"{aid}.json":
            errors.append(f"failure filename/attempt mismatch: {path.name}")
            continue
        if aid in failures:
            errors.append(f"duplicate failure record for {aid}")
            continue
        failures[aid] = data
    return failures, errors


def _verify_ui_success(*, root: Path, data: dict, registered: dict,
                       ui_configuration_sha: str, roster: dict,
                       roster_sha: str, errors: list[str]) -> None:
    aid = data["attempt_id"]
    if data.get("protocol_doi") != PROTOCOL_DOI:
        errors.append(f"{aid}: UI protocol DOI mismatch")
    if data.get("service_lineage_id") != registered["service_lineage_id"]:
        errors.append(f"{aid}: UI service lineage mismatch")
    if data.get("query_form_id") != registered["query_form_id"]:
        errors.append(f"{aid}: UI query form mismatch")
    if str(data.get("window_id")) != str(registered["window_id"]):
        errors.append(f"{aid}: UI window mismatch")
    if int(data.get("replication", -1)) != int(registered["replication"]):
        errors.append(f"{aid}: UI replication mismatch")
    if data.get("ui_configuration_sha256") != ui_configuration_sha:
        errors.append(f"{aid}: UI configuration SHA-256 mismatch")
    if data.get("operator_roster_sha256") != roster_sha:
        errors.append(f"{aid}: operator roster SHA-256 mismatch")
    try:
        operator_roster.assert_operator_assigned(
            roster,
            service_lineage_id=registered["service_lineage_id"],
            operator_id=str(data.get("operator_id", "")),
        )
    except ValueError as exc:
        errors.append(f"{aid}: {exc}")
    if data.get("operator_confirmed_new_session") is not True:
        errors.append(f"{aid}: fresh-session confirmation missing")
    if data.get("browser_automation") is not False or data.get("programmatic_output_extraction") is not False:
        errors.append(f"{aid}: Ecological Live automation boundary violated")
    _verify_file_hash(root, data.get("prompt_file"), data.get("prompt_sha256"), f"{aid} prompt", errors)
    _verify_file_hash(root, data.get("output_file"), data.get("output_sha256"), f"{aid} output", errors)
    if data.get("prompt_sha256") != registered["query_sha256"]:
        errors.append(f"{aid}: captured prompt hash differs from registered query hash")
    source_state = data.get("sources_capture_state")
    if source_state == "captured":
        _verify_file_hash(root, data.get("sources_file"), data.get("sources_sha256"), f"{aid} sources", errors)
        if data.get("sources_displayed") is not True:
            errors.append(f"{aid}: sources captured but sources_displayed is not true")
    elif source_state == "none_displayed":
        if data.get("sources_displayed") is not False:
            errors.append(f"{aid}: none_displayed but sources_displayed is not false")
        if data.get("sources_file") or data.get("sources_sha256"):
            errors.append(f"{aid}: none_displayed should not contain a sources file/hash")
    else:
        errors.append(f"{aid}: invalid or missing sources_capture_state")
    try:
        submitted = ui_capture.parse_utc(data["submitted_at_utc"])
        captured = ui_capture.parse_utc(data["captured_at_utc"])
        start, end = ui_capture.window_bounds(registered["wave_id"], registered["window_id"])
        if not (start <= submitted < end):
            errors.append(f"{aid}: UI submission outside registered window")
        if not (start <= captured < end):
            errors.append(f"{aid}: UI capture outside registered window")
        if captured < submitted:
            errors.append(f"{aid}: UI capture precedes submission")
    except (KeyError, ValueError) as exc:
        errors.append(f"{aid}: invalid UI timestamps: {exc}")


def _verify_api_success(*, root: Path, data: dict, registered: dict,
                        provider_freeze_sha: str, errors: list[str]) -> None:
    aid = data["attempt_id"]
    _verify_file_hash(root, data.get("raw_file"), data.get("raw_file_sha256"), f"{aid} API raw", errors)
    raw_file = root / str(data.get("raw_file", ""))
    if not raw_file.is_file():
        return
    try:
        raw = _load_json(raw_file)
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"{aid}: cannot parse raw API envelope: {exc}")
        return
    if raw.get("attempt_id") != aid:
        errors.append(f"{aid}: API raw envelope attempt mismatch")
    if raw.get("protocol_doi") != PROTOCOL_DOI:
        errors.append(f"{aid}: API protocol DOI mismatch")
    for field in ("service_lineage_id", "line_id", "query_form_id"):
        if raw.get(field) != registered[field]:
            errors.append(f"{aid}: API raw {field} mismatch")
    if int(raw.get("replication", -1)) != int(registered["replication"]):
        errors.append(f"{aid}: API replication mismatch")
    if raw.get("configuration_freeze_sha256") != provider_freeze_sha:
        errors.append(f"{aid}: API provider-freeze SHA-256 mismatch")
    if raw.get("model_id_requested") != registered.get("model_id"):
        errors.append(f"{aid}: requested API model differs from frozen manifest")
    try:
        started = ui_capture.parse_utc(raw["started_at_utc"])
        completed = ui_capture.parse_utc(raw["completed_at_utc"])
        start, end = ui_capture.window_bounds(registered["wave_id"], registered["window_id"])
        if not (start <= started < end):
            errors.append(f"{aid}: API request started outside registered window")
        if completed < started:
            errors.append(f"{aid}: API completion precedes start")
    except (KeyError, ValueError) as exc:
        errors.append(f"{aid}: invalid API timestamps: {exc}")


def _audit_sample(valid_attempt_ids: list[str], wave_id: str, site_id: str) -> list[str]:
    if not valid_attempt_ids:
        return []
    n = max(1, math.ceil(len(valid_attempt_ids) * 0.05))
    ranked = sorted(
        valid_attempt_ids,
        key=lambda aid: hashlib.sha256(
            f"MIBO-v1.0|{wave_id}|{site_id}|operational-audit|{aid}".encode("utf-8")
        ).hexdigest(),
    )
    return ranked[:n]


def run_qc(*, data_root: Path, ui_manifest: Path, ui_configuration: Path,
           operator_roster_path: Path, paired_manifest: Path | None = None,
           provider_freeze: Path | None = None) -> dict[str, Any]:
    ui_rows = core.read_csv(ui_manifest)
    errors: list[str] = []
    warnings: list[str] = []
    structural = core.validate_manifest(ui_rows)
    strict = manifest_integrity.strict_validate_manifest(ui_rows)
    errors.extend(f"UI manifest: {e}" for e in structural + strict)
    if not ui_rows or any(r["line_id"] != "LUI" for r in ui_rows):
        raise ValueError("UI manifest must contain Ecological Live rows only")
    wave_id = ui_rows[0]["wave_id"]
    site_id = ui_rows[0]["site_id"]

    ui_config, ui_config_sha = ui_capture.load_ui_configuration(
        ui_configuration, wave_id=wave_id, site_id=site_id
    )
    for service in core._services():
        ui_capture.validate_ui_service_configuration(ui_config, service["service_lineage_id"])
    roster, roster_sha = operator_roster.load_roster(
        operator_roster_path, wave_id=wave_id, site_id=site_id
    )

    all_rows = list(ui_rows)
    paired_rows: list[dict] = []
    provider_freeze_sha = ""
    if paired_manifest is not None:
        if provider_freeze is None:
            raise ValueError("paired_manifest requires provider_freeze")
        paired_rows = core.read_csv(paired_manifest)
        errors.extend(f"paired manifest: {e}" for e in core.validate_manifest(paired_rows))
        errors.extend(f"paired manifest: {e}" for e in manifest_integrity.strict_validate_manifest(paired_rows))
        try:
            paired_executor._validate_freeze_binding(paired_rows, provider_freeze, require_credentials=False)
        except ValueError as exc:
            errors.append(f"paired freeze binding: {exc}")
        provider_freeze_sha = sha256_file(provider_freeze)
        all_rows.extend(paired_rows)

    root = wave_root(data_root, site_id, wave_id)
    successes, success_errors = _load_success_metadata(root)
    failures, failure_errors = _load_failures(root)
    errors.extend(success_errors)
    errors.extend(failure_errors)
    overlap = sorted(set(successes).intersection(failures))
    if overlap:
        errors.append(f"same Attempt ID has both success and failure records: {overlap[:10]}")

    registered_by_base = _registered_row_by_base(all_rows)
    success_by_base: dict[str, list[str]] = defaultdict(list)
    failure_by_base: dict[str, list[str]] = defaultdict(list)

    for aid, data in successes.items():
        try:
            number = attempt_number(aid)
            base = attempt_base(aid)
        except ValueError as exc:
            errors.append(str(exc)); continue
        if number not in {1, 2, 3}:
            errors.append(f"{aid}: attempt number exceeds A03")
        registered = registered_by_base.get(base)
        if registered is None:
            errors.append(f"{aid}: success does not map to a registered replication")
            continue
        success_by_base[base].append(aid)
        if data.get("_kind") == "ui":
            _verify_ui_success(
                root=root, data=data, registered=registered,
                ui_configuration_sha=ui_config_sha, roster=roster,
                roster_sha=roster_sha, errors=errors,
            )
        else:
            if not paired_rows:
                errors.append(f"{aid}: API success exists but no paired manifest was supplied")
            else:
                _verify_api_success(
                    root=root, data=data, registered=registered,
                    provider_freeze_sha=provider_freeze_sha, errors=errors,
                )

    for aid, data in failures.items():
        try:
            number = attempt_number(aid)
            base = attempt_base(aid)
        except ValueError as exc:
            errors.append(str(exc)); continue
        if number not in {1, 2, 3}:
            errors.append(f"{aid}: failure attempt number exceeds A03")
        registered = registered_by_base.get(base)
        if registered is None:
            errors.append(f"{aid}: failure does not map to a registered replication")
            continue
        failure_by_base[base].append(aid)
        failed_at_text = data.get("failed_at_utc")
        if failed_at_text:
            try:
                failed_at = ui_capture.parse_utc(failed_at_text)
                start, end = ui_capture.window_bounds(registered["wave_id"], registered["window_id"])
                if not (start <= failed_at < end):
                    errors.append(f"{aid}: technical failure recorded outside registered window")
            except ValueError as exc:
                errors.append(f"{aid}: invalid failure timestamp: {exc}")

    cells: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in all_rows:
        cells[cell_key(row)].append(row)
    cell_reports: list[dict[str, Any]] = []
    for key in sorted(cells):
        rows = cells[key]
        if len(rows) != 10:
            errors.append(f"cell {key} has {len(rows)} registered rows, expected 10")
        valid_reps = 0
        multiple_success_reps = 0
        exhausted_or_missing = 0
        for row in rows:
            base = attempt_base(row["attempt_id"])
            successful = success_by_base.get(base, [])
            if successful:
                valid_reps += 1
                if len(successful) > 1:
                    multiple_success_reps += 1
                    errors.append(f"replication {base} has multiple retained successful attempts: {successful}")
            else:
                exhausted_or_missing += 1
        eligibility = "primary" if valid_reps >= 8 else ("sensitivity" if valid_reps >= 5 else "descriptive")
        cell_reports.append({
            "service_lineage_id": key[0],
            "line_id": key[1],
            "query_form_id": key[2],
            "window_id": key[3],
            "registered_replications": len(rows),
            "valid_replications": valid_reps,
            "missing_or_technically_unresolved": exhausted_or_missing,
            "multiple_success_replications": multiple_success_reps,
            "eligibility": eligibility,
        })

    valid_attempt_ids = sorted(successes)
    audit = _audit_sample(valid_attempt_ids, wave_id, site_id)
    eligibility_counts = {"primary": 0, "sensitivity": 0, "descriptive": 0}
    for cell in cell_reports:
        eligibility_counts[cell["eligibility"]] += 1

    if paired_rows and not any(c["line_id"] in {"PLR", "FRZ"} and c["eligibility"] == "primary" for c in cell_reports):
        warnings.append("paired manifest supplied but no paired cell currently reaches primary valid-count eligibility")

    return {
        "schema_version": "1.0",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "substantive_response_content_inspected": False,
        "imputation_performed": False,
        "integrity_pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "registered": {
            "ui_rows": len(ui_rows),
            "paired_rows": len(paired_rows),
            "total_rows": len(all_rows),
            "cells": len(cell_reports),
        },
        "observed": {
            "valid_attempts": len(successes),
            "technical_failure_attempts": len(failures),
            "successful_replications": sum(c["valid_replications"] for c in cell_reports),
        },
        "cell_eligibility_counts": eligibility_counts,
        "cells": cell_reports,
        "operational_audit": {
            "sampling_fraction": 0.05,
            "method": "deterministic SHA-256 ranking independent of response content",
            "sample_size": len(audit),
            "attempt_ids": audit,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--ui-manifest", required=True, type=Path)
    p.add_argument("--ui-configuration", required=True, type=Path)
    p.add_argument("--operator-roster", required=True, type=Path)
    p.add_argument("--paired-manifest", type=Path)
    p.add_argument("--provider-freeze", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = run_qc(
        data_root=args.data_root,
        ui_manifest=args.ui_manifest,
        ui_configuration=args.ui_configuration,
        operator_roster_path=args.operator_roster,
        paired_manifest=args.paired_manifest,
        provider_freeze=args.provider_freeze,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as fh:
            fh.write(text)
    print(text, end="")
    return 0 if report["integrity_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
