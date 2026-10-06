"""Hash-bound lineage readiness for the prospective v2.0.2 admission policy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import core_v2_runner as runner
from core_v2_preflight import SYNTHETIC_PROMPT

VERSION = "2.0.2"
POLICY = "human-authorized-ready-lineages-original-windows-v1"
INITIAL_SCOPE = ["MIBO-SL-001", "MIBO-SL-002", "MIBO-SL-004"]
GOOGLE_SCOPE = ["MIBO-SL-003"]


def scope(value: object) -> list[str]:
    # This amendment permits the reviewed three-provider scope or Google joining
    # separately. It does not admit arbitrary subsets or automatic promotion.
    if not isinstance(value, list) or value not in (INITIAL_SCOPE, GOOGLE_SCOPE):
        raise ValueError("unapproved lineage admission scope")
    return list(value)


def checked(path: Path, expected: str) -> dict:
    if runner.sha256_file(path) != expected:
        raise ValueError("readiness evidence hash mismatch")
    return json.loads(path.read_text())


def validate_report(path: Path, *, protocol: dict, protocol_sha: str,
                    freeze: dict, freeze_sha: str, admitted: list[str]) -> dict:
    if protocol["protocol_version"] == runner.STANDARD_PROTOCOL_VERSION:
        import core_v2_standard
        return core_v2_standard.validate_report(path, protocol=protocol, protocol_sha=protocol_sha,
            freeze=freeze, freeze_sha=freeze_sha, admitted=admitted)
    if protocol["protocol_version"] == runner.PRIORITY_PROTOCOL_VERSION:
        import core_v2_priority
        return core_v2_priority.validate_report(path, protocol=protocol, protocol_sha=protocol_sha,
            freeze=freeze, freeze_sha=freeze_sha, admitted=admitted)
    admitted = scope(admitted)
    report = json.loads(path.read_text())
    expected = {"protocol_version": VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha, "provider_freeze_sha256": freeze_sha,
        "wave_id": freeze["wave_id"], "site_id": freeze["site_id"],
        "readiness_scope": "admitted_lineages_only", "admitted_lineages": admitted,
        "synthetic_smoke_requested": True, "pass": True}
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError("scoped readiness identity/scope mismatch: " + key)
    checks = report.get("synthetic_smoke_checks", [])
    if len(checks) != 4 or {c.get("service_lineage_id") for c in checks} != set(freeze["core_api"]):
        raise ValueError("scoped readiness must disclose all four lineages")
    prompt_sha = hashlib.sha256(SYNTHETIC_PROMPT.encode()).hexdigest()
    for sid in admitted:
        check = next(c for c in checks if c["service_lineage_id"] == sid)
        cfg = freeze["core_api"][sid]
        if check.get("pass") is not True or check.get("model_id") != cfg["model_id"]:
            raise ValueError("admitted lineage has no matching passing smoke")
        evidence_path = Path(check["file"])
        if not evidence_path.is_absolute():
            raise ValueError("scoped evidence requires an absolute private path")
        evidence = checked(evidence_path, check["sha256"])
        if (evidence.get("pass") is not True or evidence.get("readiness_only") is not True
                or evidence.get("requested_model") != cfg["model_id"]
                or evidence.get("returned_model") != cfg["model_id"]
                or evidence.get("synthetic_prompt_sha256") != prompt_sha
                or not 200 <= evidence.get("http_status", 0) < 300):
            raise ValueError("admitted synthetic evidence model/prompt/status mismatch")
        if runner.parse_aware_utc(report["checked_at_utc"]) < runner.parse_aware_utc(evidence["completed_at_utc"]):
            raise ValueError("scoped readiness cannot predate the smoke response")
    if admitted == INITIAL_SCOPE:
        google = next(c for c in checks if c["service_lineage_id"] == GOOGLE_SCOPE[0])
        if google.get("pass") is not False or google.get("http_status") != 503:
            raise ValueError("initial scope must disclose deferred Google HTTP 503")
        old_freeze = checked(Path(report["prior_freeze_file"]), report["prior_freeze_sha256"])
        old_report = checked(Path(report["prior_report_file"]), report["prior_report_sha256"])
        if old_report.get("pass") is not False:
            raise ValueError("prior four-provider report must remain failed")
        if old_report.get("provider_freeze_sha256") != report["prior_freeze_sha256"]:
            raise ValueError("prior report/freeze binding mismatch")
        models = old_report.get("model_checks", [])
        if (len(models) != 4 or {c.get("service_lineage_id") for c in models} != set(freeze["core_api"])
                or not all(c.get("exact_metadata_verified") is True for c in models)):
            raise ValueError("original four-provider model metadata is incomplete")
        for sid in freeze["core_api"]:
            old, new = old_freeze["core_api"][sid], freeze["core_api"][sid]
            if old["model_id"] != new["model_id"] or old["request_profile"] != new["request_profile"]:
                raise ValueError("readiness reuse requires unchanged model and profile")
        for check in checks:
            original = next(c for c in old_report["synthetic_smoke_checks"]
                            if c["service_lineage_id"] == check["service_lineage_id"])
            if {k: v for k, v in check.items() if k != "file"} != {k: v for k, v in original.items() if k != "file"}:
                raise ValueError("prior smoke result was changed")
            expected_path = (Path(report["prior_report_file"]).parent / original["file"]).resolve()
            if Path(check["file"]).resolve() != expected_path:
                raise ValueError("reused smoke evidence path mismatch")
            checked(Path(check["file"]), check["sha256"])
    else:
        if report.get("human_google_admission_required") is not True:
            raise ValueError("Google recovery must retain the human admission gate")
        if not isinstance(report.get("google_recovery_probe_number"), int) or report["google_recovery_probe_number"] not in {1, 2, 3}:
            raise ValueError("Google recovery probe number is out of bounds")
    return report


def validate_authorization(auth: dict, *, protocol_path: Path, freeze_path: Path,
                           protocol: dict, freeze: dict) -> list[str]:
    admitted = scope(auth.get("admitted_lineages"))
    if protocol["protocol_version"] == runner.STANDARD_PROTOCOL_VERSION:
        if admitted != GOOGLE_SCOPE or auth.get("prospective_gemini_standard_amendment_reviewed") is not True:
            raise ValueError("Google Standard human amendment authorization is missing")
    if protocol["protocol_version"] == runner.PRIORITY_PROTOCOL_VERSION:
        if admitted != GOOGLE_SCOPE or auth.get("prospective_gemini_priority_amendment_reviewed") is not True:
            raise ValueError("Google Priority human amendment authorization is missing")
    if auth.get("prospective_lineage_admission_amendment_reviewed") is not True:
        raise ValueError("lineage admission amendment not human reviewed")
    if auth.get("admission_policy") != POLICY:
        raise ValueError("lineage admission policy mismatch")
    path = Path(auth["readiness_report_file"])
    checked(path, auth["readiness_report_sha256"])
    report = validate_report(path, protocol=protocol,
        protocol_sha=runner.sha256_file(protocol_path), freeze=freeze,
        freeze_sha=runner.sha256_file(freeze_path), admitted=admitted)
    if runner.parse_aware_utc(auth["authorized_at_utc"]) < runner.parse_aware_utc(report["checked_at_utc"]):
        raise ValueError("authorization cannot predate scoped readiness")
    return admitted
