#!/usr/bin/env python3
"""Deterministic manifest layer for a prospectively registered API-only MIBO Core v2.0.

This module does not alter or reinterpret MIBO Core v1.0. It fails closed until
the v2 protocol and exact four-provider model freeze are finalized by a human.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import mibo_runner as v1

PROTOCOL_VERSION = "2.0"
SCIENTIFIC_CLASS = "confirmatory_primary"
OBSERVATION_SURFACE = "provider_api"
ENVIRONMENT_CLASS = "CLOSED"
LINE_ID = "ACI"
MODE_ID = "ACI"
REPLICATIONS = 10
SEED_FORMULA = 'SHA-256("MIBO-v1.0|<Wave ID>|<Site ID>|<Mode ID>"), first eight hex characters as integer'
MISSINGNESS_RULE = "retain; no fallback model, provider substitution, or imputation"
RETRY_RULE = "technical failures only; at most two retries; retry 1 after at least 10 minutes and retry 2 after at least an additional 30 minutes"
EXPECTED_ADAPTER = {
    "OpenAI": "openai_responses",
    "Anthropic": "anthropic_messages",
    "Google": "gemini_generate_content",
    "Perplexity AI": "perplexity_sonar",
}
FORBIDDEN_PROFILE_KEYS = {
    "tools", "tool_choice", "instructions", "system", "system_instruction",
    "web_search", "file_search", "google_search", "url_context", "files",
    "mcp_servers", "computer_use",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_protocol(path: Path, *, require_final: bool = True) -> tuple[dict[str, Any], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": PROTOCOL_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "primary_scientific_class": SCIENTIFIC_CLASS,
        "observation_surface": OBSERVATION_SURFACE,
        "environment_class": ENVIRONMENT_CLASS,
        "instrument_source_doi": v1.PROTOCOL_DOI,
        "instrument_file": "instrument_v1.0.json",
        "service_file": "services_v1.0.json",
        "query_forms": 24,
        "replications_per_form_per_lineage": REPLICATIONS,
        "line_id": LINE_ID,
        "mode_id": MODE_ID,
        "seed_formula": SEED_FORMULA,
        "retrieval_and_tools": "disabled",
        "missingness_rule": MISSINGNESS_RULE,
        "retry_rule": RETRY_RULE,
    }
    for field, value in expected.items():
        if data.get(field) != value:
            raise ValueError(f"Core v2 protocol {field} mismatch")
    if data.get("required_service_lineages") != [s["service_lineage_id"] for s in v1._services()]:
        raise ValueError("Core v2 protocol must contain the exact four frozen service lineages in order")
    if data.get("preserves_prior_record") is not True:
        raise ValueError("Core v2 protocol must preserve the prior v1.0 record")
    if require_final:
        if data.get("protocol_status") != "finalized_and_prospectively_registered":
            raise ValueError("Core v2 protocol is not finalized and prospectively registered")
        reg = data.get("protocol_registration_id")
        if not isinstance(reg, str) or not reg.strip() or reg.startswith("REPLACE_"):
            raise ValueError("Core v2 protocol registration ID is not finalized")
    waves = data.get("waves")
    if not isinstance(waves, list) or len(waves) != 12:
        raise ValueError("Core v2 protocol requires exactly twelve waves")
    ids = [w.get("wave_id") for w in waves if isinstance(w, dict)]
    expected_ids = [f"MIBO2-W{i:02d}" for i in range(1, 13)]
    if ids != expected_ids:
        raise ValueError("Core v2 wave IDs must be MIBO2-W01 through MIBO2-W12 in order")
    calibration_ids = [w["wave_id"] for w in waves if w.get("calibration_wave") is True]
    if calibration_ids != ["MIBO2-W01", "MIBO2-W04", "MIBO2-W07", "MIBO2-W10"]:
        raise ValueError("Core v2 calibration waves must be W01/W04/W07/W10")
    previous_start: datetime | None = None
    for item in waves:
        try:
            start = datetime.fromisoformat(item["start_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
            close = datetime.fromisoformat(item["close_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Core v2 wave {item.get('wave_id')} has invalid UTC bounds") from exc
        if close - start != timedelta(hours=48):
            raise ValueError(f"Core v2 wave {item['wave_id']} must have a 48-hour field window")
        if previous_start is not None and start <= previous_start:
            raise ValueError("Core v2 wave starts must be strictly chronological")
        previous_start = start
        if item["calibration_wave"]:
            if item.get("window_a") != {"start_offset_hours": 0, "end_offset_hours": 12}:
                raise ValueError(f"Core v2 wave {item['wave_id']} Window A mismatch")
            if item.get("window_b") != {"start_offset_hours": 24, "end_offset_hours": 36}:
                raise ValueError(f"Core v2 wave {item['wave_id']} Window B mismatch")
        elif item.get("window_a") is not None or item.get("window_b") is not None:
            raise ValueError(f"Core v2 non-calibration wave {item['wave_id']} must not define calibration windows")
    return data, sha256_file(path)


def wave(protocol: dict[str, Any], wave_id: str) -> dict[str, Any]:
    matches = [w for w in protocol["waves"] if w["wave_id"] == wave_id]
    if len(matches) != 1:
        raise ValueError(f"unknown Core v2 wave_id: {wave_id}")
    return matches[0]


def load_freeze(path: Path, *, protocol: dict[str, Any], wave_id: str,
                site_id: str) -> tuple[dict[str, Any], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != PROTOCOL_VERSION or data.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("Core v2 provider freeze schema/protocol version mismatch")
    if data.get("protocol_registration_id") != protocol.get("protocol_registration_id"):
        raise ValueError("Core v2 provider freeze registration ID mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("Core v2 provider freeze wave/site mismatch")
    if data.get("observation_surface") != OBSERVATION_SURFACE or data.get("environment_class") != ENVIRONMENT_CLASS:
        raise ValueError("Core v2 provider freeze surface/environment mismatch")
    if not data.get("frozen_at_utc"):
        raise ValueError("Core v2 provider freeze is not finalized")
    entries = data.get("core_api")
    expected_ids = {s["service_lineage_id"] for s in v1._services()}
    if not isinstance(entries, dict) or set(entries) != expected_ids:
        raise ValueError("Core v2 provider freeze must contain exactly the four Core lineages")
    for service in v1._services():
        sid = service["service_lineage_id"]
        cfg = entries[sid]
        if not isinstance(cfg, dict) or cfg.get("status") != "eligible":
            raise ValueError(f"{sid} must be eligible in the finalized Core v2 provider freeze")
        for field in (
            "model_id", "selection_rationale", "provider_evidence", "verified_at_utc",
            "terms_review_date", "terms_review_source", "request_profile",
        ):
            if not cfg.get(field):
                raise ValueError(f"{sid} eligible Core v2 configuration requires {field}")
        if cfg.get("model_version_locked") is not True:
            raise ValueError(f"{sid} requires a human-attested version-locked model ID")
        profile = cfg["request_profile"]
        if not isinstance(profile, dict):
            raise ValueError(f"{sid} request_profile must be an object")
        if profile.get("adapter") != EXPECTED_ADAPTER[service["provider"]]:
            raise ValueError(f"{sid} request_profile adapter mismatch")
        if FORBIDDEN_PROFILE_KEYS.intersection(profile):
            raise ValueError(f"{sid} request_profile contains forbidden capability keys")
        if not profile.get("api_key_env"):
            raise ValueError(f"{sid} request_profile requires api_key_env")
        if profile.get("max_output_tokens") is None:
            raise ValueError(f"{sid} request_profile requires max_output_tokens")
        if service["provider"] == "Perplexity AI" and profile.get("disable_search") is not True:
            raise ValueError(f"{sid} Perplexity API-only Core requires disable_search=true")
    return data, sha256_file(path)


def deterministic_seed(wave_id: str, site_id: str) -> int:
    # Deliberately preserves the registered v1.0 seed formula verbatim.
    token = f"MIBO-v1.0|{wave_id}|{site_id}|{MODE_ID}"
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)


def attempt_id(site_id: str, wave_id: str, service_short: str, item_id: str,
               language: str, window_id: str, replication: int, attempt: int) -> str:
    wave_short = wave_id.replace("MIBO2-", "")
    item_short = item_id.replace("MIBO-", "")
    return (f"MIBO2-SITE-{site_id}-{wave_short}-{service_short}-{LINE_ID}-"
            f"{item_short}-{language}-{window_id}-R{replication:02d}-A{attempt:02d}")


def generate_manifest(*, protocol_path: Path, freeze_path: Path,
                      wave_id: str, site_id: str = "JP01") -> list[dict[str, Any]]:
    if v1.verify_frozen_config():
        raise ValueError("; ".join(v1.verify_frozen_config()))
    protocol, protocol_sha = load_protocol(protocol_path)
    wave_cfg = wave(protocol, wave_id)
    freeze, freeze_sha = load_freeze(
        freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id,
    )
    forms = v1._forms()
    services = v1._services()
    if len(forms) != 24 or len(services) != 4:
        raise ValueError("frozen v1.0 instrument/service source is not 24 forms x 4 lineages")
    seed = deterministic_seed(wave_id, site_id)
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []

    def append_row(service: dict[str, Any], replication: int,
                   form: dict[str, Any], window_id: str) -> None:
        sid = service["service_lineage_id"]
        order = len(rows) + 1
        rows.append({
            "attempt_id": attempt_id(site_id, wave_id, service["short_id"], form["item_id"], form["language"], window_id, replication, 1),
            "observation_id": "",
            "protocol_version": PROTOCOL_VERSION,
            "protocol_registration_id": protocol["protocol_registration_id"],
            "protocol_file_sha256": protocol_sha,
            "instrument_source_doi": v1.PROTOCOL_DOI,
            "scientific_class": SCIENTIFIC_CLASS,
            "observation_surface": OBSERVATION_SURFACE,
            "environment_class": ENVIRONMENT_CLASS,
            "wave_id": wave_id,
            "site_id": site_id,
            "service_lineage_id": sid,
            "service_name": service["name"],
            "provider": service["provider"],
            "line_id": LINE_ID,
            "item_id": form["item_id"],
            "query_form_id": form["query_form_id"],
            "language": form["language"],
            "anchor": str(form["anchor"]).lower(),
            "window_id": window_id,
            "replication": replication,
            "attempt": 1,
            "execution_order": order,
            "random_seed": seed,
            "query_sha256": form["sha256"],
            "provider_freeze_sha256": freeze_sha,
            "model_id": freeze["core_api"][sid]["model_id"],
            "status": "intended_confirmatory_api",
        })

    if wave_cfg["calibration_wave"]:
        anchor_en = [f for f in forms if f["anchor"] and f["language"] == "EN"]
        remaining = [f for f in forms if not (f["anchor"] and f["language"] == "EN")]
        if len(anchor_en) != 4 or len(remaining) != 20:
            raise ValueError("frozen instrument does not contain 4 EN anchors + 20 remaining forms")
        for service in services:
            block = [(rep, form) for rep in range(1, REPLICATIONS + 1) for form in anchor_en]
            rng.shuffle(block)
            for replication, form in block:
                append_row(service, replication, form, "WA")
        for service in services:
            for replication in range(1, REPLICATIONS + 1):
                round_forms = list(remaining)
                rng.shuffle(round_forms)
                for form in round_forms:
                    append_row(service, replication, form, "STD")
        for service in services:
            block = [(rep, form) for rep in range(1, REPLICATIONS + 1) for form in anchor_en]
            rng.shuffle(block)
            for replication, form in block:
                append_row(service, replication, form, "WB")
    else:
        for service in services:
            for replication in range(1, REPLICATIONS + 1):
                round_forms = list(forms)
                rng.shuffle(round_forms)
                for form in round_forms:
                    append_row(service, replication, form, "STD")
    return rows


def validate_manifest(rows: list[dict[str, Any]], *, protocol_path: Path,
                      freeze_path: Path) -> list[str]:
    if not rows:
        return ["Core v2 manifest is empty"]
    errors: list[str] = []
    try:
        protocol, protocol_sha = load_protocol(protocol_path)
    except ValueError as exc:
        return [str(exc)]
    wave_ids = {r.get("wave_id") for r in rows}
    site_ids = {r.get("site_id") for r in rows}
    if len(wave_ids) != 1 or len(site_ids) != 1:
        return ["Core v2 manifest must contain exactly one wave and site"]
    wave_id = next(iter(wave_ids))
    site_id = next(iter(site_ids))
    try:
        wave_cfg = wave(protocol, wave_id)
        freeze, freeze_sha = load_freeze(freeze_path, protocol=protocol, wave_id=wave_id, site_id=site_id)
    except ValueError as exc:
        return [str(exc)]
    services = {s["service_lineage_id"]: s for s in v1._services()}
    forms = {f["query_form_id"]: f for f in v1._forms()}
    expected_total = 1120 if wave_cfg["calibration_wave"] else 960
    if len(rows) != expected_total:
        errors.append(f"Core v2 API manifest count {len(rows)} != {expected_total}")
    ids = [r.get("attempt_id") for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("Core v2 attempt_id values are not unique")
    orders = [int(r.get("execution_order", 0)) for r in rows]
    if sorted(orders) != list(range(1, len(rows) + 1)):
        errors.append("Core v2 execution_order is not contiguous and unique")
    seed = deterministic_seed(wave_id, site_id)
    for i, row in enumerate(rows, 1):
        sid = row.get("service_lineage_id")
        service = services.get(sid)
        form = forms.get(row.get("query_form_id"))
        if service is None or form is None:
            errors.append(f"row {i}: unknown service or query form")
            continue
        constants = {
            "protocol_version": PROTOCOL_VERSION,
            "protocol_registration_id": protocol["protocol_registration_id"],
            "protocol_file_sha256": protocol_sha,
            "instrument_source_doi": v1.PROTOCOL_DOI,
            "scientific_class": SCIENTIFIC_CLASS,
            "observation_surface": OBSERVATION_SURFACE,
            "environment_class": ENVIRONMENT_CLASS,
            "line_id": LINE_ID,
            "status": "intended_confirmatory_api",
        }
        for field, expected in constants.items():
            if row.get(field) != expected:
                errors.append(f"row {i}: {field} mismatch")
        if row.get("service_name") != service["name"] or row.get("provider") != service["provider"]:
            errors.append(f"row {i}: service/provider metadata mismatch")
        if row.get("item_id") != form["item_id"] or row.get("language") != form["language"]:
            errors.append(f"row {i}: item/language mismatch")
        if row.get("query_sha256") != form["sha256"] or row.get("anchor") != str(form["anchor"]).lower():
            errors.append(f"row {i}: frozen query identity mismatch")
        if int(row.get("replication", 0)) not in range(1, REPLICATIONS + 1) or int(row.get("attempt", 0)) != 1:
            errors.append(f"row {i}: replication/attempt mismatch")
        if int(row.get("random_seed", -1)) != seed:
            errors.append(f"row {i}: random seed mismatch")
        if wave_cfg["calibration_wave"]:
            expected_windows = {"WA", "WB"} if form["anchor"] and form["language"] == "EN" else {"STD"}
        else:
            expected_windows = {"STD"}
        if row.get("window_id") not in expected_windows:
            errors.append(f"row {i}: window_id mismatch")
        if row.get("provider_freeze_sha256") != freeze_sha:
            errors.append(f"row {i}: provider freeze SHA-256 mismatch")
        if row.get("model_id") != freeze["core_api"][sid]["model_id"]:
            errors.append(f"row {i}: model ID does not match provider freeze")
        expected_id = attempt_id(site_id, wave_id, service["short_id"], form["item_id"], form["language"], row["window_id"], int(row["replication"]), 1)
        if row.get("attempt_id") != expected_id:
            errors.append(f"row {i}: attempt ID mismatch")
    for sid in services:
        subset = [r for r in rows if r.get("service_lineage_id") == sid]
        expected_service = 280 if wave_cfg["calibration_wave"] else 240
        if len(subset) != expected_service:
            errors.append(f"{sid} Core v2 count {len(subset)} != {expected_service}")
        for qid in forms:
            form = forms[qid]
            expected_form = 20 if wave_cfg["calibration_wave"] and form["anchor"] and form["language"] == "EN" else REPLICATIONS
            if sum(r.get("query_form_id") == qid for r in subset) != expected_form:
                errors.append(f"{sid} {qid} count must equal {expected_form}")
    if wave_cfg["calibration_wave"]:
        counts = {window: sum(r.get("window_id") == window for r in rows) for window in ("WA", "WB", "STD")}
        if counts != {"WA": 160, "WB": 160, "STD": 800}:
            errors.append(f"Core v2 calibration window counts {counts} are invalid")
    elif any(r.get("window_id") != "STD" for r in rows):
        errors.append("Core v2 non-calibration manifest must use STD only")
    return errors


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty Core v2 manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        for field in ("replication", "attempt", "execution_order", "random_seed"):
            row[field] = int(row[field])
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--protocol", required=True, type=Path)
    g.add_argument("--freeze", required=True, type=Path)
    g.add_argument("--wave", required=True)
    g.add_argument("--site", default="JP01")
    g.add_argument("--out", required=True, type=Path)
    v = sub.add_parser("validate")
    v.add_argument("manifest", type=Path)
    v.add_argument("--protocol", required=True, type=Path)
    v.add_argument("--freeze", required=True, type=Path)
    args = p.parse_args()
    if args.cmd == "generate":
        rows = generate_manifest(protocol_path=args.protocol, freeze_path=args.freeze, wave_id=args.wave, site_id=args.site)
        errors = validate_manifest(rows, protocol_path=args.protocol, freeze_path=args.freeze)
        if errors:
            raise SystemExit("\n".join(errors))
        write_csv(rows, args.out)
        print(f"wrote {len(rows)} Core v2 API-only rows to {args.out}")
        return 0
    errors = validate_manifest(read_csv(args.manifest), protocol_path=args.protocol, freeze_path=args.freeze)
    if errors:
        print("\n".join(errors))
        return 1
    print("Core v2 API-only manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
