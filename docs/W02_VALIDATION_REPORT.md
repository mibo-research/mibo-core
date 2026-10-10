# W02 hardening validation

Date: 10 October 2026. Base: `1b12602cb311d14659a6b4e290db03d3222b71d0`
(`codex/w01-close-20261008`). Engineering work and independent review were
assisted by Codex. No live provider/API calls or controlled-VM changes were made.

## Results

| Check | Result |
|---|---|
| `python3 -m unittest discover -s automation/tests -v` | **318/318 PASS**; baseline135, added183 |
| Full-size registered-v2.0.1 W02 synthetic rehearsal | **960 captures**,240/lineage, STD only; restart adds **zero** provider calls |
| Durable execution fault and terminal-evidence tests | 35 PASS |
| Google actual-adapter/mock-HTTP model-binding tests | 3 PASS |
| Prewave/waiter gates | 17 PASS |
| Technical cell accounting | 8 PASS |
| Technical monitoring | 6 PASS |
| Generic offline closure | 25 PASS |
| Trusted-receipt archive and read-only restoration verifier | 37 PASS |
| Offline controlled-VM stager | 4 PASS |
| Retry-After transport and installed-source integrity | 19 PASS |
| Offline technical wave audit | 22 PASS |
| Central deterministic manifest validation | 4 PASS |
| Added nonroot refusal regressions | 2 PASS |
| Frozen instrument/config validation | PASS |
| W01 UI1120-row manifest, structural and strict integrity | PASS |
| W01 synthetic paired160-row manifest, structural and strict integrity | PASS |
| Exploratory API Shadow960-row manifest | PASS, separate namespace |
| Automation/runtime Python compilation | PASS |
| Staging shell syntax | PASS |
| `systemd-analyze verify` collector/prewave/monitor units and timer | PASS |
| `git diff --check` | PASS |
| Frozen scientific configs, original versioned manuals/amendments and preserved W01 close helper | Unchanged |

The three baseline date-dependent executor tests initially failed after the W01
window elapsed. Their synthetic clock is now explicitly fixed inside the test
window. The full baseline135 passed before hardening validation. One integrated
test initially expected the older symlink-error wording; its assertion now
accepts the earlier shared namespace rejection while still requiring failure.
The initial277-test local run passed after this correction. GitHub's nonroot
runner then exposed two older synthetic fixtures that depended on root ownership
operations. The fixtures now explicitly simulate those operations; production
root requirements remain unchanged and two refusal regressions were added.
The affected20 tests also passed with nonroot/denied-ownership simulation.
Real alternate-UID execution is unavailable in this local UID namespace;
GitHub's real nonroot runner supplies the separate environment check.

Stricter terminal-evidence checks also exposed one incomplete synthetic row,
three canned response times predating their synthetic dispatch claims and
incorrect synthetic retry/window times. The test fixtures were aligned to full
registered rows and the same synthetic clock; the production checks were not
relaxed. The final318-test run passed after these integration corrections.

Full local test log SHA-256:
`940f5a86c41728b928f5dfd5e2fc0c5e995f08ca280462f42e10a585bd328ef5`.
The log is transient, contains only synthetic test output and is not a private
VM observation record. `W02_VALIDATION_SHA256SUMS.txt` binds the tested automation,
runtime, policy and CI source/fixtures for reproducible comparison.

## Controlled comparison and parallel-PR reconciliation

The same synthetic public-entry-point harness was run against detached base
`1b12602cb311d14659a6b4e290db03d3222b71d0` and this candidate. Provider adapters,
credentials/preflight and request prompts are mocked; no live request is sent.

| Trigger | Exact base behavior | Hardened behavior |
|---|---|---|
| Swap two otherwise valid execution-order values | Accepted without validation errors | Two deterministic order mismatches |
| Retain an unresolved dispatch in another version namespace | Two mock adapter calls | Zero calls; replay blocked |
| Restart after an environment mismatch | One additional mock adapter call | Zero additional calls |
| Prior Google attempt filename contradicts embedded OpenAI lineage | Two mock adapter calls | Zero calls; identity conflict rejected |

The reusable harness is
`automation/validation/w02_controlled_comparison.py`; run it with the absolute
path to each isolated repository checkout. Disclosure-safe outputs are
`automation/tests/w02_baseline_control.synthetic.json` and
`automation/tests/w02_hardened_control.synthetic.json`. Harness SHA-256:
`a21d670246977f6e91e519d7b0ddc375dea715b72d308ee9e72537af9850a981`.
These are controlled software counterexamples, not diagnoses of the actual W01
failure or evidence of live W02 readiness.

[Draft PR20](https://github.com/mibo-research/mibo-core/pull/20), reviewed at
`5c67218cc0de77667008d1131cd6250071a1b33d`, contained a complementary technical
wave audit and centralized manifest-order validation. Those components and
their synthetic regressions were carried into this broader candidate; the
audit was adapted to the current durable claim timestamp. Its alternative
closure implementation was not substituted for this candidate's generic
closure. PR20's branch and evidence are preserved. This candidate supplies one
combined review tree; the two overlapping PRs must not be merged independently.

## Limits and deployment acceptance

PASS verifies synthetic software behavior, not live provider availability,
deployed VM state, actual W02 authorization, scientific data collection or cloud
backup existence. Full capture, namespace closure/seal, archive integrity,
independent backup and restored-copy verification are separate claims.

Read [W02_RUNTIME_HARDENING.md](W02_RUNTIME_HARDENING.md) for controlled-VM
staging, actual service-user gates, monitoring, closure and restoration checks.
The existing approved v2.0.1 full-panel path is available if its scientific
conditions are prospectively carried forward with fresh W02 freeze/readiness/
human authorization. The decision draft does not supply that authorization.
