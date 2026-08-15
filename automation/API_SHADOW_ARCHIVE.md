# MIBO API Shadow Archive v0.1

**Status:** exploratory auxiliary archive; not part of MIBO Core v1.0 confirmatory analyses  
**Canonical Core protocol:** DOI `10.5281/zenodo.21936410`

## Purpose

The API Shadow Archive captures a fully automated longitudinal API-side record alongside MIBO Core without changing the registered meaning of Ecological Live or the paired Live/Frozen confirmatory module.

The archive is deliberately separated from confirmatory Core data. It is intended for exploratory longitudinal analyses, engineering diagnostics, future hypothesis generation, and later protocol development.

## Frozen v0.1 shadow design

For each survey wave and each prospectively admitted API lineage:

- all 24 frozen MIBO query forms are administered;
- each query form receives `k = 10` independent stateless requests;
- requests use one prospectively frozen current API model per Service Lineage;
- the observation line is `ASH` (API Shadow, environment-closed);
- tools, retrieval, files, system/developer prompts, and conversation memory are disabled;
- Perplexity Sonar uses `web_search_options.disable_search = true` in the closed shadow condition;
- initial rows use the 48-hour standard (`STD`) field window;
- execution order is deterministically randomized from `SHA-256("MIBO-API-SHADOW-v0.1|<Wave ID>|<Site ID>")`;
- only registered technical failures are retry-eligible;
- no substantive answer is ever retried because of content;
- missing output is never imputed.

If all four lineages are admitted, one wave contains:

`4 lineages × 24 query forms × 10 replications = 960 initial API requests`.

## Scientific firewall

API Shadow observations MUST NOT be:

- labeled as Ecological Live;
- pooled into MIBO Core v1.0 confirmatory tests;
- used to retrospectively select a paired Live/Frozen model;
- used to change frozen Core hypotheses, thresholds, prompts, windows, or comparability decisions;
- used to choose a replacement model after inspecting outputs.

The shadow configuration is frozen prospectively in a separate `api_shadow_freeze.<wave>.json` record. A provider/model that is unavailable remains missing unless a prospective new shadow version is issued before affected outputs are inspected.

## Provider surfaces

The v0.1 implementation supports:

- OpenAI Responses API;
- Anthropic Messages API;
- Gemini `generateContent` API;
- Perplexity Sonar API with search disabled for the environment-closed shadow line.

The exact model identifier, request profile, access/Terms evidence, and verification timestamp are execution facts recorded in the shadow freeze file and are not hard-coded in source.

## Automation target

After the shadow freeze and human authorization are complete, the archive is intended to run unattended on the controlled Japan-site runtime:

`shadow freeze -> deterministic 960-row manifest -> exact-UTC wave wait -> API execution -> technical retries -> append-only raw archive -> SHA-256 -> structural QC -> shadow freeze record`

This auxiliary pipeline is operationally independent from the Ecological Live human-operated UI workflow and from the paired API confirmatory pipeline.
