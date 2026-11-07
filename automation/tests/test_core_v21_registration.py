"""Local public DRAFT packaging is deterministic, allowlisted and never live."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_v21_registration as registration

REPO = Path(__file__).resolve().parents[2]


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "public"
        self.root.mkdir()
        required = {"automation/config/core_v21_protocol.draft.json",
            "automation/config/core_v21_source_registry.json", "automation/config/core_v21_provider_freeze.template.json",
            "runtime/mibo-core-v21.env.example", "docs/v2.1/zenodo-metadata.draft.json",
            registration.W03_OWNER_DECISION, registration.W03_DRAFT_DIR + "/analysis-spec.draft.json",
            registration.W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md",
            registration.POLICY_OWNER_DECISION,
            "automation/config/core_v21_analysis_policy.json", "automation/config/core_v21_scoring_qualification.json",
            "docs/analysis/W03-URL-variation-v1.0/REGISTRATION.md", "docs/analysis/W03-URL-variation-v1.0/analysis-spec.json",
            "automation/url_set_variation.py", "automation/url_set_variation_v11.py", "automation/tests/test_url_set_variation_v11.py",
            registration.METADATA_OWNER_DECISION, registration.PARENT_CITATION,
            "CITATION.cff", "LICENSE_NOTICE.md", "LICENSE_CODE_MIT.txt",
            "docs/v2.1/AMENDMENT_v2.1_DRAFT.md", registration.W03_DRAFT_DIR + "/CITATION.cff"}
        required |= {"docs/v2.1/reference/" + name for name in registration.CANONICAL}
        for relative in required:
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, dest)
        self.files = sorted(required)

    def test_inspection_verifies_canonical_sources_and_preserves_unsigned_state(self):
        report = registration.inspect_draft(self.root)
        self.assertEqual(report["initial_counts"], {"ordinary": 720, "calibration": 840})
        self.assertFalse(report["registered"])
        self.assertFalse(report["publish_authorized"])
        self.assertEqual(report["effective_wave_choice"], "MIBO2-W03")
        self.assertTrue(report["owner_effective_wave_choice_recorded"])
        self.assertFalse(report["W03_analysis_amendment_published"])
        self.assertTrue(report["baseline_transition_fixed"])
        self.assertTrue(report["scoring_qualification_criteria_fixed"])
        self.assertFalse(report["actual_AI_qualification_complete"])
        self.assertTrue(report["owner_metadata_and_disclosures_confirmed"])
        self.assertTrue(report["component_license_split_owner_approved"])
        self.assertTrue(report["draft_citation_versions_checked"])
        self.assertFalse(report["exact_final_public_artifact_approved"])

    def test_mutated_canonical_file_is_rejected(self):
        path = self.root / "docs/v2.1/reference/MIBO_Query_Codebook_v1.0.md"
        path.write_bytes(path.read_bytes() + b"\nSYNTHETIC_MUTATION\n")
        with self.assertRaisesRegex(ValueError, "canonical reference hash"): registration.inspect_draft(self.root)

    def test_completed_models_registration_or_enabled_env_are_rejected(self):
        protocol = self.root / "automation/config/core_v21_protocol.draft.json"
        original = protocol.read_bytes()
        data = json.loads(original); data["protocol_registration_id"] = "invented-registration"
        protocol.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "manufacture"): registration.inspect_draft(self.root)
        protocol.write_bytes(original)
        env = self.root / "runtime/mibo-core-v21.env.example"
        env.write_text(env.read_text().replace("MIBO_CORE_V21_EXECUTION=DISABLED", "MIBO_CORE_V21_EXECUTION=ENABLED"))
        with self.assertRaisesRegex(ValueError, "sentinel"): registration.inspect_draft(self.root)

    def test_unrelated_untracked_files_are_not_in_the_allowlist(self):
        tracked = "automation/core_v2_runner.py\0README.md\0private/secret.json\0docs/analysis/unrelated.md\0automation/url_set_variation.py\0"
        with mock.patch.object(registration.subprocess, "check_output", return_value=tracked.encode()):
            selected = registration.source_files(self.root)
        self.assertIn("automation/core_v2_runner.py", selected)
        self.assertNotIn("private/secret.json", selected)
        self.assertNotIn("docs/analysis/unrelated.md", selected)
        self.assertIn("automation/url_set_variation.py", selected)
        self.assertIn("automation/url_set_variation_v11.py", selected)

    def test_changed_start_wave_or_fabricated_W03_publication_rejected(self):
        path = self.root / "automation/config/core_v21_protocol.draft.json"
        original = path.read_bytes()
        for kind in ("wave", "publication"):
            data = json.loads(original)
            if kind == "wave": data["effective_from_wave_id"] = "MIBO2-W04"
            else: data["W03_analysis_transition"]["registration_id"] = "invented-publication"
            path.write_text(json.dumps(data))
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "owner choice|no automatic substitution"):
                registration.inspect_draft(self.root)

    def test_draft_rejects_old_four_series_hash_reuse_and_contrast_promotion(self):
        path = self.root / registration.W03_DRAFT_DIR / "analysis-spec.draft.json"
        original = path.read_bytes()
        for kind in ("freeze", "contrast", "denominator", "baseline"):
            data = json.loads(original)
            if kind == "freeze": data["collection_binding"]["provider_freeze_sha256"] = "a" * 64
            if kind == "contrast": data["primary_contrast"]["status"] = "approved-W03-minus-W02"
            if kind == "denominator": data["paper_primary_subset"]["planned_responses_per_wave"] = 80
            if kind == "baseline": data["baseline_wave"] = "MIBO2-W02"
            path.write_text(json.dumps(data))
            with self.subTest(kind=kind), self.assertRaises(ValueError): registration.inspect_draft(self.root)

    def test_owner_wave_choice_is_not_an_API_or_publication_approval(self):
        path = self.root / registration.W03_OWNER_DECISION
        original = path.read_bytes()
        for field in ("publication_approved_by_this_reply", "observation_API_approved_by_this_reply"):
            data = json.loads(original); data[field] = True
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "broaden"):
                registration.inspect_draft(self.root)

    def test_policy_approval_does_not_authorize_API_or_fabricate_qualification(self):
        path = self.root / registration.POLICY_OWNER_DECISION
        original = path.read_bytes()
        for field in ("observation_API_approved", "scoring_API_approved", "actual_model_qualification_completed"):
            data = json.loads(original); data[field] = True
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "broaden"):
                registration.inspect_draft(self.root)

    def test_secret_path_pattern_and_escape_rejected_without_echoing_value(self):
        for name in (".env", "private/x.txt", "public.txt"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"sk-proj-" + b"x" * 30)
            with self.subTest(name=name), self.assertRaises(ValueError) as caught:
                registration.read_public(self.root, name)
            self.assertNotIn("x" * 30, str(caught.exception))
        with self.assertRaises(ValueError): registration.read_public(self.root, "../outside.txt")

    def test_confirmed_facts_must_match_the_metadata_approval_record(self):
        path = self.root / registration.PUBLICATION_METADATA
        original = path.read_bytes()
        for field in ("creators", "funding_declaration", "competing_interests_declaration", "AI_assistance_disclosure"):
            data = json.loads(original)
            data[field] = [] if field == "creators" else "SYNTHETIC_MISMATCH"
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "owner-confirmed"):
                registration.inspect_draft(self.root)

    def test_confirmed_metadata_cannot_be_promoted_to_publication_or_API_authority(self):
        path = self.root / registration.PUBLICATION_METADATA
        original = path.read_bytes()
        for field in ("exact_final_public_artifact_approved", "publish_authorized", "model_metadata_API_authorized",
                "observation_API_authorized", "scoring_API_authorized"):
            data = json.loads(original); data[field] = True
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "not final-artifact"):
                registration.inspect_draft(self.root)

    def test_metadata_owner_approval_cannot_fabricate_labels_qualification_or_execution(self):
        path = self.root / registration.METADATA_OWNER_DECISION
        original = path.read_bytes()
        for field in ("publication_approved", "model_metadata_API_approved", "observation_API_approved",
                "scoring_API_approved", "exact_final_public_artifact_approved",
                "actual_model_qualification_completed", "authored_calibration_labels_substantively_reviewed_by_this_reply",
                "named_FINAL_execution_authorization_created", "frozen_historical_releases_relicensed",
                "runtime_install_or_activation_approved"):
            data = json.loads(original); data[field] = True
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "must not broaden"):
                registration.inspect_draft(self.root)

    def test_Core_and_analysis_document_version_sequences_are_not_interchanged(self):
        for relative, field in ((registration.PUBLICATION_METADATA, "version"),
                (registration.W03_DRAFT_DIR + "/analysis-spec.draft.json", "analysis_version")):
            path = self.root / relative
            original = path.read_bytes()
            data = json.loads(original); data[field] = "1.1-draft" if field == "version" else "2.1-draft"
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "version or citation"):
                registration.inspect_draft(self.root)
            path.write_bytes(original)

    def test_new_draft_citations_cannot_reuse_parent_DOI_or_release_date(self):
        for relative in ("CITATION.cff", registration.W03_DRAFT_DIR + "/CITATION.cff"):
            path = self.root / relative
            original = path.read_bytes()
            for line in ('doi: "10.5281/zenodo.22264635"', 'date-released: "2026-09-03"'):
                path.write_bytes(original + ("\n" + line + "\n").encode())
                with self.subTest(path=relative, line=line), self.assertRaisesRegex(ValueError, "published DOI"):
                    registration.inspect_draft(self.root)
            path.write_bytes(original)

    def test_prose_disclosures_are_bound_to_the_same_confirmed_metadata(self):
        for relative in ("docs/v2.1/AMENDMENT_v2.1_DRAFT.md", registration.W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md"):
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(original.replace(b"an equity holder of Scrumy Inc.", b"no disclosed company relationships"))
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "prose declarations"):
                registration.inspect_draft(self.root)
            path.write_bytes(original)

    def test_MIT_notice_and_component_specific_scope_are_required(self):
        for relative in ("LICENSE_CODE_MIT.txt", "LICENSE_NOTICE.md"):
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(b"SYNTHETIC_NO_LICENSE_SCOPE\n")
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "license|rights"):
                registration.inspect_draft(self.root)
            path.write_bytes(original)

    def test_published_parent_citation_is_preserved_byte_for_byte(self):
        path = self.root / registration.PARENT_CITATION
        path.write_bytes(path.read_bytes() + b"\nSYNTHETIC_MUTATION\n")
        with self.assertRaisesRegex(ValueError, "published-parent citation"):
            registration.inspect_draft(self.root)

    def test_new_metadata_and_license_artifacts_are_in_the_explicit_allowlist(self):
        with mock.patch.object(registration.subprocess, "check_output", return_value=b""):
            files = registration.source_files(self.root)
        for relative in (registration.METADATA_OWNER_DECISION, registration.PARENT_CITATION,
                "LICENSE_CODE_MIT.txt", "docs/v2.1/CITATION_GUIDE.md", registration.W03_DRAFT_DIR + "/CITATION.cff"):
            with self.subTest(path=relative):
                self.assertIn(relative, files)

    def test_zip_reproducible_independently_verified_and_never_overwritten(self):
        output1, output2 = Path(self.temp.name) / "package-a", Path(self.temp.name) / "package-b"
        with mock.patch.object(registration, "source_files", return_value=self.files), \
                mock.patch.object(registration.subprocess, "check_output", return_value="a" * 40):
            first = registration.build(self.root, output1)
            second = registration.build(self.root, output2)
            with self.assertRaises(FileExistsError): registration.build(self.root, output1)
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertTrue(first["archive_members_independently_verified"])
        self.assertFalse(first["network_or_upload_capability"])
        with zipfile.ZipFile(output1.with_name(output1.name + ".zip")) as archive:
            self.assertIn("SHA256SUMS.txt", archive.namelist())
            self.assertFalse(json.loads(archive.read("PACKAGE_STATUS.json"))["observation_API_authorized"])

    def commit_fixture(self):
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL)
        git("init", "-q")
        git("config", "core.autocrlf", "false")
        git("add", "--all")
        git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic local fixture")
        return git("rev-parse", "HEAD").decode().strip()

    def test_clean_commit_build_pins_source_without_self_referential_metadata(self):
        commit = self.commit_fixture()
        output = Path(self.temp.name) / "pinned-package"
        with mock.patch.object(registration, "source_files", return_value=self.files):
            receipt = registration.build(self.root, output, reviewed_commit=commit)
        self.assertTrue(receipt["source_pin_complete"])
        self.assertEqual(receipt["reviewed_clean_source_commit"], commit)
        self.assertNotIn("reviewed_clean_source_commit", receipt["open_release_gates"])
        self.assertFalse(receipt["registered"])
        self.assertFalse(receipt["publish_authorized"])
        with zipfile.ZipFile(output.with_name(output.name + ".zip")) as archive:
            provenance = json.loads(archive.read("SOURCE_PROVENANCE.json"))
            tracked = json.loads(archive.read(registration.PUBLICATION_METADATA))
            bound = json.loads(archive.read("PUBLICATION_METADATA_BOUND_DRAFT.json"))
            self.assertEqual(provenance["reviewed_candidate_commit"], commit)
            self.assertEqual(provenance["source_bytes"], "git_commit_blobs")
            self.assertIsNone(tracked["reviewed_source_commit"])
            self.assertEqual(bound["reviewed_source_commit"], commit)
            self.assertEqual(bound["source_worksheet_sha256"], registration.sha(archive.read(registration.PUBLICATION_METADATA)))
            self.assertFalse(bound["publish_authorized"])
            self.assertFalse(bound["observation_API_authorized"])
            self.assertFalse(bound["scoring_API_authorized"])

    def test_clean_commit_build_rejects_dirty_source_before_writing_a_package(self):
        commit = self.commit_fixture()
        (self.root / "unreviewed.txt").write_text("synthetic")
        output = Path(self.temp.name) / "not-built"
        with self.assertRaisesRegex(ValueError, "clean"):
            registration.build(self.root, output, reviewed_commit=commit)
        self.assertFalse(output.exists())

    def test_clean_commit_package_rebuild_is_reproducible(self):
        commit = self.commit_fixture()
        with mock.patch.object(registration, "source_files", return_value=self.files):
            first = registration.build(self.root, Path(self.temp.name) / "pinned-a", reviewed_commit=commit)
            second = registration.build(self.root, Path(self.temp.name) / "pinned-b", reviewed_commit=commit)
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])


if __name__ == "__main__":
    unittest.main()
