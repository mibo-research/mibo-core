"""Offline rating admission/qualification decisions; no model transport or gold fabrication.

Validation metrics are supplied by a separately audited metric computation.
This module checks declared evidence and thresholds; it does not independently
verify a reference's truth, calculate empirical metrics or certify a model.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

POLICY_ID = "MIBO-CORE-v21-SCORING-QUALIFICATION-v1.0"
POLICY_FILE = "core_v21_scoring_qualification.json"
ROOT = Path(__file__).parent / "config"
FAMILIES = {"openai", "anthropic", "gemini"}
STATES = {"CODED", "NOT_APPLICABLE", "CANNOT_DETERMINE", "HOLD_EXTERNAL_VERIFICATION"}
BENCHMARKS = {"binary_nominal": ("macro_f1", .80), "ordinal": ("ordinal_krippendorff_alpha", .80),
              "deterministic_extraction": ("exact_match_rate", .95)}


def validate_policy(data: dict) -> None:
    expected = {"policy_id": POLICY_ID, "operational_qualification_is_not_validity": True,
        "families": ["openai", "anthropic", "gemini"], "self_family_judging": False,
        "aggregation": "exact-variable-consensus-only-no-averaging-or-fallback",
        "malformed_or_out_of_domain_rating_admitted": False, "H_values_finalized_by_AI_consensus": False,
        "development_cases": 72, "minimum_validation_responses": 240, "basic_validation_per_family": 80,
        "development_validation_overlap": False, "independent_reference_required": True,
        "AI_consensus_may_replace_independent_reference": False, "undefined_metric_may_pass": False,
        "unreferenced_AI_use_scope": "auxiliary_exploratory_only",
        "H_variable_policy": "external-evidence-human-verification-held-until-qualified",
        "per_variable_reference_benchmark_not_global_model_certification": True,
        "primary_URL_analysis_blocked_by_AI_qualification": False, "second_human_recruitment_required": False,
        "scoring_API_authorized": False}
    for key, value in expected.items():
        if data.get(key) != value or (isinstance(value, bool) and data.get(key) is not value):
            raise ValueError("approved scoring qualification policy mismatch: " + key)
    if data.get("reference_benchmarks") != {k: {"metric": v[0], "threshold": v[1]} for k, v in BENCHMARKS.items()}:
        raise ValueError("registered reference benchmarks must not be replaced by AI agreement or kappa")


def load_policy(path: Path | None = None) -> dict:
    result = json.loads((path or ROOT / POLICY_FILE).read_text(encoding="utf-8"))
    validate_policy(result)
    return result


def _external(spec: dict) -> bool:
    return "H" in spec.get("method", "") or spec.get("role") == "external_hold"


def _value_in_domain(value, spec: dict) -> bool:
    kind = spec.get("kind")
    if kind == "binary": return type(value) is int and value in (0, 1)
    if kind in {"ordinal", "count"}:
        return type(value) is int and spec.get("minimum", 0) <= value <= spec["maximum"]
    if kind == "category": return isinstance(value, str) and value in spec["values"]
    if kind == "set":
        return (isinstance(value, list) and all(isinstance(v, str) for v in value)
            and len(value) == len(set(value)) and set(value) <= set(spec["values"]))
    if kind in {"continuous", "proportion"}:
        return (type(value) in (int, float) and math.isfinite(value)
            and spec.get("minimum", 0) <= value <= spec.get("maximum", 1))
    return False


def screen_codes(*, source_family: str, judge_family: str, codes, variables: dict) -> dict:
    """Validate the code-map only; callers separately bind response/model/prompt IDs."""
    errors = []
    if not isinstance(variables, dict) or not variables:
        return {"operationally_admissible": False, "errors": ["FROZEN_VARIABLE_SPEC_REQUIRED"],
            "semantic_correctness_verified": False, "human_validity_established": False}
    if (not isinstance(source_family, str) or not isinstance(judge_family, str)
            or source_family not in FAMILIES or judge_family not in FAMILIES or source_family == judge_family):
        errors.append("UNKNOWN_OR_SELF_FAMILY_JUDGE")
    if not isinstance(codes, dict) or set(codes) != set(variables):
        errors.append("APPLICABLE_VARIABLE_SCHEMA_MISMATCH")
    else:
        for name, spec in variables.items():
            code = codes[name]
            if (not isinstance(code, dict) or set(code) != {"state", "value", "evidence"}
                    or not isinstance(code.get("state"), str) or code["state"] not in STATES
                    or not isinstance(code.get("evidence"), list)
                    or any(not isinstance(q, str) for q in code.get("evidence", []))):
                errors.append(name + ":INVALID_CODE_SCHEMA")
                continue
            state, value = code["state"], code["value"]
            if _external(spec):
                if state != "HOLD_EXTERNAL_VERIFICATION" or value is not None or code["evidence"]:
                    errors.append(name + ":H_EXTERNAL_VALUE_MUST_REMAIN_HELD")
            elif state == "CODED":
                if not _value_in_domain(value, spec): errors.append(name + ":OUT_OF_DOMAIN")
            elif value is not None:
                errors.append(name + ":NON_CODED_STATE_REQUIRES_NULL")
    return {"operationally_admissible": not errors, "errors": errors,
        "semantic_correctness_verified": False, "human_validity_established": False}


def aggregate_pair(*, source_family: str, ratings: list[dict], variables: dict) -> dict:
    result = {"status": "HOLD_OPERATIONAL_GATE", "consensus": {}, "conflicts": [],
        "individual_ratings": copy.deepcopy(ratings), "use_scope": "auxiliary_exploratory_only",
        "H_verified": False, "human_validity_established": False}
    if (not isinstance(source_family, str) or source_family not in FAMILIES or not isinstance(ratings, list) or len(ratings) != 2
            or any(not isinstance(r, dict) for r in ratings)
            or any(not isinstance(r.get("judge_family"), str) for r in ratings)
            or {r.get("judge_family") for r in ratings} != FAMILIES - {source_family}):
        result["reason"] = "REQUIRES_EXACT_TWO_OTHER_PROVIDER_FAMILIES"
        return result
    checks = [screen_codes(source_family=source_family, judge_family=r["judge_family"],
        codes=r.get("codes"), variables=variables) for r in ratings]
    result["operational_checks"] = checks
    if not all(c["operationally_admissible"] for c in checks): return result
    for name, spec in variables.items():
        first, second = (r["codes"][name] for r in ratings)
        left, right = first["value"], second["value"]
        if spec["kind"] == "set" and first["state"] == second["state"] == "CODED":
            left, right = sorted(left), sorted(right)
        if first["state"] == second["state"] and left == right:
            result["consensus"][name] = {"state": first["state"], "value": copy.deepcopy(left)}
        else:
            result["consensus"][name] = {"state": "CONFLICT_HOLD", "value": None}
            result["conflicts"].append(name)
    result["status"] = "HAS_CONFLICTS_HELD" if result["conflicts"] else "EXACT_CONSENSUS_NOT_VALIDATION"
    return result


def qualification_decision(*, variable_type: str, method: str, evidence: dict,
                           policy: dict | None = None) -> dict:
    """Assess a supplied metric summary against declared, hash-bound evidence only."""
    policy = policy if policy is not None else load_policy()
    validate_policy(policy)
    result = {"status": "HOLD", "reference_benchmark_met_on_declared_evidence": False,
        "use_scope": "auxiliary_exploratory_only", "independent_reference_audited_here": False,
        "global_model_qualified": False, "human_validity_established": False}
    if not isinstance(evidence, dict) or not isinstance(method, str):
        result["status"] = "HOLD_MALFORMED_EVIDENCE"; return result
    if "H" in method:
        result.update(status="HOLD_EXTERNAL_VERIFICATION", use_scope="external_verification_hold")
        return result
    if evidence.get("operational_gate_passed") is not True:
        result["status"] = "HOLD_OPERATIONAL_GATE"; return result
    if (not isinstance(evidence.get("variable_id"), str) or not evidence["variable_id"]
            or not isinstance(evidence.get("judge_family"), str) or evidence["judge_family"] not in FAMILIES
            or not isinstance(evidence.get("source_families"), list) or not evidence["source_families"]
            or any(not isinstance(f, str) or f not in FAMILIES or f == evidence["judge_family"]
                   for f in evidence["source_families"])):
        result["status"] = "HOLD_VARIABLE_OR_NONSELF_JUDGE_BINDING"; return result
    if not isinstance(variable_type, str) or variable_type not in BENCHMARKS:
        result["status"] = "HOLD_METRIC_NOT_PROSPECTIVELY_SPECIFIED"; return result
    if (evidence.get("reference_status") != "independently_verified"
            or evidence.get("reference_is_AI_consensus") is not False
            or evidence.get("validation_set_locked") is not True
            or evidence.get("development_validation_disjoint") is not True
            or evidence.get("validation_partition_status") != "PARTITION_SHAPE_AND_DISJOINTNESS_PASS"
            or type(evidence.get("validation_total_responses")) is not int
            or evidence["validation_total_responses"] < policy["minimum_validation_responses"]
            or any(not isinstance(evidence.get(k), str) or not re.fullmatch(r"[0-9a-f]{64}", evidence[k])
                   for k in ("reference_sha256", "validation_set_sha256", "metric_computation_record_sha256",
                             "validation_partition_record_sha256", "judge_freeze_sha256",
                             "prompt_and_schema_sha256", "stratified_diagnostics_record_sha256"))):
        result["status"] = "HOLD_INDEPENDENT_REFERENCE_OR_PROVENANCE"; return result
    metric, threshold = BENCHMARKS[variable_type]
    if evidence.get("metric") != metric:
        result["status"] = "HOLD_WRONG_METRIC_NO_KAPPA_SUBSTITUTION"; return result
    value, n = evidence.get("value"), evidence.get("n_compared")
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value > 1 or (metric != "ordinal_krippendorff_alpha" and value < 0)
            or type(n) is not int or n <= 0 or n > evidence["validation_total_responses"]):
        result["status"] = "HOLD_UNDEFINED_OR_INVALID_METRIC"; return result
    result.update(variable_id=evidence["variable_id"], judge_family=evidence["judge_family"],
        metric=metric, threshold=threshold, n_compared=n, value=value)
    if value < threshold:
        result["status"] = "BENCHMARK_NOT_MET_NO_SOLE_CONFIRMATORY_CLAIM"
    else:
        result.update(status="DECLARED_REFERENCE_BENCHMARK_MET_PENDING_VARIABLE_REVIEW",
            reference_benchmark_met_on_declared_evidence=True,
            use_scope="eligible_for_variable_specific_confirmation_review_not_global_certification")
    return result


def validation_partition(development_ids: list[str], validation_rows: list[dict]) -> dict:
    """Check reserved-sample shape/disjointness, not reference truth or actual locking."""
    if not isinstance(validation_rows, list) or any(not isinstance(r, dict) for r in validation_rows):
        return {"status": "HOLD_INVALID_VALIDATION_SCOPE", "qualified": False}
    ids = [r.get("actual_observation_id") for r in validation_rows]
    if any(not isinstance(i, str) or not i for i in ids):
        return {"status": "HOLD_UNSAMPLED", "qualified": False}
    if (not isinstance(development_ids, list) or len(development_ids) < 72
            or any(not isinstance(i, str) or not i for i in development_ids)
            or len(set(development_ids)) != len(development_ids)):
        return {"status": "HOLD_DEVELOPMENT_SET_NOT_BOUND", "qualified": False}
    if any(not isinstance(r.get("raw_response_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", r["raw_response_sha256"]) for r in validation_rows):
        return {"status": "HOLD_CAPTURE_PROVENANCE", "qualified": False}
    cells, families = {}, {}
    for row in validation_rows:
        family, qid = row.get("source_family"), row.get("query_form_id")
        if not isinstance(family, str) or family not in FAMILIES or not isinstance(qid, str):
            return {"status": "HOLD_INVALID_VALIDATION_SCOPE", "qualified": False}
        families[family] = families.get(family, 0) + 1
        cells[qid] = cells.get(qid, 0) + 1
    expected = {f"MIBO-I{i:02d}-{lang}" for i in range(1, 13) for lang in ("EN", "JA")}
    valid = (len(ids) >= 240 and len(set(ids)) == len(ids) and not set(ids) & set(development_ids)
        and set(cells) == expected and all(n >= 10 for n in cells.values())
        and set(families) == FAMILIES and all(n >= 80 for n in families.values()))
    return {"status": "PARTITION_SHAPE_AND_DISJOINTNESS_PASS" if valid else "HOLD_SAMPLE_OR_OVERLAP",
        "qualified": False, "content_validity_verified": False, "responses": len(ids)}
