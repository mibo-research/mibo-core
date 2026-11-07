"""Prospective three-series Core v2.1 gates; no transport or credentials."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = "2.1"
LINEAGES = ("MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-003")
PROVIDERS = dict(zip(LINEAGES, ("OpenAI", "Anthropic", "Google")))
PANEL_POLICY = "openai-anthropic-google-only-no-substitution-v1"
TRANSITION_POLICY = "separate-version-estimands-no-automatic-pooling-v1"
SCORING_POLICY = "two-other-provider-family-judges-common-calibration-v1"
SENTINEL_ENV = "MIBO_CORE_V21_EXECUTION"
SENTINEL = "ENABLED_AFTER_CORE_V21_GATE"
AUTHORIZATION_GATES = (
    "prospective_three_series_amendment_reviewed",
    "three_series_panel_approved",
    "version_boundary_no_pooling_reviewed",
    "reciprocal_ai_scoring_change_reviewed",
)
PRIOR_REGISTRATION = "10.5281/zenodo.22264635"
W03_ANALYSIS_REGISTRATION = "https://github.com/mibo-research/mibo-core/blob/30e48170f7387002e506baabd36884f12cc7a250/docs/analysis/W03-URL-variation-v1.0/REGISTRATION.md"


def validate_approved_policy_bindings(data: dict[str, Any]) -> None:
    import core_v21_analysis as analysis
    import core_v21_scoring as scoring
    analysis.load_policy()
    scoring.load_policy()
    for prefix, module in (("analysis", analysis), ("scoring_qualification", scoring)):
        if (data.get(prefix + "_policy_file") != module.POLICY_FILE
                or data.get(prefix + "_policy_sha256") != hashlib.sha256((module.ROOT / module.POLICY_FILE).read_bytes()).hexdigest()):
            raise ValueError("approved v2.1 policy file/SHA-256 mismatch: " + prefix)
    if data.get("effective_from_wave_id") != "MIBO2-W03" or data.get("analysis_transition_decision") != analysis.POLICY_ID:
        raise ValueError("approved v2.1 policy fixes W03 baseline/effective wave; no automatic substitution")
    plan = data.get("ai_scoring_qualification_plan")
    if (not isinstance(plan, dict) or plan.get("policy_id") != scoring.POLICY_ID
            or plan.get("status") != "prospectively_fixed"
            or plan.get("operational_qualification_is_not_validity") is not True
            or plan.get("primary_URL_analysis_blocked_by_AI_qualification") is not False
            or plan.get("unreferenced_AI_use_scope") != "auxiliary_exploratory_only"):
        raise ValueError("approved scoring policy must separate operational admission from validity")


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("v2.1 timestamps require an explicit timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid v2.1 timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("v2.1 timestamps require an explicit timezone")
    return result.astimezone(timezone.utc)


def validate_protocol(data: dict[str, Any], original_waves: list,
                      *, require_final: bool) -> None:
    for key, value in {
        "prior_protocol_registration_id": PRIOR_REGISTRATION,
        "lineage_panel_policy": PANEL_POLICY,
        "analysis_transition_policy": TRANSITION_POLICY,
        "scoring_policy": SCORING_POLICY,
        "coexisting_W03_analysis_registration_id": W03_ANALYSIS_REGISTRATION,
        "required_service_lineages": list(LINEAGES),
        "waves": original_waves,
    }.items():
        if data.get(key) != value:
            raise ValueError(f"v2.1 {key} mismatch; preserve the registered design")
    if any(key in data for key in ("lineage_admission_policy", "perplexity_transport_contract")):
        raise ValueError("v2.1 must not inherit the historical Perplexity/admission amendment")
    validate_approved_policy_bindings(data)
    if not require_final:
        return
    reg = data.get("protocol_registration_id")
    if (not isinstance(reg, str) or reg in {PRIOR_REGISTRATION, "10.5281/zenodo.21936410"}
            or not re.fullmatch(
                r"10\.5281/zenodo\.[0-9]+|https://github\.com/mibo-research/mibo-core/blob/[0-9a-f]{40}/docs/v2\.1/[^?#]+", reg)):
        raise ValueError("v2.1 requires its own immutable public registration identifier")
    registered = timestamp(data.get("prospectively_registered_at_utc"))
    effective = data.get("effective_from_wave_id")
    matches = [w for w in original_waves if w["wave_id"] == effective]
    if len(matches) != 1 or registered >= timestamp(matches[0]["start_utc"]):
        raise ValueError("v2.1 effective wave must be selected and registered before its original start")
    transition = data.get("W03_analysis_transition")
    ids = [w["wave_id"] for w in original_waves]
    if not isinstance(transition, dict):
        raise ValueError("v2.1 must resolve the existing four-series W03 analysis registration")
    if ids.index(effective) > ids.index("MIBO2-W03"):
        if transition != {"status": "preserved-unmodified", "registration_id": W03_ANALYSIS_REGISTRATION}:
            raise ValueError("later v2.1 activation must explicitly preserve the four-series W03 registration")
    else:
        replacement = transition.get("registration_id")
        if (transition.get("status") != "separately-amended-prospectively"
                or replacement == W03_ANALYSIS_REGISTRATION or not isinstance(replacement, str)
                or not re.fullmatch(r"10\.5281/zenodo\.[0-9]+|https://github\.com/mibo-research/mibo-core/blob/[0-9a-f]{40}/docs/analysis/[^?#]+", replacement)
                or timestamp(transition.get("registered_at_utc")) > registered):
            raise ValueError("v2.1 W03 activation requires a separately published prospective W03 analysis amendment")
    decision = data.get("analysis_transition_decision")
    if not isinstance(decision, str) or not decision.strip() or decision.startswith("REPLACE_"):
        raise ValueError("v2.1 analysis/baseline transition decision is not prospectively fixed")
    qualification = data.get("ai_scoring_qualification_plan")
    if (not isinstance(qualification, dict)
            or qualification.get("status") != "prospectively_fixed"
            or not isinstance(qualification.get("ai_agreement_criteria"), str)
            or not qualification["ai_agreement_criteria"].strip()
            or qualification.get("external_validity_claim") != "not_established_by_inter_ai_agreement"
            or qualification.get("H_variable_policy") != "external-evidence-human-verification-held-until-qualified"):
        raise ValueError("v2.1 AI qualification criteria and H-variable responsibility are not fixed")


def validate_wave(protocol: dict[str, Any], wave_id: str) -> None:
    ids = [w["wave_id"] for w in protocol["waves"]]
    effective = protocol.get("effective_from_wave_id")
    if effective not in ids or wave_id not in ids or ids.index(wave_id) < ids.index(effective):
        raise ValueError("wave predates the prospective v2.1 effective-wave boundary")


def validate_profile(provider: str, profile: dict[str, Any]) -> None:
    common = {"adapter", "api_key_env", "max_output_tokens", "temperature", "top_p"}
    extra = {"OpenAI": {"endpoint", "reasoning"}, "Anthropic": {"endpoint", "anthropic_version"},
             "Google": {"endpoint_base"}}[provider]
    if set(profile) - common - extra:
        raise ValueError("v2.1 profile has unsupported settings; no hidden routing, tools or fallback")
    key, endpoint, credential = {
        "OpenAI": ("endpoint", "https://api.openai.com/v1/responses", "OPENAI_API_KEY"),
        "Anthropic": ("endpoint", "https://api.anthropic.com/v1/messages", "ANTHROPIC_API_KEY"),
        "Google": ("endpoint_base", "https://generativelanguage.googleapis.com/v1beta/models", "GEMINI_API_KEY"),
    }[provider]
    if profile.get(key) != endpoint or profile.get("api_key_env") != credential:
        raise ValueError("v2.1 requires the official first-party endpoint and provider credential name")
    limit = profile.get("max_output_tokens")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("v2.1 output budget must be a positive integer")


def require_execution_sentinels() -> None:
    if (os.environ.get("MIBO_CORE_V2_EXECUTION") != "ENABLED_AFTER_CORE_V2_GATE"
            or os.environ.get(SENTINEL_ENV) != SENTINEL):
        raise ValueError("v2.1 requires both the Core v2 and dedicated v2.1 execution sentinels")


def require_readiness_sentinels(*, smoke: bool) -> None:
    if os.environ.get("MIBO_CORE_V21_READINESS") != "ENABLED_AFTER_CORE_V21_READINESS_APPROVAL":
        raise ValueError("v2.1 metadata/smoke requests require separate explicit readiness approval")
    if smoke and os.environ.get("MIBO_CORE_V2_SMOKE_TEST") != "ENABLED_AFTER_TERMS_REVIEW":
        raise ValueError("v2.1 synthetic smoke requires the additional terms-review sentinel")


def _evidence(report_path: Path, relative: Any, digest: Any) -> dict[str, Any]:
    if (not isinstance(relative, str) or "\\" in relative
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("v2.1 readiness evidence path/hash is invalid")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or rel.as_posix() != relative or any(p in {"", ".", ".."} for p in rel.parts):
        raise ValueError("v2.1 readiness evidence path is unsafe")
    path = report_path.parent / rel
    if (not path.is_file() or any(p.is_symlink() for p in (path, *path.parents))
            or not path.resolve().is_relative_to(report_path.parent.resolve())):
        raise ValueError("v2.1 readiness evidence must be an existing local regular file")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("v2.1 readiness evidence SHA-256 mismatch")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("v2.1 readiness evidence must be an object")
    return data


def validate_readiness(report_path: Path, *, protocol: dict[str, Any], protocol_sha: str,
                       freeze: dict[str, Any], freeze_sha: str) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for field, expected in {
        "schema_version": VERSION, "protocol_version": VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha, "provider_freeze_sha256": freeze_sha,
        "wave_id": freeze["wave_id"], "site_id": freeze["site_id"],
        "scientific_class": "confirmatory_primary", "pass": True,
        "synthetic_smoke_requested": True, "automatic_model_selection": False,
        "automatic_provider_substitution": False, "provider_freeze_modified": False,
        "registered_mibo_prompts_used": False, "errors": [],
    }.items():
        actual = report.get(field)
        if actual != expected or (isinstance(expected, bool) and actual is not expected):
            raise ValueError(f"v2.1 readiness {field} mismatch")
    if timestamp(report.get("checked_at_utc")) < timestamp(freeze["frozen_at_utc"]):
        raise ValueError("v2.1 readiness predates the new freeze")
    for field in ("model_checks", "synthetic_smoke_checks"):
        checks = report.get(field)
        if (not isinstance(checks, list) or len(checks) != len(LINEAGES)
                or any(not isinstance(c, dict) for c in checks)
                or {c.get("service_lineage_id") for c in checks} != set(LINEAGES)):
            raise ValueError("v2.1 requires exactly three distinct passing readiness lineages")
        for check in checks:
            sid = check["service_lineage_id"]
            provider = PROVIDERS[sid]
            if check.get("model_id") != freeze["core_api"][sid]["model_id"] or check.get("provider") != provider:
                raise ValueError("v2.1 readiness frozen model mismatch")
            if field == "model_checks":
                # These helpers parse already captured JSON; no provider call.
                from api_preflight import catalog_model_ids, returned_metadata_model_id
                if check.get("exact_metadata_verified") is not True:
                    raise ValueError("v2.1 readiness model was not verified")
                if check.get("metadata_file"):
                    evidence = _evidence(report_path, check["metadata_file"], check.get("metadata_sha256"))
                    response = evidence.get("response")
                    if (check.get("verification_method") != "exact_metadata_endpoint"
                            or not isinstance(response, dict)
                            or returned_metadata_model_id(provider, response) != check["model_id"]
                            or check.get("metadata_returned_model_id") != check["model_id"]):
                        raise ValueError("v2.1 captured metadata does not verify the frozen model")
                else:
                    catalog = report.get("catalogs", {}).get(provider, {})
                    evidence = _evidence(report_path, catalog.get("file"), catalog.get("sha256"))
                    response = evidence.get("response")
                    ids = catalog_model_ids(provider, response) if isinstance(response, dict) else []
                    if (check.get("verification_method") != "catalog_listing"
                            or check.get("metadata_returned_model_id") is not None
                            or check.get("listed_in_catalog_response") is not True
                            or check["model_id"] not in ids
                            or catalog.get("model_ids") != ids
                            or evidence.get("normalized_model_ids") != ids):
                        raise ValueError("v2.1 captured catalog does not verify the frozen model")
                status = evidence.get("http_status")
                if (type(status) is not int or not 200 <= status < 300
                        or evidence.get("service_provider_label") != provider
                        or evidence.get("api_provider") != provider
                        or evidence.get("credential_value_recorded") is not False
                        or not (timestamp(freeze["frozen_at_utc"])
                            <= timestamp(evidence.get("started_at_utc"))
                            <= timestamp(evidence.get("completed_at_utc"))
                            <= timestamp(report["checked_at_utc"]))):
                    raise ValueError("v2.1 captured model evidence provider/status/timing mismatch")
            else:
                if check.get("pass") is not True:
                    raise ValueError("v2.1 requires all three passing smoke checks")
                evidence = _evidence(report_path, check.get("file"), check.get("sha256"))
                if (evidence.get("pass") is not True
                        or evidence.get("service_lineage_id") != sid
                        or evidence.get("requested_model") != check["model_id"]
                        or evidence.get("returned_model") != check["model_id"]
                        or evidence.get("registered_mibo_prompt_used") is not False):
                    raise ValueError("v2.1 smoke evidence identity or outcome mismatch")
    return report


def readiness_evidence_paths(report_path: Path, report: dict[str, Any]) -> list[Path]:
    """Call only after validate_readiness has confined and hashed these paths."""
    relative = {c["file"] for c in report["synthetic_smoke_checks"]}
    for check in report["model_checks"]:
        if check.get("metadata_file"):
            relative.add(check["metadata_file"])
        else:
            relative.add(report["catalogs"][check["provider"]]["file"])
    return [report_path.parent / name for name in sorted(relative)]
