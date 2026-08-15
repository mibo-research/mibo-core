# MIBO Core automation

This directory is the deterministic execution layer for MIBO Core v1.0.

## Design principle

**Codex builds and reviews the observer; Codex does not improvise the observation.**

The scientific protocol is frozen at DOI `10.5281/zenodo.21936410`. The automation layer converts that protocol into reproducible manifests, identifiers, scheduling checks, collection adapters, raw-data hashing, and quality control.

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
- CI tests; and
- a manual Codex maintainer workflow.

## What is deliberately not automated yet

Provider calls and public-web UI interactions remain disabled until the Pre-Wave-1 Execution Gate is closed for the relevant condition. Exact deployed model IDs, account/mode settings, provider access terms, and paired comparability classes are time-sensitive execution facts.

## W01 timing

- Field start: **2026-09-01 00:00 UTC / 09:00 JST**
- Window A: **2026-09-01 00:00–12:00 UTC / 09:00–21:00 JST**
- Window B: **2026-09-02 00:00–12:00 UTC / 09:00–21:00 JST**
- Field close: **2026-09-03 00:00 UTC / 09:00 JST**

Pre-wave readiness must begin no later than 24 hours before field start.

## Commands

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

## Runtime architecture for September 1

Use a dedicated, controlled Japan-site machine or VM for scientific collection. Use GitHub for source control, CI, review, manifests, and disclosure-safe hashes. Do not use GitHub-hosted cron as the sole scientific scheduler.

Recommended runtime states:

`PREWAVE -> MANIFEST_FROZEN -> WINDOW_A -> STANDARD -> WINDOW_B -> RETRIES -> QC -> WAVE_FROZEN`

Provider adapters should be added behind explicit configuration-freeze gates.
