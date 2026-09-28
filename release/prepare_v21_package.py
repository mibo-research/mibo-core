#!/usr/bin/env python3
"""Prepare a disclosure-safe v2.1 Zenodo version package after DOI reservation.

The resulting archive is a release candidate. Publishing it and attesting the
private Pre-Wave gate remain human actions; this tool never authorizes execution.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "automation"))
import core_v21_runner as runner  # noqa: E402

DRAFT_JSON = ROOT / "automation/config/core_v21_protocol.draft.json"
DRAFT_PROTOCOL = ROOT / "docs/v2.1/MIBO_Core_Protocol_v2.1_DRAFT.md"
DRAFT_NOTES = ROOT / "docs/v2.1/RELEASE_NOTES_v2.1_DRAFT.md"
DRAFT_ADDENDUM = ROOT / "docs/v2.1/OPERATIONS_ADDENDUM_v2.1_DRAFT.md"
PACKAGE = "MIBO_Core_Protocol_Package_v2.1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(content.encode("utf-8") if isinstance(content, str) else content)


def build(version_doi: str, release_date: str, out_dir: Path) -> Path:
    if not re.fullmatch(r"10\.5281/zenodo\.[0-9]+", version_doi) or version_doi == runner.PREDECESSOR_DOI:
        raise ValueError("a distinct reserved Zenodo version DOI is required")
    datetime.fromisoformat(release_date)
    if out_dir.exists():
        raise FileExistsError(out_dir)
    package = out_dir / PACKAGE
    docs = package / "documents"
    config = package / "configuration"

    protocol = json.loads(DRAFT_JSON.read_text(encoding="utf-8"))
    protocol["protocol_status"] = "finalized_and_prospectively_registered"
    protocol["protocol_registration_id"] = version_doi
    final_json = config / "core_v21_protocol.final.json"
    write(final_json, json.dumps(protocol, indent=2, ensure_ascii=False) + "\n")
    runner.load_protocol(final_json)

    text = DRAFT_PROTOCOL.read_text(encoding="utf-8")
    text = text.replace(
        "**Status:** DRAFT — NOT REGISTERED. No confirmatory collection is authorized by this document.",
        "**Status:** Prospective release candidate. Confirmatory collection requires this version's public registration before the first request.",
    ).replace(
        "**Version-specific registration:** PENDING — reserve and publish a new version-specific DOI before the first observation",
        f"**Version-specific registration:** `{version_doi}` (publish this version before the first observation)",
    ).replace(
        "This v2.1 draft has no confirmatory authority until its own\nversion-specific DOI is reserved, inserted into the complete package and\nmachine-readable protocol, and the new version is published before collection.",
        "This v2.1 release candidate has no confirmatory authority until its\nversion-specific DOI is published before collection.",
    )
    if "PENDING" in text or "DRAFT — NOT REGISTERED" in text:
        raise ValueError("unresolved draft marker in v2.1 protocol")
    write(docs / "MIBO_Core_Protocol_v2.1.md", text)
    notes = DRAFT_NOTES.read_text(encoding="utf-8").replace(
        "**Status:** Not registered. This draft has no authority for confirmatory collection.",
        "**Status:** Release candidate. Publish under the reserved version DOI before collection.",
    ).replace("The version-specific\nv2.1 DOI", f"The version-specific\nv2.1 DOI `{version_doi}`")
    write(docs / "RELEASE_NOTES_v2.1.md", notes)
    write(docs / "OPERATIONS_ADDENDUM_v2.1.md",
          DRAFT_ADDENDUM.read_text(encoding="utf-8").replace(
              "# MIBO Core v2.1 Operations Addendum (draft)",
              "# MIBO Core v2.1 Operations Addendum"))

    inherited = (
        "MIBO_Operations_Manual_v2.0.md", "MIBO_Statistical_Analysis_Plan_v2.0.md",
        "MIBO_API_Terms_Access_Review_Template_v2.0.md",
    )
    for name in inherited:
        write(docs / name, (ROOT / "docs/v2.0" / name).read_bytes())
    for name in (
        "instrument_v1.0.json", "services_v1.0.json",
        "core_v21_provider_freeze.example.json",
        "core_v21_execution_authorization.example.json",
    ):
        write(config / name, (ROOT / "automation/config" / name).read_bytes())
    write(package / "LICENSE_NOTICE.md", (ROOT / "LICENSE_NOTICE.md").read_bytes())
    write(package / "README.md", f"""# MIBO Core Protocol Package v2.1

Version-specific DOI: https://doi.org/{version_doi}

This prospective package changes only the W01 field window to 2026-10-01
00:00–2026-10-03 00:00 UTC. The v2.0 Operations Manual, Statistical Analysis
Plan and Terms/access template are included without modification; the v2.1
Operations Addendum governs the changed clock, paths and sentinel. The fixed
instrument and lineages retain their v1.0 identity.

Publication of this package under its reserved version DOI must precede any
confirmatory v2.1 request. Private model freezes, authorizations, credentials,
readiness evidence and raw responses are excluded. Package preparation alone
is neither publication nor authorization.
""")
    write(package / "CITATION.cff", f"""cff-version: 1.2.0
message: "Cite this version-specific Zenodo record."
title: "MIBO Core Protocol Package v2.1"
version: "2.1"
date-released: "{release_date}"
authors:
  - family-names: "Sasano"
    given-names: "Kento"
    orcid: "https://orcid.org/0009-0009-3853-8029"
doi: "{version_doi}"
repository-code: "https://github.com/mibo-research/mibo-core"
url: "https://doi.org/{version_doi}"
license: CC-BY-4.0
references:
  - type: generic
    title: "MIBO Core Protocol Package v2.0"
    doi: "{runner.PREDECESSOR_DOI}"
""")
    write(package / "PROVENANCE.json", json.dumps({
        "package": PACKAGE, "protocol_version": "2.1", "version_doi": version_doi,
        "release_date": release_date, "protocol_file_sha256": sha(final_json),
        "published_by_builder": False, "execution_authorized_by_builder": False,
        "contains_private_records": False,
    }, indent=2, sort_keys=True) + "\n")
    files = sorted(p for p in package.rglob("*") if p.is_file())
    write(package / "SHA256SUMS.txt", "".join(
        f"{sha(p)}  {p.relative_to(package).as_posix()}\n" for p in files))
    all_files = sorted(p for p in package.rglob("*") if p.is_file())
    write(package / "PACKAGE_MANIFEST.json", json.dumps({
        "package": PACKAGE, "protocol_version": "2.1", "version_doi": version_doi,
        "files": [{"path": p.relative_to(package).as_posix(), "sha256": sha(p)} for p in all_files],
    }, indent=2, sort_keys=True) + "\n")
    archive = out_dir / "mibo-core-protocol-v2.1.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in package.rglob("*") if p.is_file()):
            zf.write(path, (Path(PACKAGE) / path.relative_to(package)).as_posix())
    return archive


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version-doi", required=True)
    ap.add_argument("--release-date", required=True)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    print(build(a.version_doi, a.release_date, a.out_dir))


if __name__ == "__main__":
    main()
