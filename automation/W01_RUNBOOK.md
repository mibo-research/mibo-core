# MIBO-W01 automation runbook

Protocol DOI: `10.5281/zenodo.21936410`

## Before 31 August 2026 00:00 UTC / 09:00 JST
- close all applicable Pre-Wave-1 Execution Gate items;
- record exact service modes, account tiers, and provider terms/access status;
- freeze exact Paired Live and Frozen identifiers for every admitted provider;
- freeze the materially matched provider request profile for every admitted pair;
- record comparability class;
- run synthetic dry-run tests only;
- record software commit and environment hash;
- generate manifests;
- run both structural validation and `automation/manifest_integrity.py` strict deterministic identity validation;
- store final manifest SHA-256 hashes before observation.

A manifest must not be designated `MANIFEST_FROZEN` if either validator reports an error.

## 31 August 2026
- do not use confirmatory prompts for readiness testing;
- verify Japan-site UTC clock synchronization;
- verify append-only research-data storage;
- verify new-session behavior and registered UI modes using non-confirmatory material;
- finalize the private provider Configuration Freeze Record;
- generate the final paired manifest from that exact freeze record;
- generate the private execution-authorization record with the exact manifest and freeze SHA-256 values;
- set provider credentials only on the private Japan-site runtime;
- after all applicable gates close, set `MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE`;
- start `mibo-paired.service`; it waits on the controlled runtime for the registered W01 UTC start;
- human Operations Lead authorizes W01.

The paired API runtime does **not** substitute for Ecological Live public-interface observations. UI collection remains a separate observational condition and must use the registered public interface and settings.

## 1 September 2026
- 00:00 UTC / 09:00 JST: W01 field opens.
- the Japan-site paired service launches from the frozen UTC timestamp without GitHub-hosted scheduling;
- Window A lasts through 12:00 UTC / 21:00 JST;
- all ten English Anchor replications per service are collected in Window A for Ecological Live;
- standard non-anchor query forms may run elsewhere in the 48-hour field window;
- paired API Provider × Anchor Item blocks use the frozen model IDs, frozen request profile, and fixed harness;
- each paired 20-call block should complete within two hours; any excess is retained and logged as a timing deviation;
- valid outcomes are never retried because of content.

## 2 September 2026
- 00:00–12:00 UTC / 09:00–21:00 JST: Window B;
- repeat all ten English Anchor Ecological Live replications per service;
- paired API retries, if any, obey the registered technical-failure rule and remain inside the primary field window.

## 3 September 2026
- 00:00 UTC / 09:00 JST: primary field window closes;
- do not schedule a primary retry whose due time falls outside the field window;
- complete structural QC, strict manifest checks, retry linkage, file hashes, missingness, and 5% operational audit;
- build the wave-level SHA-256 manifest;
- freeze raw wave package before substantive coding.
