"""Build a local, allowlisted public-registration DRAFT. No network or publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import core_v2_runner as runner
import core_v21_analysis as analysis_policy
import core_v21_policy as policy
import core_v21_scoring as scoring_policy
import core_v21_source as source

ROOT_FILES = {"AGENTS.md", "README.md", "CITATION.cff", "LICENSE_NOTICE.md", "LICENSE_CODE_MIT.txt", ".gitattributes"}
PUBLIC_PREFIXES = ("automation/", "runtime/", "docs/v2.0/", "docs/v2.0.1/",
                   "docs/v2.0.2/", "docs/v2.0.3/", "docs/v2.0.4/")
W03_DRAFT_DIR = "docs/analysis/W03-URL-variation-v1.1-DRAFT"
W03_OWNER_DECISION = "docs/v2.1/OWNER_DECISION_W03_20261107.json"
POLICY_OWNER_DECISION = "docs/v2.1/OWNER_DECISION_BASELINE_SCORING_20261107.json"
METADATA_OWNER_DECISION = "docs/v2.1/OWNER_DECISION_METADATA_LICENSE_20261107.json"
PUBLICATION_METADATA = "docs/v2.1/zenodo-metadata.draft.json"
PARENT_CITATION = "docs/v2.1/reference/PUBLISHED_CORE_v2.0.CITATION.cff"
PARENT_CITATION_SHA256 = "30911a7814b03dcd0bb17a52b00f1248881cdbcade8391eca1180379a45bf926"
MIT_LICENSE_LF_SHA256 = "5c5c2d0c30f135dd661c9e6e12dedd698214edb1f3c9e3c53d5c36656f8f1118"
HISTORICAL_W03 = {
    "docs/analysis/W03-URL-variation-v1.0/REGISTRATION.md": "1b0079041e0b3e344ec140e160745e9725be0022517bff41cbdada4b41ba1f3c",
    "docs/analysis/W03-URL-variation-v1.0/analysis-spec.json": "1f33325c3b759884c622c07c5e75fca6a8e7157c7656fa4c4461a52629eba28a",
    "automation/url_set_variation.py": "914b61672d66ca0dd21f3bd4a89e70dd5d7589d4322f3106e95b9f32535216a6",
}
NEW_FILES = {
    ".gitattributes", "automation/core_v21_policy.py", "automation/core_v21_waiter.py",
    "automation/core_v21_registration.py", "automation/config/core_v21_protocol.draft.json",
    "automation/config/core_v21_provider_freeze.template.json", "automation/config/core_v21_source_registry.json",
    "automation/tests/test_core_v21_three_series.py", "automation/tests/test_core_v21_registration.py",
    "runtime/mibo-core-v21.env.example", "runtime/mibo-core-v21.service",
    "docs/v2.1/README.md", "docs/v2.1/AMENDMENT_v2.1_DRAFT.md", "docs/v2.1/SAP_TRANSITION_v2.1_DRAFT.md",
    "docs/v2.1/AI_SCORING_v2.1_DRAFT.md", "docs/v2.1/REGISTRATION_CHECKLIST.md",
    "docs/v2.1/zenodo-metadata.draft.json", "docs/v2.1/scoring/README.md",
    "docs/v2.1/W03_DEPENDENCY_REVIEW.md",
    "docs/v2.1/scoring/coding-profile-v0.2-draft.json", "docs/v2.1/scoring/common-calibration-v0.2-draft.json",
    "docs/v2.1/scoring/validation-allocation-240-draft.json", "docs/v2.1/scoring/canonical-comparison.json",
    "docs/v2.1/reference/MIBO_Query_Codebook_v1.0.md", "docs/v2.1/reference/MIBO_Statistical_Analysis_Plan_v1.0.md",
    "docs/v2.1/reference/MIBO_Fixed_Query_Instrument_v1.0.md", "docs/v2.1/reference/SOURCE.json",
    "docs/v2.1/reference/SHA256SUMS.txt",
    W03_OWNER_DECISION,
    W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md", W03_DRAFT_DIR + "/analysis-spec.draft.json",
    "docs/analysis/W03-URL-variation-v1.0/REGISTRATION.md",
    "docs/analysis/W03-URL-variation-v1.0/analysis-spec.json",
    "automation/url_set_variation.py", "automation/tests/test_url_set_variation.py",
    "automation/url_set_variation_v11.py", "automation/tests/test_url_set_variation_v11.py",
    "automation/core_v21_analysis.py", "automation/core_v21_scoring.py",
    "automation/config/core_v21_analysis_policy.json", "automation/config/core_v21_scoring_qualification.json",
    "automation/tests/test_core_v21_baseline_scoring.py", POLICY_OWNER_DECISION,
    "docs/v2.1/SCORING_QUALIFICATION_SPEC_v1.0.md",
    "automation/core_v21_source.py", "automation/tests/test_core_v21_source.py",
    "docs/v2.1/SOURCE_REVIEW.md",
    METADATA_OWNER_DECISION, PARENT_CITATION, "LICENSE_CODE_MIT.txt",
    "docs/v2.1/CITATION_GUIDE.md", W03_DRAFT_DIR + "/CITATION.cff",
}
CANONICAL = {
    "MIBO_Query_Codebook_v1.0.md": "c6e19da13c5f64aaf073bf557518f90d69579c3697ace7791a9153f67b18218e",
    "MIBO_Statistical_Analysis_Plan_v1.0.md": "394523064ebfa24dd5762d4bb99288df6d8256376a5a00a130652b3517810992",
    "MIBO_Fixed_Query_Instrument_v1.0.md": "4f3eb973d5488a13f67caf4aaff1308073577e5f67666b89041e7215cde611e9",
}
SECRET_PATTERNS = (rb"sk-proj-[A-Za-z0-9_-]{20,}", rb"sk-ant-api[0-9A-Za-z_-]{20,}",
                   rb"AIza[A-Za-z0-9_-]{30,}", rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----")


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_public(root: Path, relative: str) -> bytes:
    path = root / relative
    if (not relative or "\\" in relative or Path(relative).is_absolute()
            or any(part in {"", ".", ".."} for part in relative.split("/"))
            or not path.is_file() or any(p.is_symlink() for p in (path, *path.parents))
            or not path.resolve().is_relative_to(root.resolve())):
        raise ValueError("unsafe or missing public package path")
    if path.name.startswith(".env") or any(part.lower() in {"private", "api_raw", "credentials"} for part in path.parts):
        raise ValueError("private path is not a public-registration input")
    payload = path.read_bytes()
    if any(re.search(pattern, payload) for pattern in SECRET_PATTERNS):
        raise ValueError("possible credential in public artifact; stop without exposing it")
    return payload


def inspect_publication_metadata(root: Path, metadata: dict, analysis: dict) -> None:
    """Verify owner-confirmed facts, never turn them into release authority."""
    decision = json.loads(read_public(root, METADATA_OWNER_DECISION))
    if (decision.get("record_type") != "CHAT_METADATA_DISCLOSURE_LICENSE_APPROVAL_NOT_PUBLICATION_OR_EXECUTION_AUTHORIZATION"
            or decision.get("existing_affiliations_funding_and_competing_interests_unchanged") is not True
            or decision.get("expanded_AI_assistance_disclosure_scope_approved") is not True
            or decision.get("original_software_MIT_approved") is not True
            or decision.get("existing_component_and_third_party_terms_preserved") is not True
            or any(decision.get(k) is not False for k in (
                "frozen_historical_releases_relicensed", "exact_final_public_artifact_approved",
                "publication_approved", "model_metadata_API_approved", "observation_API_approved",
                "scoring_API_approved", "actual_model_qualification_completed",
                "authored_calibration_labels_substantively_reviewed_by_this_reply",
                "named_FINAL_execution_authorization_created", "runtime_install_or_activation_approved"))):
        raise ValueError("metadata/license approval must not broaden into publication, execution or qualification")
    approved = decision.get("approved_metadata", {})
    if (metadata.get("metadata_owner_decision_file") != METADATA_OWNER_DECISION
            or metadata.get("owner_metadata_and_disclosures_confirmed") is not True
            or any(metadata.get(k) is not False for k in (
                "exact_final_public_artifact_approved", "publish_authorized", "model_metadata_API_authorized",
                "observation_API_authorized", "scoring_API_authorized"))):
        raise ValueError("confirmed metadata facts are not final-artifact or API authority")
    for field in ("creators", "funding_declaration", "competing_interests_declaration", "AI_assistance_disclosure"):
        if not approved.get(field) or metadata.get(field) != approved[field]:
            raise ValueError("publication metadata differs from the owner-confirmed declarations")
    creators = approved["creators"]
    if (not isinstance(creators, list) or len(creators) != 1
            or creators[0].get("name") != "Sasano, Kento"
            or creators[0].get("given_name") != "Kento" or creators[0].get("family_name") != "Sasano"
            or creators[0].get("orcid") != "0009-0009-3853-8029"
            or creators[0].get("affiliation") != "Okayama University; Keio Research Institute at SFC, Keio University"):
        raise ValueError("author/ORCID/affiliation must retain the owner-confirmed identity")
    for field in ("funding_declaration", "competing_interests_declaration", "AI_assistance_disclosure"):
        if not isinstance(approved[field], str) or not approved[field].strip():
            raise ValueError("publication declarations must be nonempty text")
    if (approved.get("protocol_text_license") != "CC-BY-4.0"
            or approved.get("original_software_license") != "MIT"
            or metadata.get("software_license") != {"id": "MIT", "license_file": "LICENSE_CODE_MIT.txt",
                "scope": approved.get("software_license_scope")}
            or not approved.get("software_license_scope")):
        raise ValueError("CC BY 4.0 protocol text and scoped MIT software must remain distinct")
    mit_text = read_public(root, "LICENSE_CODE_MIT.txt").decode("utf-8").replace("\r\n", "\n")
    if sha(mit_text.encode("utf-8")) != MIT_LICENSE_LF_SHA256:
        raise ValueError("MIT software license notice text changed")
    notice = read_public(root, "LICENSE_NOTICE.md").decode("utf-8")
    if any(fragment not in notice for fragment in (
            "Protocol text: CC BY 4.0", "Original software: MIT", "LICENSE_CODE_MIT.txt",
            "Existing and third-party terms preserved", "not a retroactive rewrite")):
        raise ValueError("component-specific license scope or historical rights notice missing")
    if sha(read_public(root, PARENT_CITATION)) != PARENT_CITATION_SHA256:
        raise ValueError("preserved published-parent citation bytes changed")
    analysis_citation = W03_DRAFT_DIR + "/CITATION.cff"
    expected_analysis = {"title": "W03 Derivative URL-String Analysis v1.1: Prospective Three-Series Amendment (DRAFT)",
        "version": "1.1-draft", "citation_file": analysis_citation, "new_registration_identifier": None}
    if (metadata.get("version") != "2.1-draft" or metadata.get("citation_file") != "CITATION.cff"
            or metadata.get("analysis_draft") != expected_analysis
            or analysis.get("analysis_version") != "1.1-draft"
            or analysis.get("core_protocol_package_version") != "2.1-draft"
            or analysis.get("publication_metadata_file") != PUBLICATION_METADATA
            or analysis.get("metadata_owner_decision_file") != METADATA_OWNER_DECISION
            or analysis.get("citation_file") != analysis_citation
            or analysis.get("protocol_text_license") != "CC BY 4.0"
            or not analysis.get("original_software_license", "").startswith("MIT;")):
        raise ValueError("Core/analysis draft version or citation binding mismatch")
    for path, title, version in (("CITATION.cff", metadata.get("title"), "2.1-draft"),
            (analysis_citation, expected_analysis["title"], "1.1-draft")):
        citation = read_public(root, path).decode("utf-8")
        if (not isinstance(title, str) or not title.endswith("(DRAFT)")
                or "title: " + json.dumps(title) not in citation.splitlines()
                or "version: " + json.dumps(version) not in citation.splitlines()
                or re.search(r"^(?:doi|date-released):", citation, re.MULTILINE)
                or not any(line.startswith("message: ") and "UNPUBLISHED" in line for line in citation.splitlines())
                or "license: CC-BY-4.0" not in citation.splitlines()):
            raise ValueError("draft citation must not inherit a published DOI, release date or wrong version")
        author = creators[0]
        for field, value in (("family-names", author["family_name"]), ("given-names", author["given_name"]),
                ("orcid", "https://orcid.org/" + author["orcid"]), ("affiliation", author["affiliation"])):
            if field + ": " + json.dumps(value) not in citation:
                raise ValueError("citation author metadata mismatch")
    for path in ("docs/v2.1/AMENDMENT_v2.1_DRAFT.md", W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md"):
        document = read_public(root, path).decode("utf-8")
        if (creators[0]["affiliation"] not in document or any(approved[field] not in document for field in (
                "funding_declaration", "competing_interests_declaration", "AI_assistance_disclosure"))):
            raise ValueError("protocol/analysis prose declarations differ from confirmed metadata")


def inspect_draft(root: Path) -> dict:
    protocol, _ = runner.load_protocol(root / "automation/config/core_v21_protocol.draft.json", require_final=False)
    if (protocol["protocol_version"] != policy.VERSION
            or protocol["protocol_status"] != "draft_requires_prospective_registration"
            or any(protocol.get(k) is not None for k in ("protocol_registration_id", "prospectively_registered_at_utc"))):
        raise ValueError("draft preparation must not manufacture registration or FINAL status")
    if (protocol.get("owner_baseline_scoring_decision_file") != POLICY_OWNER_DECISION
            or protocol["ai_scoring_qualification_plan"].get("empirical_qualification_complete") is not False
            or protocol["ai_scoring_qualification_plan"].get("publicly_registered") is not False):
        raise ValueError("policy approval does not establish empirical qualification or public registration")
    if (protocol.get("effective_from_wave_id") != "MIBO2-W03"
            or protocol.get("owner_effective_wave_decision_file") != W03_OWNER_DECISION
            or protocol.get("W03_analysis_transition") != {
                "status": "amendment-draft-prepared-not-published",
                "draft_file": W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md",
                "registration_id": None, "registered_at_utc": None}):
        raise ValueError("draft must reflect the recorded W03 owner choice without inventing publication")
    decision = json.loads(read_public(root, W03_OWNER_DECISION))
    if (decision.get("owner_effective_wave_choice_recorded") is not True
            or decision.get("effective_from_wave_id") != "MIBO2-W03"
            or decision.get("active_lineages") != list(policy.LINEAGES)
            or decision.get("ordinary_wave_initial_count") != 720
            or decision.get("W03_I03_intended_slots") != 60
            or decision.get("prepare_separate_W03_analysis_amendment") is not True
            or any(decision.get(k) is not False for k in (
                "publication_approved_by_this_reply", "model_metadata_API_approved_by_this_reply",
                "observation_API_approved_by_this_reply", "scoring_API_approved_by_this_reply",
                "Core_baseline_or_cross_version_comparison_decision_finalized"))):
        raise ValueError("W03 choice record must not broaden owner authority")
    approved = json.loads(read_public(root, POLICY_OWNER_DECISION))
    if (approved.get("baseline_and_comparison_policy_approved") is not True
            or approved.get("operational_and_validity_qualification_separation_approved") is not True
            or approved.get("baseline_wave") != "MIBO2-W03"
            or approved.get("W02_excluded_from_primary_comparison") is not True
            or any(approved.get(k) is not False for k in ("publication_approved", "model_metadata_API_approved",
                "observation_API_approved", "scoring_API_approved", "actual_model_qualification_completed",
                "authored_calibration_labels_substantively_reviewed_by_this_reply"))):
        raise ValueError("approved policy record must not broaden scientific review into API/publication authority")
    for module in (analysis_policy, scoring_policy):
        public = json.loads(read_public(root, "automation/config/" + module.POLICY_FILE))
        module.validate_policy(public)
        if public != module.load_policy():
            raise ValueError("packaged policy differs from the tested source policy")
    if any(scoring_policy.load_policy().get(k) is not False for k in (
            "actual_calibration_complete", "actual_validation_complete", "authored_label_content_review_complete")):
        raise ValueError("preparation cannot fabricate empirical grading or authored-label review")
    analysis = json.loads(read_public(root, W03_DRAFT_DIR + "/analysis-spec.draft.json"))
    read_public(root, W03_DRAFT_DIR + "/REGISTRATION_DRAFT.md")
    if (analysis.get("status") != "LOCAL_UNPUBLISHED_PROSPECTIVE_AMENDMENT_DRAFT"
            or analysis.get("owner_decision_file") != W03_OWNER_DECISION
            or analysis.get("owner_effective_wave_choice_recorded") is not True
            or analysis.get("prospective_wave") != "MIBO2-W03"
            or analysis.get("policy_decision_file") != POLICY_OWNER_DECISION
            or analysis.get("collection_design") != {"lineage_ids": list(policy.LINEAGES), "lineages": 3,
                "query_forms": 24, "replications": 10, "planned_initial_requests": 720}
            or analysis.get("paper_primary_subset") != {"item_id": "MIBO-I03", "languages": ["EN", "JA"],
                "lineages": 3, "planned_cells_per_wave": 6, "planned_responses_per_wave": 60}
            or analysis.get("baseline_wave") != "MIBO2-W03"
            or analysis.get("baseline_transition_decision_finalized") is not True
            or analysis.get("primary_contrast", {}).get("status") != "W02_EXCLUDED_FROM_PRIMARY_ANALYSIS"
            or analysis.get("primary_contrast", {}).get("owner_approved_baseline_and_comparison_policy") is not True
            or any(analysis.get(k) is not False for k in ("publish_authorized", "model_metadata_API_authorized",
                "observation_API_authorized", "scoring_API_authorized"))
            or any(analysis.get(k) is not None for k in ("new_registration_identifier", "prospectively_registered_at_utc", "named_execution_authorization"))):
        raise ValueError("W03 analysis draft scope, comparison or authorization mismatch")
    binding = analysis.get("collection_binding", {})
    for prefix, module in (("analysis", analysis_policy), ("scoring_qualification", scoring_policy)):
        if (analysis.get(prefix + "_policy_file") != "automation/config/" + module.POLICY_FILE
                or analysis.get(prefix + "_policy_sha256") != protocol[prefix + "_policy_sha256"]):
            raise ValueError("analysis specification must bind the approved policy hashes")
    if (binding.get("protocol_version") != policy.VERSION or binding.get("initial_request_count") != 720
            or binding.get("no_old_four_series_freeze_manifest_or_authorization_reused") is not True
            or analysis.get("w03_window") != runner.wave(protocol, "MIBO2-W03")):
        raise ValueError("W03 collection binding or original window mismatch")
    for key in ("protocol_registration_id", "collection_source_commit", "protocol_file_sha256", "manifest_sha256",
                "provider_freeze_sha256", "readiness_report_sha256", "exact_model_identifiers", "material_request_profiles",
                "all_material_request_profiles_equal_W02"):
        if analysis.get("collection_binding", {}).get(key) is not None:
            raise ValueError("W03 draft must not inherit old deployment/freeze/manifest bindings")
    prior = analysis["prior_registration"]
    if prior.get("identifier") != policy.W03_ANALYSIS_REGISTRATION:
        raise ValueError("W03 amendment must identify the preserved v1.0 public registration")
    for relative, digest in HISTORICAL_W03.items():
        if sha(read_public(root, relative)) != digest:
            raise ValueError("preserved W03 v1.0 source/registration bytes changed")
    for file_key, hash_key in (("registration_file", "registration_sha256"), ("analysis_spec_file", "analysis_spec_sha256")):
        if sha(read_public(root, prior[file_key])) != prior[hash_key]:
            raise ValueError("preserved W03 v1.0 registration bytes changed")
    implementation = analysis["implementation"]
    for file_key, hash_key in (("source_file", "source_sha256"), ("synthetic_tests_file", "synthetic_tests_sha256"),
                              ("immutable_legacy_dependency", "immutable_legacy_dependency_sha256")):
        if sha(read_public(root, implementation[file_key])) != implementation[hash_key]:
            raise ValueError("W03 analysis implementation binding SHA-256 mismatch")
    for name, digest in CANONICAL.items():
        if sha(read_public(root, "docs/v2.1/reference/" + name)) != digest:
            raise ValueError("canonical reference hash mismatch")
    registry = json.loads(read_public(root, "automation/config/core_v21_source_registry.json"))
    if [s["service_lineage_id"] for s in registry["active_lineages"]] != list(policy.LINEAGES):
        raise ValueError("public three-series registry mismatch")
    freeze = json.loads(read_public(root, "automation/config/core_v21_provider_freeze.template.json"))
    if (set(freeze["core_api"]) != set(policy.LINEAGES) or freeze.get("frozen_at_utc") is not None
            or freeze.get("wave_id") is not None or freeze.get("protocol_registration_id") is not None
            or any(c.get("status") != "pending" or c.get("model_id") is not None
                   or c.get("model_version_locked") is not False for c in freeze["core_api"].values())):
        raise ValueError("public provider freeze must remain an uncompleted three-series template")
    metadata = json.loads(read_public(root, PUBLICATION_METADATA))
    if (metadata.get("language_id") != "eng" or metadata.get("license", {}).get("id") != "cc-by-4.0"
            or metadata.get("effective_wave_owner_choice") != "MIBO2-W03"
            or metadata.get("W03_analysis_amendment_status") != "LOCAL_DRAFT_UNPUBLISHED"
            or any(metadata.get(k) is not None for k in (
                "new_version_doi", "reviewed_source_commit", "publication_date", "prospectively_registered_at_utc"))):
        raise ValueError("metadata must retain English, CC BY 4.0 and unpublished draft state")
    inspect_publication_metadata(root, metadata, analysis)
    env = read_public(root, "runtime/mibo-core-v21.env.example").decode()
    for line in ("MIBO_CORE_V2_EXECUTION=DISABLED", "MIBO_CORE_V21_EXECUTION=DISABLED",
                 "MIBO_CORE_V21_READINESS=DISABLED", "MIBO_CORE_V2_SMOKE_TEST=DISABLED"):
        if line not in env.splitlines():
            raise ValueError("public runtime example must keep every request sentinel disabled")
    return {"status": "LOCAL_PUBLIC_REGISTRATION_DRAFT", "proposed_protocol_version": policy.VERSION,
        "registered": False, "publish_authorized": False, "observation_API_authorized": False,
        "scoring_API_authorized": False, "canonical_reference_hashes_verified": True,
        "initial_counts": {"ordinary": 720, "calibration": 840},
        "effective_wave_choice": "MIBO2-W03", "owner_effective_wave_choice_recorded": True,
        "W03_analysis_amendment_published": False, "baseline_transition_fixed": True,
        "scoring_qualification_criteria_fixed": True, "actual_AI_qualification_complete": False,
        "owner_metadata_and_disclosures_confirmed": True, "component_license_split_owner_approved": True,
        "draft_citation_versions_checked": True, "draft_document_version": "2.1-draft",
        "W03_analysis_document_version": "1.1-draft", "exact_final_public_artifact_approved": False,
        "AI_unreferenced_use_scope": "auxiliary_exploratory_only",
        "open_release_gates": ["W03_analysis_and_Core_public_registration", "authored_content_and_source_review",
            "exact_final_public_artifact_and_publication_approval", "reviewed_clean_source_commit"],
        "not_deployed_or_empirically_validated": True}


def source_files(root: Path) -> list[str]:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
    selected = {p for p in tracked if p in ROOT_FILES or p.startswith(PUBLIC_PREFIXES)}
    # Unrelated concurrent untracked analysis files are deliberately not swept in.
    return sorted(selected | NEW_FILES)


def build(root: Path, output: Path, *, reviewed_commit: str | None = None) -> dict:
    root, output = root.resolve(strict=True), output.absolute()
    archive = output.with_name(output.name + ".zip")
    receipt_path = output.with_name(output.name + ".receipt.json")
    if any(p.exists() for p in (output, archive, receipt_path)):
        raise FileExistsError("preserve existing package/archive/receipt; use a new output name")
    if output.resolve().is_relative_to(root):
        raise ValueError("keep package output outside the public source checkout")
    if reviewed_commit is None:
        status = inspect_draft(root)
        files = {rel: read_public(root, rel) for rel in source_files(root)}
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise ValueError("source parent commit is unresolved")
        provenance = {"parent_commit": head, "reviewed_candidate_commit": None,
            "status": "UNCOMMITTED_LOCAL_CANDIDATE_NOT_A_RUNTIME_SOURCE_PIN"}
    else:
        identity, committed = source.committed_snapshot(root, reviewed_commit)
        selected = source_files(root)
        if not set(selected) <= set(committed):
            raise ValueError("every packaged source file must belong to the pinned Git tree")
        with tempfile.TemporaryDirectory(prefix="mibo-v21-pinned-source-") as tmp:
            canonical = Path(tmp)
            source.write_snapshot(canonical, committed)
            status = inspect_draft(canonical)
            files = {rel: read_public(canonical, rel) for rel in selected}
            bound = json.loads(files[PUBLICATION_METADATA])
            bound.update(reviewed_source_commit=reviewed_commit,
                worksheet_status="LOCAL_COMMIT_BOUND_DRAFT_NOT_AN_API_SUBMISSION_PAYLOAD",
                source_worksheet_file=PUBLICATION_METADATA,
                source_worksheet_sha256=sha(files[PUBLICATION_METADATA]),
                generated_from_reviewed_commit=True)
            inspect_publication_metadata(canonical, bound,
                json.loads(files[W03_DRAFT_DIR + "/analysis-spec.draft.json"]))
            files["PUBLICATION_METADATA_BOUND_DRAFT.json"] = encoded(bound)
        if source.clean_commit(root, reviewed_commit) != identity:
            raise ValueError("source changed before pinned package construction")
        status.update(reviewed_clean_source_commit=reviewed_commit, source_pin_complete=True,
            source_pin_is_public_registration=False, source_pin_is_execution_authorization=False,
            source_bytes="git_commit_blobs",
            generated_non_source_members=["PUBLICATION_METADATA_BOUND_DRAFT.json"])
        status["open_release_gates"].remove("reviewed_clean_source_commit")
        provenance = {**identity, "status": "CLEAN_REVIEWED_LOCAL_COMMIT_UNPUBLISHED_NOT_RUNTIME_AUTHORIZATION",
            "source_bytes": "git_commit_blobs", "source_pin_is_public_registration": False,
            "source_pin_is_execution_authorization": False}
    files["SOURCE_PROVENANCE.json"] = encoded({**provenance,
        "historical_installed_W02_base_commit": "d970efab834f193b7f3d12ecded20be6f0e8f445",
        "W03_analysis_amendment_draft_and_unchanged_v1_dependency_included": True,
        "collection_enabled_by_packager": False, "publication_performed": False})
    files["PACKAGE_STATUS.json"] = encoded(status)
    file_hashes = {name: sha(payload) for name, payload in sorted(files.items())}
    files["FILE_MANIFEST.json"] = encoded({"schema_version": "1.0", "purpose": status["status"], "files": file_hashes,
        "self_manifest_and_SHA256SUMS_excluded_from_this_mapping": True})
    sums = {name: sha(payload) for name, payload in sorted(files.items())}
    files["SHA256SUMS.txt"] = ("\n".join(f"{digest}  {name}" for name, digest in sums.items()) + "\n").encode()
    output.mkdir(parents=True)
    for name, payload in sorted(files.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle: handle.write(payload)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as zf:
        for name, payload in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(2026, 11, 7, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            zf.writestr(item, payload)
    # Reopen and independently check every archive member against the source map.
    with zipfile.ZipFile(archive) as zf:
        if len(zf.namelist()) != len(set(zf.namelist())) or set(zf.namelist()) != set(files):
            raise ValueError("package member identity mismatch")
        for name, payload in files.items():
            if sha(zf.read(name)) != sha(payload): raise ValueError("package member SHA-256 mismatch")
    receipt = {**status, "archive_file": archive.name, "archive_sha256": sha(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size, "member_count": len(files),
        "file_manifest_sha256": sha(files["FILE_MANIFEST.json"]),
        "SHA256SUMS_sha256": sha(files["SHA256SUMS.txt"]), "archive_members_independently_verified": True,
        "network_or_upload_capability": False, "private_data_or_completed_authorization_included": False}
    with receipt_path.open("xb") as handle: handle.write(encoded(receipt))
    return receipt


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--out", type=Path)
    p.add_argument("--reviewed-commit", help="Full clean local HEAD; package immutable Git blobs, never publish")
    args = p.parse_args()
    if args.reviewed_commit and not args.out:
        p.error("--reviewed-commit requires --out")
    result = build(args.source, args.out, reviewed_commit=args.reviewed_commit) if args.out else inspect_draft(args.source)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
