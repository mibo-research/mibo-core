# Perplexity Agent transport review — DRAFT

Prepared: 6 October 2026 (JST).
Status: engineering preparation; not a scientific amendment, completed Terms
review, provider freeze, registration, or execution authorization.

## Why review is needed

The registered MIBO Core v2.0 protocol, section 4, explicitly requires
`web_search_options.disable_search=true`. The Agent API represents search
disablement by omitting search tools instead. Changing only a frozen model
string cannot migrate the request and response formats.

The new adapter is available as `perplexity_agent`, but the Core v2.0 freeze
validator continues to require `perplexity_sonar`. This PR does not admit the
Agent transport to any existing registered scientific executor. Private
candidate records must remain pending until prospective review is complete.

## Proposed request contract

- Exactly one explicit `perplexity/` model; no preset, saved provider profile,
  fallback model list, or automatic model selection.
- Exactly one user message with the unchanged query; no history or researcher
  system/developer instructions.
- Omit tools and skills; specify `tool_choice="none"` and `max_steps=1`.
- Set `stream=false`, `background=false`, and `store=false`.
- Preserve the frozen output budget and any explicitly frozen supported
  sampling/reasoning settings. Never migrate unsupported settings silently.
- Retain the exact credential-free request, raw response, response metadata,
  timing and usage through the existing adapter result interface.
- Require a completed response and the exact returned model ID. Reject
  reported tools, tool usage, enabled storage, continuation state, and output
  item types other than messages or reasoning. Retain mismatch responses as
  non-retryable technical failures; do not inspect answer words for eligibility.

The official `store=false` control hides responses from subsequent retrieval;
the documentation says it does not prevent use as a continuation source.
Absence of `previous_response_id` in each independent request is therefore
also required. This is not a claim of provider-side deletion.

## Decisions required before scientific admission

The Operations Lead must classify and prospectively date the transport change,
and approve a public amendment or future prospective protocol version that
explicitly describes the new search-disablement mechanism. Keep the original
v2.0 DOI record intact. Do not claim the new wire request meets the literal old
section 4 requirement.

Before enabling a scientific executor: complete the API Terms/access review;
verify the exact human-selected model through the private VM catalog; run one
fixed non-confirmatory smoke test on that VM; review the emitted payload and
returned environment metadata; deploy and hash an immutable reviewed code
commit; regenerate and validate the hash-bound freeze, manifest and bundle;
and obtain a new explicit human execution authorization. Existing authorizations
must not be rewritten or reused for changed hashes. Preserve all old records.

Keep the registered query hashes, panel, replication count, execution order,
retry rules and field windows intact. If the pre-wave requirements are not
complete in time, record the blocked start and obtain a prospective scheduling
decision; do not backdate readiness or silently move the registered windows.

## Official technical sources

- https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to
- https://docs.perplexity.ai/docs/agent-api/models
- https://docs.perplexity.ai/docs/agent-api/quickstart
- https://docs.perplexity.ai/api-reference/agent-post

Validation uses synthetic fixtures only. No live API call is made by the Codex
maintainer workflow. Readiness evidence and completed private records belong
only on the controlled research runtime.
