#!/usr/bin/env bash
set -euo pipefail

: "${MIBO_DATA_ROOT:?Set MIBO_DATA_ROOT to the private research-data root}"
: "${MIBO_UI_CONFIGURATION:?Set MIBO_UI_CONFIGURATION to the finalized private UI configuration file}"
: "${MIBO_PROVIDER_FREEZE:?Set MIBO_PROVIDER_FREEZE to the finalized private provider freeze file}"

WAVE="${MIBO_WAVE:-MIBO-W01}"
SITE="${MIBO_SITE:-JP01}"
BUNDLE_DIR="${MIBO_PREWAVE_BUNDLE_DIR:-/srv/mibo-private/${WAVE}-${SITE}-prewave}"

python3 automation/mibo_runner.py verify-config
python3 -m unittest discover -s automation/tests -v

python3 automation/runtime_health.py \
  --data-root "${MIBO_DATA_ROOT}" \
  --credential-env OPENAI_API_KEY \
  --credential-env ANTHROPIC_API_KEY \
  --credential-env GEMINI_API_KEY \
  --out "/srv/mibo-private/${WAVE}-${SITE}-runtime-health.json"

python3 automation/prewave_bundle.py \
  --wave "${WAVE}" \
  --site "${SITE}" \
  --ui-configuration "${MIBO_UI_CONFIGURATION}" \
  --provider-freeze "${MIBO_PROVIDER_FREEZE}" \
  --out-dir "${BUNDLE_DIR}"

printf '\nPre-Wave bundle created at: %s\n' "${BUNDLE_DIR}"
printf 'Collection is still NOT authorized. Complete and sign the Pre-Wave gate and private authorization record before enabling provider execution.\n'
