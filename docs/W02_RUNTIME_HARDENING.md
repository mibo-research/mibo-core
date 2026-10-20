# W02 runtime hardening and acceptance

Engineering candidate prepared 10 October 2026. This changes software and
operational verification, not the registered scientific protocol. Source must be
reviewed and installed on the controlled VM before any live execution. No live
API calls, VM deployment or W01 data changes were performed by Codex.

## Registered target and scope

MIBO2-W02 runs **3 November 2026 09:00 JST–5 November 2026 09:00 JST**
(3 November 00:00 UTC–5 November 00:00 UTC). Its ordinary-wave manifest has
**960 initial logical cells: four lineages × 24 forms × 10 repetitions**;
240 per lineage, all STD. A retry is another attempt at one logical cell.

W01 used separate scientific namespaces: v2.0.2 for the initial three
providers and v2.0.4 for Google Standard. These versions describe participation
and processing conditions, not just software revisions. v2.0.4 authorizes only
Google; it does not authorize all four providers. W02 requires new, wave-bound
human freezes, readiness evidence and authorizations for the applicable scopes.
Existing W01 files or signatures cannot be recycled as W02 authorization.
Any changed model/profile/admission condition needs prospective human review
and, where scientifically material, a prospective protocol amendment.

**Prospective W02 scope review:** the current v2.0.2 three-provider gate
specifically requires a failed four-provider readiness report with deferred
Google HTTP503; v2.0.4 requires the separate Standard-restoration evidence.
These are W01 remediation conditions, not a general all-four-PASS admission
policy. If W02 readiness passes for all four, do not invent a503 or reuse W01
evidence to satisfy those gates. The approved v2.0.1 amendment already retains
the full four-lineage admission gate, Perplexity Agent CLOSED contract and
the twelve-wave schedule. It is an available software path for fresh all-four
readiness if the Operations Lead prospectively carries those registered
conditions into W02 and issues its new wave-bound freeze/authorization.
Disclose W02's chosen version and W01's mixed-version history; do not relabel
or automatically pool them. A changed scientific policy/profile requires a
new prospective amendment and matching software/schema support. This PR does
not make that choice for the Operations Lead. The full-size synthetic v2.0.1
rehearsal tests960-cell capacity and deterministic behavior, not live eligibility
of a particular W02 model.
The concrete proposal is [W02_SCOPE_DECISION_DRAFT.md](W02_SCOPE_DECISION_DRAFT.md);
it remains unapproved and does not enable collection.

## Evidence and repairs

The historical W01 facts below are disclosure-safe operator-reported evidence
from the earlier closure review, not a new inspection of the private VM.
Latent defects found in source are distinguished from incidents observed in W01.

| W01 evidence or discovered defect | Repair | Acceptance evidence |
|---|---|---|
| Google: 3/280 captures, 277 missing, seven HTTP503 failure attempts; process nevertheless reported success | Count logical cells, capture hashes and retained suspension independently of process exit; incomplete executor CLI exits 2 | Three captures plus `Result=success` produces SUSPENDED, not complete; full-size W02 produces 960/960 |
| W01 started after the planned time; the generic waiter previously deferred configuration checks until start | Validate bound W02 files, credentials, deterministic order, real authorization dates, VM, source, UTC clock, disk and service-user writes before waiting; repeat at dispatch | Stale W01, future/unsigned authorization, missing secret, wrong host, altered inputs/order, unknown NTP, sealed/aliased namespace and disk shortage rejected |
| Latent generic Type=oneshot startup timeout | Type=simple, unlimited startup wait, no automatic restart; Python bytecode disabled | Service-template and waiter tests; VM acceptance still required |
| Latent restart forgot suspension and provider pause | Restore technical failure/retry/suspension state from retained records | Restart after503 exhaustion sends no further affected-lineage requests; retained Retry-After/minimum delays preserved |
| Latent crash/concurrent dispatch could duplicate calls | Durable pre-dispatch claims and execution locks; ambiguous attempts hold their lineage | Crash before archival, raw-only capture, corrupt state, duplicate executor and interrupted retry-link writes tested |
| Latent version switching could replay an uncertain dispatch; clock rollback could shorten a retry wait | Cross-version lineage locks and retained-claim guards; recheck real UTC and pinned inputs before adapter dispatch | Nonoverlapping scopes can run; overlapping scopes/replay, clock backstep, input changes and close during durable writes rejected |
| A checksum alone does not prove that a capture belongs to the frozen request or started in its registered window | Bind new technical capture metadata to the regenerated row, HTTP status and request times; use a separate offline audit of retained technical envelopes | Wrong query/model/freeze identity, non-2xx capture, reversed times and early retry are rejected; completion after close is permitted when the request started within its registered window |
| Latent HTTP-date Retry-After was ignored | Parse date and round remaining seconds upward | Long provider wait extends minimum delay; out-of-window retry rejected |
| Latent installed-source verification accepted empty/partial/unsafe checksum lists | Validate complete source payload, hashes, commit and safe paths | Empty/partial manifests, uncovered code/bytecode, dirty provenance, links and path escapes rejected |
| W01 closure was tied to280 and calibration windows | Separate generic offline close derives counts from frozen manifest/scope, retains missingness, requires real terminal sign-off | W02 STD240/provider, incomplete captures, stopped collectors, candidate-export failures and archive integrity tested |
| W01 snapshots reached READY; restored contents had not been verified | Separate read-only verifier binds trusted receipt, archive and internal manifests; optionally compare restored tree | W01/W02 synthetic archive, corruption, omissions/extra files, links, unsafe members and restored-copy mismatch tested |

Google availability cannot be guaranteed by software. Suspended or ambiguous
execution remains visible and does not trigger model substitution, another
recovery block or missing-data replacement. Max two retries, minimum10 minutes
then an additional30 minutes, provider longer waits and registered windows stay
unchanged. Valid refusals/nonanswers remain observations.

New collectors retain the technical identity, HTTP status and timing needed for
content-blind restart/status verification alongside each raw-file checksum.
Older capture metadata that lacks this evidence is conservatively rejected by
the new collector; the retained response is never automatically resent or
rewritten. The separate offline audit can inspect historical technical envelope
fields without interpreting response text. W01 remains under its original
pinned collector and closure helper.

## Controlled-VM preparation

1. Preserve W01 originals, its pinned collector/closure sources and completion
   record. The historical completion signature predates independent snapshots;
   do not rewrite that fact. Keep boot/data snapshots and receipt digests.
2. Review this candidate's full Git commit and the staging script's SHA-256.
   On the SSH terminal of `mibo-runtime-jp01`, run the reviewed script with
   that commit and actual hostname:

   ```bash
   sudo bash stage-core-v2-w02.sh REVIEWED_FULL_40_HEX_COMMIT mibo-runtime-jp01
   ```

   The script fetches exactly that source, creates a separate source snapshot,
   runs synthetic tests without inherited credentials, validates W01 frozen
   manifests and writes source hashes/staging receipt. It does not install or
   start services, run readiness requests or create execution authorization.
   Record its new source path; use it as `W02_SOURCE` below. Failed candidates
   remain available for diagnosis; never point a collector at one.
3. On that VM, complete fresh W02 Terms/profile/model freeze and permitted fixed
   synthetic readiness checks. Use the generic `core_v2_preflight.py` and
   `core_v2_bundle.py --wave MIBO2-W02` interfaces for the registered protocol
   and scope. W01-specific restoration/preparation scripts are not W02 installers.
   Hash-bound authorization remains an explicit Operations Lead act. A readiness
   failure blocks its scope and does not select a replacement model.
4. Use separate W02 environment files and unit names for each authorized scope.
   Set W02 paths and identity explicitly; the historic generic environment
   example contains W01 placeholders. Required values include:

   | Variable | W02 value |
   |---|---|
   | `MIBO_CORE_V2_WAVE` | `MIBO2-W02` |
   | `MIBO_CORE_V2_PROTOCOL` / `FREEZE` / `MANIFEST` / `AUTHORIZATION` | Absolute paths to matching new W02 private files |
   | `MIBO_CORE_V2_SOURCE_COMMIT` | Full reviewed commit of installed candidate |
   | `MIBO_RUNTIME_HOST` | Actual controlled VM short hostname |
   | `MIBO_DATA_ROOT` | Existing private data mount, normally `/srv/mibo-data` |
   | `MIBO_CORE_V2_EXECUTION` | `ENABLED_AFTER_CORE_V2_GATE`, only after human authorization |
   | `PYTHONDONTWRITEBYTECODE` | `1` |
   | `MIBO_CORE_V2_SOURCE_ROOT` / `SERVICE` | Installed W02 source path / actual scope collector unit, for monitoring |

   Private files stay out of GitHub. Environment files are root-owned0600;
   frozen inputs must be readable by service user `mibo`. The data directory
   must be writable by `mibo`. Do not run a root readiness check and assume it
   proves service-user access.
5. Run `core_v2_prewave.py` as the actual service user with its private
   environment loaded through systemd; require strict runtime validation:

   Install the reviewed `mibo-core-v2-prewave@.service` template, then start
   `mibo-core-v2-prewave@INSTANCE.service` with the matching private
   `/etc/mibo/INSTANCE.env`. This loads the root-owned environment through
   systemd and runs the gate as `mibo`, without granting that user direct access
   to the0600 file. Check its exit status and retained journal report. The
   equivalent Python arguments, for a correctly provisioned environment, are:

   ```bash
   python3 -B "$W02_SOURCE/automation/core_v2_prewave.py" \
     --protocol "$MIBO_CORE_V2_PROTOCOL" --wave MIBO2-W02 --site JP01 \
     --manifest "$MIBO_CORE_V2_MANIFEST" --freeze "$MIBO_CORE_V2_FREEZE" \
     --authorization "$MIBO_CORE_V2_AUTHORIZATION" --data-root "$MIBO_DATA_ROOT" \
     --expected-host mibo-runtime-jp01 \
     --expected-source-commit "$MIBO_CORE_V2_SOURCE_COMMIT" --strict-runtime
   ```

   The command can pass before November3 using the real current clock. It makes
   zero provider calls and creates no observations. Do not simulate a future
   date to bypass field or authorization gates. Its report must show the intended
   panel960, each admitted lineage240, correct scope, source and registered times.

## Arm and monitor

Adapt the reviewed `runtime/mibo-core-v2.service` into new W02 scope units,
using the actual separate source snapshot in WorkingDirectory and ExecStart
and the matching W02 EnvironmentFile. Keep Type=simple, Restart=no,
TimeoutStartSec=infinity, strict host/source checks and `-B`. Existing W01
units remain disabled. Use `systemd-analyze verify` before enabling the W02
units. Start them before the field start and require:

- `ActiveState=active`, nonzero MainPID and `CORE_V2_PREWAVE=PASS` for every scope;
- no observation dispatch before3 November00:00 UTC;
- `CORE_V2_DISPATCH_GATE=PASS` and actual first-dispatch times after start;
- technical capture counts rather than `Result=success` as completion evidence.

Install the reviewed `mibo-core-v2-monitor@.service` and `.timer`. For each
collector, `/etc/mibo/INSTANCE.env` must contain its bound W02 paths plus
`MIBO_CORE_V2_SOURCE_ROOT` and `MIBO_CORE_V2_SERVICE`. Enable and start
`mibo-core-v2-monitor@INSTANCE.timer`; check its first journal report and timer
listing. It checks locally every five minutes, records attention reasons in the
VM journal, never calls providers and never restarts collectors. It does not
send notifications to a person. Monitor ATTENTION_REQUIRED, suspended lineages,
missing captures with inactive services, clock and storage problems.

`core_v2_status.py` is also available for read-only checks. Exit0 means the
authorized namespace scope is complete; exit2 means incomplete; exit1 means
unverified integrity. A complete Google-only namespace is not a complete wave:
inspect `completion_scope`, `intended_panel_cells`,
`registered_panel_fully_included` and the other scopes separately.

For a separate cross-namespace inspection, follow
[W02_AUDIT_TOOL.md](W02_AUDIT_TOOL.md). Supply the full registered baseline and
explicit authorized version/lineage assignments. The offline audit checks
technical raw-envelope fields and hashes, reports duplicate captures across
versions and distinguishes missing evidence from proven submission. It makes
no content-validity, comparability or independent-backup decision.

The VM, disks, network, clock synchronization and W02 units must remain running.
The operator's computer is not the scheduler. Check cloud restart/maintenance
settings and services after any reboot; unexpected uncertain claims require
human review, not automatic resend.

## Close, independent backup and restored-copy check

After5 November09:00 JST, stop and disable **every W02 collector scope**, then
verify MainPID0 and no collector/cgroup processes. Set each collector's private
`MIBO_CORE_V2_EXECUTION` environment value to `DISABLED` after stopping it and
retain the resulting configuration hash. This prevents an accidental manual
restart from leaving an armed execution sentinel. Run the new offline helper
first without `--close`, supplying the exact collector units:

```bash
sudo python3 -B "$W02_SOURCE/runtime/close-core-v2-wave.py" \
  --wave MIBO2-W02 --site JP01 --unit ACTUAL_W02_COLLECTOR_UNIT.service
```

Repeat `--unit` for multiple scopes. Confirm no overlapping scope and whole
panel inclusion; review captured/failed/unattempted/uncertain counts. Then use
the same command with `--close` and the real Operations Lead terminal sign-off.
Missing cells are retained. A verified candidate archive is made before original
closure writes. On any failure preserve the candidate and originals; inspect
partial closure instead of deleting files or resetting evidence to rerun.

Keep the returned receipt SHA-256 **outside the VM/export**. The helper records
the actual seal/signature times and only same-VM export verification. It does
not certify an independent backup. Create and verify independent backups of the
data and boot disks on the controlled cloud account; retain source-disk identity,
creation timestamps and READY state separately from the historical signature.

Restore the backup into an isolated, read-only verification environment. Supply
a dedicated restored root containing only the exported namespace/site/wave
trees (not unrelated waves or disk metadata). The verifier itself neither
extracts files nor rewrites originals:

```bash
python3 -B "$W02_SOURCE/automation/core_v2_archive_verify.py" \
  --archive /ABSOLUTE/COPY/MIBO2-W02-sealed.tar.gz \
  --receipt /ABSOLUTE/COPY/CLOSE_RECEIPT.json \
  --expected-receipt-sha256 INDEPENDENTLY_RETAINED_RECEIPT_SHA256 \
  --wave MIBO2-W02 --site JP01 \
  --restored-data-root /ABSOLUTE/DEDICATED/RESTORED_ROOT
```

Require archive PASS and restoration_check PASS, and separately verify cloud
backup provenance. A hash taken from the same untrusted export is not an
independent trust anchor. W01 can be checked with this read-only verifier and
its own receipt; its preserved close helper and sealed files remain unchanged.

## Acceptance still required on the actual VM

Local synthetic acceptance proves the software paths, not provider availability
or deployed state. Before W02, retain evidence for: reviewed installed source;
fresh authorized scopes and readiness; strict service-user prewave PASS;
armed units and first monitor report; durable data mount and backup restoration;
then actual dispatch, final logical-cell counts, seal and independent backup.
No item should be marked complete merely because the source PR exists.
