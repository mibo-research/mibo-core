#!/usr/bin/env python3
"""Human-operated Ecological Live capture utilities for MIBO Core v1.0.

This module deliberately contains no browser automation, DOM access, scraping,
network interception, clipboard monitoring, or provider HTTP calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import mibo_runner as core
import operator_roster
from raw_archive import canonical_json_bytes, wave_root


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def window_bounds(wave_id: str, window_id: str) -> tuple[datetime, datetime]:
    wave = core._wave(wave_id)
    start = parse_utc(wave["start_utc"])
    close = parse_utc(wave["close_utc"])
    if window_id == "STD":
        return start, close
    if window_id == "WA" and wave.get("window_a"):
        spec = wave["window_a"]
        return start + timedelta(hours=spec["start_offset_hours"]), start + timedelta(hours=spec["end_offset_hours"])
    if window_id == "WB" and wave.get("window_b"):
        spec = wave["window_b"]
        return start + timedelta(hours=spec["start_offset_hours"]), start + timedelta(hours=spec["end_offset_hours"])
    raise ValueError(f"window {window_id} is not registered for {wave_id}")


def within_registered_window(row: dict, now: datetime | None = None) -> bool:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start, end = window_bounds(row["wave_id"], row["window_id"])
    return start <= current < end


def load_ui_configuration(path: Path, *, wave_id: str, site_id: str) -> tuple[dict[str, Any], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("protocol_doi") != "10.5281/zenodo.21936410":
        raise ValueError("UI configuration protocol DOI mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("UI configuration wave/site mismatch")
    if not data.get("frozen_at_utc"):
        raise ValueError("UI configuration is not finalized")
    return data, sha256_file(path)


def validate_ui_service_configuration(config: dict[str, Any], service_lineage_id: str) -> dict[str, Any]:
    entry = (config.get("ecological_live") or {}).get(service_lineage_id)
    if not isinstance(entry, dict):
        raise ValueError(f"{service_lineage_id} missing from Ecological Live configuration")
    if entry.get("status") != "ready_human_operated":
        raise ValueError(f"{service_lineage_id} is not ready for human-operated UI collection")
    if entry.get("interaction_mode") != "human_only":
        raise ValueError(f"{service_lineage_id} interaction_mode must be human_only")
    if entry.get("terms_review_complete") is not True:
        raise ValueError(f"{service_lineage_id} Terms/access review is not complete")
    if entry.get("new_session_required") is not True:
        raise ValueError(f"{service_lineage_id} must require a fresh session")
    return entry


def _write_exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)
    return sha256_bytes(data)


def capture_ui_observation(*, data_root: Path, row: dict, prompt_text: str, output_text: str,
                           ui_configuration_path: Path, operator_roster_path: Path,
                           operator_id: str, operator_confirmed_new_session: bool,
                           submitted_at_utc: str, captured_at_utc: str,
                           sources_displayed: bool, sources_text: str | None = None,
                           displayed_service_mode: str | None = None,
                           displayed_model_label: str | None = None,
                           notes: str | None = None,
                           now: datetime | None = None) -> dict[str, Any]:
    if row.get("line_id") != "LUI":
        raise ValueError("Ecological Live capture accepts LUI rows only")
    if not operator_confirmed_new_session:
        raise ValueError("operator must confirm a fresh session before capture")
    operator_id = operator_id.strip()
    if not operator_id:
        raise ValueError("operator_id is required")
    if not within_registered_window(row, now=now):
        raise ValueError("capture is outside the row's registered observation window")
    if sources_displayed and not (sources_text or "").strip():
        raise ValueError("displayed citations/source cards/links must be captured when sources_displayed is true")
    if not sources_displayed and (sources_text or "").strip():
        raise ValueError("sources_text was supplied while sources_displayed is false")

    config, config_sha = load_ui_configuration(
        ui_configuration_path, wave_id=row["wave_id"], site_id=row["site_id"]
    )
    service_cfg = validate_ui_service_configuration(config, row["service_lineage_id"])
    roster, roster_sha = operator_roster.load_roster(
        operator_roster_path, wave_id=row["wave_id"], site_id=row["site_id"]
    )
    operator_roster.assert_operator_assigned(
        roster, service_lineage_id=row["service_lineage_id"], operator_id=operator_id
    )

    actual_prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    if actual_prompt_hash != row["query_sha256"]:
        raise ValueError("prompt text does not match frozen query SHA-256")

    root = wave_root(data_root, row["site_id"], row["wave_id"])
    attempt_id = row["attempt_id"]
    prompt_path = root / "ui_raw" / f"{attempt_id}.prompt.txt"
    output_path = root / "ui_raw" / f"{attempt_id}.output.txt"
    prompt_hash = _write_exclusive(prompt_path, prompt_text.encode("utf-8"))
    output_hash = _write_exclusive(output_path, output_text.encode("utf-8"))

    sources_file: str | None = None
    sources_hash: str | None = None
    if sources_displayed:
        sources_path = root / "ui_raw" / f"{attempt_id}.sources.txt"
        sources_hash = _write_exclusive(sources_path, (sources_text or "").encode("utf-8"))
        sources_file = str(sources_path.relative_to(root))

    metadata = {
        "attempt_id": attempt_id,
        "retry_of_attempt_id": row.get("retry_of_attempt_id"),
        "protocol_doi": row["protocol_doi"],
        "wave_id": row["wave_id"],
        "site_id": row["site_id"],
        "service_lineage_id": row["service_lineage_id"],
        "service_name": row["service_name"],
        "line_id": "LUI",
        "query_form_id": row["query_form_id"],
        "item_id": row["item_id"],
        "language": row["language"],
        "window_id": row["window_id"],
        "replication": row["replication"],
        "attempt": row["attempt"],
        "operator_id": operator_id,
        "operator_roster_sha256": roster_sha,
        "operator_confirmed_new_session": True,
        "interaction_mode": "human_only",
        "browser_automation": False,
        "programmatic_output_extraction": False,
        "ui_configuration_sha256": config_sha,
        "account_tier": service_cfg.get("account_tier"),
        "configured_mode": service_cfg.get("mode"),
        "configured_search_tools_state": service_cfg.get("search_tools_state"),
        "configured_memory_personalization_state": service_cfg.get("memory_personalization_state"),
        "configured_locale": service_cfg.get("locale"),
        "displayed_service_mode": displayed_service_mode,
        "displayed_model_label": displayed_model_label,
        "submitted_at_utc": submitted_at_utc,
        "captured_at_utc": captured_at_utc,
        "prompt_file": str(prompt_path.relative_to(root)),
        "prompt_sha256": prompt_hash,
        "output_file": str(output_path.relative_to(root)),
        "output_sha256": output_hash,
        "sources_displayed": bool(sources_displayed),
        "sources_capture_state": "captured" if sources_displayed else "none_displayed",
        "sources_file": sources_file,
        "sources_sha256": sources_hash,
        "notes": notes,
        "status": "captured_human_operated",
    }
    metadata_path = root / "metadata" / f"{attempt_id}.ui.json"
    metadata_hash = _write_exclusive(metadata_path, canonical_json_bytes(metadata))
    return {**metadata, "metadata_file_sha256": metadata_hash}


def completed_attempt_ids(data_root: Path, site_id: str, wave_id: str) -> set[str]:
    root = wave_root(data_root, site_id, wave_id) / "metadata"
    if not root.exists():
        return set()
    return {p.name[:-8] for p in root.glob("*.ui.json") if p.name.endswith(".ui.json")}
