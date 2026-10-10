#!/usr/bin/env python3
"""Read-only technical cell accounting; never interpret response content."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

import core_v2_archive as archive
import core_v2_runner as runner
import mibo_runner as v1


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("technical record must be an object")
    return value


def build_report(*, protocol_path: Path, manifest_path: Path, freeze_path: Path,
                 data_root: Path, authorization_path: Path | None = None,
                 current: datetime | None = None, expected_wave: str | None = None,
                 expected_site: str | None = None) -> dict[str, Any]:
    """Account for initial logical cells, not attempted requests or exit status.

    Raw JSON is deliberately never decoded: only bytes are hashed. Failure
    messages, bodies, credentials and returned answer content are never reported.
    A concurrently changing archive can yield a conservative integrity error;
    take another read-only snapshot after the collector finishes writing.
    """
    now = current or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("status clock must be timezone-aware")
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    rows = runner.read_csv(manifest_path)
    errors = runner.validate_manifest(rows, protocol_path=protocol_path, freeze_path=freeze_path)
    if errors or not rows:
        raise ValueError("invalid frozen manifest")
    wave_id, site_id = rows[0]["wave_id"], rows[0]["site_id"]
    if expected_wave is not None and wave_id != expected_wave:
        raise ValueError("status wave mismatch")
    if expected_site is not None and site_id != expected_site:
        raise ValueError("status site mismatch")
    generated = runner.generate_manifest(protocol_path=protocol_path, freeze_path=freeze_path,
                                         wave_id=wave_id, site_id=site_id)
    if rows != generated:
        raise ValueError("manifest differs from deterministic generation")
    admitted = {r["service_lineage_id"] for r in rows}
    intended_panel_cells = len(rows)
    intended_panel_lineages = sorted(admitted)
    scope_verified = False
    if authorization_path is not None:
        # Lazy import avoids a dependency cycle when executor.main calls status.
        from core_v2_executor import load_authorization
        auth = load_authorization(authorization_path, protocol_path=protocol_path,
                                  manifest_path=manifest_path, freeze_path=freeze_path,
                                  protocol=protocol, wave_id=wave_id, site_id=site_id)
        if protocol["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
            admitted = set(auth["admitted_lineages"])
        scope_verified = True
    elif protocol["protocol_version"] in runner.SCOPED_PROTOCOL_VERSIONS:
        raise ValueError("scoped status requires bound private authorization")
    rows = [r for r in rows if r["service_lineage_id"] in admitted]
    root = archive.wave_root(data_root, site_id, wave_id, protocol["protocol_version"])
    errors = []
    captured: set[str] = set()
    failed: set[str] = set()
    uncertain: set[str] = set()
    suspended: set[str] = set()
    referenced: set[Path] = set()
    seen: set[str] = set()
    technical_failures: Counter[str] = Counter()
    attempts: dict[str, tuple[dict[str, Any], int, str | None]] = {}
    services = {s["service_lineage_id"]: s for s in v1._services()}
    for row in rows:
        parent = None
        for number in range(1, 4):
            aid = runner.attempt_id(site_id, wave_id, services[row["service_lineage_id"]]["short_id"],
                                    row["item_id"], row["language"], row["window_id"],
                                    int(row["replication"]), number)
            attempts[aid] = (row, number, parent)
            parent = aid
    # Share the strict recovery validator without its repair writes. This also
    # checks retry timing, parent failures, pause state and claim provenance.
    try:
        from core_v2_execution_state import LegacyCaptureMetadataError, restore
        from core_v2_executor import _clone_retry_row, _row_bounds
        retained = restore(root=root, initial_rows=rows, clone_retry=_clone_retry_row,
                           row_bounds=lambda row: _row_bounds(protocol, row), data_root=data_root,
                           authorization_sha256=_sha(authorization_path) if authorization_path else None,
                           persist=False, current=now)
        suspended.update(retained.suspended)
        uncertain.update(attempts[aid][0]["attempt_id"] for aid in retained.uncertain)
    except LegacyCaptureMetadataError:
        errors.append("legacy capture lacks complete technical metadata; retained data cannot be counted or automatically resent")
    except (OSError, ValueError, TypeError, KeyError):
        errors.append("retained execution state could not be verified")
    if root.exists() and any(p.is_symlink() or not (p.is_file() or p.is_dir())
                             for p in [root, *root.rglob("*")]):
        errors.append("archive contains symlink or special file")
    if not errors:
        for folder in ("metadata", "failures"):
            for path in sorted((root / folder).glob("*.json")):
                try:
                    value = _record(path)
                    if path.name.startswith("first-dispatch-"):
                        if value.get("service_lineage_id") not in admitted:
                            raise ValueError("dispatch identity")
                        continue
                    if path.name.startswith("retry-link-"):
                        aid = value.get("retry_attempt_id")
                        if aid not in attempts or attempts[aid][1] == 1 or value.get("original_attempt_id") != attempts[aid][2]:
                            raise ValueError("retry identity")
                        continue
                    aid = value.get("attempt_id")
                    if aid not in attempts or path.name != aid + ".json" or aid in seen:
                        raise ValueError("attempt identity")
                    row, number, parent = attempts[aid]
                    if (value.get("protocol_version") != protocol["protocol_version"]
                            or value.get("retry_of_attempt_id") != parent):
                        raise ValueError("attempt binding")
                    if value.get("service_lineage_id") != row["service_lineage_id"]:
                        raise ValueError("lineage binding")
                    seen.add(aid)
                    if folder == "metadata":
                        rel = value.get("raw_file")
                        if not isinstance(rel, str) or rel != "api_raw/" + aid + ".json":
                            raise ValueError("raw path binding")
                        raw = root / PurePosixPath(rel)
                        if not raw.is_file() or _sha(raw) != value.get("raw_file_sha256"):
                            raise ValueError("raw hash")
                        if value.get("status") != "valid_confirmatory_api_capture" or row["attempt_id"] in captured:
                            raise ValueError("capture identity")
                        captured.add(row["attempt_id"])
                        referenced.add(raw)
                    else:
                        if int(value.get("attempt", 0)) != number:
                            raise ValueError("failure attempt binding")
                        failed.add(row["attempt_id"])
                        technical_failures[row["service_lineage_id"]] += 1
                except (OSError, ValueError, TypeError, KeyError):
                    errors.append("invalid retained " + folder + " record")
        actual_raw = set((root / "api_raw").glob("*"))
        if actual_raw != referenced:
            errors.append("unlinked or missing raw capture")
        for path in sorted((root / "deviations").glob("*.json")):
            try:
                value = _record(path)
                kind = value.get("type", "")
                if isinstance(kind, str) and ("suspend" in kind or "uncertain" in kind):
                    sid = value.get("service_lineage_id")
                    if sid not in admitted:
                        raise ValueError("suspension identity")
                    suspended.add(sid)
            except (OSError, ValueError, TypeError):
                errors.append("invalid retained deviation record")
        # Durable pre-dispatch journal: an unresolved marker may have reached
        # the provider, so it must never be counted as an unattempted cell.
        for folder in ("dispatch", "dispatches"):
            for path in sorted((root / folder).glob("*.json")):
                try:
                    value = _record(path)
                    aid = value.get("attempt_id")
                    if aid not in attempts:
                        raise ValueError("dispatch identity")
                    if aid not in seen:
                        uncertain.add(attempts[aid][0]["attempt_id"])
                except (OSError, ValueError, TypeError):
                    errors.append("invalid retained dispatch record")
    summaries, cells, dimensions = {}, [], Counter()
    for row in rows:
        aid, sid = row["attempt_id"], row["service_lineage_id"]
        state = ("captured" if aid in captured else "uncertain_no_capture" if aid in uncertain
                 else "failed_no_capture" if aid in failed else "unattempted_no_capture")
        cells.append({k: row[k] for k in ("attempt_id", "service_lineage_id", "query_form_id", "language", "window_id")}
                     | {"state": state})
        dimensions[(sid, row["query_form_id"], row["language"], row["window_id"], state)] += 1
    for sid in sorted(admitted):
        subset = [c for c in cells if c["service_lineage_id"] == sid]
        counts = Counter(c["state"] for c in subset)
        summaries[sid] = {"planned": len(subset), "captured": counts["captured"],
                          "missing": len(subset) - counts["captured"],
                          "failed_no_capture": counts["failed_no_capture"],
                          "unattempted_no_capture": counts["unattempted_no_capture"],
                          "uncertain_no_capture": counts["uncertain_no_capture"],
                          "technical_failure_attempts": technical_failures[sid],
                          "suspended": sid in suspended}
    wave_cfg = runner.wave(protocol, wave_id)
    start, close = (runner.parse_aware_utc(wave_cfg[k]) for k in ("start_utc", "close_utc"))
    complete = not errors and len(captured) == len(rows) and not uncertain
    status = ("INTEGRITY_ERROR" if errors else "COMPLETE" if complete else "SUSPENDED" if suspended or uncertain
              else "INCOMPLETE" if now >= close else "WAITING" if now < start else "COLLECTING")
    return {"wave_id": wave_id, "site_id": site_id, "protocol_version": protocol["protocol_version"],
            "checked_at_utc": now.astimezone(timezone.utc).isoformat(),
            "protocol_sha256": protocol_sha, "manifest_sha256": _sha(manifest_path),
            "freeze_sha256": _sha(freeze_path), "authorization_scope_verified": scope_verified,
            "status": status, "integrity_pass": not errors, "integrity_errors": sorted(set(errors)),
            "completion_scope": "authorized_lineages_in_this_namespace",
            "scope_collection_complete": complete,
            "scientific_collection_complete": complete,
            "intended_panel_cells": intended_panel_cells,
            "intended_panel_lineages": intended_panel_lineages,
            "registered_panel_fully_included": admitted == set(intended_panel_lineages),
            "whole_wave_completion_assessed": admitted == set(intended_panel_lineages),
            "whole_wave_collection_complete": complete if admitted == set(intended_panel_lineages) else None,
            "planned_cells": len(rows),
            "captured_cells": len(captured), "missing_cells": len(rows) - len(captured),
            "lineages": summaries, "cells": cells,
            "dimension_counts": [{"service_lineage_id": k[0], "query_form_id": k[1], "language": k[2],
                                  "window_id": k[3], "state": k[4], "count": n}
                                 for k, n in sorted(dimensions.items())],
            "raw_content_inspected": False, "independent_backup_verified": False}


def service_states(units: list[str]) -> dict[str, Any]:
    result = {}
    for unit in units:
        if not unit.endswith(".service") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.@-" for c in unit):
            raise ValueError("invalid service name")
        try:
            proc = subprocess.run(["systemctl", "show", unit, "-p", "ActiveState", "-p", "MainPID",
                                   "-p", "UnitFileState", "-p", "Result"], capture_output=True,
                                  text=True, timeout=10, check=False)
            values = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
            result[unit] = {"available": proc.returncode == 0,
                            **{k: values.get(k) for k in ("ActiveState", "MainPID", "UnitFileState", "Result")}}
        except (OSError, subprocess.TimeoutExpired):
            result[unit] = {"available": False}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("protocol", "manifest", "freeze", "data-root"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--wave")
    parser.add_argument("--site")
    parser.add_argument("--unit", action="append", default=[])
    parser.add_argument("--include-cells", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(protocol_path=args.protocol, manifest_path=args.manifest, freeze_path=args.freeze,
                              data_root=args.data_root, authorization_path=args.authorization,
                              expected_wave=args.wave, expected_site=args.site)
        if not args.include_cells:
            report.pop("cells")
            report.pop("dimension_counts")
        report["services"] = service_states(args.unit)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if not report["integrity_pass"] else 0 if report["scientific_collection_complete"] else 2
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "INTEGRITY_ERROR", "integrity_pass": False,
                          "error": "status inputs or retained state could not be verified"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
