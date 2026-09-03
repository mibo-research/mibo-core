# Zenodo release checklist — MIBO Core Protocol Package v2.0

## Release result

- Published: `2026-09-03`
- Version DOI: `10.5281/zenodo.22264635`
- Concept DOI: `10.5281/zenodo.21936409`
- Archive: `mibo-core-protocol-v2.0.zip`
- Archive SHA-256: `34bd2863c19962a02ff6f1e2b61ef7496d36530d01dc5de44b338ec9a16ac1b0`
- Source commit embedded in the archive: `1bd161bbc77d95d43d73616b52d80e848cad352d`
- v1.0 file preserved; transition note added to v1.0 metadata only.

## New-version metadata

- Title: `MIBO Core Protocol Package v2.0`
- Resource type: Technical note
- Publication date: `2026-09-03`
- Version: `2.0`
- Creator: Kento Sasano
- ORCID: `0009-0009-3853-8029`
- Affiliations: Okayama University; Keio Research Institute at SFC, Keio University
- Language: English
- License: Creative Commons Attribution 4.0 International
- Repository: `https://github.com/mibo-research/mibo-core`
- Related founding paper: `10.5281/zenodo.22025100`

## Description

MIBO Core Protocol Package v2.0 prospectively defines a fully automated,
provider-API observation design for MIBO Core. The primary API Core Interface
(`ACI`) condition follows the four registered MIBO service lineages with the
unchanged 24 Japanese/English Query Forms and ten independent replications per
cell. Ordinary waves contain 960 intended initial API requests; W01, W04, W07,
and W10 are adjacent-window calibration waves with 1,120 intended initial
requests. Requests are stateless and environment-closed, with retrieval and
tools disabled; Perplexity search is explicitly disabled.

This is a prospective scientific successor to MIBO Core Protocol Package v1.0
(`10.5281/zenodo.21936410`), not a correction or relabeling of v1.0. The planned
v1.0 W01 public-interface collection did not commence inside its registered
field window. No v2.0 API observation is represented as v1.0 Ecological Live,
Paired Live Reference, Frozen Reference, or API Shadow data. The v1.0 record and
founding paper remain preserved as the historical public-interface design.

The package contains the v2.0 protocol, operations manual, statistical analysis
plan, transition record, Terms/access review template, machine-readable wave
registry, and unchanged v1.0 service/instrument identities. Completed private
configuration freezes, execution authorizations, credentials, readiness
evidence, and raw observations are excluded.

## Keywords

`MIBO`; `machine information behavior`; `generative AI`; `API observatory`;
`longitudinal observation`; `sentinel panel`; `re-observability`;
`generalizability theory`; `open science`; `automated measurement`

## Publication checks

1. Create the record through **New version** on v1.0; do not edit or replace the
   v1.0 file.
2. Reserve the version-specific DOI.
3. Put that DOI in `automation/config/core_v2_protocol.v2.0.json` and the
   protocol document.
4. Run the complete local tests, release-package test, W01 manifest validation,
   and repository validation.
5. Build the final ZIP with `release/build_v2_package.py`.
6. Verify the ZIP SHA-256 and inspect every included filename.
7. Upload only `mibo-core-protocol-v2.0.zip`.
8. Preview title, description, creator, date, version, license, language,
   keywords, relationships, and file before publishing.
9. Publish v2.0 and record both the version DOI and concept DOI.
10. Edit only the v1.0 metadata description to add the public status note and
    v2.0 link; do not change the v1.0 file.

## v1.0 metadata note after v2.0 publication

Status update (3 September 2026): the planned MIBO Core v1.0 W01
public-interface collection did not commence inside its registered field
window. The v1.0 package remains the preserved historical specification and is
not being rewritten or backfilled. MIBO Core continues prospectively under the
API-only v2.0 protocol at `10.5281/zenodo.22264635`. API observations collected under
v2.0 are not Ecological Live observations and must not be pooled with v1.0
confirmatory data.
