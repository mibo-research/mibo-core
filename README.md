# MIBO Core

**Canonical scientific release:** MIBO Core Protocol Package v1.0  
**DOI:** https://doi.org/10.5281/zenodo.21936410  
**Scientific freeze:** 15 August 2026  
**Effective date / Wave 1 start:** 1 September 2026  
**License for protocol text:** CC BY 4.0

MIBO Core is the common sentinel-panel program of MIBO for longitudinal observation of public generative-AI information behavior. The **Zenodo v1.0 record is the authoritative frozen archival specification**. This GitHub repository is its public operational mirror and implementation workspace.

MIBO is composed of **MIBO Core, MIBO Satellite, and MIBO Network**.

## First-year v1.0 design

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

Use the following precedence for current v1.0 work:

1. **Zenodo:** `10.5281/zenodo.21936410` — frozen scientific specification;
2. current v1.0 documents and governance files mirrored in this repository;
3. prospectively completed Pre-Wave execution/configuration records;
4. implementation code under `automation/` and `runtime/`;
5. historical release-candidate files, which are retained only for provenance.

A software change must not silently change the frozen scientific specification.

## Automation status

The repository contains a protocol-locked automation layer for W01:

- machine-readable frozen service, wave, and 24-form instrument configuration;
- deterministic manifest generation and strict integrity validation;
- fail-closed paired API adapters for currently admissible providers after Configuration Freeze;
- append-only raw-response, failure, retry, deviation, and SHA-256 records;
- exact-UTC paired execution on a controlled Japan-site runtime rather than GitHub-hosted scheduling;
- a terms-aware **human-operated** Ecological Live workstation that automates local manifest/tasking, timing, hashing, provenance, retry bookkeeping, and QC without scraping or controlling consumer webpages; and
- a read-only Codex maintainer workflow for engineering/readiness review.

See `automation/README.md` and `automation/W01_RUNBOOK.md` for the operational layer.

## Pre-Wave-1 gate

The scientific specification is frozen, but time-sensitive execution facts remain prospective. Before confirmatory collection, the applicable items in `PRE_WAVE1_EXECUTION_GATE.md` must be closed, including current provider Terms/access review, deployed UI configuration, paired model identifiers and comparability, technical dry run, storage/runtime readiness, and any required institutional determination.

Failure to close a gate postpones or narrows collection; it does not authorize retrospective alteration of v1.0.

## Historical rc3 files

Files whose names end in `v1.0-rc3` are retained as historical pre-release artifacts. They are **not** the current protocol and must not be used in place of the Zenodo v1.0 release.

## Citation

Sasano, K. (2026). *MIBO Core Protocol Package v1.0*. Zenodo. https://doi.org/10.5281/zenodo.21936410
