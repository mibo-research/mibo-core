#!/usr/bin/env python3
"""Deterministic manifest layer for the exploratory MIBO API Shadow Archive v0.1.

This module is intentionally separate from ``mibo_runner.py`` so the auxiliary
API archive can never be mistaken for a MIBO Core v1.0 confirmatory manifest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import mibo_runner as core

ARCHIVE_VERSION = "0.1"
ARCHIVE_CLASS = "exploratory_auxiliary"
CONFIRMATORY_USE = "prohibited"
LINE_ID = "ASH"
ENVIRONMENT_CLASS = "CLOSED"
ALLOWED_FINAL_STATUSES = {"eligible", "ineligible"}
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


def shadow_seed(wave_id: str, site_id: str) -> int:
    token = f"MIBO-API-SHADOW-v{ARCHIVE_VERSION}|{wave_id}|{site_id}"
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)


def load_shadow_freeze(path: Path, wave_id: str, site_id: str) -> tuple[dict[str, Any], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != ARCHIVE_VERSION:
        raise ValueError("API Shadow freeze schema_version mismatch")
    if data.get("archive_class") != ARCHIVE_CLASS:
        raise ValueError("API Shadow freeze archive_class mismatch")
    if data.get("confirmatory_use") != CONFIRMATORY_USE:
        raise ValueError("API Shadow freeze must prohibit confirmatory use")
    if data.get("protocol_doi") != core.PROTOCOL_DOI:
        raise ValueError("API Shadow freeze protocol DOI mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("API Shadow freeze wave/site mismatch")
    if data.get("environment_class") != ENVIRONMENT_CLASS:
        raise ValueError("API Shadow v0.1 requires environment_class CLOSED")
    if not data.get("frozen_at_utc"):
        raise ValueError("API Shadow freeze is not finalized")

    entries = data.get("shadow_api")
    if not isinstance(entries, dict):
        raise ValueError("API Shadow freeze requires shadow_api object")
    expected_ids = {s["service_lineage_id"] for s in core._services()}
    if set(entries) != expected_ids:
        raise ValueError("API Shadow freeze must contain exactly the four Core Service Lineage IDs")

    for service in core._services():
        sid = service["service_lineage_id"]
        cfg = entries[sid]
        if not isinstance(cfg, dict):
            raise ValueError(f"{sid} shadow configuration must be an object")
        status = cfg.get("status")
        if status not in ALLOWED_FINAL_STATUSES:
            raise ValueError(f"{sid} final shadow status must be eligible or ineligible")
        if status == "ineligible":
            if not cfg.get("ineligibility_reason"):
                raise ValueError(f"{sid} ineligible shadow status requires ineligibility_reason")
            continue

        for field in (
            "model_id", "selection_rationale", "provider_evidence", "verified_at_utc",
            "terms_review_date", "terms_review_source", "request_profile",
        ):
            if not cfg.get(field):
                raise ValueError(f"{sid} eligible shadow configuration requires {field}")
        profile = cfg["request_profile"]
        if not isinstance(profile, dict):
            raise ValueError(f"{sid} request_profile must be an object")
        expected_adapter = EXPECTED_ADAPTER.get(service["provider"])
        if profile.get("adapter") != expected_adapter:
            raise ValueError(f"{sid} request_profile adapter mismatch")
        if FORBIDDEN_PROFILE_KEYS.intersection(profile):
            raise ValueError(f"{sid} request_profile contains forbidden capability keys")
        if not profile.get("api_key_env"):
            raise ValueError(f"{sid} request_profile requires api_key_env")
        if service["provider"] == "Anthropic" and profile.get("max_output_tokens") is None:
            raise ValueError(f"{sid} Anthropic shadow profile requires max_output_tokens")
        if service["provider"] == "Perplexity AI" and profile.get("disable_search") is not True:
            raise ValueError(f"{sid} Perplexity closed shadow profile requires disable_search=true")
    return data, sha256_file(path)


def eligible_lineages(freeze: dict[str, Any]) -> list[str]:
    return sorted(
        sid for sid, cfg in freeze["shadow_api"].items()
        if cfg.get("status") == "eligible"
    )


def generate_shadow_manifest(wave_id: str, freeze_path: Path, site_id: str = "JP01") -> list[dict]:
    config_errors = core.verify_frozen_config()
    if config_errors:
        raise ValueError("; ".join(config_errors))
    core._wave(wave_id)
    freeze, freeze_sha = load_shadow_freeze(freeze_path, wave_id, site_id)
    eligible = set(eligible_lineages(freeze))
    if not eligible:
        raise ValueError("API Shadow freeze has no eligible lineages")

    services = [s for s in core._services() if s["service_lineage_id"] in eligible]
    forms = core._forms()
    if len(forms) != 24:
        raise ValueError("frozen Core instrument must contain exactly 24 query forms")

    seed = shadow_seed(wave_id, site_id)
    rng = random.Random(seed)
    tasks = [
        (service, replication, form)
        for service in services
        for replication in range(1, 11)
        for form in forms
    ]
    rng.shuffle(tasks)

    rows: list[dict] = []
    for order, (service, replication, form) in enumerate(tasks, 1):
        sid = service["service_lineage_id"]
        model_id = freeze["shadow_api"][sid]["model_id"]
        rows.append({
            "attempt_id": core.attempt_id(
                site_id, wave_id, service["short_id"], LINE_ID, form["item_id"],
                form["language"], "STD", replication, 1,
            ),
            "observation_id": "",
            "protocol_doi": core.PROTOCOL_DOI,
            "archive_version": ARCHIVE_VERSION,
            "archive_class": ARCHIVE_CLASS,
            "confirmatory_use": CONFIRMATORY_USE,
            "wave_id": wave_id,
            "site_id": site_id,
            "service_lineage_id": sid,
            "service_name": service["name"],
            "provider": service["provider"],
            "line_id": LINE_ID,
            "environment_class": ENVIRONMENT_CLASS,
            "item_id": form["item_id"],
            "query_form_id": form["query_form_id"],
            "language": form["language"],
            "anchor": str(form["anchor"]).lower(),
            "window_id": "STD",
            "replication": replication,
            "attempt": 1,
            "execution_order": order,
            "random_seed": seed,
            "query_sha256": form["sha256"],
            "shadow_freeze_sha256": freeze_sha,
            "model_id": model_id,
            "status": "intended_exploratory",
        })
    return rows


def validate_shadow_manifest(rows: list[dict], freeze_path: Path) -> list[str]:
    errors = list(core.verify_frozen_config())
    if not rows:
        return errors + ["shadow manifest is empty"]

    wave_ids = {r.get("wave_id") for r in rows}
    site_ids = {r.get("site_id") for r in rows}
    if len(wave_ids) != 1 or len(site_ids) != 1:
        return errors + ["shadow manifest must contain exactly one wave and one site"]
    wave_id = next(iter(wave_ids))
    site_id = next(iter(site_ids))
    try:
        freeze, freeze_sha = load_shadow_freeze(freeze_path, wave_id, site_id)
    except ValueError as exc:
        return errors + [str(exc)]

    services = {s["service_lineage_id"]: s for s in core._services()}
    forms = {f["query_form_id"]: f for f in core._forms()}
    eligible = set(eligible_lineages(freeze))
    expected_count = 240 * len(eligible)
    if len(rows) != expected_count:
        errors.append(f"shadow manifest count {len(rows)} != expected {expected_count}")

    attempt_ids = [r.get("attempt_id") for r in rows]
    if len(attempt_ids) != len(set(attempt_ids)):
        errors.append("shadow attempt_id values are not unique")
    orders = [int(r.get("execution_order", 0)) for r in rows]
    if sorted(orders) != list(range(1, len(rows) + 1)):
        errors.append("shadow execution_order must be a contiguous unique sequence starting at 1")
    expected_seed = shadow_seed(wave_id, site_id)

    for i, row in enumerate(rows, 1):
        sid = row.get("service_lineage_id")
        service = services.get(sid)
        form = forms.get(row.get("query_form_id"))
        if service is None:
            errors.append(f"row {i}: unknown service lineage")
            continue
        if sid not in eligible:
            errors.append(f"row {i}: lineage is not eligible in shadow freeze")
        if form is None:
            errors.append(f"row {i}: unknown query form")
            continue
        required_constants = {
            "protocol_doi": core.PROTOCOL_DOI,
            "archive_version": ARCHIVE_VERSION,
            "archive_class": ARCHIVE_CLASS,
            "confirmatory_use": CONFIRMATORY_USE,
            "line_id": LINE_ID,
            "environment_class": ENVIRONMENT_CLASS,
            "window_id": "STD",
            "status": "intended_exploratory",
        }
        for field, expected in required_constants.items():
            if row.get(field) != expected:
                errors.append(f"row {i}: {field} mismatch")
        if row.get("service_name") != service["name"] or row.get("provider") != service["provider"]:
            errors.append(f"row {i}: service/provider metadata mismatch")
        if row.get("item_id") != form["item_id"] or row.get("language") != form["language"]:
            errors.append(f"row {i}: item/language mismatch")
        if row.get("anchor") != str(form["anchor"]).lower():
            errors.append(f"row {i}: anchor flag mismatch")
        if row.get("query_sha256") != form["sha256"]:
            errors.append(f"row {i}: query SHA-256 mismatch")
        if int(row.get("replication", 0)) not in range(1, 11) or int(row.get("attempt", 0)) != 1:
            errors.append(f"row {i}: replication/attempt mismatch")
        if int(row.get("random_seed", -1)) != expected_seed:
            errors.append(f"row {i}: shadow random seed mismatch")
        if row.get("shadow_freeze_sha256") != freeze_sha:
            errors.append(f"row {i}: shadow freeze SHA-256 mismatch")
        expected_model = freeze["shadow_api"][sid].get("model_id")
        if row.get("model_id") != expected_model:
            errors.append(f"row {i}: model ID does not match shadow freeze")
        expected_attempt = core.attempt_id(
            site_id, wave_id, service["short_id"], LINE_ID, form["item_id"],
            form["language"], "STD", int(row["replication"]), int(row["attempt"]),
        )
        if row.get("attempt_id") != expected_attempt:
            errors.append(f"row {i}: attempt ID mismatch")

    for sid in eligible:
        sr = [r for r in rows if r.get("service_lineage_id") == sid]
        if len(sr) != 240:
            errors.append(f"{sid} shadow count {len(sr)} != 240")
        for qid in forms:
            if sum(r.get("query_form_id") == qid for r in sr) != 10:
                errors.append(f"{sid} {qid} shadow count must equal 10")
    return errors


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty shadow manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        for field in ("replication", "attempt", "execution_order", "random_seed"):
            row[field] = int(row[field])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("generate")
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("validate")
    p.add_argument("manifest", type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    args = parser.parse_args()

    if args.cmd == "generate":
        rows = generate_shadow_manifest(args.wave, args.freeze, args.site)
        errors = validate_shadow_manifest(rows, args.freeze)
        if errors:
            raise SystemExit("\n".join(errors))
        write_csv(rows, args.out)
        print(f"wrote {len(rows)} exploratory API Shadow rows to {args.out}")
        return 0

    rows = read_csv(args.manifest)
    errors = validate_shadow_manifest(rows, args.freeze)
    if errors:
        print("\n".join(errors))
        return 1
    print("API Shadow manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
