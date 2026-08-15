# Controlled Japan-site runtime — Ubuntu installation

This is the deployment path for the authoritative W01 runtime. Provisioning installs a commit-bound code snapshot and **does not enable collection**.

## 1. Prepare the machine

Recommended baseline:

- dedicated Ubuntu 24.04 LTS machine or VM physically/logically located at the Japan site;
- Python 3.12+;
- Git and systemd;
- reliable wired/network connection;
- UTC/NTP synchronization;
- encrypted persistent storage and backup for `/srv/mibo-data`;
- no unrelated automation sharing the provider accounts used for MIBO.

## 2. Check out the reviewed commit

On the machine, clone `mibo-research/mibo-core` and check out the exact reviewed commit intended for W01. The source working tree must be clean.

```bash
git status --porcelain
git rev-parse HEAD
```

Record the commit in the private Pre-Wave execution record.

## 3. Provision without enabling collection

From the clean repository checkout:

```bash
sudo bash runtime/provision-ubuntu.sh
```

The script:

- creates the `mibo` service user;
- creates `/opt/mibo-core`, `/srv/mibo-data`, `/srv/mibo-private`, and `/etc/mibo`;
- installs a clean code snapshot without `.git`, caches, raw data, or secrets;
- writes `INSTALL_PROVENANCE.json` with the source commit;
- writes `INSTALL_SHA256SUMS.txt` for the installed runtime snapshot;
- installs but does not start `mibo-paired.service`;
- installs private environment templates if they do not already exist;
- validates the systemd unit, frozen machine-readable protocol configuration, and unit tests.

Provisioning deliberately leaves `MIBO_PROVIDER_EXECUTION=DISABLED`.

## 4. Populate private configuration

Create/finalize under `/srv/mibo-private`:

- `ui_configuration.W01.json`;
- `operator_roster.W01.json`;
- `provider_freeze.W01.json`.

Edit `/etc/mibo/mibo-prewave.env` so the paths point to those exact files. Add only the API credentials required by providers prospectively frozen as paired-eligible.

Do not commit these completed private records or credentials to the public repository.

## 5. Run the Pre-Wave preflight

Load the private environment and run:

```bash
set -a
source /etc/mibo/mibo-prewave.env
set +a
cd /opt/mibo-core
bash runtime/preflight.sh
```

The runtime-health check verifies the installed code snapshot against `INSTALL_SHA256SUMS.txt`, records the source commit from `INSTALL_PROVENANCE.json`, checks disk/clock status, and records only credential presence, never credential values.

The Pre-Wave bundle remains unauthorized by construction.

## 6. Human authorization

Review:

- `PRE_WAVE1_EXECUTION_GATE.md`;
- runtime-health report;
- Pre-Wave bundle report and SHA-256 manifest;
- UI configuration and operator roster;
- provider Configuration Freeze and evidence;
- synthetic dry-run results.

Complete and sign the private authorization record prospectively. Only after all applicable gates close may the paired execution sentinel be changed to:

```text
MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE
```

## 7. Arm the paired runtime

Copy the final manifest/freeze/authorization paths into `/etc/mibo/mibo-paired.env`, then:

```bash
sudo systemctl enable mibo-paired.service
sudo systemctl start mibo-paired.service
sudo systemctl status mibo-paired.service
```

Starting before W01 is allowed after authorization: `wave_waiter.py` remains idle until the exact frozen W01 UTC start. GitHub Actions is not in the authoritative scientific timing path.

## 8. Ecological Live operators

The human-operated Ecological Live workstation may run on controlled operator terminals that have the exact same reviewed code and access to the private manifest/configuration/roster and append-only data root. Each operator supplies their frozen operator ID; the software rejects unassigned service lineages.

Consumer provider webpages remain human-operated. The workstation does not automate browser interaction or extraction.
