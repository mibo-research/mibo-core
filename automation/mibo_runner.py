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


def load_json(name: str) -> dict:
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


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
                  execution_order: int, seed: int) -> dict:
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
        "status": "intended",
    }


def generate_ui_manifest(wave_id: str, site_id: str = "JP01") -> list[dict]:
    """Generate the registered Japan-site Ecological Live manifest."""
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
        assert len(anchor_en) == 4
        assert len(remaining) == 20

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


def generate_paired_manifest(wave_id: str, lineages: Iterable[str],
                             site_id: str = "JP01") -> list[dict]:
    """Generate paired API blocks after final provider eligibility is frozen."""
    wanted = set(lineages)
    services = [s for s in _services() if s["service_lineage_id"] in wanted]
    if len(services) != len(wanted):
        known = {s["service_lineage_id"] for s in _services()}
        raise ValueError(f"Unknown lineages: {sorted(wanted - known)}")
    if any(s["paired_candidate"] == "no" for s in services):
        raise ValueError("A non-admissible v1 lineage was requested for paired API.")
    anchors = [f for f in _forms() if f["anchor"] and f["language"] == "EN"]
    seed = deterministic_seed(wave_id, site_id, "PAIRED")
    rng = random.Random(seed)
    rows: list[dict] = []
    order = 0
    for service in services:
        for form in anchors:
            block = [(rep, line) for rep in range(1, 11) for line in ("PLR", "FRZ")]
            rng.shuffle(block)
            for rep, line in block:
                order += 1
                rows.append(_manifest_row(site_id=site_id, wave_id=wave_id,
                    service=service, line_id=line, form=form, window_id="STD",
                    replication=rep, execution_order=order, seed=seed))
    return rows


def validate_manifest(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["manifest is empty"]
    instrument = {f["query_form_id"]: f for f in _forms()}
    ids = [r["attempt_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("attempt_id values are not unique")
    for i, row in enumerate(rows, 1):
        qid = row["query_form_id"]
        if qid not in instrument:
            errors.append(f"row {i}: unknown query_form_id {qid}")
            continue
        if row["query_sha256"] != instrument[qid]["sha256"]:
            errors.append(f"row {i}: query hash mismatch for {qid}")
        if row["protocol_doi"] != PROTOCOL_DOI:
            errors.append(f"row {i}: protocol DOI mismatch")
        if row["replication"] not in range(1, 11):
            errors.append(f"row {i}: replication out of range")
        if row["attempt"] != 1:
            errors.append(f"row {i}: initial manifest attempt must be 1")

    wave = _wave(rows[0]["wave_id"])
    ui = [r for r in rows if r["line_id"] == "LUI"]
    paired = [r for r in rows if r["line_id"] in {"PLR", "FRZ"}]
    if ui:
        expected = 1120 if wave["calibration_wave"] else 960
        if len(ui) != expected:
            errors.append(f"UI manifest count {len(ui)} != expected {expected}")
        if wave["calibration_wave"]:
            wa = sum(r["window_id"] == "WA" for r in ui)
            wb = sum(r["window_id"] == "WB" for r in ui)
            std = sum(r["window_id"] == "STD" for r in ui)
            if (wa, wb, std) != (160, 160, 800):
                errors.append(f"calibration window counts {(wa, wb, std)} != (160, 160, 800)")
    if paired and len(paired) % 80 != 0:
        errors.append("paired API manifest is not a multiple of 80 rows per lineage")
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
    p = sub.add_parser("generate-ui"); p.add_argument("--wave", required=True); p.add_argument("--site", default="JP01"); p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("generate-paired"); p.add_argument("--wave", required=True); p.add_argument("--site", default="JP01"); p.add_argument("--lineage", action="append", required=True); p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("validate"); p.add_argument("manifest", type=Path)
    p = sub.add_parser("show-wave"); p.add_argument("--wave", required=True)
    args = parser.parse_args()
    if args.cmd == "generate-ui":
        rows = generate_ui_manifest(args.wave, args.site); errors = validate_manifest(rows)
        if errors: raise SystemExit("\n".join(errors))
        write_csv(rows, args.out); print(f"wrote {len(rows)} rows to {args.out}")
    elif args.cmd == "generate-paired":
        rows = generate_paired_manifest(args.wave, args.lineage, args.site); errors = validate_manifest(rows)
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
