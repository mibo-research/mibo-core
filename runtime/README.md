# Japan-site runtime

This directory contains a **fail-closed** runtime template for the MIBO Core paired API module. It is not the public-UI collector.

The service must run on a dedicated Japan-site machine or VM with synchronized UTC time. GitHub Actions is used for source control, CI and review, not as the authoritative scientific clock.

## Safety gates

Provider execution remains impossible unless all of the following are true:

1. the paired manifest passes structural and strict deterministic validation;
2. every row is cryptographically bound to the supplied Configuration Freeze Record;
3. the private execution-authorization record confirms the applicable Pre-Wave gates;
4. the authorization hashes match the exact manifest and freeze file;
5. the current time is inside the registered 48-hour primary field window; and
6. `MIBO_PROVIDER_EXECUTION=ENABLED_AFTER_PREWAVE_GATE` is set on the runtime machine.

The repository contains examples only. Completed authorization records, credentials, session material and raw outputs stay off public GitHub.

## Provider API surfaces

The implementation uses current provider primary API surfaces but never hard-codes W01 model IDs:

- OpenAI Responses API (`/v1/responses`), with `store=false` and no tools;
- Anthropic Messages API (`/v1/messages`), user message only and no tools;
- Gemini `generateContent`, user content only and no tools.

Exact model identifiers, output limits and any optional materially matched generation settings are frozen prospectively in the private provider Configuration Freeze Record. Perplexity is not an admissible v1 paired provider.

## Retry rule

Only technical failures are eligible. Retry 1 waits at least 10 minutes; Retry 2 waits at least an additional 30 minutes. A longer provider-mandated `Retry-After` extends, never shortens, the registered wait. Valid refusals, safety responses, nonanswers and clarification requests are retained as observations and are not retried.

## Raw data

Successful API calls are written append-only under:

`/srv/mibo-data/v1.0/<site>/<wave>/api_raw/`

Failures are stored separately. No file is silently overwritten. A wave-level SHA-256 manifest is generated at freeze time.
