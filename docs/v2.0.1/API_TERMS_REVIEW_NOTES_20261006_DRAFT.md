# API Terms/access source notes — DRAFT

Reviewed public sources on 6 October 2026 (JST). These notes are inputs to the
private per-wave review, not a completed eligibility or authorization record.
Account terms, billing, quota, regional availability and identifier stability
must be matched to the actual private runtime before eligibility is attested.

| Provider | Official source | Effective/updated date | Relevant source facts |
|---|---|---|---|
| OpenAI | https://openai.com/policies/services-agreement/ | Effective 1 January 2026 | Business/API integrations are covered; customer content is not used to improve services unless the customer explicitly agrees. Restrictions include competing-model training, unauthorized extraction and circumventing limits. |
| Anthropic | https://www.anthropic.com/legal/commercial-terms | Effective 17 June 2025 | These terms cover API keys. Customer content is not used for model training. Usage, supported-region and service-specific policies apply; competing services and reverse engineering are restricted. |
| Google | https://ai.google.dev/gemini-api/terms | Effective 23 March 2026 | Gemini paid-service status depends on the API key's project having active billing. Paid prompts/responses are not used to improve products; limited safety/legal retention remains. Unpaid use has different data-use terms. |
| Perplexity | https://www.perplexity.ai/en-GB/hub/legal/perplexity-api-terms-of-service | Updated 23 January 2026 | API services have separate terms; customer content is not used to train or improve generative models. Acceptable-use, quota and applicable third-party-model terms remain relevant. |

The Perplexity privacy page at
https://docs.perplexity.ai/docs/resources/privacy-security explicitly discusses
zero retention for Chat Completions. Do not generalize that statement to the
new Agent endpoint. Its explicit `store=false` control is not a deletion claim.

The procedure proposed here uses provider APIs on a private runtime, fixed
non-personal instrument content, no external tools or retrieval, and no model
training or account-limit evasion. Final private review must record the actual
applicable sources, acquisition timestamps and hashes, account/billing state,
adequate rate limits, material limitations, reviewer and eligibility decision.
No API key, account identifier, raw output or completed private approval belongs
in this public file.
