#!/usr/bin/env bash
set -euo pipefail

: "${MIBO_DATA_ROOT:?Set MIBO_DATA_ROOT}"
: "${MIBO_CORE_V21_PROTOCOL:?Set the finalized prospectively registered protocol path}"
: "${MIBO_CORE_V21_FREEZE:?Set the finalized four-provider freeze path}"

WAVE="${MIBO_CORE_V21_WAVE:-MIBO2-W01}"
SITE="${MIBO_SITE:-JP01}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE="${MIBO_CORE_V21_EVIDENCE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-core-v21-preflight-${STAMP}}"
BUNDLE="${MIBO_CORE_V21_BUNDLE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-core-v21-bundle-${STAMP}}"

python3 -m unittest discover -s automation/tests -v

ARGS=(
  --protocol "${MIBO_CORE_V21_PROTOCOL}"
  --freeze "${MIBO_CORE_V21_FREEZE}"
  --out-dir "${EVIDENCE}"
)
if [[ "${MIBO_CORE_V21_SMOKE_TEST:-DISABLED}" == "ENABLED_AFTER_TERMS_REVIEW" ]]; then
  ARGS+=(--smoke)
fi
python3 automation/core_v21_preflight.py "${ARGS[@]}"
python3 automation/core_v21_bundle.py \
  --protocol "${MIBO_CORE_V21_PROTOCOL}" \
  --wave "${WAVE}" --site "${SITE}" \
  --freeze "${MIBO_CORE_V21_FREEZE}" \
  --preflight-report "${EVIDENCE}/CORE_V21_API_PREFLIGHT_REPORT.json" \
  --out-dir "${BUNDLE}"

printf 'Core v2.1 readiness evidence: %s\n' "${EVIDENCE}"
printf 'Core v2.1 hash-bound bundle: %s\n' "${BUNDLE}"
printf 'Execution remains disabled until the human authorization is completed and the dedicated sentinel is enabled.\n'
