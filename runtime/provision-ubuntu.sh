#!/usr/bin/env bash
set -euo pipefail

# Provision the controlled MIBO Japan-site runtime without starting collection.
# Run from the repository root on Ubuntu 24.04+ as root/sudo.

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

for command in python3 git systemctl install cp find; do
  command -v "${command}" >/dev/null || { echo "Missing required command: ${command}" >&2; exit 1; }
done

python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required; found {sys.version.split()[0]}")
PY

if ! id "${MIBO_USER}" >/dev/null 2>&1; then
  if ! getent group "${MIBO_GROUP}" >/dev/null 2>&1; then
    groupadd --system "${MIBO_GROUP}"
  fi
  useradd --system --gid "${MIBO_GROUP}" --home-dir /var/lib/mibo --create-home --shell /usr/sbin/nologin "${MIBO_USER}"
fi

install -d -o root -g "${MIBO_GROUP}" -m 0755 "${INSTALL_ROOT}"
install -d -o "${MIBO_USER}" -g "${MIBO_GROUP}" -m 0700 "${DATA_ROOT}" "${PRIVATE_ROOT}"
install -d -o root -g "${MIBO_GROUP}" -m 0750 "${ETC_ROOT}"

# Install a clean code snapshot. Never copy .git, caches, local data or secrets.
find "${INSTALL_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a \
  "${REPO_ROOT}/automation" \
  "${REPO_ROOT}/runtime" \
  "${REPO_ROOT}/AGENTS.md" \
  "${REPO_ROOT}/PRE_WAVE1_EXECUTION_GATE.md" \
  "${INSTALL_ROOT}/"
find "${INSTALL_ROOT}" -type d -name '__pycache__' -prune -exec rm -rf -- {} +
chown -R root:"${MIBO_GROUP}" "${INSTALL_ROOT}"
find "${INSTALL_ROOT}" -type d -exec chmod 0755 {} +
find "${INSTALL_ROOT}" -type f -exec chmod 0644 {} +
chmod 0755 "${INSTALL_ROOT}"/runtime/*.sh 2>/dev/null || true

install -o root -g root -m 0644 "${REPO_ROOT}/runtime/mibo-paired.service" /etc/systemd/system/mibo-paired.service

if [[ ! -e "${ETC_ROOT}/mibo-paired.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 "${REPO_ROOT}/runtime/mibo-paired.env.example" "${ETC_ROOT}/mibo-paired.env"
fi
if [[ ! -e "${ETC_ROOT}/mibo-prewave.env" ]]; then
  install -o root -g "${MIBO_GROUP}" -m 0640 "${REPO_ROOT}/runtime/mibo-prewave.env.example" "${ETC_ROOT}/mibo-prewave.env"
fi

systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/mibo-paired.service >/dev/null

(
  cd "${INSTALL_ROOT}"
  python3 automation/mibo_runner.py verify-config
  python3 -m unittest discover -s automation/tests -v
)

# Deliberately do NOT enable/start mibo-paired.service and do NOT enable the
# MIBO_PROVIDER_EXECUTION sentinel. Human Pre-Wave authorization remains required.

echo
echo "MIBO Japan-site runtime provisioned, but collection remains DISABLED."
echo "Install root: ${INSTALL_ROOT}"
echo "Data root:    ${DATA_ROOT}"
echo "Private root: ${PRIVATE_ROOT}"
echo "Config root:  ${ETC_ROOT}"
echo
echo "Next: edit private configuration under ${PRIVATE_ROOT}/${ETC_ROOT}, run runtime/preflight.sh,"
echo "close the Pre-Wave-1 Execution Gate, and only then enable/start the paired service."
