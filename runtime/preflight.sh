#!/usr/bin/env bash
set -euo pipefail

: "${MIBO_DATA_ROOT:?Set MIBO_DATA_ROOT to the private research-data root}"
: "${MIBO_UI_CONFIGURATION:?Set MIBO_UI_CONFIGURATION to the finalized private UI configuration file}"
: "${MIBO_OPERATOR_ROSTER:?Set MIBO_OPERATOR_ROSTER to the finalized private operator roster file}"
: "${MIBO_PROVIDER_FREEZE:?Set MIBO_PROVIDER_FREEZE to the finalized private provider freeze file}"

WAVE="${MIBO_WAVE:-MIBO-W01}"
SITE="${MIBO_SITE:-JP01}"
BUNDLE_DIR="${MIBO_PREWAVE_BUNDLE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-prewave}"
API_EVIDENCE_DIR="${MIBO_API_EVIDENCE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-api-preflight}"

python3 automation/mibo_runner.py verify-config
python3 -m unittest discover -s automation/tests -v

python3 automation/runtime_health.py \
  --data-root "${MIBO_DATA_ROOT}" \
  --provider-freeze "${MIBO_PROVIDER_FREEZE}" \
  --out "/srv/mibo-private/${WAVE}-${SITE}-runtime-health.json"

API_ARGS=(
  --freeze "${MIBO_PROVIDER_FREEZE}"
  --out-dir "${API_EVIDENCE_DIR}"
  --catalog-all-present
)
if [[ "${MIBO_API_SMOKE_TEST:-DISABLED}" == "ENABLED_AFTER_TERMS_REVIEW" ]]; then
  API_ARGS+=(--smoke)
fi
python3 automation/api_preflight.py "${API_ARGS[@]}"

python3 automation/prewave_bundle.py \
  --wave "${WAVE}" \
  --site "${SITE}" \
  --ui-configuration "${MIBO_UI_CONFIGURATION}" \
  --operator-roster "${MIBO_OPERATOR_ROSTER}" \
  --provider-freeze "${MIBO_PROVIDER_FREEZE}" \
  --out-dir "${BUNDLE_DIR}"

printf '\nAPI readiness evidence created at: %s\n' "${API_EVIDENCE_DIR}"
printf 'Pre-Wave bundle created at: %s\n' "${BUNDLE_DIR}"

# API Shadow is exploratory auxiliary infrastructure and must never block Core
# collection merely because it is not configured. When a separate finalized
# shadow freeze is supplied, however, its own preflight/bundle is fail-closed.
if [[ -n "${MIBO_API_SHADOW_FREEZE:-}" ]]; then
  SHADOW_EVIDENCE_DIR="${MIBO_API_SHADOW_EVIDENCE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-api-shadow-preflight}"
  SHADOW_BUNDLE_DIR="${MIBO_API_SHADOW_BUNDLE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-api-shadow}"
  SHADOW_ARGS=(
    --freeze "${MIBO_API_SHADOW_FREEZE}"
    --out-dir "${SHADOW_EVIDENCE_DIR}"
  )
  if [[ "${MIBO_API_SHADOW_SMOKE_TEST:-DISABLED}" == "ENABLED_AFTER_TERMS_REVIEW" ]]; then
    SHADOW_ARGS+=(--smoke)
  fi
  python3 automation/shadow_preflight.py "${SHADOW_ARGS[@]}"
  python3 automation/shadow_bundle.py \
    --wave "${WAVE}" \
    --site "${SITE}" \
    --freeze "${MIBO_API_SHADOW_FREEZE}" \
    --preflight-report "${SHADOW_EVIDENCE_DIR}/API_SHADOW_PREFLIGHT_REPORT.json" \
    --out-dir "${SHADOW_BUNDLE_DIR}"
  printf 'API Shadow readiness evidence created at: %s\n' "${SHADOW_EVIDENCE_DIR}"
  printf 'API Shadow bundle created at: %s\n' "${SHADOW_BUNDLE_DIR}"
  printf 'API Shadow remains NOT authorized until its separate human authorization record is completed.\n'
else
  printf 'API Shadow not configured; Core Pre-Wave readiness is unaffected.\n'
fi

printf 'Collection is still NOT authorized. Complete and sign the applicable private authorization record(s) before enabling provider execution.\n'
