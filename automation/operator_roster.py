#!/usr/bin/env python3
"""Frozen human-operator roster validation for MIBO Core Ecological Live."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import mibo_runner as core

PROTOCOL_DOI = "10.5281/zenodo.21936410"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_roster(path: Path, *, wave_id: str, site_id: str) -> tuple[dict[str, Any], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("protocol_doi") != PROTOCOL_DOI:
        raise ValueError("operator roster protocol DOI mismatch")
    if data.get("wave_id") != wave_id or data.get("site_id") != site_id:
        raise ValueError("operator roster wave/site mismatch")
    if not data.get("frozen_at_utc"):
        raise ValueError("operator roster is not finalized")
    if not data.get("operations_lead"):
        raise ValueError("operator roster requires operations_lead")
    service_operators = data.get("service_operators")
    if not isinstance(service_operators, dict):
        raise ValueError("operator roster requires service_operators")
    expected = {s["service_lineage_id"] for s in core._services()}
    if set(service_operators) != expected:
        raise ValueError("operator roster service-lineage set does not match MIBO Core v1.0")
    for sid, operators in service_operators.items():
        if not isinstance(operators, list) or not operators:
            raise ValueError(f"{sid} requires at least one assigned Service Operator")
        normalized = [str(v).strip() for v in operators]
        if any(not v for v in normalized):
            raise ValueError(f"{sid} contains an empty operator ID")
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"{sid} contains duplicate operator IDs")
    return data, sha256_file(path)


def assert_operator_assigned(roster: dict[str, Any], *, service_lineage_id: str, operator_id: str) -> None:
    allowed = (roster.get("service_operators") or {}).get(service_lineage_id) or []
    if operator_id not in allowed:
        raise ValueError(f"operator {operator_id!r} is not assigned to {service_lineage_id}")


def assigned_lineages(roster: dict[str, Any], operator_id: str) -> list[str]:
    return sorted(
        sid for sid, operators in (roster.get("service_operators") or {}).items()
        if operator_id in operators
    )
