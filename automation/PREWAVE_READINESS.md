# MIBO Core v1.0 — W01 Pre-Wave readiness workflow

This workflow is executed on the controlled Japan-site runtime after the scientific protocol has already been frozen. It creates a **private execution bundle**; it does not authorize data collection.

## Inputs that humans must finalize prospectively

### Ecological Live configuration

Start from `automation/config/ui_configuration.example.json` and record, for every Core lineage:

- `status = ready_human_operated` only after readiness is confirmed;
- `interaction_mode = human_only` unless an explicit provider permission is archived;
- current Terms/access review date and source;
- dedicated account tier;
- displayed/registered mode;
- search/tool state;
- memory/personalization state;
- locale; and
- `frozen_at_utc`.

### Paired provider Configuration Freeze

Start from `automation/config/provider_freeze.example.json`. For every candidate, record the final status. Every provider marked `eligible` must include:

- exact Paired Live Reference model ID;
- exact Frozen Reference model ID;
- final comparability Class A or B;
- dated model/version evidence;
- `verified_at_utc`;
- current Terms/access review date and source; and
- the frozen request profile, including output limit and any materially matched sampling/reasoning settings.

Do not promote a provider after confirmatory outputs are inspected.

## Controlled runtime checks

`automation/runtime_health.py` records:

- Git commit SHA and whether the working tree is clean;
- Python/platform information;
- disk capacity;
- NTP synchronization where `timedatectl` is available; and
- only the **presence**, never the values, of credentials required by providers actually frozen as eligible.

A missing NTP system check requires an independent documented clock check; an explicit `NTPSynchronized=no` fails readiness.

## Build the private bundle

The bundle builder:

1. revalidates all frozen machine-readable scientific configuration;
2. validates all four Ecological Live lineages as ready under the private UI configuration;
3. validates dated evidence for every eligible paired provider;
4. deterministically generates the W01 UI manifest;
5. generates the paired manifest only for prospectively eligible lineages;
6. runs structural and strict deterministic identity validation;
7. copies the exact private configuration records into the bundle;
8. computes SHA-256 for every bundle file; and
9. creates an authorization template with every human gate still set to **false**.

Example:

```bash
python automation/prewave_bundle.py \
  --wave MIBO-W01 \
  --site JP01 \
  --ui-configuration /srv/mibo-private/ui_configuration.W01.json \
  --provider-freeze /srv/mibo-private/provider_freeze.W01.json \
  --out-dir /srv/mibo-private/MIBO-W01-JP01-prewave
```

The resulting directory contains:

```text
configuration/
  ui_configuration.json
  provider_freeze.json
manifests/
  MIBO-W01-JP01-LUI.csv
  MIBO-W01-JP01-PAIRED.csv   # only when at least one lineage is eligible
PREWAVE_BUNDLE_REPORT.json
execution_authorization.PAIRED.template.json
SHA256SUMS.txt
```

If fewer than two paired lineages are eligible, the bundle explicitly reports that the first-year primary paired hypothesis set is not fully ready and must be prospectively reduced/classified according to the frozen SAP. Ecological Live can still proceed if its own gates are closed.

## One-command private-runtime preflight

After setting the three private paths and eligible provider API keys in the runtime environment:

```bash
export MIBO_DATA_ROOT=/srv/mibo-data
export MIBO_UI_CONFIGURATION=/srv/mibo-private/ui_configuration.W01.json
export MIBO_PROVIDER_FREEZE=/srv/mibo-private/provider_freeze.W01.json

bash runtime/preflight.sh
```

The script runs tests, records runtime health, and builds the private Pre-Wave bundle.

**It still does not authorize collection.**

The Operations Lead/PI must complete the applicable `PRE_WAVE1_EXECUTION_GATE.md`, review the hashes, complete the private authorization record, and only then enable the paired runtime execution sentinel.
