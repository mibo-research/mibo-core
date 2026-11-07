"""Synthetic-only W03 three-series derivative checks; no real responses."""
import copy
import hashlib
import itertools
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import url_set_variation as original
import url_set_variation_v11 as amendment


def dataset(valid_n=10):
    forms = amendment.frozen_query_hashes()
    rows = []
    for lineage, language, rep in itertools.product(amendment.policy.LINEAGES, ("EN", "JA"), range(1, 11)):
        valid = rep <= valid_n
        rows.append({"protocol_version": "2.1", "wave_id": "MIBO2-W03", "site_id": "JP01",
            "service_lineage_id": lineage, "item_id": "MIBO-I03", "language": language,
            "condition": "ACI", "window_id": "STD", "replication": rep, "model_id": "synthetic-" + lineage,
            "query_sha256": forms[language], "request_profile_sha256": "a" * 64,
            "technical_status": "valid" if valid else "technical_missing",
            "text": "https://example.invalid/synthetic" if valid else None,
            "citations": [] if valid else None,
            "raw_capture_sha256": hashlib.sha256(("SYNTHETIC|" + lineage + language + str(rep)).encode()).hexdigest() if valid else None})
    return {"schema": amendment.SCHEMA, "rows": rows,
        "provenance": {k: "b" * 64 for k in amendment.AUDIT_FIELDS}}


class W03ThreeSeriesURLTests(unittest.TestCase):
    def test_sixty_slots_six_cells_and_no_cross_version_contrast(self):
        result = amendment.analyze_w03(dataset())
        self.assertEqual(result["intended_I03_slots"], 60)
        self.assertEqual(len(result["cells"]), 6)
        self.assertTrue(all(c["planned_n"] == c["valid_n"] == 10 for c in result["cells"]))
        self.assertTrue(all(c["exact_url_jaccard"]["all_pair_count"] == 45 for c in result["cells"]))
        self.assertTrue(all(c["exact_url_jaccard"]["mean"] == 1 for c in result["cells"]))
        self.assertEqual(result["contrasts"], [])
        self.assertEqual(result["baseline_wave"], "MIBO2-W03")
        self.assertFalse(result["automatic_baseline_substitution"])
        self.assertFalse(result["AI_qualification_required_for_URL_analysis"])
        self.assertFalse(result["restricted_raw_archive_independently_verified_here"])

    def test_immutable_four_series_validator_and_source_are_not_rewritten(self):
        self.assertEqual(len(original.LINEAGES), 4)
        self.assertEqual(hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(), amendment.LEGACY_SOURCE_SHA256)
        with self.assertRaisesRegex(ValueError, "80 planned"):
            original.validate_rows(dataset()["rows"], "MIBO2-W03")

    def test_perplexity_and_old_eighty_slot_inputs_are_not_filtered(self):
        for kind in ("replace", "append"):
            data = dataset()
            fourth = copy.deepcopy(data["rows"][0]); fourth["service_lineage_id"] = "MIBO-SL-004"
            if kind == "replace": data["rows"][0] = fourth
            else: data["rows"].extend([fourth] * 20)
            with self.subTest(kind=kind), self.assertRaises(ValueError): amendment.analyze_w03(data)

    def test_missing_slots_and_duplicate_retry_do_not_change_n(self):
        for kind in ("missing", "duplicate"):
            data = dataset()
            if kind == "missing": data["rows"].pop()
            else: data["rows"].append(copy.deepcopy(data["rows"][0]))
            with self.subTest(kind=kind), self.assertRaises(ValueError): amendment.analyze_w03(data)

    def test_technical_missingness_retained_and_minimum_n_not_imputed(self):
        for n in (0, 7, 8, 9):
            result = amendment.analyze_w03(dataset(n))
            for cell in result["cells"]:
                self.assertEqual(cell["planned_n"], 10)
                self.assertEqual(cell["valid_n"], n)
                self.assertEqual(cell["technical_missing_n"], 10 - n)
                self.assertEqual(cell["minimum_n8_rule_satisfied"], n >= 8)
                if n == 0: self.assertIsNone(cell["exact_url_jaccard"]["mean"])

    def test_valid_refusals_are_url_free_not_technical_failures(self):
        data = dataset()
        for row in data["rows"]: row["text"] = "Synthetic valid refusal."
        result = amendment.analyze_w03(data)
        self.assertTrue(all(c["valid_n"] == c["url_free_n"] == 10 for c in result["cells"]))
        self.assertTrue(all(c["exact_url_jaccard"]["mean"] is None for c in result["cells"]))
        self.assertTrue(all(c["baseline_cell"]["eligible"] for c in result["cells"]))
        self.assertTrue(all(not c["URL_baseline_eligible"] for c in result["cells"]))
        self.assertTrue(all(not c["undefined_URL_baseline_may_be_substituted"] for c in result["cells"]))

    def test_changed_query_protocol_wave_or_profile_pool_rejected(self):
        for field, value in (("query_sha256", "f" * 64), ("protocol_version", "2.0.1"),
                             ("wave_id", "MIBO2-W02"), ("model_id", "other-synthetic"),
                             ("request_profile_sha256", "c" * 64), ("replication", True)):
            data = dataset(); data["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): amendment.analyze_w03(data)

    def test_input_audit_hashes_and_capture_provenance_are_required(self):
        for kind in ("audit", "capture", "fabricated_missing"):
            data = dataset()
            if kind == "audit": data["provenance"].pop(amendment.AUDIT_FIELDS[0])
            if kind == "capture": data["rows"][0]["raw_capture_sha256"] = None
            if kind == "fabricated_missing": data["rows"][0]["technical_status"] = "technical_missing"
            with self.subTest(kind=kind), self.assertRaises(ValueError): amendment.analyze_w03(data)

    def test_baseline_payload_cannot_silently_enable_W02_comparison(self):
        data = dataset(); data["baseline"] = {"rows": []}
        with self.assertRaisesRegex(ValueError, "cross-version comparison"): amendment.analyze_w03(data)

    def test_old_cross_wave_function_never_called_by_new_path(self):
        with mock.patch.object(original, "analyze", side_effect=AssertionError("old four-series path forbidden")), \
                mock.patch.object(original, "leave_one_out_contrast", side_effect=AssertionError("contrast held")):
            self.assertEqual(amendment.analyze_w03(dataset())["contrasts"], [])

    def test_exact_extraction_and_empty_pair_rules_are_inherited(self):
        self.assertEqual(original.extract_urls("https://E.test/x?a=1 https://e.test/x?a=2", []),
            ["https://E.test/x?a=1", "https://e.test/x?a=2"])
        self.assertIsNone(original.pair_jaccard(set(), set()))
        self.assertEqual(original.pair_jaccard(set(), {"a"}), 0)


if __name__ == "__main__":
    unittest.main()
