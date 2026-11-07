"""Synthetic baseline and qualification-control checks; no real answers or API."""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v2_runner as runner
import core_v21_analysis as analysis
import core_v21_scoring as scoring
from test_core_v21_three_series import ThreeSeriesFixture


def code(value=1, state="CODED", evidence=None):
    return {"state": state, "value": value, "evidence": [] if evidence is None else evidence}


BINARY = {"x": {"kind": "binary", "method": "A", "role": "text"}}
EXTERNAL = {"h": {"kind": "ordinal", "maximum": 2, "method": "H", "role": "external_hold"}}


def metric_evidence(metric="macro_f1", value=.8):
    return {"variable_id": "SYNTHETIC-variable", "judge_family": "anthropic", "source_families": ["openai", "gemini"],
        "judge_freeze_sha256": "e" * 64, "prompt_and_schema_sha256": "f" * 64,
        "stratified_diagnostics_record_sha256": "0" * 64,
        "operational_gate_passed": True, "reference_status": "independently_verified",
        "reference_is_AI_consensus": False, "validation_set_locked": True,
        "development_validation_disjoint": True, "validation_total_responses": 240,
        "validation_partition_status": "PARTITION_SHAPE_AND_DISJOINTNESS_PASS",
        "reference_sha256": "a" * 64, "validation_set_sha256": "b" * 64,
        "metric_computation_record_sha256": "c" * 64, "validation_partition_record_sha256": "d" * 64,
        "metric": metric, "value": value, "n_compared": 20}


class BaselinePolicyTests(unittest.TestCase):
    def test_baseline_is_W03_STD_and_requires_eight_valid_responses(self):
        for n in range(11):
            result = analysis.baseline_cell(wave_id="MIBO2-W03", window_id="STD", valid_n=n)
            self.assertEqual(result["eligible"], n >= 8)
            self.assertFalse(result["automatic_substitution"])
            self.assertFalse(result["AI_qualification_required"])

    def test_later_wave_or_W02_cannot_replace_missing_baseline(self):
        for wave in ("MIBO2-W02", "MIBO2-W04", "MIBO2-W05"):
            result = analysis.baseline_cell(wave_id=wave, window_id="STD", valid_n=10)
            self.assertFalse(result["eligible"])
            self.assertEqual(result["baseline_wave"], "MIBO2-W03")

    def test_calibration_windows_are_separate_even_when_they_have_ten(self):
        for window in ("WA", "WB"):
            result = analysis.baseline_cell(wave_id="MIBO2-W04", window_id=window, valid_n=10)
            self.assertEqual(result["status"], "SEPARATE_CALIBRATION_NOT_STD_BASELINE")
            self.assertFalse(result["eligible"])

    def test_primary_comparison_cannot_bridge_W02_or_calibration(self):
        self.assertFalse(analysis.primary_comparison_gate(baseline_wave="MIBO2-W02",
            target_wave="MIBO2-W03", baseline_window="STD", target_window="STD", baseline_valid_n=10)["baseline_gate_pass"])
        self.assertFalse(analysis.primary_comparison_gate(baseline_wave="MIBO2-W03",
            target_wave="MIBO2-W04", baseline_window="STD", target_window="WA", baseline_valid_n=10)["baseline_gate_pass"])
        self.assertFalse(analysis.primary_comparison_gate(baseline_wave="MIBO2-W03",
            target_wave="MIBO2-W02", baseline_window="STD", target_window="STD", baseline_valid_n=10)["baseline_gate_pass"])
        result = analysis.primary_comparison_gate(baseline_wave="MIBO2-W03",
            target_wave="MIBO2-W05", baseline_window="STD", target_window="STD", baseline_valid_n=8)
        self.assertTrue(result["baseline_gate_pass"])
        self.assertFalse(result["statistical_contrast_computed"])

    def test_baseline_cannot_count_retries_bool_or_imputed_slots(self):
        for n in (-1, 11, True, 8.0):
            with self.subTest(n=n), self.assertRaises(ValueError):
                analysis.baseline_cell(wave_id="MIBO2-W03", window_id="STD", valid_n=n)

    def test_policy_cannot_enable_fallback_or_change_existing_threshold(self):
        for change in ({"automatic_baseline_substitution": True}, {"minimum_valid_n": 7},
                       {"W02_primary_comparison": True}, {"baseline_wave": "MIBO2-W04"}):
            data = {**analysis.load_policy(), **change}
            with self.subTest(change=change), self.assertRaises(ValueError): analysis.validate_policy(data)

    def test_source_collection_policy_does_not_require_completed_AI_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = ThreeSeriesFixture(Path(temp))
            protocol, _ = runner.load_protocol(fixture.protocol)
            self.assertFalse(protocol["ai_scoring_qualification_plan"]["empirical_qualification_complete"])
            self.assertEqual(len(fixture.rows), 720)

    def test_policy_hash_drift_or_unreferenced_confirmatory_promotion_is_rejected(self):
        for kind in ("hash", "scope"):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "protocol.json"
                data = json.loads((Path(runner.__file__).parent / "config/core_v21_protocol.draft.json").read_text())
                if kind == "hash": data["analysis_policy_sha256"] = "0" * 64
                else: data["ai_scoring_qualification_plan"]["unreferenced_AI_use_scope"] = "confirmatory_primary"
                path.write_text(json.dumps(data))
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    runner.load_protocol(path, require_final=False)


class OperationalScoringTests(unittest.TestCase):
    def test_all_three_rotating_nonself_pairs_are_operationally_admissible(self):
        for family in scoring.FAMILIES:
            ratings = [{"judge_family": j, "codes": {"x": code()}} for j in sorted(scoring.FAMILIES - {family})]
            result = scoring.aggregate_pair(source_family=family, ratings=ratings, variables=BINARY)
            self.assertEqual(result["status"], "EXACT_CONSENSUS_NOT_VALIDATION")
            self.assertFalse(result["human_validity_established"])
            self.assertEqual(result["use_scope"], "auxiliary_exploratory_only")

    def test_self_unknown_or_repeated_judge_family_never_passes(self):
        for judges in (("openai", "anthropic"), ("anthropic", "anthropic"), ("unknown", "gemini"), ({}, "gemini")):
            ratings = [{"judge_family": j, "codes": {"x": code()}} for j in judges]
            self.assertEqual(scoring.aggregate_pair(source_family="openai", ratings=ratings,
                variables=BINARY)["status"], "HOLD_OPERATIONAL_GATE")

    def test_schema_and_domain_violations_are_rejected_not_corrected(self):
        for bad in ({}, {"x": code(2)}, {"x": code(True)}, {"x": code("1")},
                    {"x": code(0, "CANNOT_DETERMINE")}, {"x": {"value": 1}},
                    {"x": code(1), "extra": code()}, {"x": code(1, state=[])}):
            result = scoring.screen_codes(source_family="openai", judge_family="anthropic", codes=bad, variables=BINARY)
            self.assertFalse(result["operationally_admissible"])

    def test_H_consensus_cannot_become_factual_citation_or_human_verification(self):
        for value in (0, 2):
            ratings = [{"judge_family": j, "codes": {"h": code(value)}} for j in ("anthropic", "gemini")]
            self.assertEqual(scoring.aggregate_pair(source_family="openai", ratings=ratings,
                variables=EXTERNAL)["status"], "HOLD_OPERATIONAL_GATE")
        ratings = [{"judge_family": j, "codes": {"h": code(None, "HOLD_EXTERNAL_VERIFICATION")}}
                   for j in ("anthropic", "gemini")]
        result = scoring.aggregate_pair(source_family="openai", ratings=ratings, variables=EXTERNAL)
        self.assertIsNone(result["consensus"]["h"]["value"])
        self.assertFalse(result["H_verified"])

    def test_disagreement_is_held_without_numeric_averaging(self):
        ratings = [{"judge_family": "anthropic", "codes": {"x": code(0)}},
                   {"judge_family": "gemini", "codes": {"x": code(1)}}]
        result = scoring.aggregate_pair(source_family="openai", ratings=ratings, variables=BINARY)
        self.assertEqual(result["consensus"]["x"], {"state": "CONFLICT_HOLD", "value": None})
        self.assertEqual(result["individual_ratings"], ratings)

    def test_matching_null_states_not_zero_and_different_null_states_conflict(self):
        ratings = [{"judge_family": j, "codes": {"x": code(None, "CANNOT_DETERMINE")}}
                   for j in ("anthropic", "gemini")]
        result = scoring.aggregate_pair(source_family="openai", ratings=ratings, variables=BINARY)
        self.assertEqual(result["consensus"]["x"]["state"], "CANNOT_DETERMINE")
        self.assertIsNone(result["consensus"]["x"]["value"])
        ratings[1]["codes"]["x"]["state"] = "NOT_APPLICABLE"
        self.assertEqual(scoring.aggregate_pair(source_family="openai", ratings=ratings,
            variables=BINARY)["consensus"]["x"]["state"], "CONFLICT_HOLD")

    def test_set_order_and_distinct_evidence_quotes_do_not_force_disagreement(self):
        spec = {"x": {"kind": "set", "values": ["a", "b"], "method": "A"}}
        ratings = [{"judge_family": "anthropic", "codes": {"x": code(["a", "b"], evidence=["synthetic a"])}},
                   {"judge_family": "gemini", "codes": {"x": code(["b", "a"], evidence=["synthetic b"])}}]
        result = scoring.aggregate_pair(source_family="openai", ratings=ratings, variables=spec)
        self.assertEqual(result["consensus"]["x"]["value"], ["a", "b"])

    def test_legacy_eight_nine_count_values_remain_numeric_not_missing_codes(self):
        spec = {"x": {"kind": "count", "maximum": 9, "method": "A"}}
        for value in (8, 9):
            self.assertTrue(scoring.screen_codes(source_family="openai", judge_family="anthropic",
                codes={"x": code(value)}, variables=spec)["operationally_admissible"])

    def test_empty_rubric_never_vacuously_qualifies(self):
        self.assertFalse(scoring.screen_codes(source_family="openai", judge_family="anthropic",
            codes={}, variables={})["operationally_admissible"])


class ReferenceQualificationTests(unittest.TestCase):
    def decide(self, evidence, kind="binary_nominal", method="A"):
        return scoring.qualification_decision(variable_type=kind, method=method, evidence=evidence)

    def test_original_metric_cutoffs_are_variable_specific_boundary_inclusive(self):
        for kind, (metric, threshold) in scoring.BENCHMARKS.items():
            for value, expected in ((threshold, True), (threshold - .001, False), (1.0, True)):
                result = self.decide(metric_evidence(metric, value), kind)
                self.assertEqual(result["reference_benchmark_met_on_declared_evidence"], expected)
                self.assertFalse(result["independent_reference_audited_here"])
                self.assertFalse(result["global_model_qualified"])
                self.assertFalse(result["human_validity_established"])

    def test_perfect_AI_consensus_is_not_independent_reference(self):
        data = metric_evidence(value=1.0); data["reference_is_AI_consensus"] = True
        self.assertEqual(self.decide(data)["status"], "HOLD_INDEPENDENT_REFERENCE_OR_PROVENANCE")
        data["reference_status"] = "AI_consensus"
        self.assertFalse(self.decide(data)["reference_benchmark_met_on_declared_evidence"])

    def test_missing_unlocked_overlapping_or_undersized_reference_never_passes(self):
        for key, value in (("reference_sha256", None), ("validation_set_locked", False),
                           ("development_validation_disjoint", False), ("validation_total_responses", 239),
                           ("metric_computation_record_sha256", "not-a-digest")):
            data = metric_evidence(value=1); data[key] = value
            with self.subTest(key=key): self.assertFalse(self.decide(data)["reference_benchmark_met_on_declared_evidence"])

    def test_undefined_nonfinite_and_no_comparable_labels_are_held_not_zero_filled(self):
        for value in (None, math.nan, math.inf, True, "0.9"):
            self.assertEqual(self.decide(metric_evidence(value=value))["status"], "HOLD_UNDEFINED_OR_INVALID_METRIC")
        data = metric_evidence(); data["n_compared"] = 0
        self.assertEqual(self.decide(data)["status"], "HOLD_UNDEFINED_OR_INVALID_METRIC")

    def test_malformed_metric_evidence_is_held_not_treated_as_a_model_pass(self):
        for evidence in (None, [], "invalid"):
            self.assertEqual(self.decide(evidence)["status"], "HOLD_MALFORMED_EVIDENCE")

    def test_weighted_kappa_does_not_replace_ordinal_alpha(self):
        self.assertEqual(self.decide(metric_evidence("weighted_kappa", 1), "ordinal")["status"],
            "HOLD_WRONG_METRIC_NO_KAPPA_SUBSTITUTION")

    def test_unbound_global_metric_or_self_family_cannot_qualify_a_variable(self):
        for change in ({"variable_id": None}, {"source_families": ["anthropic"]},
                       {"judge_freeze_sha256": None}):
            data = {**metric_evidence(value=1), **change}
            self.assertFalse(self.decide(data)["reference_benchmark_met_on_declared_evidence"])

    def test_H_and_unsupported_variable_metrics_do_not_automatically_pass(self):
        self.assertEqual(self.decide(metric_evidence(value=1), method="H/A")["status"], "HOLD_EXTERNAL_VERIFICATION")
        self.assertEqual(self.decide(metric_evidence(value=1), kind="set")["status"], "HOLD_METRIC_NOT_PROSPECTIVELY_SPECIFIED")

    def test_operational_failure_is_not_rescued_by_high_metric(self):
        data = metric_evidence(value=1); data["operational_gate_passed"] = False
        self.assertEqual(self.decide(data)["status"], "HOLD_OPERATIONAL_GATE")

    def test_unperformed_real_calibration_and_validation_are_not_promoted(self):
        plan = scoring.load_policy()
        self.assertFalse(plan["actual_calibration_complete"])
        self.assertFalse(plan["actual_validation_complete"])
        self.assertFalse(plan["scoring_API_authorized"])

    def test_development_and_reserved_validation_remain_disjoint_with_80_per_family(self):
        root = Path(runner.__file__).parents[1]
        plan = json.loads((root / "docs/v2.1/scoring/validation-allocation-240-draft.json").read_text())
        self.assertEqual(scoring.validation_partition(["dev-001"], plan["rows"])["status"], "HOLD_UNSAMPLED")
        rows = copy.deepcopy(plan["rows"])
        for i, row in enumerate(rows):
            row.update(actual_observation_id=f"SYNTHETIC-ONLY-{i:03d}", raw_response_sha256="a" * 64)
        development = [f"SYNTHETIC-DEV-{i:03d}" for i in range(72)]
        result = scoring.validation_partition(development, rows)
        self.assertEqual(result["status"], "PARTITION_SHAPE_AND_DISJOINTNESS_PASS")
        self.assertFalse(result["qualified"])
        overlapping = [rows[0]["actual_observation_id"], *development[1:]]
        self.assertEqual(scoring.validation_partition(overlapping, rows)["status"], "HOLD_SAMPLE_OR_OVERLAP")
        self.assertEqual(scoring.validation_partition(development, rows[:-1])["status"], "HOLD_SAMPLE_OR_OVERLAP")
        self.assertEqual(scoring.validation_partition([], rows)["status"], "HOLD_DEVELOPMENT_SET_NOT_BOUND")

    def test_malformed_validation_sample_is_held(self):
        for rows in (None, ["invalid"]):
            self.assertEqual(scoring.validation_partition([], rows)["status"], "HOLD_INVALID_VALIDATION_SCOPE")


if __name__ == "__main__":
    unittest.main()
