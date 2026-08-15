#!/usr/bin/env python3
"""Strict deterministic identity validation for frozen MIBO manifests.

This layer complements the structural checks in ``mibo_runner.validate_manifest`` by
recomputing registered identity fields that must never drift after generation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import mibo_runner as core


def strict_validate_manifest(rows: list[dict]) -> list[str]:
    errors = list(core.validate_manifest(rows))
    if not rows:
        return errors

    services = {s["service_lineage_id"]: s for s in core._services()}
    forms = {f["query_form_id"]: f for f in core._forms()}

    for i, row in enumerate(rows, 1):
        service = services.get(row.get("service_lineage_id"))
        if service is None:
            errors.append(f"row {i}: unknown service_lineage_id {row.get('service_lineage_id')}")
            continue

        form = forms.get(row.get("query_form_id"))
        if form is None:
            continue

        if row.get("service_name") != service["name"]:
            errors.append(f"row {i}: service_name mismatch for {service['service_lineage_id']}")
        if row.get("provider") != service["provider"]:
            errors.append(f"row {i}: provider mismatch for {service['service_lineage_id']}")
        if row.get("anchor") != str(form["anchor"]).lower():
            errors.append(f"row {i}: anchor flag mismatch for {form['query_form_id']}")

        line_id = row.get("line_id")
        if line_id == "LUI":
            mode_id = "LUI"
        elif line_id in {"PLR", "FRZ"}:
            mode_id = "PAIRED"
        else:
            continue

        expected_seed = core.deterministic_seed(
            row["wave_id"], row["site_id"], mode_id
        )
        if row.get("random_seed") != expected_seed:
            errors.append(
                f"row {i}: random_seed mismatch; expected {expected_seed}"
            )

        expected_attempt_id = core.attempt_id(
            row["site_id"],
            row["wave_id"],
            service["short_id"],
            line_id,
            row["item_id"],
            row["language"],
            row["window_id"],
            int(row["replication"]),
            int(row["attempt"]),
        )
        if row.get("attempt_id") != expected_attempt_id:
            errors.append(
                f"row {i}: attempt_id mismatch; expected {expected_attempt_id}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    errors = strict_validate_manifest(core.read_csv(args.manifest))
    if errors:
        print("\n".join(errors))
        return 1
    print("strict manifest integrity valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
