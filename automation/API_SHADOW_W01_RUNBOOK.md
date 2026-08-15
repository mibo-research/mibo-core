# W01 runbook — MIBO API Shadow Archive v0.1

This runbook is for the **exploratory auxiliary** API Shadow Archive only. It does not change or replace the MIBO Core v1.0 W01 runbook.

## Before 31 August 2026

1. Copy `automation/config/api_shadow_freeze.example.json` to the private runtime as `/srv/mibo-private/api_shadow_freeze.W01.json`.
2. For every Core Service Lineage, set a final status of `eligible` or `ineligible`.
3. For each eligible lineage, prospectively record:
   - exact current API `model_id`;
   - selection rationale;
   - provider model evidence;
   - verification timestamp;
   - dated API Terms/access source;
   - exact request profile and credential environment name.
4. Keep the v0.1 environment class `CLOSED`.
5. For Perplexity, keep `disable_search=true`.
6. Do not use any registered MIBO query for technical smoke testing.

## 31 August — automated readiness

Run the ordinary Core preflight with the additional environment variable:

```bash
export MIBO_API_SHADOW_FREEZE=/srv/mibo-private/api_shadow_freeze.W01.json
```

`runtime/preflight.sh` then additionally performs:

- provider catalog retrieval;
- exact frozen shadow model verification;
- optional non-confirmatory smoke tests;
- 24-form × k=10 shadow manifest generation;
- deterministic manifest validation;
- hash-bound API Shadow bundle creation;
- disabled Shadow authorization-template creation.

To enable the optional smoke test after the dated Terms/access review:

```bash
export MIBO_API_SHADOW_SMOKE_TEST=ENABLED_AFTER_TERMS_REVIEW
```

The smoke prompt is fixed in `shadow_preflight.py` and is not one of the registered MIBO queries.

## Human authorization

The bundle emits `execution_authorization.SHADOW.template.json` with all human gates disabled.

Create the final private authorization record only after review. It must retain:

- `archive_class = exploratory_auxiliary`;
- `confirmatory_use = prohibited`;
- exact manifest SHA-256;
- exact shadow-freeze SHA-256;
- `acknowledge_exploratory_only = true`;
- Terms/access, institutional-process, and dry-run gates set prospectively;
- Operations Lead and authorization timestamp.

Then set the runtime sentinel:

```text
MIBO_API_SHADOW_EXECUTION=ENABLED_AFTER_SHADOW_GATE
```

The Core paired sentinel does not authorize Shadow execution.

## W01 execution

If all four lineages are eligible, the manifest contains exactly **960 initial requests**:

`4 services × 24 frozen forms × 10 replications`.

The executor follows one globally deterministic interleaved execution order, uses stateless provider requests, and runs within the registered 48-hour W01 field window.

Start the systemd unit after authorization:

```bash
sudo systemctl enable mibo-shadow.service
sudo systemctl start mibo-shadow.service
sudo systemctl status mibo-shadow.service
```

The service may be armed before W01; `shadow_waiter.py` waits until the frozen UTC wave start.

The executor:

- never selects or substitutes a model;
- never retries because an answer is substantively undesirable;
- applies only the registered technical retry delays;
- pauses a rate-limited or service-unavailable lineage while other providers continue;
- suspends a repeatedly unavailable lineage rather than falling back;
- stores all raw data under `auxiliary/api-shadow-v0.1/`, never under the Core confirmatory raw namespace;
- can resume after interruption by skipping already captured attempts and reconstructing stored retry links.

## Post-field

After 2026-09-03 00:00 UTC / 09:00 JST:

```bash
python automation/shadow_qc.py \
  --data-root /srv/mibo-data \
  --manifest /srv/mibo-private/MIBO-W01-JP01-api-shadow/manifests/MIBO-W01-JP01-API-SHADOW.csv \
  --freeze /srv/mibo-private/api_shadow_freeze.W01.json
```

Then freeze the auxiliary raw archive:

```bash
python automation/shadow_freeze.py \
  --data-root /srv/mibo-data \
  --manifest /srv/mibo-private/MIBO-W01-JP01-api-shadow/manifests/MIBO-W01-JP01-API-SHADOW.csv \
  --freeze /srv/mibo-private/api_shadow_freeze.W01.json
```

This writes the Shadow QC report, Shadow freeze record, and SHA-256 manifest. Missing observations remain missing. No imputation is performed.

## Analytical rule

The API Shadow Archive is exploratory auxiliary evidence. Any later paper using it must identify it explicitly as such and must not present its analyses as preregistered MIBO Core v1.0 confirmatory results.
