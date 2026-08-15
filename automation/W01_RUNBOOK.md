# MIBO-W01 automation runbook

Protocol DOI: `10.5281/zenodo.21936410`

## Before 31 August 2026 00:00 UTC / 09:00 JST
- close all applicable Pre-Wave-1 Execution Gate items;
- record exact service modes, account tiers, and provider terms/access status;
- freeze exact Paired Live and Frozen identifiers for every admitted provider;
- record comparability class;
- run synthetic dry-run tests;
- record software commit and environment hash;
- generate manifests;
- run both structural validation and `automation/manifest_integrity.py` strict deterministic identity validation;
- store final manifest SHA-256 hashes before observation.

A manifest must not be designated `MANIFEST_FROZEN` if either validator reports an error.

## 31 August 2026
- no confirmatory prompts for readiness testing;
- verify clock synchronization;
- verify storage;
- verify new-session behavior and registered UI modes using non-confirmatory material;
- human Operations Lead authorizes W01.

## 1 September 2026
- 00:00 UTC / 09:00 JST: W01 field opens.
- Window A lasts through 12:00 UTC / 21:00 JST.
- All ten English Anchor replications per service are collected in Window A.
- Standard non-anchor query forms may run elsewhere in the 48-hour field window.
- Valid outcomes are never retried because of content.

## 2 September 2026
- 00:00–12:00 UTC / 09:00–21:00 JST: Window B.
- Repeat all ten English Anchor replications per service.
- Paired API blocks, when admitted, use the frozen model IDs and fixed harness.

## 3 September 2026
- 00:00 UTC / 09:00 JST: primary field window closes.
- Complete structural QC, retry linkage, hashes, missingness, and 5% operational audit.
- Freeze raw wave package before substantive coding.
