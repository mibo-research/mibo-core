#!/usr/bin/env bash
# Stage a reviewed candidate on the controlled VM. No readiness/provider calls,
# private credentials, execution authorization, or service installation/activation.
set -euo pipefail
umask 077

if [[ "$#" -ne 2 ]]; then
  echo "Usage: sudo bash runtime/stage-core-v2-w02.sh <reviewed-full-commit> <expected-VM-hostname>" >&2
  exit 2
fi
commit="$1"
expected_host="$2"
if [[ ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "A reviewed full lowercase 40-hex Git commit is required." >&2
  exit 2
fi
if [[ ! "$expected_host" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]]; then
  echo "An explicit controlled VM short hostname is required." >&2
  exit 2
fi
if [[ "$(hostname -s)" != "$expected_host" ]]; then
  echo "Wrong host: connect to the observation VM before staging; Cloud Shell is not the VM." >&2
  exit 1
fi
if [[ "$(id -u)" != 0 ]]; then
  echo "Run as root on the controlled VM." >&2
  exit 1
fi
if ! getent group mibo >/dev/null; then
  echo "The controlled runtime mibo group must already exist." >&2
  exit 1
fi
test -d /srv/mibo-private

git_safe() {
  env -i PATH="$PATH" LANG=C.UTF-8 GIT_TERMINAL_PROMPT=0 \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    git -c credential.helper= -c core.hooksPath=/dev/null "$@"
}
staging_tool=$(readlink -f -- "${BASH_SOURCE[0]}")
work=$(mktemp -d /srv/mibo-private/w02-stage.XXXXXX)
code=""
finish() {
  local result=$?
  trap - EXIT
  if [[ "$result" -ne 0 ]]; then
    printf 'exit_code=%s\nsource_commit=%s\nsource_candidate=%s\nservices_installed=false\nexecution_authorized=false\ndispatched_calls=0\n' \
      "$result" "$commit" "$code" > "$work/STAGING_FAILURE.txt"
  fi
  chown -R root:mibo "$work" || result=1
  chmod -R u=rwX,g=rX,o= "$work" || result=1
  if [[ -n "$code" ]]; then
    chown -R root:mibo "$code" || result=1
    chmod -R u=rwX,g=rX,o= "$code" || result=1
  fi
  if [[ "$result" -ne 0 ]]; then
    printf 'Staging stopped; retained private evidence: %s\nRetained source candidate: %s\n' "$work" "$code" >&2
  fi
  exit "$result"
}
trap finish EXIT
code=$(mktemp -d /opt/mibo-core-w02.XXXXXX)

git_safe init -q "$work/git"
git_safe -C "$work/git" \
  fetch -q --depth=1 https://github.com/mibo-research/mibo-core.git "$commit" \
  > "$work/source-fetch.log" 2>&1
if [[ "$(git_safe -C "$work/git" rev-parse FETCH_HEAD)" != "$commit" ]]; then
  echo "Fetched source does not match the reviewed commit." >&2
  exit 1
fi
git_safe -C "$work/git" archive FETCH_HEAD | tar -x -C "$code"

# A clean environment ensures synthetic checks cannot inherit provider keys or
# execution sentinels. No tests are run against installed W01 source or data.
(
  cd "$code"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B -m unittest discover -s automation/tests -v
) > "$work/synthetic-tests.log" 2>&1
(
  cd "$code"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/mibo_runner.py verify-config
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/mibo_runner.py generate-ui --wave MIBO-W01 --site JP01 --out "$work/W01-UI-synthetic.csv"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/mibo_runner.py validate "$work/W01-UI-synthetic.csv"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/manifest_integrity.py "$work/W01-UI-synthetic.csv"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/mibo_runner.py generate-paired --wave MIBO-W01 --site JP01 \
      --freeze automation/tests/provider_freeze.synthetic.json --lineage MIBO-SL-002 --lineage MIBO-SL-003 \
      --out "$work/W01-paired-synthetic.csv"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/mibo_runner.py validate "$work/W01-paired-synthetic.csv"
  env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    python3 -B automation/manifest_integrity.py "$work/W01-paired-synthetic.csv"
) > "$work/frozen-manifest-checks.log" 2>&1

env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
  python3 -B "$code/runtime/seal-installed-snapshot.py" --root "$code" --source-commit "$commit" \
  > "$work/installed-source-provenance.json"

env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
  python3 -B - "$code" "$work" "$commit" "$expected_host" "$staging_tool" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

source, private = Path(sys.argv[1]), Path(sys.argv[2])
commit, host = sys.argv[3], sys.argv[4]
sys.path.insert(0, str(source / "automation"))
import runtime_health

state = runtime_health.installed_snapshot_state(source)
if (not state or state.get("snapshot_integrity_pass") is not True
        or state.get("commit_sha") != commit):
    raise SystemExit("Staged source integrity or reviewed commit verification failed")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt = {
    "schema_version": "1.0",
    "staging_status": "SOURCE_VERIFIED_ONLY",
    "staged_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "controlled_vm_hostname": host,
    "candidate_source": str(source), "private_evidence": str(private),
    "source_commit_sha": commit,
    "staging_tool_sha256": digest(Path(sys.argv[5])),
    "installed_snapshot_integrity_pass": True,
    "install_sha256s_sha256": digest(source / "INSTALL_SHA256SUMS.txt"),
    "install_provenance_sha256": digest(source / "INSTALL_PROVENANCE.json"),
    "synthetic_tests_log_sha256": digest(private / "synthetic-tests.log"),
    "source_fetch_log_sha256": digest(private / "source-fetch.log"),
    "frozen_manifest_checks_log_sha256": digest(private / "frozen-manifest-checks.log"),
    "synthetic_manifest_sha256": {
        name: digest(private / name)
        for name in ("W01-UI-synthetic.csv", "W01-paired-synthetic.csv")
    },
    "services_installed": False, "execution_authorized": False,
    "provider_readiness_checks_performed": False, "dispatched_calls": 0,
    "W01_source_and_data_modified": False,
}
path = private / "W02_STAGING_RECEIPT.json"
with path.open("x", encoding="utf-8") as handle:
    json.dump(receipt, handle, indent=2, sort_keys=True)
    handle.write("\n")
receipt_sha = digest(path)
with (private / "STAGING_SHA256SUMS.txt").open("x", encoding="utf-8") as handle:
    for name in ("W02_STAGING_RECEIPT.json", "synthetic-tests.log",
                 "frozen-manifest-checks.log", "installed-source-provenance.json", "source-fetch.log",
                 "W01-UI-synthetic.csv", "W01-paired-synthetic.csv"):
        handle.write(digest(private / name) + "  " + name + "\n")
print("STAGING_SOURCE_INTEGRITY=PASS")
print("PRIVATE_SOURCE=" + str(source))
print("SOURCE_COMMIT=" + commit)
print("PRIVATE_TEST_LOG=" + str(private / "synthetic-tests.log"))
print("INSTALL_SHA256SUMS_SHA256=" + receipt["install_sha256s_sha256"])
print("PRIVATE_STAGING_RECEIPT=" + str(path))
print("STAGING_RECEIPT_SHA256=" + receipt_sha)
print("SERVICES_INSTALLED=false / EXECUTION_AUTHORIZED=false / DISPATCHED_CALLS=0")
PY
