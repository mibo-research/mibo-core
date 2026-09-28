# MIBO Core v2.1 Operations Addendum (draft)

This addendum takes precedence over the unchanged v2.0 Operations Manual for
version identifiers, the W01 field window, private paths, and execution
commands. All other scientific and operational rules in the v2.0 manual remain.
It does not authorize collection before a public v2.1 version-specific DOI.

## W01 timing

- Start: 1 October 2026 00:00 UTC / 09:00 JST.
- Close: 3 October 2026 00:00 UTC / 09:00 JST.
- Window A English Anchors: 1 October 00:00–12:00 UTC.
- Window B English Anchors: 2 October 00:00–12:00 UTC.
- Standard non-Anchor forms: inside the 48-hour field window.

## Controlled runtime

Use the `core_v21_*` modules, `runtime/preflight-core-v21.sh`, and
`mibo-core-v21.service` exclusively for the new version. The private protocol,
Provider Freeze Record and execution authorization all carry version `2.1`
and the new DOI. Raw records are written append-only under
`<MIBO_DATA_ROOT>/v2.1/<Site ID>/<Wave ID>/`. The v2.0 service and sentinel
must remain disabled for this W01.

After the four dated Terms/access decisions, exact human model freeze,
non-confirmatory four-provider smoke checks, 1,120-row strict manifest
validation, runtime health, and hash-bound human authorization, the Operations
Lead may set `MIBO_CORE_V21_EXECUTION=ENABLED_AFTER_CORE_V21_GATE`. Arming the
service before the registered start makes it wait on the controlled UTC clock.
The public package, GitHub branch, or preflight bundle alone never authorizes
execution. A failed gate blocks W01 and is recorded as a deviation.
