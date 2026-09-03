#!/usr/bin/env bash
set -euo pipefail

# Provision the controlled MIBO Japan-site runtime without enabling collection.
# Run from a clean repository checkout on Ubuntu 24.04+ as root/sudo.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root, e.g. sudo bash runtime/provision-ubuntu.sh" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIBO_USER="${MIBO_USER:-mibo}"
MIBO_GROUP="${MIBO_GROUP:-mibo}"
INSTALL_ROOT="${MIBO_INSTALL_ROOT:-/opt/mibo-core}"
DATA_ROOT="${MIBO_DATA_ROOT:-/srv/mibo-data}"
PRIVATE_ROOT="${MIBO_PRIVATE_ROOT:-/srv/mibo-private}"
ETC_ROOT="${MIBO_ETC_ROOT:-/etc/mibo}"

for command in python3 git systemctl systemd-analyze install cp find getent groupadd useradd; do
  command -v "${command}" >/dev/null || {
    echo "Missing required command: ${command}" >&2
    exit 1
  }
done

python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required; found {sys.version.split()[0]}")
PY

SOURCE_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
  echo "Refusing to provision from a dirty Git working tree." >&2
  exit 1
fi

if ! getent group "${MIBO_GROUP}" >/dev/null 2>&1; then
  groupadd --system "${MIBO_GROUP}"
fi
if ! id "${MIBO_USER}" >/dev/null 2>&1; then
  useradd --system --gid "${MIBO_GROUP}" --home-dir /var/lib/mibo \
    --create-home --shell /usr/sbin/nologin "${MIBO_USER}"
fi

install -d -o root -g "${MIBO_GROUP}" -m 0755 "${INSTALL_ROOT}"
install -d -o "${MIBO_USER}" -g "${MIBO_GROUP}" -m 0700 "${DATA_ROOT}"
install -d -o root -g "${MIBO_GROUP}" -m 0750 "${PRIVATE_ROOT}" "${ETC_ROOT}"

# Install a clean code snapshot. Never copy .git, raw data, private config, or secrets.
find "${INSTALL_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a \
  "${REPO_ROOT}/automation" \
  "${REPO_ROOT}/runtime" \
  "${REPO_ROOT}/AGENTS.md" \
  "${REPO_ROOT}/PRE_WAVE1_EXECUTION_GATE.md" \
  "${INSTALL_ROOT}/"
find "${INSTALL_ROOT}" -type d -name '__pycache__' -prune -exec rm -rf -- {} +

# Verify the installed code before it is sealed. Tests are synthetic and make no live calls.
(
  cd "${INSTALL_ROOT}"
  python3 automation/mibo_runner.py verify-config
  python3 -m py_compile automation/*.py
  python3 -m unittest discover -s automation/tests -v
  python3 automation/shadow_runner.py generate \
    --wave MIBO-W01 --site JP01 \
    --freeze automation/tests/api_shadow_freeze.synthetic.json \
    --out /tmp/mibo-provision-shadow.csv
  python3 automation/shadow_runner.py validate /tmp/mibo-provision-shadow.csv \
    --freeze automation/tests/api_shadow_freeze.synthetic.json
  rm -f /tmp/mibo-provision-shadow.csv
)
find "${INSTALL_ROOT}" -type d -name '__pycache__' -prune -exec rm -rf -- {} +

# Seal the installed snapshot with source commit provenance and file hashes.
SOURCE_COMMIT="${SOURCE_COMMIT}" INSTALL_ROOT="${INSTALL_ROOT}" python3 - <<'PY'
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["INSTALL_ROOT"])
provenance = {
    "schema_version": "1.0",
    "source_commit_sha": os.environ["SOURCE_COMMIT"],
    "installed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "source_worktree_clean": True,
    "collection_enabled_by_provisioner": False,
    "installed_services": ["mibo-paired.service", "mibo-shadow.service", "mibo-core-v2.service"],
}
(root / "INSTALL_PROVENANCE.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
entries = []
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.name == "INSTALL_SHA256SUMS.txt":
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(f"{digest}  {path.relative_to(root).as_posix()}")
(root / "INSTALL_SHA256SUMS.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
PY

chown -R root:"${MIBO_GROUP}" "${INSTALL_ROOT}"
find "${INSTALL_ROOT}" -type d -exec chmod 0755 {} +
find "${INSTALL_ROOT}" -type f -exec chmod 0644 {} +
chmod 0755 "${INSTALL_ROOT}/runtime/"*.sh 2>/dev/null || true

# Install environment templates only when the administrator has not already supplied one.
if [[ ! -e "${ETC_ROOT}/mibo-prewave.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 \
    "${INSTALL_ROOT}/runtime/mibo-prewave.env.example" "${ETC_ROOT}/mibo-prewave.env"
fi
if [[ ! -e "${ETC_ROOT}/mibo-paired.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 \
    "${INSTALL_ROOT}/runtime/mibo-paired.env.example" "${ETC_ROOT}/mibo-paired.env"
fi
if [[ ! -e "${ETC_ROOT}/mibo-shadow.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 \
    "${INSTALL_ROOT}/runtime/mibo-shadow.env.example" "${ETC_ROOT}/mibo-shadow.env"
fi
if [[ ! -e "${ETC_ROOT}/mibo-core-v2.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 \
    "${INSTALL_ROOT}/runtime/mibo-core-v2.env.example" "${ETC_ROOT}/mibo-core-v2.env"
fi

install -o root -g root -m 0644 \
  "${INSTALL_ROOT}/runtime/mibo-paired.service" /etc/systemd/system/mibo-paired.service
install -o root -g root -m 0644 \
  "${INSTALL_ROOT}/runtime/mibo-shadow.service" /etc/systemd/system/mibo-shadow.service
install -o root -g root -m 0644 \
  "${INSTALL_ROOT}/runtime/mibo-core-v2.service" /etc/systemd/system/mibo-core-v2.service
install -o root -g root -m 0755 \
  "${INSTALL_ROOT}/runtime/mibo-set-core-v2-api-key" /usr/local/sbin/mibo-set-core-v2-api-key

systemd-analyze verify /etc/systemd/system/mibo-paired.service
systemd-analyze verify /etc/systemd/system/mibo-shadow.service
systemd-analyze verify /etc/systemd/system/mibo-core-v2.service
systemctl daemon-reload

# Safety assertion: provisioning itself must never arm any API executor.
grep -q '^MIBO_PROVIDER_EXECUTION=DISABLED$' "${ETC_ROOT}/mibo-paired.env" || {
  echo "Expected paired execution to remain DISABLED after provisioning." >&2
  exit 1
}
grep -q '^MIBO_API_SHADOW_EXECUTION=DISABLED$' "${ETC_ROOT}/mibo-shadow.env" || {
  echo "Expected API Shadow execution to remain DISABLED after provisioning." >&2
  exit 1
}
grep -q '^MIBO_CORE_V2_EXECUTION=DISABLED$' "${ETC_ROOT}/mibo-core-v2.env" || {
  echo "Expected Core v2 execution to remain DISABLED after provisioning." >&2
  exit 1
}

echo "MIBO Japan-site runtime provisioned from commit ${SOURCE_COMMIT}."
echo "Installed snapshot: ${INSTALL_ROOT}"
echo "Private configuration: ${PRIVATE_ROOT} and ${ETC_ROOT}"
echo "Research data: ${DATA_ROOT}"
echo "Paired, API Shadow, and Core v2 collection all remain disabled and were not started."
