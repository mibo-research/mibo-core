"""Prospective Google-only Standard restoration admission; other lineages retain old records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import core_v2_admission as admission
import core_v2_runner as runner
from core_v2_preflight import SYNTHETIC_PROMPT

VERSION = "2.0.4"
POLICY = "restore-standard-after-priority-eligibility-review-v1"


def block_prior_google_attempts(data_root: Path, site_id: str, wave_id: str) -> None:
    for version in ("2.0", "2.0.1", "2.0.2", "2.0.3"):
        root = data_root / ("v" + version) / site_id / wave_id
        if (root / "metadata/first-dispatch-MIBO-SL-003.json").exists():
            raise ValueError("prior Google dispatch exists; no Standard restoration queue replay")
        for folder in ("api_raw", "failures"):
            for path in (root / folder).glob("*.json"):
                value = json.loads(path.read_text())
                if not value.get("service_lineage_id"):
                    raise ValueError("prior attempt cannot be classified by lineage")
                if value["service_lineage_id"] == admission.GOOGLE_SCOPE[0]:
                    raise ValueError("prior Google confirmatory attempts exist; no Standard restoration queue replay")


def validate_report(path: Path, *, protocol: dict, protocol_sha: str,
                    freeze: dict, freeze_sha: str, admitted: list[str]) -> dict:
    if admitted != admission.GOOGLE_SCOPE:
        raise ValueError("Standard restoration version authorizes only Google")
    report = json.loads(path.read_text())
    expected = {"protocol_version": VERSION,
        "protocol_registration_id": protocol["protocol_registration_id"],
        "protocol_file_sha256": protocol_sha, "provider_freeze_sha256": freeze_sha,
        "wave_id": freeze["wave_id"], "site_id": freeze["site_id"],
        "readiness_scope": "admitted_lineages_only", "admitted_lineages": admitted,
        "synthetic_smoke_requested": True, "pass": True,
        "gemini_standard_policy": POLICY, "new_standard_readiness_confirmed": True,
        "human_google_admission_required": True}
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError("Standard restoration readiness identity/gate mismatch: " + key)
    if report.get("google_recovery_probe_number") not in {1, 2, 3}:
        raise ValueError("Standard restoration probe number is out of bounds")
    original = admission.checked(Path(report["prior_report_file"]), report["prior_report_sha256"])
    original_freeze = admission.checked(Path(report["prior_freeze_file"]), report["prior_freeze_sha256"])
    if (original.get("pass") is not False
            or original.get("provider_freeze_sha256") != report["prior_freeze_sha256"]):
        raise ValueError("original readiness/freeze identity mismatch")
    checks = report.get("synthetic_smoke_checks", [])
    if len(checks) != 4 or {c.get("service_lineage_id") for c in checks} != set(freeze["core_api"]):
        raise ValueError("Standard restoration readiness must disclose all four intended lineages")
    metadata = original.get("model_checks", [])
    if (len(metadata) != 4 or {c.get("service_lineage_id") for c in metadata} != set(freeze["core_api"])
            or not all(c.get("exact_metadata_verified") is True for c in metadata)):
        raise ValueError("prior model metadata is incomplete")
    for sid, new_cfg in freeze["core_api"].items():
        old_cfg = original_freeze["core_api"][sid]
        expected_profile = dict(old_cfg["request_profile"])
        if new_cfg["model_id"] != old_cfg["model_id"] or new_cfg["request_profile"] != expected_profile:
            raise ValueError("Standard restoration amendment changed another model/profile setting")
        check = next(c for c in checks if c["service_lineage_id"] == sid)
        if check.get("pass") is not True or check.get("model_id") != new_cfg["model_id"]:
            raise ValueError("Standard restoration report requires passing named readiness evidence")
        evidence = admission.checked(Path(check["file"]), check["sha256"])
        if (evidence.get("readiness_only") is not True or evidence.get("pass") is not True
                or evidence.get("requested_model") != new_cfg["model_id"]
                or evidence.get("returned_model") != new_cfg["model_id"]
                or evidence.get("synthetic_prompt_sha256") != hashlib.sha256(SYNTHETIC_PROMPT.encode()).hexdigest()
                or not 200 <= evidence.get("http_status", 0) < 300):
            raise ValueError("Standard restoration/reused smoke evidence mismatch")
        if runner.parse_aware_utc(report["checked_at_utc"]) < runner.parse_aware_utc(evidence["completed_at_utc"]):
            raise ValueError("Standard restoration readiness cannot predate its evidence")
        if sid == admission.GOOGLE_SCOPE[0]:
            if "service_tier" in evidence.get("request_payload", {}):
                raise ValueError("Standard restoration readiness cannot reuse a Priority request")
            if (evidence.get("response_metadata") or {}).get("service_tier_actual") == "priority":
                raise ValueError("unexpected Priority processing under Standard restoration")
            if runner.parse_aware_utc(evidence["started_at_utc"]) < runner.parse_aware_utc(freeze["frozen_at_utc"]):
                raise ValueError("Standard restoration requires new evidence after the new freeze")
            model = (evidence.get("response") or {}).get("modelVersion")
            if model is not None and (not isinstance(model, str) or
                    not model_matches(model, new_cfg["model_id"])):
                raise ValueError("Standard restoration returned model mismatch")
            payload = evidence.get("request_payload", {})
            expected_generation = {dst: expected_profile[src] for src, dst in
                (("max_output_tokens", "maxOutputTokens"), ("temperature", "temperature"), ("top_p", "topP"))
                if expected_profile.get(src) is not None}
            if payload != {"contents": [{"role": "user", "parts": [{"text": SYNTHETIC_PROMPT}]}],
                           "generationConfig": expected_generation}:
                raise ValueError("Standard readiness wire profile/prompt mismatch")
        else:
            old = next(c for c in original["synthetic_smoke_checks"] if c["service_lineage_id"] == sid)
            if {k: v for k, v in check.items() if k != "file"} != {k: v for k, v in old.items() if k != "file"}:
                raise ValueError("other lineage readiness evidence changed")
            expected_path = (Path(report["prior_report_file"]).parent / old["file"]).resolve()
            if Path(check["file"]).resolve() != expected_path:
                raise ValueError("reused evidence path changed")
    history = admission.checked(Path(report["prior_readiness_history_file"]), report["prior_readiness_history_sha256"])
    for entry in history["files"]:
        admission.checked(Path(entry["file"]), entry["sha256"])
    return report


def model_matches(version: str, model_id: str) -> bool:
    if not isinstance(version, str):
        return False
    normalized = version.removeprefix("models/")
    return normalized == model_id or normalized.startswith(model_id + "-")
