# MIBO Core

- **Current scientific release:** MIBO Core Protocol Package v2.0
- **DOI:** https://doi.org/10.5281/zenodo.22264635
- **Prospective registration:** 3 September 2026
- **First v2.0 field window:** 6 October 2026 00:00 UTC
- **Historical v1.0 DOI:** https://doi.org/10.5281/zenodo.21936410
- **License for protocol text:** CC BY 4.0

MIBO Core is the common sentinel-panel program of MIBO for longitudinal observation of generative-AI information behavior. The **Zenodo v2.0 record is the authoritative prospective specification for the API Core Interface (`ACI`) condition**. The Zenodo v1.0 record remains the frozen historical specification for its public-interface design; it is not amended, backfilled, or relabeled by v2.0. This GitHub repository is the public operational mirror and implementation workspace.

MIBO is composed of **MIBO Core, MIBO Satellite, and MIBO Network**.

## Founding and methods paper

The founding and methods preprint provides the scholarly account of the MIBO design, developmental pilot lessons, and international mirror-replication architecture.

- **Canonical preprint DOI:** https://doi.org/10.5281/zenodo.22025100
- **SSRN distribution copy:** https://doi.org/10.2139/ssrn.7319218

The paper is a companion scholarly output. It does **not** replace or amend the frozen MIBO Core Protocol Package v1.0, and its publication is not an additional MIBO-W01 start condition.

## Current v2.0 design

- fully automated, stateless provider-API observation on a controlled private runtime;
- a distinct API Core Interface (`ACI`) condition, never labeled Ecological Live;
- the unchanged four service lineages and 24 Japanese/English query forms from v1.0;
- ten independent replications per cell: 960 initial requests in ordinary waves;
- 1,120 initial requests in W01/W04/W07/W10 calibration waves;
- retrieval and tools disabled, including disabled Perplexity search;
- exact model identifiers and material settings frozen by a human before each wave; and
- fail-closed execution, append-only capture, registered retry limits, and retained missingness.

See `docs/v2.0/` and DOI `10.5281/zenodo.22264635`.

## Historical v1.0 design

- four persistent public service lineages;
- 12 conceptual items and 24 Japanese/English query forms;
- 12 synchronized monthly waves;
- ten independent replications per required observational cell;
- Ecological Live public-interface observation;
- a separate Paired Live Reference / Frozen Reference API module where technically defensible;
- four English Anchor Items for calibration;
- multisite G-theory re-observability calibration; and
- prospective correction, amendment, missingness, and withdrawal governance.

## Scientific source of truth

Use the following precedence:

1. **Zenodo v2.0:** `10.5281/zenodo.22264635` — current API-only scientific specification;
2. **Zenodo v1.0:** `10.5281/zenodo.21936410` — frozen historical public-interface specification;
3. the matching versioned documents and governance files mirrored in this repository;
4. prospectively completed private execution/configuration records;
5. implementation code under `automation/` and `runtime/`; and
6. historical release-candidate files, retained only for provenance.

A software change must not silently change the frozen scientific specification.

## Automation status

The repository contains a protocol-locked, fail-closed automation layer for v2.0 API Core and retains the v1.0 operational implementation for provenance:

- machine-readable frozen service, wave, and 24-form instrument configuration;
- deterministic manifest generation and strict integrity validation;
- fail-closed paired API adapters for currently admissible providers after Configuration Freeze;
- append-only raw-response, failure, retry, deviation, and SHA-256 records;
- exact-UTC paired execution on a controlled Japan-site runtime rather than GitHub-hosted scheduling;
- a terms-aware **human-operated** Ecological Live workstation that automates local manifest/tasking, timing, hashing, provenance, retry bookkeeping, and QC without scraping or controlling consumer webpages; and
- a read-only Codex maintainer workflow for engineering/readiness review.

See `docs/v2.0/`, `automation/core_v2_runner.py`, and the v2.0 runtime templates for the current operational layer.

## Pre-wave execution gate

The v2.0 scientific specification is public, but time-sensitive execution facts remain prospective. Before confirmatory collection, the v2.0 Terms/access review, exact provider/model freeze, synthetic readiness checks, deterministic manifest validation, controlled-runtime health checks, and human-signed execution authorization must all be complete. The dedicated execution sentinel remains disabled until that gate closes.

Failure to close a gate postpones or narrows collection; it does not authorize model substitution, retrospective alteration, or self-authorization.

## Historical rc3 files

Files whose names end in `v1.0-rc3` are retained as historical pre-release artifacts. They are **not** the current protocol and must not be used in place of the Zenodo v1.0 release.

## Citation

For the current API-only protocol package:

Sasano, K. (2026). *MIBO Core Protocol Package v2.0*. Zenodo. https://doi.org/10.5281/zenodo.22264635

For the historical public-interface protocol package:

Sasano, K. (2026). *MIBO Core Protocol Package v1.0*. Zenodo. https://doi.org/10.5281/zenodo.21936410

For the founding and methods paper:

Sasano, K. (2026). *MIBO: A Sentinel Panel Survey of Public Generative-AI Information Behavior: Design, Pilot Lessons, and an International Mirror-Replication Architecture* (Version 1.0) [Preprint]. Zenodo. https://doi.org/10.5281/zenodo.22025100

Also available as an SSRN distribution copy: https://doi.org/10.2139/ssrn.7319218
