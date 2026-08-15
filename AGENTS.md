# AGENTS.md — MIBO Core automation rules

## Canonical scientific source
- The frozen scientific specification is **MIBO Core Protocol Package v1.0**, DOI `10.5281/zenodo.21936410`.
- Do not change fixed query wording, query hashes, panel membership, wave dates, hypotheses, thresholds, or comparability rules in an automation PR.
- A scientific change requires a prospective protocol version. Do not disguise it as a software fix.

## Codex role
- Codex is a **software-engineering and review agent**, not an adaptive scientific observer.
- Codex may implement, test, document, and review deterministic collectors, manifests, provider adapters, QC, and packaging.
- Codex must never decide which prompt to ask, rewrite a prompt, replace a missing observation, change a retry rule, or select a provider/model because of an observed answer.
- During an active wave, do not self-modify collection code. A technical repair requires a new commit hash and a recorded deviation.

## Data and secrets
- Never commit API keys, cookies, access tokens, session exports, account credentials, completed private authorization records, or restricted raw outputs.
- Tests use synthetic fixtures only and must not make live provider or UI calls.
- Raw observation data must be written to the configured research-data store, not to this public repository.
- Public GitHub artifacts should contain code, schemas, manifests, hashes, examples, and disclosure-safe summaries only.

## Engineering expectations
- Python code in `automation/` must use the standard library unless a dependency is explicitly justified.
- Run `python -m unittest discover -s automation/tests -v` before proposing a PR.
- Run W01 manifest generation and both structural and strict integrity validation before changing collection logic.
- Preserve deterministic seed formula: `SHA-256("MIBO-v1.0|<Wave ID>|<Site ID>|<Mode ID>")`, first eight hex characters interpreted as an integer.
- Preserve `k=10`, W01/W04/W07/W10 calibration windows, and the Ecological Live / Paired Live Reference / Frozen Reference separation.

## Provider adapters
- Provider-specific adapters remain disabled until the Pre-Wave Configuration Freeze Record names the exact eligible model/service identifiers and the Terms/access review is complete.
- Live provider execution must occur only on the controlled private runtime, never in pull-request CI or the Codex maintainer workflow.
- Provider execution requires a finalized Configuration Freeze Record, a matching private execution-authorization record, the registered field window, and the explicit runtime execution sentinel.
- Every adapter must expose the exact request payload minus credentials, raw response, returned model metadata, timing, usage metadata if available, error records, and hashes.
- Paired API adapters must disable retrieval/tools and match material generation/reasoning settings as required by the v1.0 comparability rules.
- Exact model IDs and material request settings come from the prospectively frozen execution record; do not hard-code them in source.

## Retry and capture rules
- Only registered technical failures may trigger retries.
- Preserve the maximum of two retries: Retry 1 after at least 10 minutes; Retry 2 after at least an additional 30 minutes. A provider-mandated longer wait may extend but never shorten the interval.
- Valid refusals, safety responses, nonanswers, or clarification requests are observations and must not be retried because of content.
- Raw capture is append-only. Never silently overwrite a retained response or failure record.

## Code review rules
- Flag any change that could alter the scientific estimand, prompt text, execution window, retry eligibility, missingness rule, or provider comparability after outcomes are observable.
- Flag any workflow that exposes secrets to untrusted PR code.
- Flag any GitHub Actions `schedule` as authoritative timing for scientific collection; GitHub scheduled events can be delayed. Scheduling may be used for reminders and preflight, not as the sole clock for registered windows.
