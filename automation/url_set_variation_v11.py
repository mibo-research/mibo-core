"""Offline W03 three-series derivative-analysis preparation; no API or network.

The immutable v1.0 URL extraction/similarity functions are reused without
changing their four-series validator. This draft reports W03 descriptions
only; it never automatically runs a cross-version W03-minus-W02 contrast.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from itertools import product
from pathlib import Path

import core_v21_analysis as analysis_policy
import core_v21_policy as policy
import mibo_runner
import url_set_variation as prior

SCHEMA = "mibo-w03-three-series-url-input-1.1"
LEGACY_SOURCE_SHA256 = "914b61672d66ca0dd21f3bd4a89e70dd5d7589d4322f3106e95b9f32535216a6"
AUDIT_FIELDS = ("technical_audit_sha256", "raw_wave_manifest_sha256", "core_protocol_sha256",
                "collection_manifest_sha256", "provider_freeze_sha256")


def frozen_query_hashes() -> dict[str, str]:
    forms = [f for f in mibo_runner._forms() if f["item_id"] == "MIBO-I03"]
    if len(forms) != 2 or {f["language"] for f in forms} != {"EN", "JA"}:
        raise ValueError("frozen I03 query forms changed")
    return {f["language"]: f["sha256"] for f in forms}


def _digest(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_rows(rows: list[dict]) -> dict:
    if not isinstance(rows, list):
        raise ValueError("expected the complete 60-slot W03 row list")
    query_hashes = frozen_query_hashes()
    groups, seen = defaultdict(list), set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("wave_id") != "MIBO2-W03"
                or row.get("protocol_version") != policy.VERSION
                or row.get("site_id") != "JP01" or row.get("item_id") != "MIBO-I03"
                or row.get("condition") != "ACI" or row.get("window_id") != "STD"
                or row.get("service_lineage_id") not in policy.LINEAGES
                or row.get("language") not in query_hashes):
            raise ValueError("row is outside the v2.1 three-series W03 I03 subset")
        if row.get("query_sha256") != query_hashes[row["language"]]:
            raise ValueError("row does not match the frozen I03 query hash")
        if not _digest(row.get("request_profile_sha256")):
            raise ValueError("missing or invalid request-profile digest")
        if not isinstance(row.get("model_id"), str) or not row["model_id"].strip():
            raise ValueError("missing frozen model identifier")
        rep = row.get("replication")
        if type(rep) is not int or rep not in range(1, 11):
            raise ValueError("replication is not a planned logical slot")
        logical = (row["service_lineage_id"], row["language"], rep)
        if logical in seen:
            raise ValueError("duplicate logical slot; retries cannot increase the denominator")
        seen.add(logical)
        if row.get("technical_status") == "valid":
            prior.extract_urls(row.get("text"), row.get("citations"))
            if not _digest(row.get("raw_capture_sha256")):
                raise ValueError("valid response requires its archived capture digest")
        elif row.get("technical_status") == "technical_missing":
            if (row.get("text") not in (None, "") or row.get("citations") not in (None, [])
                    or row.get("raw_capture_sha256") is not None):
                raise ValueError("technical missingness must not carry a fabricated response or capture")
        else:
            raise ValueError("valid refusal/nonanswer is not technical missingness")
        groups[(row["service_lineage_id"], row["language"])].append(row)
    if len(rows) != 60 or set(groups) != set(product(policy.LINEAGES, ("EN", "JA"))):
        raise ValueError("include all 60 intended I03 slots across six cells, including missing slots")
    for members in groups.values():
        if (len(members) != 10
                or len({(r["model_id"], r["request_profile_sha256"]) for r in members}) != 1):
            raise ValueError("do not pool model/settings deployments within a cell")
    return groups


def analyze_w03(document: dict) -> dict:
    """Pure descriptive library entry point, used only with synthetic data here.

    Audit-digest *shape* is checked; this function does not independently open
    or verify a restricted raw archive and never asserts registered validity.
    """
    if (not isinstance(document, dict) or document.get("schema") != SCHEMA
            or any(k in document for k in ("baseline", "baseline_rows", "W02_rows", "prospective"))):
        raise ValueError("expected W03-only three-series input; cross-version comparison is held")
    provenance = document.get("provenance")
    if not isinstance(provenance, dict) or any(not _digest(provenance.get(k)) for k in AUDIT_FIELDS):
        raise ValueError("missing hash-bound technical-audit/configuration provenance")
    if hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest() != LEGACY_SOURCE_SHA256:
        raise ValueError("preserved v1.0 URL-rule dependency SHA-256 mismatch")
    groups = validate_rows(document.get("rows"))
    cells = []
    for (lineage, language), rows in sorted(groups.items()):
        summary, _sets = prior.summarize(rows)
        baseline = analysis_policy.baseline_cell(wave_id="MIBO2-W03", window_id="STD", valid_n=summary["valid_n"])
        cells.append({"protocol_version": policy.VERSION, "wave_id": "MIBO2-W03", "site_id": "JP01",
            "service_lineage_id": lineage, "item_id": "MIBO-I03", "language": language,
            "condition": "ACI", "window_id": "STD", "model_id": rows[0]["model_id"],
            "query_sha256": rows[0]["query_sha256"], "request_profile_sha256": rows[0]["request_profile_sha256"],
            "minimum_n8_rule_satisfied": summary["valid_n"] >= 8,
            "baseline_cell": baseline,
            "URL_baseline_eligible": baseline["eligible"] and summary["exact_url_jaccard"]["mean"] is not None,
            "undefined_URL_baseline_may_be_substituted": False,
            **summary})
    return {"schema": "mibo-w03-three-series-url-descriptions-1.1-draft",
        "analysis_status": "LOCAL_AMENDMENT_DRAFT_NOT_A_REGISTERED_RESULT", "intended_I03_slots": 60,
        "intended_I03_cells": 6, "cells": cells, "contrasts": [],
        "W02_comparison_status": "EXCLUDED_FROM_PRIMARY_SEPARATE_PROSPECTIVE_PLAN_REQUIRED_FOR_EXPLORATION",
        "baseline_wave": "MIBO2-W03", "baseline_policy_id": analysis_policy.POLICY_ID,
        "baseline_policy_sha256": analysis_policy.policy_digest(),
        "automatic_baseline_substitution": False, "first_separate_calibration_wave": "MIBO2-W04",
        "AI_qualification_required_for_URL_analysis": False,
        "hypothesis_tests": None, "additional_human_case_grading": 0,
        "pair_rows_are_not_independent_responses": True,
        "technical_audit_hashes": {k: provenance[k] for k in AUDIT_FIELDS},
        "audit_digest_shapes_checked": True, "restricted_raw_archive_independently_verified_here": False,
        "factuality_H_or_human_validity_established": False, "network_requests": False,
        "observation_or_scoring_API_calls": 0}
