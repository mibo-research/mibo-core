# Controlled-VM Gemini Standard restoration

Use only the controlled private VM. No live provider calls run in Codex or CI.
The prospective amendment is
https://github.com/mibo-research/mibo-core/blob/bc5976aefcc88429655384cd0b4db28ddc194561/docs/v2.0.4/AMENDMENT_v2.0.4.md.
Its public availability was verified at 2026-10-06T03:38:00.379Z.

## Stage the reviewed immutable source

Download `runtime/stage-and-start-core-v2-standard.sh` from the reviewed full Git
commit, verify its supplied SHA-256, and run it with that same full commit as the
sole argument. It creates a separate sealed `/opt/mibo-core-v2.0.4.*` snapshot
after running all synthetic tests without provider credentials. Existing three
provider services and installed source snapshots are not modified.

The private global anchor is
`/srv/mibo-private/MIBO2-W01-standard-runtime.json`. Repeating the installer reuses
the same snapshot, evidence directory and bounded block. It cannot reset probe
limits. Do not remove the anchor or any old Standard/Priority evidence.

## Preparation and human gate

The helper checks original sealed evidence, Terms/profile review, NTP, free disk,
the configured `MIBO_DATA_ROOT`, earlier waits and the absence of older Google
confirmatory attempts. It records the Tier 1 eligibility correction and hashes
the original Standard/Priority readiness history. It restores the exact earlier
Standard profile by omitting `service_tier`, with no model/settings substitution.

Only a new fixed non-confirmatory Standard readiness response may pass. A prior
Priority response processed at Standard cannot be reused. One probe and at most
two technical retries are allowed; waits are at least ten minutes and then an
additional thirty minutes, extended by any longer provider Retry-After. A failed
probe stops; rerun only at the displayed eligible time. A mismatch, interruption
or exhausted block requires review rather than another block.

After PASS the program displays the protocol, freeze, full manifest and bundle
hashes. The intended manifest has 1120 rows, with 280 Google rows authorized by
this scope. Review those concrete hashes and the unchanged field windows, then
enter the Operations Lead name and exactly `AUTHORIZE_GOOGLE_STANDARD`.

This explicit private human action is required by the Operations Manual, section
2: "execution authorization remains an explicit human act and is never generated
or enabled by automation." The earlier chat approval authorizes preparation and
configuration; it is not fabricated into a completed private execution record.

The helper starts only `mibo-core-v2-google-standard.service` after this gate.
Private credentials are copied only into its private environment file. Dormant
alternative Google services are disabled; active alternatives block migration.
The existing `mibo-core-v2-ready-three.service` is not stopped or replaced.

## Verify actual execution

The service must report `ActiveState=active` and `SubState=running`. Service
activation alone does not prove that a request was dispatched. The new source's
`runtime/status-core-v2-standard.py` reports actual first-dispatch UTC, saved
response counts and actual tier metadata without printing answers. Use the same
snapshot's `runtime/status-core-v2-scoped.py` to check the existing three-provider
collector. Resolve the installed source from the private Standard anchor.

Google data use `<MIBO_DATA_ROOT>/v2.0.4/JP01/MIBO2-W01`; other providers retain
their v2.0.2 namespaces. The wave still ends 8 October at 09:00 JST; WA closes
6 October at 21:00 and WB runs 7 October 09:00-21:00. Record actual times and
expired rows; do not shift windows, backfill, pool or relabel old records.
