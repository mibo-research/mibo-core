# Private VM: v2.0.2 lineage admission

The immutable amendment is
https://github.com/mibo-research/mibo-core/blob/71bd6cf4c3267ddf655eed21935837b19d54b030/docs/v2.0.2/AMENDMENT_v2.0.2.md.
It was publicly verified at 2026-10-06T01:48:39.132Z. It supplements the prior
registrations; no new Zenodo DOI is asserted.

## Start the reviewed three-provider scope

On the controlled private VM, run the pinned, SHA256-verified
runtime/stage-and-start-core-v2-scoped.sh with its reviewed full commit SHA.
It installs a separate sealed snapshot, runs only synthetic tests, verifies the
old sealed source and all retained readiness evidence, carries unchanged human
profiles into the new registered version, and builds a complete 1120-row bundle.
It sends no new provider readiness prompt.

Review the displayed exact hashes and 840-row admission scope. At the private
terminal, enter the Operations Lead's name and AUTHORIZE_READY_THREE only if
authorizing that concrete bundle. An empty or wrong response stops execution.
The original authorization and service remain intact. The new service is
mibo-core-v2-ready-three.service, running as mibo and surviving SSH disconnects.
It waits for the original Window B without a systemd startup timeout. It never
requests a Google credential for the three-provider process and filters Google
before constructing its execution/retry queue.

Private records are under /srv/mibo-private/scoped-ready.*/readiness/.
RUNTIME_LINK.json identifies the actual source and data root. Scope admission,
executor activation and per-lineage first dispatch are append-only in the new
v2.0.2 namespace. First dispatch timestamps identify the call to the adapter;
provider request/response times are retained in each response envelope. Initial
preparation files keep observation start null until submission occurs; a service
activation record alone is never called an observation.

Run runtime/status-core-v2-scoped.py from the same sealed snapshot as root to
display actual start timestamps and saved counts without printing answers.

## Google: fixed recovery and a separate human join

Use the installed_source and readiness paths from RUNTIME_LINK.json, not a new
checkout and not an edit to the active collector. Run:

    sudo python3 -B <installed_source>/runtime/admit-core-v2-google.py --readiness <readiness>

Each manual invocation makes at most one fixed non-confirmatory Google call.
The new, explicitly documented recovery block honors prior Retry-After and a
minimum ten-minute wait since earlier Google failures. It allows one new probe
and at most two technical retries, at least ten minutes and then an additional
thirty minutes apart, within the original field window. An interrupted probe,
non-retryable failure, model mismatch, passing probe or exhaustion prevents more
calls. It does not reset confirmatory retries, erase old recovery failures or
repeatedly submit the 280 intended Google observations.

A PASS builds an unsigned Google-only 280-row scope whose full 1120-row manifest
hash is identical to the initial bundle. It never starts collection. Review the
printed passed-probe path and then run:

    sudo python3 -B <installed_source>/runtime/admit-core-v2-google.py --readiness <readiness> --authorize-passed-probe <passed_probe>

Review the hashes and Google-only scope; enter the Operations Lead's name and
AUTHORIZE_GOOGLE_JOIN. This creates mibo-core-v2-google.service separately, using
the same sealed code, unchanged freeze and unchanged full manifest. The active
three-provider service and its initial authorization remain intact.

Expired Window A rows are archived as uncollected, without sending their query.
Other rows can be submitted only inside their original bounds. If Google never
joins, its 280 rows remain in the full manifest as missing at closure. Pending
rows during open windows must not be reported as final missingness. Closure/QC
uses the full intended denominator and discloses provider/window missingness;
scope readiness alone does not certify statistical eligibility.

## Stop and review conditions

A retained confirmatory attempt from v2.0 or v2.0.1 blocks this migration. Failed
hash checks, changed settings, an already-running incompatible service or an
unsynchronized VM clock also stop preparation. A repeated first-start command
must not overwrite an existing service or authorization. If a service start
fails after human authorization, preserve its concrete private records and
inspect that exact service; do not create a new authorization to hide the failure.

All provider calls are restricted to this private VM. Codex and repository CI
run synthetic tests only. No credentials, human private authorization, raw
outputs or private readiness responses belong in the public repository.
