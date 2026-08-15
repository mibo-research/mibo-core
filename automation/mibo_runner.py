#!/usr/bin/env python3
"""Deterministic MIBO Core v1.0 manifest and QC runner.

This module deliberately does NOT call provider APIs or browser UIs.
Collection adapters are added only after the pre-wave configuration freeze.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"
PROTOCOL_DOI = "10.5281/zenodo.21936410"
ELIGIBLE_COMPARABILITY_CLASSES = {"A", "B"}


def load_json(name: str) -> dict:
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_config() -> list[str]:
    """Verify machine-readable config against its own frozen integrity claims."""
    errors: list[str] = []
    instrument = load_json("instrument_v1.0.json")
    services = load_json("services_v1.0.json")
    waves = load_json("waves_v1.0.json")

    for name, obj in (("instrument", instrument), ("services", services), ("waves", waves)):
        if obj.get("protocol_doi") != PROTOCOL_DOI:
            errors.append(f"{name} protocol DOI mismatch")

    forms = instrument.get("forms", [])
    if len(forms) != 24:
        errors.append(f"instrument has {len(forms)} forms, expected 24")
    qids = [f.get("query_form_id") for f in forms]
    if len(qids) != len(set(qids)):
        errors.append("query_form_id values are not unique")
    for form in forms:
        actual = sha256_text(form.get("text", ""))
        if actual != form.get("sha256"):
            errors.append(f"frozen query text hash mismatch for {form.get('query_form_id')}")

    service_rows = services.get("services", [])
    if len(service_rows) != 4:
        errors.append(f"service registry has {len(service_rows)} rows, expected 4")
    service_ids = [s.get("service_lineage_id") for s in service_rows]
    if len(service_ids) != len(set(service_ids)):
        errors.append("service_lineage_id values are not unique")

    wave_rows = waves.get("waves", [])
    if len(wave_rows) != 12:
        errors.append(f"wave calendar has {len(wave_rows)} waves, expected 12")
    wave_ids = [w.get("wave_id") for w in wave_rows]
    if len(wave_ids) != len(set(wave_ids)):
        errors.append("wave_id values are not unique")
    calibration = [w.get("wave_id") for w in wave_rows if w.get("calibration_wave")]
    if calibration != ["MIBO-W01", "MIBO-W04", "MIBO-W07", "MIBO-W10"]:
        errors.append(f"calibration waves mismatch: {calibration}")
    return errors


def deterministic_seed(wave_id: str, site_id: str, mode_id: str) -> int:
    token = f"MIBO-v1.0|{wave_id}|{site_id}|{mode_id}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def short_wave(wave_id: str) -> str:
    return wave_id.replace("MIBO-", "")


def short_item(item_id: str) -> str:
    return item_id.replace("MIBO-", "")


def attempt_id(site_id: str, wave_id: str, service_short: str, line_id: str,
               item_id: str, language: str, window_id: str, replication: int,
               attempt: int = 1) -> str:
    return (f"MIBO-SITE-{site_id}-{short_wave(wave_id)}-{service_short}-"
            f"{line_id}-{short_item(item_id)}-{language}-{window_id}-"
            f"R{replication:02d}-A{attempt:02d}")


def _wave(wave_id: str) -> dict:
    waves = load_json("waves_v1.0.json")["waves"]
    matches = [w for w in waves if w["wave_id"] == wave_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown wave_id: {wave_id}")
    return matches[0]


def _services() -> list[dict]:
    return load_json("services_v1.0.json")["services"]


def _forms() -> list[dict]:
    return load_json("instrument_v1.0.json")["forms"]


def _manifest_row(*, site_id: str, wave_id: str, service: dict, line_id: str,
                  form: dict, window_id: str, replication: int,
                  execution_order: int, seed: int,
                  configuration_freeze_sha256: str = "",
                  model_id: str = "", comparability_class: str = "") -> dict:
    aid = attempt_id(site_id, wave_id, service["short_id"], line_id,
                     form["item_id"], form["language"], window_id, replication)
    return {
        "attempt_id": aid,
        "observation_id": "",
        "protocol_doi": PROTOCOL_DOI,
        "wave_id": wave_id,
        "site_id": site_id,
        "service_lineage_id": service["service_lineage_id"],
        "service_name": service["name"],
        "provider": service["provider"],
        "line_id": line_id,
        "item_id": form["item_id"],
        "query_form_id": form["query_form_id"],
        "language": form["language"],
        "anchor": str(form["anchor"]).lower(),
        "window_id": window_id,
        "replication": replication,
        "attempt": 1,
        "execution_order": execution_order,
        "random_seed": seed,
        "query_sha256": form["sha256"],
        "configuration_freeze_sha256": configuration_freeze_sha256,
        "model_id": model_id,
        "comparability_class": comparability_class,
        "status": "intended",
    }


def generate_ui_manifest(wave_id: str, site_id: str = "JP01") -> list[dict]:
    """Generate the registered Japan-site Ecological Live manifest."""
    config_errors = verify_frozen_config()
    if config_errors:
        raise ValueError("; ".join(config_errors))
    wave = _wave(wave_id)
    forms = _forms()
    services = _services()
    seed = deterministic_seed(wave_id, site_id, "LUI")
    rng = random.Random(seed)
    rows: list[dict] = []
    order = 0

    if wave["calibration_wave"]:
        anchor_en = [f for f in forms if f["anchor"] and f["language"] == "EN"]
        remaining = [f for f in forms if not (f["anchor"] and f["language"] == "EN")]
        if len(anchor_en) != 4 or len(remaining) != 20:
            raise ValueError("frozen instrument does not contain 4 EN anchors + 20 remaining forms")

        for service in services:
            block = [(r, f) for r in range(1, 11) for f in anchor_en]
            rng.shuffle(block)
            for rep, form in block:
                order += 1
                rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                    service=service, line_id="LUI", form=form, window_id="WA",
                    replication=rep, execution_order=order, seed=seed))

        for service in services:
            for rep in range(1, 11):
                round_forms = list(remaining)
                rng.shuffle(round_forms)
                for form in round_forms:
                    order += 1
                    rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                        service=service, line_id="LUI", form=form, window_id="STD",
                        replication=rep, execution_order=order, seed=seed))

        for service in services:
            block = [(r, f) for r in range(1, 11) for f in anchor_en]
            rng.shuffle(block)
            for rep, form in block:
                order += 1
                rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                    service=service, line_id="LUI", form=form, window_id="WB",
                    replication=rep, execution_order=order, seed=seed))
    else:
        for service in services:
            for rep in range(1, 11):
                round_forms = list(forms)
                rng.shuffle(round_forms)
                for form in round_forms:
                    order += 1
                    rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                        service=service, line_id="LUI", form=form, window_id="STD",
                        replication=rep, execution_order=order, seed=seed))
    return rows


def load_provider_freeze(path: Path, wave_id: str, site_id: str) -> tuple[dict, str]:
    """Load and validate the prospective provider Configuration Freeze Record."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("wave_id") != wave_id:
        raise ValueError("provider freeze wave_id does not match requested wave")
    if data.get("site_id") != site_id:
        raise ValueError("provider freeze site_id does not match requested site")
    if not data.get("frozen_at_utc"):
        raise ValueError("provider freeze is not finalized: frozen_at_utc is empty")
    return data, sha256_file(path)


def generate_paired_manifest(wave_id: str, lineages: Iterable[str],
                             freeze_path: Path, site_id: str = "JP01") -> list[dict]:
    """Generate paired API blocks only from a finalized provider freeze record."""
    config_errors = verify_frozen_config()
    if config_errors:
        raise ValueError("; ".join(config_errors))
    freeze, freeze_sha = load_provider_freeze(freeze_path, wave_id, site_id)
    wanted = set(lineages)
    services = [s for s in _services() if s["service_lineage_id"] in wanted]
    if len(services) != len(wanted):
        known = {s["service_lineage_id"] for s in _services()}
        raise ValueError(f"Unknown lineages: {sorted(wanted - known)}")

    paired_cfg = freeze.get("paired_api", {})
    for service in services:
        sid = service["service_lineage_id"]
        if service["paired_candidate"] == "no":
            raise ValueError(f"{sid} is non-admissible for v1 paired API")
        cfg = paired_cfg.get(sid)
        if not cfg:
            raise ValueError(f"{sid} missing from provider freeze")
        if cfg.get("status") != "eligible":
            raise ValueError(f"{sid} provider freeze status is not eligible")
        if cfg.get("comparability_class") not in ELIGIBLE_COMPARABILITY_CLASSES:
            raise ValueError(f"{sid} comparability class must be A or B")
        if not cfg.get("live_model_id") or not cfg.get("frozen_model_id"):
            raise ValueError(f"{sid} requires both live_model_id and frozen_model_id")

    anchors = [f for f in _forms() if f["anchor"] and f["language"] == "EN"]
    if len(anchors) != 4:
        raise ValueError("frozen instrument does not contain exactly 4 English anchors")
    seed = deterministic_seed(wave_id, site_id, "PAIRED")
    rng = random.Random(seed)
    rows: list[dict] = []
    order = 0
    for service in services:
        cfg = paired_cfg[service["service_lineage_id"]]
        for form in anchors:
            block = [(rep, line) for rep in range(1, 11) for line in ("PLR", "FRZ")]
            rng.shuffle(block)
            for rep, line in block:
                order += 1
                model_id = cfg["live_model_id"] if line == "PLR" else cfg["frozen_model_id"]
                rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                    service=service, line_id=line, form=form, window_id="STD",
                    replication=rep, execution_order=order, seed=seed,
                    configuration_freeze_sha256=freeze_sha, model_id=model_id,
                    comparability_class=cfg["comparability_class"]))
    return rows


def validate_manifest(rows: list[dict]) -> list[str]:
    errors = verify_frozen_config()
    if not rows:
        return errors + ["manifest is empty"]
    instrument = {f["query_form_id"]: f for f in _forms()}
    ids = [r["attempt_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("attempt_id values are not unique")
    orders = [r["execution_order"] for r in rows]
    if sorted(orders) != list(range(1, len(rows) + 1)):
        errors.append("execution_order must be a unique contiguous sequence starting at 1")

    wave_ids = {r["wave_id"] for r in rows}
    site_ids = {r["site_id"] for r in rows}
    if len(wave_ids) != 1:
        errors.append("manifest contains multiple wave_id values")
        return errors
    if len(site_ids) != 1:
        errors.append("manifest contains multiple site_id values")
    wave = _wave(next(iter(wave_ids)))

    for i, row in enumerate(rows, 1):
        qid = row["query_form_id"]
        if qid not in instrument:
            errors.append(f"row {i}: unknown query_form_id {qid}")
            continue
        form = instrument[qid]
        if row["query_sha256"] != form["sha256"]:
            errors.append(f"row {i}: query hash mismatch for {qid}")
        if row["protocol_doi"] != PROTOCOL_DOI:
            errors.append(f"row {i}: protocol DOI mismatch")
        if row["replication"] not in range(1, 11):
            errors.append(f"row {i}: replication out of range")
        if row["attempt"] != 1:
            errors.append(f"row {i}: initial manifest attempt must be 1")
        if row["item_id"] != form["item_id"] or row["language"] != form["language"]:
            errors.append(f"row {i}: item/language mismatch for {qid}")

    ui = [r for r in rows if r["line_id"] == "LUI"]
    paired = [r for r in rows if r["line_id"] in {"PLR", "FRZ"}]
    unknown_lines = [r["line_id"] for r in rows if r["line_id"] not in {"LUI", "PLR", "FRZ"}]
    if unknown_lines:
        errors.append(f"unknown line_id values: {sorted(set(unknown_lines))}")
    if ui and paired:
        errors.append("UI and paired API rows must be stored in separate manifests")

    if ui:
        expected = 1120 if wave["calibration_wave"] else 960
        if len(ui) != expected:
            errors.append(f"UI manifest count {len(ui)} != expected {expected}")
        for service in _services():
            sr = [r for r in ui if r["service_lineage_id"] == service["service_lineage_id"]]
            expected_service = 280 if wave["calibration_wave"] else 240
            if len(sr) != expected_service:
                errors.append(f"{service['service_lineage_id']} UI count {len(sr)} != {expected_service}")
        if wave["calibration_wave"]:
            wa = sum(r["window_id"] == "WA" for r in ui)
            wb = sum(r["window_id"] == "WB" for r in ui)
            std = sum(r["window_id"] == "STD" for r in ui)
            if (wa, wb, std) != (160, 160, 800):
                errors.append(f"calibration window counts {(wa, wb, std)} != (160, 160, 800)")
        elif any(r["window_id"] != "STD" for r in ui):
            errors.append("non-calibration UI manifest must use STD window only")

    if paired:
        lineages = sorted({r["service_lineage_id"] for r in paired})
        if len(paired) != 80 * len(lineages):
            errors.append(f"paired API count {len(paired)} != 80 x {len(lineages)} lineages")
        for sid in lineages:
            sr = [r for r in paired if r["service_lineage_id"] == sid]
            if len(sr) != 80:
                errors.append(f"{sid} paired count {len(sr)} != 80")
            if sum(r["line_id"] == "PLR" for r in sr) != 40 or sum(r["line_id"] == "FRZ" for r in sr) != 40:
                errors.append(f"{sid} paired line counts must be 40 PLR + 40 FRZ")
            if any(r["window_id"] != "STD" for r in sr):
                errors.append(f"{sid} paired rows must use STD window")
            if any(not r.get("configuration_freeze_sha256") for r in sr):
                errors.append(f"{sid} paired rows missing configuration freeze hash")
            if any(not r.get("model_id") for r in sr):
                errors.append(f"{sid} paired rows missing frozen model identifiers")
            if any(r.get("comparability_class") not in ELIGIBLE_COMPARABILITY_CLASSES for r in sr):
                errors.append(f"{sid} paired rows have invalid comparability class")
    return errors


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        for field in ("replication", "attempt", "execution_order", "random_seed"):
            row[field] = int(row[field])
    return rows


def show_wave(wave_id: str) -> None:
    wave = _wave(wave_id)
    start = datetime.fromisoformat(wave["start_utc"].replace("Z", "+00:00"))
    jst = timezone(timedelta(hours=9))
    print(json.dumps({**wave, "start_jst": start.astimezone(jst).isoformat(),
        "close_jst": datetime.fromisoformat(wave["close_utc"].replace("Z", "+00:00")).astimezone(jst).isoformat()}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-config")
    p = sub.add_parser("generate-ui"); p.add_argument("--wave", required=True); p.add_argument("--site", default="JP01"); p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("generate-paired"); p.add_argument("--wave", required=True); p.add_argument("--site", default="JP01"); p.add_argument("--freeze", required=True, type=Path); p.add_argument("--lineage", action="append", required=True); p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("validate"); p.add_argument("manifest", type=Path)
    p = sub.add_parser("show-wave"); p.add_argument("--wave", required=True)
    args = parser.parse_args()
    if args.cmd == "verify-config":
        errors = verify_frozen_config()
        if errors:
            print("\n".join(errors)); return 1
        print("frozen config valid")
    elif args.cmd == "generate-ui":
        rows = generate_ui_manifest(args.wave, args.site); errors = validate_manifest(rows)
        if errors: raise SystemExit("\n".join(errors))
        write_csv(rows, args.out); print(f"wrote {len(rows)} rows to {args.out}")
    elif args.cmd == "generate-paired":
        rows = generate_paired_manifest(args.wave, args.lineage, args.freeze, args.site); errors = validate_manifest(rows)
        if errors: raise SystemExit("\n".join(errors))
        write_csv(rows, args.out); print(f"wrote {len(rows)} rows to {args.out}")
    elif args.cmd == "validate":
        errors = validate_manifest(read_csv(args.manifest))
        if errors: print("\n".join(errors)); return 1
        print("manifest valid")
    elif args.cmd == "show-wave":
        show_wave(args.wave)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
