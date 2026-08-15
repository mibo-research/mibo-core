# MIBO Core automation

This directory is the deterministic execution layer for MIBO Core v1.0.

## Design principle

**Codex builds and reviews the observer; Codex does not improvise the observation.**

The scientific protocol is frozen at DOI `10.5281/zenodo.21936410`. The automation layer converts that protocol into reproducible manifests, identifiers, timing checks, provider adapters, human-operated UI task control, raw-data hashing, retry control, and quality control.

## What is automated now

- frozen machine-readable service, wave, and instrument configuration;
- exact 24 query forms and SHA-256 hashes;
- registered randomization seed;
- W01 calibration Window A / Window B manifest generation;
- ordinary-wave manifest generation;
- paired API block manifest generation only from a finalized provider-freeze record;
- Attempt ID generation;
- structural manifest validation;
- strict deterministic identity validation for seed, Attempt ID, service/provider metadata, and Anchor flags;
- fail-closed OpenAI, Anthropic, and Gemini paired API adapters with no retrieval/tools;
- protocol-locked technical retry scheduling;
- append-only API capture, failure records, retry linkage, deviations, and SHA-256 utilities;
- private paired execution authorization bound to exact manifest and Configuration Freeze hashes;
- exact-UTC W01 waiting on the controlled Japan-site runtime rather than GitHub-hosted scheduling;
- a human-operated Ecological Live workstation that selects registered tasks, displays exact prompts, enforces windows, captures human-pasted outputs append-only, and records provenance/hashes;
- Ecological Live outage pause and documented recovery scheduling;
- CI tests with synthetic fixtures only; and
- a manual read-only Codex maintainer workflow.

## Ecological Live boundary

Ecological Live is the public consumer-interface condition and is **not** replaced by the paired API module.

The dated pre-wave Terms/access review is stored at `automation/compliance/UI_TERMS_REVIEW_2026-08-15.md`. Under the current reviewed conditions, MIBO v1.0 defaults to **human-operated UI interaction** across the four Core lineages unless explicit provider permission covering a more automated procedure is prospectively archived.

The Ecological Live workstation therefore does **not**:

- open or control provider webpages;
- run headless browsers;
- scrape the DOM or page source;
- automate cookies/sessions;
- intercept provider network traffic; or
- programmatically extract outputs.

It may automate only the local research workflow: manifest selection, exact prompt display, registered-window validation, explicit human confirmations, local paste capture, append-only storage, hashing, retry bookkeeping, outage records, and QC.

### Ecological Live commands

Generate and freeze the UI manifest as usual, then use the private finalized UI configuration record:

```bash
python automation/ui_operator.py status \
  --manifest /srv/mibo-private/MIBO-W01-JP01-LUI.csv \
  --data-root /srv/mibo-data

python automation/ui_operator.py next \
  --manifest /srv/mibo-private/MIBO-W01-JP01-LUI.csv \
  --configuration /srv/mibo-private/ui_configuration.W01.json \
  --data-root /srv/mibo-data \
  --operator <OPERATOR_ID>
```

For every task the operator manually opens the registered provider UI, starts a fresh session, submits the exact displayed frozen prompt, uses the ordinary provider UI to copy the result, and pastes that result into the local MIBO capture workstation.

Calibration retries are window-bound: a WA retry must remain in WA and a WB retry must remain in WB. A service-wide outage pauses the affected lineage and requires one documented recovery block; the system does not move the observation to another surface.

## What remains deliberately gated

Real paired provider calls remain impossible until the applicable Pre-Wave-1 Execution Gate is closed. Exact deployed model IDs, output limits, materially matched generation settings, access/Terms status, and paired comparability classes are time-sensitive execution facts and must be prospectively frozen.

Ecological Live also remains gated by the finalized private UI configuration record. A lineage is not runnable until its current Terms/access check and operational settings are explicitly marked ready.

## W01 timing

- Field start: **2026-09-01 00:00 UTC / 09:00 JST**
- Window A: **2026-09-01 00:00–12:00 UTC / 09:00–21:00 JST**
- Window B: **2026-09-02 00:00–12:00 UTC / 09:00–21:00 JST**
- Field close: **2026-09-03 00:00 UTC / 09:00 JST**

Pre-wave readiness must begin no later than 24 hours before field start.

## Manifest commands

```bash
python automation/mibo_runner.py verify-config

python automation/mibo_runner.py show-wave --wave MIBO-W01

python automation/mibo_runner.py generate-ui \
  --wave MIBO-W01 \
  --site JP01 \
  --out /tmp/MIBO-W01-JP01-LUI.csv

python automation/mibo_runner.py validate /tmp/MIBO-W01-JP01-LUI.csv
python automation/manifest_integrity.py /tmp/MIBO-W01-JP01-LUI.csv

python automation/mibo_runner.py generate-paired \
  --wave MIBO-W01 \
  --site JP01 \
  --freeze /secure/path/provider_freeze.W01.json \
  --lineage MIBO-SL-002 \
  --lineage MIBO-SL-003 \
  --out /tmp/MIBO-W01-JP01-PAIRED.csv

python automation/mibo_runner.py validate /tmp/MIBO-W01-JP01-PAIRED.csv
python automation/manifest_integrity.py /tmp/MIBO-W01-JP01-PAIRED.csv
```

Both structural validation and strict identity validation are required before a manifest is frozen for scientific collection.

## Paired runtime preflight

Before `--execute`, create a private authorization record whose SHA-256 values match the exact paired manifest and provider-freeze file. A preflight can then be run without provider calls:

```bash
python automation/paired_executor.py \
  --manifest /secure/path/MIBO-W01-JP01-PAIRED.csv \
  --freeze /secure/path/provider_freeze.W01.json \
  --authorization /secure/path/execution_authorization.W01.json \
  --data-root /srv/mibo-data
```

Real execution additionally requires `MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE`, the provider credentials on the private Japan-site runtime, and the registered field window.

## Runtime architecture for September 1

Use a dedicated, controlled Japan-site machine or VM for scientific collection. Use GitHub for source control, CI, review, manifests, and disclosure-safe hashes. Do not use GitHub-hosted cron as the sole scientific scheduler.

Recommended runtime states:

`PREWAVE -> MANIFEST_FROZEN -> WINDOW_A -> STANDARD -> WINDOW_B -> RETRIES -> QC -> WAVE_FROZEN`

The `runtime/` directory contains the private-machine paired-service template. Start it only after the required freeze, authorization, credentials, and runtime sentinel are prepared.
