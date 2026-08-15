# MIBO-W01 automation runbook

Protocol DOI: `10.5281/zenodo.21936410`

## Before 31 August 2026 00:00 UTC / 09:00 JST
- close all applicable Pre-Wave-1 Execution Gate items;
- refresh the dated public-UI Terms/access review for ChatGPT, Claude, Gemini, and Perplexity;
- record exact service modes, account tiers, search/tool state, memory/personalization state, and locale for Ecological Live;
- keep `interaction_mode = human_only` for every Ecological Live lineage unless explicit provider permission covering the research procedure has been prospectively archived;
- freeze exact Paired Live and Frozen identifiers for every admitted API provider;
- freeze the materially matched provider request profile for every admitted pair;
- record comparability class;
- run synthetic dry-run tests only;
- record software commit and environment hash;
- generate UI and paired manifests;
- run both structural validation and `automation/manifest_integrity.py` strict deterministic identity validation;
- store final manifest SHA-256 hashes before observation.

A manifest must not be designated `MANIFEST_FROZEN` if either validator reports an error.

## 31 August 2026
- do not use confirmatory prompts for readiness testing;
- verify Japan-site UTC clock synchronization;
- verify append-only research-data storage;
- verify the human-operated Ecological Live workstation with non-confirmatory material only;
- verify that the UI workstation contains no browser-control, scraping, DOM extraction, cookie/session automation, or programmatic output-extraction path;
- finalize the private Ecological Live configuration record and set each ready lineage to `ready_human_operated` only after its Terms/access and configuration checks close;
- verify fresh-session procedure for all four public services;
- finalize the private paired-provider Configuration Freeze Record;
- generate the final paired manifest from that exact freeze record;
- generate the private paired execution-authorization record with the exact manifest and freeze SHA-256 values;
- set provider API credentials only on the private Japan-site runtime;
- after all applicable paired gates close, set `MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE`;
- start `mibo-paired.service`; it waits on the controlled runtime for the registered W01 UTC start;
- human Operations Lead authorizes W01.

The paired API runtime does **not** substitute for Ecological Live public-interface observations. Ecological Live remains a human-operated public-interface condition unless an explicit provider-specific automation permission has been prospectively archived.

## Ecological Live operator command

After the final UI manifest and private UI configuration record are frozen, the local workstation selects the next due row and handles local capture/provenance only:

```bash
python automation/ui_operator.py next \
  --manifest /srv/mibo-private/MIBO-W01-JP01-LUI.csv \
  --configuration /srv/mibo-private/ui_configuration.W01.json \
  --data-root /srv/mibo-data \
  --operator <OPERATOR_ID>
```

The operator must manually open the registered consumer/public interface, start a fresh session, submit the exact displayed prompt, use the provider's ordinary UI to copy the result, and paste it into the local MIBO capture workstation. The software must not control or scrape the provider webpage.

Progress can be inspected locally with:

```bash
python automation/ui_operator.py status \
  --manifest /srv/mibo-private/MIBO-W01-JP01-LUI.csv \
  --data-root /srv/mibo-data
```

## 1 September 2026
- 00:00 UTC / 09:00 JST: W01 field opens;
- the Japan-site paired service launches from the frozen UTC timestamp without GitHub-hosted scheduling;
- Window A lasts through 12:00 UTC / 21:00 JST;
- all ten English Anchor replications per service are collected in Window A for Ecological Live;
- each Ecological Live attempt uses a fresh human-operated public-interface session;
- each captured UI output is stored append-only with prompt hash, output hash, operator/timing metadata, and the frozen UI-configuration hash;
- standard non-anchor query forms may run elsewhere in the 48-hour field window;
- paired API Provider × Anchor Item blocks use the frozen model IDs, frozen request profile, and fixed harness;
- each paired 20-call block should complete within two hours; any excess is retained and logged as a timing deviation;
- valid refusals, safety responses, nonanswers, and clarification requests are observations and are never retried because of content;
- only registered technical failures may produce retry Attempt IDs.

For Window A failures, any retry must remain inside Window A. If the minimum retry delay would put the retry outside Window A, do not move it elsewhere in the 48-hour field window; retain the failure/missingness record.

## 2 September 2026
- 00:00–12:00 UTC / 09:00–21:00 JST: Window B;
- repeat all ten English Anchor Ecological Live replications per service using the same human-operated procedure;
- any Window B retry must remain inside Window B;
- paired API retries, if any, obey the registered technical-failure rule and remain inside the primary field window.

## Service-wide outage handling

When a service-wide UI outage is apparent:

- stop repeated submissions for the affected lineage;
- record the outage as a technical failure/deviation;
- the Operations Lead schedules one documented recovery block later inside the same registered observation window;
- the recovery uses a linked retry Attempt ID and must respect the registered minimum retry delay;
- never silently switch the lineage to an API or another observation surface.

## 3 September 2026
- 00:00 UTC / 09:00 JST: primary field window closes;
- do not schedule a primary paired retry whose due time falls outside the field window;
- complete structural QC, strict manifest checks, retry linkage, file hashes, missingness, and 5% operational audit;
- build the wave-level SHA-256 manifest;
- freeze raw wave package before substantive coding.
