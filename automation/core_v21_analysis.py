"""Fixed W03 baseline decisions, not an estimator, observer or API client."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

POLICY_ID = "MIBO-CORE-v21-W03-BASELINE-v1.0"
POLICY_FILE = "core_v21_analysis_policy.json"
ROOT = Path(__file__).parent / "config"


def validate_policy(data: dict) -> None:
    expected = {"policy_id": POLICY_ID, "protocol_version": "2.1", "baseline_wave": "MIBO2-W03",
        "baseline_window": "STD", "minimum_valid_n": 8, "intended_n_per_cell": 10,
        "automatic_baseline_substitution": False, "W02_primary_comparison": False,
        "W02_historical_records_preserved": True,
        "future_common_three_W02_exploration_requires_separate_prospective_plan": True,
        "first_calibration_wave": "MIBO2-W04", "calibration_windows": ["WA", "WB"],
        "calibration_separate_from_STD_baseline": True,
        "primary_URL_analysis_requires_AI_qualification": False,
        "actual_registration_or_execution_permission": False}
    for key, value in expected.items():
        if data.get(key) != value or (isinstance(value, bool) and data.get(key) is not value):
            raise ValueError("approved baseline policy mismatch: " + key)


def load_policy(path: Path | None = None) -> dict:
    result = json.loads((path or ROOT / POLICY_FILE).read_text(encoding="utf-8"))
    validate_policy(result)
    return result


def policy_digest() -> str:
    return hashlib.sha256((ROOT / POLICY_FILE).read_bytes()).hexdigest()


def baseline_cell(*, wave_id: str, window_id: str, valid_n: int, policy: dict | None = None) -> dict:
    policy = policy if policy is not None else load_policy()
    validate_policy(policy)
    if type(valid_n) is not int or valid_n not in range(0, 11):
        raise ValueError("baseline count must be a valid logical-cell count, not attempts or imputation")
    if window_id in policy["calibration_windows"]:
        status = "SEPARATE_CALIBRATION_NOT_STD_BASELINE"
    elif wave_id != policy["baseline_wave"] or window_id != policy["baseline_window"]:
        status = "NOT_REGISTERED_BASELINE_NO_AUTOMATIC_SUBSTITUTION"
    elif valid_n < policy["minimum_valid_n"]:
        status = "INSUFFICIENT_W03_BASELINE_CELL"
    else:
        status = "ELIGIBLE_W03_BASELINE_CELL"
    return {"baseline_wave": policy["baseline_wave"], "baseline_window": policy["baseline_window"],
        "valid_n": valid_n, "status": status, "eligible": status == "ELIGIBLE_W03_BASELINE_CELL",
        "automatic_substitution": False, "AI_qualification_required": False}


def primary_comparison_gate(*, baseline_wave: str, target_wave: str, baseline_window: str,
                            target_window: str, baseline_valid_n: int) -> dict:
    cell = baseline_cell(wave_id=baseline_wave, window_id=baseline_window, valid_n=baseline_valid_n)
    if "MIBO2-W02" in {baseline_wave, target_wave}:
        reason = "W02_EXCLUDED_FROM_V21_PRIMARY_COMPARISON"
    elif target_wave not in {f"MIBO2-W{i:02d}" for i in range(4, 13)}:
        reason = "TARGET_MUST_BE_A_REGISTERED_POST_BASELINE_WAVE"
    elif not cell["eligible"]:
        reason = cell["status"]
    elif target_window != "STD":
        reason = "CALIBRATION_WINDOWS_REQUIRE_SEPARATE_ANALYSIS"
    else:
        reason = "BASELINE_GATE_ONLY_OTHER_COMPARABILITY_CHECKS_STILL_REQUIRED"
    return {"baseline_gate_pass": reason.startswith("BASELINE_GATE_ONLY"), "reason": reason,
        "statistical_contrast_computed": False, "automatic_cross_version_pooling": False}
