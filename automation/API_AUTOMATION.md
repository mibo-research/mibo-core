# Maximum safe API automation for MIBO Core v1.0

MIBO Core should automate every operation that can be automated **without changing the registered observational surface or introducing adaptive researcher discretion**.

## 1. What can be fully automated

### Paired API observation
The paired Live Reference / Frozen Reference module can be almost entirely unattended after the Pre-Wave gate closes:

- exact model-ID verification;
- provider availability checks;
- request-profile verification;
- deterministic manifest generation;
- exact execution order;
- fixed prompt submission;
- raw response and metadata capture;
- retry timing for technical failures only;
- outage pause/recovery records;
- SHA-256 hashing;
- structural QC;
- wave freeze.

The existing executor still requires a prospectively completed Configuration Freeze Record, private human authorization, the exact field window, credentials, and the explicit execution sentinel.

## 2. API preflight automation

`automation/api_preflight.py` reduces the remaining manual provider-verification work.

It uses official provider API surfaces to:

- fetch model-catalog metadata;
- verify exact prospectively frozen Live/Frozen IDs through model metadata endpoints where available;
- record timestamps and provider metadata;
- optionally run one fixed **non-confirmatory** synthetic smoke test per frozen model;
- hash all evidence files.

Supported catalog surfaces:

- OpenAI: `GET /v1/models`;
- Anthropic: `GET /v1/models`;
- Gemini API: `GET /v1beta/models`;
- Perplexity: `GET /v1/models` for operational catalog evidence only.

Perplexity remains non-admissible for the v1.0 paired module.

### Normal preflight

```bash
python automation/api_preflight.py \
  --freeze /srv/mibo-private/provider_freeze.W01.json \
  --out-dir /srv/mibo-private/MIBO-W01-JP01-api-preflight \
  --catalog-all-present
```

This performs metadata/catalog checks only. It does not generate model responses.

### Synthetic smoke test

After the dated API Terms/access review is complete:

```bash
export MIBO_API_SMOKE_TEST=ENABLED_AFTER_TERMS_REVIEW
python automation/api_preflight.py \
  --freeze /srv/mibo-private/provider_freeze.W01.json \
  --out-dir /srv/mibo-private/MIBO-W01-JP01-api-smoke \
  --catalog-all-present \
  --smoke
```

The smoke test uses a fixed non-confirmatory readiness prompt. It does not use any of the 24 registered query forms and is not a scientific observation.

## 3. What must never be automated adaptively

The automation may **verify**, but must not **decide**:

- which provider enters the paired module;
- which model is the Live Reference;
- which model is the Frozen Reference;
- whether a Class A/B comparability judgment is scientifically defensible;
- whether a failed provider should be replaced by another model;
- whether a substantive answer is “bad” and deserves a retry.

Those choices are either frozen scientific rules or prospectively documented human execution decisions.

## 4. Ecological Live remains distinct

The public consumer interface is the Ecological Live observational condition. An API output cannot be relabeled as Ecological Live.

Therefore the maximum safe automation strategy is:

```text
Ecological Live
human public-UI interaction
+ automated tasking/timing/capture/QC

Paired API
fully automated after human freeze/authorization
```

If provider-specific permission later allows compliant public-interface automation, that can be evaluated prospectively without changing the meaning of previously collected Ecological Live data.

## 5. Recommended W01 operating target

By 31 August 2026, the human workload should be reduced to:

1. finalize provider/UI configuration facts;
2. assign operators;
3. make the scientific comparability decision;
4. approve the execution gate;
5. perform the actual Ecological Live public-UI interactions.

Everything else—API availability evidence, manifests, Paired API collection, technical retries, raw capture, provenance, hashing, QC, and freezing—should be automated or machine-checked.
