# W02 hardening validation

Date: 10 October 2026. Base: `1b12602cb311d14659a6b4e290db03d3222b71d0`
(`codex/w01-close-20261008`). Engineering work and independent review were
assisted by Codex. No live provider/API calls or controlled-VM changes were made.

## Results

| Check | Result |
|---|---|
| `python3 -m unittest discover -s automation/tests -v` | **277/277 PASS**; baseline135, added142 |
| Full-size registered-v2.0.1 W02 synthetic rehearsal | **960 captures**,240/lineage, STD only; restart adds **zero** provider calls |
| Durable execution fault tests | 24 PASS |
| Google actual-adapter/mock-HTTP model-binding tests | 3 PASS |
| Prewave/waiter gates | 17 PASS |
| Technical cell accounting | 6 PASS |
| Technical monitoring | 6 PASS |
| Generic offline closure | 25 PASS |
| Trusted-receipt archive and read-only restoration verifier | 37 PASS |
| Offline controlled-VM stager | 4 PASS |
| Retry-After transport and installed-source integrity | 19 PASS |
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
The final277-test run passed after this correction.

Full local test log SHA-256:
`6c578ebc31f3da49913ac58e1a22f2adfdfb7a08fa76f6a1aa2faadbcd37ede7`.
The log is transient, contains only synthetic test output and is not a private
VM observation record. `W02_VALIDATION_SHA256SUMS.txt` binds the tested automation,
runtime, policy and CI source/fixtures for reproducible comparison.

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
