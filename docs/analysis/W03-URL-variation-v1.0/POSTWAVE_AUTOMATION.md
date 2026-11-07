# W03 automatic technical QC comparison and manuscript preparation

This prospective implementation note adds an offline postwave workflow to the
W03 derivative analysis registered on 7 November 2026. It preserves the
registered collection dates, fixed questions, four requested deployments,
960-slot full matrix, 80-slot I03 subset, primary measures, n ≥ 8 contrast rule,
technical-only retries and whole-response leave-one-out sensitivity.

The PI's actual instruction authorizing automatic technical QC, W02 comparison
and manuscript preparation is retained privately. No additional human case
grading or model/API semantic grading is performed. No future observations,
completed authorization records, credentials or raw answers are published here.

## When the workflow runs

The frozen collector's `OnSuccess` and `OnFailure` hooks request the separate
`mibo-w03-postwave.service`. Before the registered start, it returns a waiting
status without reading W03 response data. While the collector is active it
waits. An inactive collector with the complete 960-slot matrix can be processed
immediately. An incomplete matrix is retained until the registered window closes.

A persistent deadline timer requests the same service on 3 December 2026 at
00:05 UTC (09:05 JST), including after a missed trigger during a VM outage.
Postwave operational failures retry at 15-minute intervals, at most six starts
within six hours. These retries do not make provider calls or retry observations.
The completion marker prevents repeat generation; its archived hashes are
checked rather than silently overwriting completed results.

The collector's Python source, manifest, protocol, model freeze and execution
authorization remain unchanged. The service hook is an additive systemd unit
drop-in installed before W03 begins. The existing waiter is not restarted by
installation of the postwave workflow.

## Data protection and technical QC

The process uses the original `d970efab834f193b7f3d12ecded20be6f0e8f445` Core
runtime and validates its installed snapshot. It acquires the same four W03
lineage locks as the collector, confirms that no collector remains active, and
copies the raw wave into a new private run directory. It checks every copied
file hash and verifies that the source file set and bytes remain unchanged.
Symlinks, hard links and special files are rejected.

This is an **automatically sealed derivative snapshot**. It does not represent
a future-data human review or a human-signed native Core closure. No terminal
confirmation is synthesized and no old PI sign-off is relabelled. Original
responses, failures and capture metadata are not rewritten.

The existing content-blind Core audit accounts for all 960 logical slots and
checks the frozen identities, capture hashes, execution windows and retry
evidence. Unknown submissions and technical missingness remain explicit. A
capture is not retried because it is a refusal, a safety response or a nonanswer.
Integrity anomalies prevent final comparison/manuscript publication; the
private failed-run record preserves the fact of failure. Attempts in another
W03 protocol namespace block automatic pooling.

The postwave service runs as the research-data user with a read-only view of
the scientific data store, except for the pre-existing execution-lock directory.
Its own derived-output directory is writable. It has no provider credentials,
an isolated network namespace and AF_UNIX-only sockets. It cannot contact a
model API or fetch cited webpages.

## Comparison and response selection

The exact registered URL implementation is reused at SHA-256
`914b61672d66ca0dd21f3bd4a89e70dd5d7589d4322f3106e95b9f32535216a6`.
The W02 normalized I03 baseline remains frozen at SHA-256
`cf305d66e998ae3a04e8b76563c399d55ef2514a9c7e6944bc61bc942d99b7df`.
The user-facing text/citation selector is copied literally from the W02 parser;
compatibility is checked against the original 80 W02 captures before deployment.

All 80 planned W03 I03 slots are represented, including technical missingness.
Only technical verification determines response retention. Content correctness
or pre-existing AI validity labels do not select the URL-analysis sample. The
nine W02 indeterminate citation judgements remain unchanged and exploratory.

Both-empty URL pairs remain undefined and are counted separately; no-URL
responses are not technical missingness. Cells with fewer than eight retained
responses in either wave have no primary numerical contrast. Undefined values
are never replaced by zero or one. Different profiles are not silently pooled.
Requested and literal returned-model identifiers are disclosed, without a
claim that unchanged strings imply unchanged hosted weights.

For the already-planned exploratory cross-wave set overlap, this implementation
prospectively specifies the collection of distinct **nonempty** exact first-five
URL sets in each cell. It reports the number shared across waves and the Jaccard
of those two collections. Empty response sets remain in the URL-free counts;
two empty collections produce an undefined overlap. This is an exploratory
description, not an additional significance test or independent-pair sample.
The primary registered metric and sensitivity procedure are unchanged.

## Review outputs

Each successful private run creates:

- `TECHNICAL_QC.json` and an observation-status CSV for the full matrix.
- A hash-bound derivative input snapshot and compressed copy.
- The 80-slot private normalized I03 input.
- `W02-W03-URL-COMPARISON.json` and a concise comparison CSV.
- An English first manuscript draft as PDF and editable HTML, with filled
  abstract, results, tables, methods, limitations, declarations and references.
- A Japanese `REVIEW_START_HERE.html` entrypoint for the PI.
- Rendered page images, an automated layout-render report, a run manifest and
  a completion marker linking input, implementation and output hashes.

The manuscript is generated from aggregate values and a fixed editorial
template. It does not paste raw answers, invent citation accuracy, rank services,
claim a causal LLMO/AIO effect, infer institutional approval, or submit/publish
itself. The author reviews the completed draft, including ethics applicability,
funding and competing-interest declarations, before any submission.

## Dependencies and validation

Collection, snapshot, normalization and analysis code use the Python standard
library. ReportLab is an explicit document-output dependency only. Poppler
renders the manuscript pages. The controlled Ubuntu runtime pins installed
package versions in its private dependency receipt; dependencies are installed
before W03, not downloaded during postwave processing.

Run the full synthetic suite in a clean Linux copy without provider credentials:

```sh
python3 -B -m unittest discover -s automation/tests -v
```

The PDF integration test requires ReportLab and Poppler and is skipped on a
generic CI host without those renderers. It is required and executed on the
controlled runtime. Synthetic fixtures exercise a complete matrix, technical
missingness, refusals, unknown response formats, hash errors, source preservation,
concurrency, repeat-run protection and the manuscript path. Layout examples are
labelled simulation and kept separate from actual research outputs.
