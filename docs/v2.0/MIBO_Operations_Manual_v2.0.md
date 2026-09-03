# MIBO Core v2.0 Operations Manual

## 1. Scope

This manual governs the automated API Core Interface (`ACI`) condition in MIBO
Core v2.0. It contains no consumer-browser collection procedure. No human is
required to operate 960 individual observations.

## 2. Roles

### Operations Lead

The Operations Lead owns the prospective scientific decisions: protocol
registration, exact model and settings freeze, Terms/access determination,
wave authorization, deviation classification, and wave-completion sign-off.

### API and Technical Lead

The API and Technical Lead deploys the immutable code snapshot, gathers
official model-catalog evidence, runs synthetic readiness probes, validates
manifests, monitors the runtime without inspecting substantive outputs during
collection, and records technical incidents.

### Data Steward

The Data Steward verifies append-only storage, file and hash completeness,
namespace separation, wave freeze, and disclosure-safe release artifacts.

One person may perform multiple roles, but the execution authorization remains
an explicit human act and is never generated or enabled by automation.

## 3. Pre-wave sequence

Before every wave:

1. verify the published v2.0 version-specific DOI and protocol hash;
2. review official API Terms, research-use conditions, data controls, rate
   limits, billing state, and account standing for all four providers;
3. inspect official model catalogs and metadata;
4. have the Operations Lead select and attest the exact four model IDs and
   material settings in the private Provider Freeze Record;
5. run the fixed non-confirmatory synthetic readiness prompt once per lineage;
6. generate the deterministic manifest;
7. run structural and strict integrity validation;
8. verify the GCP controlled runtime, synchronized UTC clock, network, service
   account, disk capacity, permissions, and append-only `MIBO_DATA_ROOT`;
9. verify that the four API credentials are present without printing them;
10. build the private hash-bound execution bundle; and
11. have the Operations Lead review the hashes and complete the private
    execution-authorization record.

A failed check blocks the affected wave. It does not authorize model
substitution or a late change to the instrument.

## 4. Automated start

The systemd service may be enabled only after all pre-wave checks pass and the
execution sentinel is set. The controlled runtime waits against its synchronized
UTC clock and launches at the registered field start. GitHub Actions and Codex
automations may remind or monitor, but neither is the authoritative clock.

For a calibration wave, the runtime executes Window A Anchor rows during the
first 12 hours, standard rows during the 48-hour field window, and waits until
the registered Window B start before executing Window B Anchor rows.

## 5. Request execution

For every manifest row, the executor:

1. verifies the row's protocol, Query Form, model, freeze, and window identity;
2. sends the exact Query Form through the registered adapter and request profile;
3. archives the request payload minus credentials and the unmodified response;
4. records returned model metadata, timestamps, duration, usage, and hashes; and
5. marks the deterministic Attempt ID as processed.

The executor must not inspect answer content to choose a retry, model, provider,
or prompt. Content coding occurs only on a derived copy after the raw wave is
frozen.

## 6. Technical failures and retries

Retry eligibility is based only on the registered technical failure taxonomy.
The executor schedules at most two retries using the 10-minute and additional
30-minute minimum delays. A retry that would fall outside the row's registered
window is not submitted; the missingness remains visible.

HTTP 429 pauses the affected lineage until the eligible retry time. An apparent
service-wide 502/503/504 condition uses a controlled pause rather than repeated
submission of the queue. After retry exhaustion, the affected lineage may be
suspended with an append-only deviation record.

## 7. Monitoring boundary

During a field window, operational monitoring may inspect service status,
counts, timestamps, error classes, rate-limit state, disk health, and process
health. It must not inspect substantive outputs in order to modify collection.

A code repair during a wave requires stopping the affected execution path,
recording a deviation, deploying a new immutable commit, re-running technical
validation, and obtaining a new authorization. Previously retained attempts are
never overwritten.

## 8. Wave close

After the field window:

1. stop and disable the execution sentinel;
2. verify that no attempt remains active;
3. produce completion counts by lineage, Query Form, language, window, attempt,
   and status;
4. retain missing and failed cells without imputation;
5. generate the wave-level `SHA256SUMS.txt` and provenance record;
6. seal the raw wave tree against modification;
7. have the Operations Lead sign the completion record; and
8. create only disclosure-safe public summaries and hashes.

## 9. Security and account rules

API keys are stored only in the controlled private runtime with least-privilege
permissions. Keys, cookies, tokens, account credentials, private authorization
records, and raw responses must never be committed or pasted into public issues,
pull requests, logs, or Zenodo packages.

Retired credentials may remain undeleted only when they are clearly recorded as
retired and are absent from every active runtime configuration. Rotation must be
verified without printing secret values.
