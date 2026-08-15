# Controlled Japan-site runtime — Ubuntu installation

This is the deployment path for the authoritative W01 runtime. It installs a commit-bound code snapshot for **MIBO Core paired API** and the optional **exploratory API Shadow Archive**, while leaving both execution paths disabled.

## 1. Machine baseline

Use a dedicated Ubuntu 24.04 LTS+ machine or VM at the Japan site with:

- Python 3.12+;
- Git and systemd;
- stable network access;
- UTC/NTP synchronization;
- encrypted persistent storage and backup for `/srv/mibo-data`;
- no unrelated automation sharing the MIBO provider credentials.

## 2. Check out the reviewed main commit

```bash
git clone https://github.com/mibo-research/mibo-core.git
cd mibo-core
git status --porcelain
git rev-parse HEAD
```

The working tree must be clean. Record the exact commit in the private Pre-Wave execution record.

## 3. Provision without enabling collection

```bash
sudo bash runtime/provision-ubuntu.sh
```

The provisioner:

- creates a dedicated `mibo` service account;
- creates `/opt/mibo-core`, `/srv/mibo-data`, `/srv/mibo-private`, and `/etc/mibo`;
- copies a clean runtime snapshot without `.git`, raw data, or secrets;
- runs frozen-config checks, Python compilation, all synthetic unit tests, and a 960-row synthetic API Shadow manifest validation;
- writes `INSTALL_PROVENANCE.json` with the exact source commit;
- writes `INSTALL_SHA256SUMS.txt` over the final installed runtime;
- installs `mibo-paired.service` and `mibo-shadow.service`;
- installs private environment templates only when the administrator has not already created them;
- verifies both systemd units;
- does **not** enable or start either service.

The safety defaults remain:

```text
MIBO_PROVIDER_EXECUTION=DISABLED
MIBO_API_SHADOW_EXECUTION=DISABLED
```

## 4. Finalize private records

Under `/srv/mibo-private`, prospectively complete the applicable W01 records:

- `ui_configuration.W01.json`;
- `operator_roster.W01.json`;
- `provider_freeze.W01.json`;
- optional `api_shadow_freeze.W01.json`.

Edit `/etc/mibo/mibo-prewave.env` with those paths and only the credentials actually required by eligible provider paths. Do not commit the completed records or keys.

## 5. Run one Pre-Wave command

```bash
set -a
source /etc/mibo/mibo-prewave.env
set +a
cd /opt/mibo-core
bash runtime/preflight.sh
```

This checks the installed snapshot hash/provenance, clock, disk, required credentials, Core API model evidence, manifests, and Pre-Wave bundle. If `MIBO_API_SHADOW_FREEZE` is set, it additionally checks Shadow provider/model evidence and builds the separate Shadow bundle.

Neither bundle authorizes collection.

## 6. Human authorization

Review and prospectively sign the applicable private authorization records.

For Core paired API, the final record must bind the exact paired manifest and provider freeze. Only after the Core Pre-Wave gate closes may `/etc/mibo/mibo-paired.env` be changed to:

```text
MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE
```

For API Shadow, the final record must additionally acknowledge `archive_class=exploratory_auxiliary` and `confirmatory_use=prohibited`. Only after its separate gate closes may `/etc/mibo/mibo-shadow.env` be changed to:

```text
MIBO_API_SHADOW_EXECUTION=ENABLED_AFTER_SHADOW_GATE
```

One sentinel never authorizes the other pipeline.

## 7. Arm the API services

After authorization, populate the exact manifest/freeze/authorization paths in the corresponding `/etc/mibo/*.env` file.

Core paired API:

```bash
sudo systemctl enable mibo-paired.service
sudo systemctl start mibo-paired.service
sudo systemctl status mibo-paired.service
```

Optional API Shadow:

```bash
sudo systemctl enable mibo-shadow.service
sudo systemctl start mibo-shadow.service
sudo systemctl status mibo-shadow.service
```

Both services can be armed before W01; the waiter processes remain idle until the frozen UTC wave start. GitHub Actions is not the authoritative scientific clock.

## 8. Ecological Live

Ecological Live remains a separate human-operated public-interface condition unless a provider-specific automation permission is prospectively archived. The API services must never be used as substitutes for missing Ecological Live observations.

## 9. Post-field

After the registered field closes, run Core structural QC/raw-wave freeze and the separate API Shadow QC/freeze if the Shadow archive was collected. Maintain the separate namespaces and analysis status throughout downstream work.
