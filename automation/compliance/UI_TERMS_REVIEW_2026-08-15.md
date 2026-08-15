# MIBO Core v1.0 — Public UI Automation Terms Review

**Review date:** 2026-08-15  
**Scope:** Ecological Live observation through consumer/public web interfaces  
**Scientific protocol:** MIBO Core Protocol Package v1.0, DOI `10.5281/zenodo.21936410`

This is an operational compliance record, not legal advice. Provider terms can change. The applicable Terms/access review must be refreshed and time-stamped in the private Pre-Wave Configuration Freeze Record before W01.

## Result

**MIBO Core v1.0 must not use unattended browser bots, scraping, DOM extraction, or other non-human automation to collect Ecological Live outputs unless the relevant provider gives explicit permission that covers the intended research procedure.**

For first-year cross-service comparability, the default Ecological Live implementation is therefore **human-operated public UI observation with deterministic software assistance outside the provider interface**:

- software selects the registered next manifest row;
- software displays the exact frozen prompt and expected public-service condition;
- a human opens/uses a fresh provider session and submits the prompt;
- a human uses the provider's ordinary UI to copy the returned output;
- a human pastes that output into the local MIBO capture workstation;
- MIBO software time-stamps, hashes, stores, validates, and audits the capture;
- software never controls the provider webpage, scrapes the page, or programmatically extracts the output.

This boundary preserves the ecological public-interface condition without treating provider consumer interfaces as unofficial APIs.

## Provider review

### OpenAI / ChatGPT

Official source reviewed:  
`https://openai.com/policies/terms-of-use/`

Current Terms of Use (effective 2026-01-01) prohibit automatically or programmatically extracting data or Output from the consumer Services. The consumer ChatGPT interface therefore remains **human-operated** for MIBO Ecological Live unless OpenAI provides applicable explicit permission.

API collection is a separate observational condition governed by the applicable API/business terms and documentation; it must not be relabeled as ChatGPT Ecological Live.

### Anthropic / Claude

Official source reviewed:  
`https://www.anthropic.com/legal/consumer-terms`

Current Consumer Terms prohibit crawling, scraping, or harvesting data from the Services except as permitted, and—except via an Anthropic API key or where Anthropic explicitly permits it—prohibit accessing the Services through automated or non-human means such as a bot or script. Claude.ai Ecological Live therefore remains **human-operated** unless explicit permission is obtained.

### Google / Gemini

Official source reviewed:  
`https://policies.google.com/terms`

Google's Terms prohibit automated means of accessing service content when that access violates machine-readable instructions on Google's webpages. Because machine-readable instructions and service-specific conditions are time-sensitive, and because the other Core consumer interfaces currently prohibit the contemplated automation, MIBO v1.0 uses the same **human-operated UI rule** for Gemini Ecological Live unless an applicable explicit permission and current machine-readable-access review are documented before collection.

### Perplexity

Official source reviewed:  
`https://www.perplexity.ai/hub/legal/terms-of-service`

Current consumer Terms prohibit using robots, spiders, crawlers, scrapers, or other automated devices/processes/software/queries to monitor, extract, copy, or collect information or data from the Service, absent an applicable exception or written permission. Perplexity Ecological Live therefore remains **human-operated** unless written permission covering the research procedure is obtained.

Perplexity API terms are separate and do not convert API outputs into the Ecological Live public-interface condition.

## Operational rule for W01

1. The Ecological Live workstation MUST NOT contain browser-control code, selectors, DOM parsers, session-cookie automation, network interception, or automated output extraction.
2. The workstation MAY automate manifest selection, prompt display, timing validation, local capture, hashing, provenance, missingness, retry bookkeeping, and QC.
3. Copying the prompt into the provider UI and copying the output back into MIBO storage are explicit human actions.
4. A provider-specific exception may be enabled only after written/official permission is archived prospectively and the Operations Lead records the scope of the permission before any affected confirmatory output is inspected.
5. If terms change before or during a wave, the affected lineage is paused and the event is recorded; the software must not silently switch to an API or another observation surface.
