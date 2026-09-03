#!/usr/bin/env python3
"""Build the disclosure-safe MIBO Core Protocol Package v2.0 archive."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUTOMATION = ROOT / "automation"
sys.path.insert(0, str(AUTOMATION))

import core_v2_runner as runner  # noqa: E402


PACKAGE_NAME = "MIBO_Core_Protocol_Package_v2.0"
DOCUMENTS = (
    "MIBO_Core_Protocol_v2.0.md",
    "MIBO_Operations_Manual_v2.0.md",
    "MIBO_Statistical_Analysis_Plan_v2.0.md",
    "MIBO_v1_to_v2_Transition_Record.md",
    "MIBO_API_Terms_Access_Review_Template_v2.0.md",
    "RELEASE_NOTES_v2.0.md",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def source_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def build(*, protocol_path: Path, version_doi: str, release_date: str,
          out_dir: Path) -> dict[str, object]:
    protocol, protocol_sha = runner.load_protocol(protocol_path)
    if protocol["protocol_registration_id"] != version_doi:
        raise ValueError("version DOI does not match protocol_registration_id")
    if not version_doi.startswith("10.5281/zenodo."):
        raise ValueError("v2.0 version DOI must be a Zenodo DOI")
    if out_dir.exists():
        raise FileExistsError(f"output directory already exists: {out_dir}")

    package = out_dir / PACKAGE_NAME
    documents = package / "documents"
    configuration = package / "configuration"
    documents.mkdir(parents=True)
    configuration.mkdir(parents=True)

    for name in DOCUMENTS:
        shutil.copyfile(ROOT / "docs" / "v2.0" / name, documents / name)
    shutil.copyfile(protocol_path, configuration / "core_v2_protocol.final.json")
    shutil.copyfile(AUTOMATION / "config" / "instrument_v1.0.json", configuration / "instrument_v1.0.json")
    shutil.copyfile(AUTOMATION / "config" / "services_v1.0.json", configuration / "services_v1.0.json")
    shutil.copyfile(AUTOMATION / "config" / "core_v2_provider_freeze.example.json", configuration / "core_v2_provider_freeze.example.json")
    shutil.copyfile(AUTOMATION / "config" / "core_v2_execution_authorization.example.json", configuration / "core_v2_execution_authorization.example.json")
    shutil.copyfile(ROOT / "LICENSE_NOTICE.md", package / "LICENSE_NOTICE.md")

    readme = f"""# MIBO Core Protocol Package v2.0

Version-specific DOI: https://doi.org/{version_doi}

This package prospectively defines the API-only MIBO Core v2.0 observation
condition. It preserves but does not amend or relabel MIBO Core v1.0
(`10.5281/zenodo.21936410`).

The `documents/` directory contains the protocol, operations manual, analysis
plan, transition record, Terms/access review template, and release notes. The
`configuration/` directory contains the finalized machine-readable protocol,
the unchanged v1.0 service and instrument identities, and public examples of
private execution records.

Completed freezes, authorizations, credentials, readiness evidence, and raw
observations are deliberately excluded.
"""
    write_exclusive(package / "README.md", readme.encode("utf-8"))

    citation = f"""cff-version: 1.2.0
message: "If you use this protocol package, please cite the version-specific Zenodo record."
title: "MIBO Core Protocol Package v2.0"
version: "2.0"
date-released: "{release_date}"
authors:
  - family-names: "Sasano"
    given-names: "Kento"
    orcid: "https://orcid.org/0009-0009-3853-8029"
    affiliation: "Okayama University; Keio Research Institute at SFC, Keio University"
doi: "{version_doi}"
repository-code: "https://github.com/mibo-research/mibo-core"
url: "https://doi.org/{version_doi}"
license: CC-BY-4.0
references:
  - type: generic
    title: "MIBO Core Protocol Package v1.0"
    doi: "10.5281/zenodo.21936410"
    scope: "Historical predecessor; not amended or relabeled by v2.0."
"""
    write_exclusive(package / "CITATION.cff", citation.encode("utf-8"))

    provenance = {
        "package": PACKAGE_NAME,
        "protocol_version": "2.0",
        "version_doi": version_doi,
        "release_date": release_date,
        "source_commit": source_commit(),
        "protocol_file_sha256": protocol_sha,
        "contains_private_records": False,
    }
    write_exclusive(
        package / "PROVENANCE.json",
        (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    files = sorted(path for path in package.rglob("*") if path.is_file())
    sums = "".join(f"{sha256(path)}  {path.relative_to(package).as_posix()}\n" for path in files)
    write_exclusive(package / "SHA256SUMS.txt", sums.encode("utf-8"))

    manifest = {
        "package": PACKAGE_NAME,
        "protocol_version": "2.0",
        "version_doi": version_doi,
        "release_date": release_date,
        "file_count_excluding_manifest": len(files) + 1,
        "files": [
            {"path": path.relative_to(package).as_posix(), "sha256": sha256(path)}
            for path in sorted(path for path in package.rglob("*") if path.is_file())
        ],
    }
    write_exclusive(
        package / "PACKAGE_MANIFEST.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    archive = out_dir / "mibo-core-protocol-v2.0.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in package.rglob("*") if p.is_file()):
            relative = Path(PACKAGE_NAME) / path.relative_to(package)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 9, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    return {
        "archive": str(archive),
        "archive_sha256": sha256(archive),
        "protocol_sha256": protocol_sha,
        "file_count": len(list(package.rglob("*"))),
        "version_doi": version_doi,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--version-doi", required=True)
    parser.add_argument("--release-date", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(
        protocol_path=args.protocol,
        version_doi=args.version_doi,
        release_date=args.release_date,
        out_dir=args.out_dir,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
