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

## Ecological Live public-interface rules
- Ecological Live is the registered public web-interface condition. Never substitute an API observation and label it Ecological Live.
- The dated UI Terms/access review is `automation/compliance/UI_TERMS_REVIEW_2026-08-15.md`; it must be refreshed during the Pre-Wave configuration freeze.
- Unless explicit provider permission covering the research procedure is prospectively archived, consumer/public interfaces are **human-operated**.
- Do not add browser-control code, headless-browser execution, selectors, DOM scraping, page-source parsing, network interception, cookie/session automation, or programmatic output extraction to the Ecological Live collector.
- Local software may select manifest rows, display exact prompts, enforce timing, record explicit human confirmations, receive human-pasted outputs, hash/store captures, schedule protocol-eligible retries, and perform QC.
- Any provider-specific exception requires an archived permission scope and a prospective Operations Lead decision before affected confirmatory output is inspected.

## Provider adapters
- Provider-specific API adapters remain disabled until the Pre-Wave Configuration Freeze Record names the exact eligible model/service identifiers and the Terms/access review is complete.
- Live API execution must occur only on the controlled private runtime, never in pull-request CI or the Codex maintainer workflow.
- Provider execution requires a finalized Configuration Freeze Record, a matching private execution-authorization record, the registered field window, and the explicit runtime execution sentinel.
- Every adapter must expose the exact request payload minus credentials, raw response, returned model metadata, timing, usage metadata if available, error records, and hashes.
- Paired API adapters must disable retrieval/tools and match material generation/reasoning settings as required by the v1.0 comparability rules.
- Exact model IDs and material request settings come from the prospectively frozen execution record; do not hard-code them in source.

## Retry and capture rules
- Only registered technical failures may trigger retries.
- Preserve the maximum of two retries: Retry 1 after at least 10 minutes; Retry 2 after at least an additional 30 minutes. A provider-mandated longer wait may extend but never shorten the interval.
- Calibration retries must remain inside their designated Window A or Window B; they may not be moved elsewhere in the 48-hour field window.
- Valid refusals, safety responses, nonanswers, or clarification requests are observations and must not be retried because of content.
- When a service-wide outage is apparent, pause the affected lineage and use one documented recovery block; do not repeatedly submit every intended observation.
- Raw capture is append-only. Never silently overwrite a retained response or failure record.

## Code review rules
- Flag any change that could alter the scientific estimand, prompt text, execution window, retry eligibility, missingness rule, or provider comparability after outcomes are observable.
- Flag any workflow that exposes secrets to untrusted PR code.
- Flag any browser automation or programmatic extraction added to Ecological Live without prospectively archived provider permission.
- Flag any GitHub Actions `schedule` as authoritative timing for scientific collection; GitHub scheduled events can be delayed. Scheduling may be used for reminders and preflight, not as the sole clock for registered windows.
