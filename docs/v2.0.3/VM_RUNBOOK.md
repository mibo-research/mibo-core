# Google Priority: controlled VM operation

The approved prospective amendment is [AMENDMENT_v2.0.3.md](AMENDMENT_v2.0.3.md).
This adds only `service_tier="priority"` to the existing Google
`gemini-3.8-flash` profile. OpenAI, Anthropic and Perplexity continue under their
existing v2.0.2 authorization and sealed source. This procedure does not start
those three services if they have not already been authorized and started.

## Eligibility and evidence

Google documents Priority access for Tier 2 and Tier 3 projects. Priority costs
approximately 1.75–2 times Standard, and Google can automatically downgrade a
request to Standard. Billing activation alone does not establish the account's
Tier. See [Google's Priority documentation](https://ai.google.dev/gemini-api/docs/generate-content/priority-inference?hl=en).

No provider calls run in Codex or CI. On the controlled VM, one fixed synthetic
Google probe checks the exact model and the actual `x-gemini-service-tier`
response header. Only an actual `priority` response can pass the admission
gate. Standard or absent-header responses are preserved and stop admission;
they do not trigger another request. This is not a guarantee against 503 errors.

## Install and authorize

1. In the SSH terminal of `mibo-runtime-jp01`, download the reviewed
   `runtime/stage-and-start-core-v2-priority.sh` from its full immutable commit.
   Verify the supplied SHA-256 before executing it with that commit argument.
2. The script creates a separate sealed v2.0.3 snapshot, runs synthetic tests,
   checks the original Terms/profile evidence, and writes a private Google
   Priority freeze. It reads the configured `MIBO_DATA_ROOT` and does not edit
   the previous three-provider collector or its authorization.
3. The VM performs the single readiness probe. After PASS it prints the protocol,
   freeze, manifest and bundle hashes, the 280-row Google execution scope, and
   the original field windows.
4. Review that concrete bundle. The human Operations Lead enters their name
   and the literal phrase `AUTHORIZE_GOOGLE_PRIORITY` on `/dev/tty`. A private
   execution authorization is written only after this explicit human act.
5. The script starts `mibo-core-v2-google-priority.service` as user `mibo`, with
   `Restart=no`. The service survives SSH disconnection. Its exact unit file and
   hashes are preserved alongside the private authorization.

The final human entry follows Operations Manual v2.0 §2: execution authorization
remains an explicit human act and is never generated or enabled by automation.
Approval of the amendment alone does not fabricate a signed execution record.

## Failure and retry

The global private anchor `/srv/mibo-private/MIBO2-W01-priority-runtime.json`
pins one source snapshot and one recovery block. Running the same pinned command
again reuses this block; it never resets the probe limit.

For eligible technical failures there are at most two further manual probes:
at least 10 minutes after the first failure, then at least another 30 minutes,
with a longer provider Retry-After honored. Earlier Standard failures and
unexpired waits remain binding. A successful probe is reused without another
API request. An interrupted probe, exhausted block, missing actual Priority
header, conflicting Google collector, or older Google confirmatory attempt
stops this procedure for review. Do not rerun the exhausted old Standard helper.

After authorization, requests continue to ask for Priority. If Google returns
Standard during collection, the valid response and actual tier are recorded;
the client does not resubmit it or switch profiles to obtain a preferred answer.

## Status and analysis provenance

Read-only status:

```bash
sudo python3 -B - <<'PY'
import json,subprocess
from pathlib import Path
record=json.loads(Path('/srv/mibo-private/MIBO2-W01-priority-runtime.json').read_text())
subprocess.run(['python3','-B',str(Path(record['installed_source'])/'runtime/status-core-v2-priority.py')],check=True)
PY
```

The status helper prints service state, actual first Google dispatch time and
saved responses by actual processing tier. It does not print observed answers.
Service activation alone is not proof of an API dispatch.

The full intended manifest retains 1,120 rows; only the 280 Google rows are
authorized by v2.0.3. Logical attempt IDs, queries, hashes, order, seeds and
original windows are unchanged. The new Priority profile produces new protocol,
freeze and manifest hashes. A private full-wave mapping records the version
split; v2.0.2 three-provider records and v2.0.3 Google records are not automatically
pooled or relabeled as one homogeneous panel. Original missingness and prior
failed readiness probes remain preserved. Actual times are never backdated to
the planned 09:00 JST start.
