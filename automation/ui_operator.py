#!/usr/bin/env python3
"""Manifest-driven human operator workstation for MIBO Ecological Live.

This program automates only local research operations. It never opens,
controls, queries, scrapes, or extracts data from provider websites.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import manifest_integrity
import mibo_runner as core
import operator_roster
from raw_archive import archive_failure, canonical_json_bytes, wave_root, write_deviation
from retry_policy import RETRY_ELIGIBLE, decide_retry
import ui_capture

CAPTURE_END = "<<<MIBO-CAPTURE-END>>>"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_exclusive(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(canonical_json_bytes(obj))


def _service(row: dict) -> dict:
    return next(s for s in core._services() if s["service_lineage_id"] == row["service_lineage_id"])


def _prompt(row: dict) -> str:
    form = next(f for f in core._forms() if f["query_form_id"] == row["query_form_id"])
    return form["text"]


def _clone_retry_row(row: dict, next_attempt: int) -> dict:
    service = _service(row)
    clone = dict(row)
    clone["retry_of_attempt_id"] = row["attempt_id"]
    clone["attempt"] = next_attempt
    clone["attempt_id"] = core.attempt_id(
        row["site_id"], row["wave_id"], service["short_id"], row["line_id"],
        row["item_id"], row["language"], row["window_id"], int(row["replication"]), next_attempt,
    )
    clone["status"] = "retry_intended"
    return clone


def _root(data_root: Path, row: dict) -> Path:
    return wave_root(data_root, row["site_id"], row["wave_id"])


def processed_attempt_ids(data_root: Path, site_id: str, wave_id: str) -> set[str]:
    root = wave_root(data_root, site_id, wave_id)
    done = ui_capture.completed_attempt_ids(data_root, site_id, wave_id)
    failure_dir = root / "failures"
    if failure_dir.exists():
        done |= {p.stem for p in failure_dir.glob("*.json")}
    return done


def paused_lineages(data_root: Path, site_id: str, wave_id: str, now: datetime | None = None) -> set[str]:
    root = wave_root(data_root, site_id, wave_id) / "configuration" / "ui_pauses"
    if not root.exists():
        return set()
    current = (now or utc_now()).astimezone(timezone.utc)
    paused: set[str] = set()
    for path in root.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        resume = data.get("resume_after_utc")
        if resume is None or current < ui_capture.parse_utc(resume):
            paused.add(data["service_lineage_id"])
    return paused


def retry_tasks(data_root: Path, site_id: str, wave_id: str) -> list[dict]:
    root = wave_root(data_root, site_id, wave_id) / "manifests" / "ui_retries"
    if not root.exists():
        return []
    tasks = []
    for path in root.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_task_path"] = str(path)
        tasks.append(data)
    return tasks


def select_next_row(rows: list[dict], *, data_root: Path, now: datetime | None = None,
                    service_lineage_id: str | None = None, window_id: str | None = None,
                    allowed_lineages: set[str] | None = None) -> dict | None:
    current = (now or utc_now()).astimezone(timezone.utc)
    if not rows:
        return None
    site_id = rows[0]["site_id"]
    wave_id = rows[0]["wave_id"]
    done = processed_attempt_ids(data_root, site_id, wave_id)
    paused = paused_lineages(data_root, site_id, wave_id, current)

    def admissible(row: dict) -> bool:
        if row["attempt_id"] in done or row["service_lineage_id"] in paused:
            return False
        if allowed_lineages is not None and row["service_lineage_id"] not in allowed_lineages:
            return False
        if service_lineage_id and row["service_lineage_id"] != service_lineage_id:
            return False
        if window_id and row["window_id"] != window_id:
            return False
        return True

    due_retries: list[tuple[datetime, dict]] = []
    for task in retry_tasks(data_root, site_id, wave_id):
        row = task["row"]
        if not admissible(row):
            continue
        due = ui_capture.parse_utc(task["due_at_utc"])
        if due <= current and ui_capture.within_registered_window(row, current):
            due_retries.append((due, row))
    if due_retries:
        due_retries.sort(key=lambda pair: (pair[0], pair[1]["attempt_id"]))
        return due_retries[0][1]

    for row in sorted(rows, key=lambda r: int(r["execution_order"])):
        if admissible(row) and ui_capture.within_registered_window(row, current):
            return row
    return None


def _write_retry_task(*, data_root: Path, row: dict, retry_row: dict, due_at_utc: str,
                      failure_kind: str, status: str) -> dict:
    root = _root(data_root, row)
    task = {
        "original_attempt_id": row["attempt_id"],
        "retry_attempt_id": retry_row["attempt_id"],
        "due_at_utc": due_at_utc,
        "failure_kind": failure_kind,
        "row": retry_row,
        "status": status,
    }
    path = root / "manifests" / "ui_retries" / f"{retry_row['attempt_id']}.json"
    _write_exclusive(path, task)
    return task


def schedule_retry(*, data_root: Path, row: dict, failure_kind: str, failed_at: datetime,
                   provider_retry_after_seconds: int | None = None) -> dict | None:
    _, window_close = ui_capture.window_bounds(row["wave_id"], row["window_id"])
    decision = decide_retry(
        attempt=int(row["attempt"]), failure_kind=failure_kind, failed_at=failed_at,
        provider_retry_after_seconds=provider_retry_after_seconds, field_close=window_close,
    )
    if not decision.retry:
        return None
    retry_row = _clone_retry_row(row, int(decision.next_attempt))
    return _write_retry_task(
        data_root=data_root, row=row, retry_row=retry_row, due_at_utc=decision.due_at_utc,
        failure_kind=failure_kind, status="scheduled_technical_retry",
    )


def pause_lineage_for_outage(*, data_root: Path, row: dict, operations_lead: str,
                             resume_after_utc: str, notes: str | None) -> dict:
    if not operations_lead.strip():
        raise ValueError("Operations Lead is required for an outage pause")
    record = {
        "service_lineage_id": row["service_lineage_id"],
        "wave_id": row["wave_id"],
        "site_id": row["site_id"],
        "paused_at_utc": utc_text(),
        "resume_after_utc": resume_after_utc,
        "operations_lead": operations_lead,
        "reason": "apparent_service_wide_outage",
        "notes": notes,
        "rule": "pause affected lineage; schedule one documented recovery block later in the registered field window",
    }
    root = _root(data_root, row)
    stamp = record["paused_at_utc"].replace(":", "").replace("-", "")
    path = root / "configuration" / "ui_pauses" / f"{row['service_lineage_id']}-{stamp}.json"
    _write_exclusive(path, record)
    deviation_id = f"UI-OUTAGE-{row['service_lineage_id']}-{stamp}"
    write_deviation(
        data_root=data_root, site_id=row["site_id"], wave_id=row["wave_id"], deviation_id=deviation_id,
        record={"deviation_id": deviation_id, **record},
    )
    return record


def schedule_outage_recovery(*, data_root: Path, row: dict, failed_at: datetime,
                             recovery_at_utc: str) -> dict:
    _, registered_end = ui_capture.window_bounds(row["wave_id"], row["window_id"])
    minimum = decide_retry(
        attempt=int(row["attempt"]), failure_kind="temporary_interface_failure",
        failed_at=failed_at, field_close=registered_end,
    )
    if not minimum.retry:
        raise ValueError("no protocol-permitted retry remains inside the registered window")
    recovery = ui_capture.parse_utc(recovery_at_utc)
    if recovery < ui_capture.parse_utc(minimum.due_at_utc):
        raise ValueError("recovery block is earlier than the registered minimum retry delay")
    if recovery >= registered_end:
        raise ValueError("recovery block falls outside the registered observation window")
    retry_row = _clone_retry_row(row, int(minimum.next_attempt))
    return _write_retry_task(
        data_root=data_root, row=row, retry_row=retry_row, due_at_utc=utc_text(recovery),
        failure_kind="temporary_interface_failure", status="scheduled_outage_recovery_retry",
    )


def _read_multiline_capture(label: str) -> str:
    print(f"Paste {label} below. Finish with a line containing exactly: {CAPTURE_END}")
    lines: list[str] = []
    for line in sys.stdin:
        value = line.rstrip("\n")
        if value == CAPTURE_END:
            break
        lines.append(value)
    return "\n".join(lines)


def run_one(*, row: dict, configuration: Path, roster_path: Path,
            data_root: Path, operator_id: str) -> None:
    roster, _ = operator_roster.load_roster(
        roster_path, wave_id=row["wave_id"], site_id=row["site_id"]
    )
    operator_roster.assert_operator_assigned(
        roster, service_lineage_id=row["service_lineage_id"], operator_id=operator_id
    )
    prompt = _prompt(row)
    service = _service(row)
    start, end = ui_capture.window_bounds(row["wave_id"], row["window_id"])
    print("\n=== MIBO ECOLOGICAL LIVE TASK ===")
    print(f"Attempt: {row['attempt_id']}")
    print(f"Service: {service['name']} ({row['service_lineage_id']})")
    print(f"Window: {row['window_id']} | {start.isoformat()} to {end.isoformat()}")
    print("Interaction: HUMAN ONLY — do not use browser automation, scraping, or DOM extraction.")
    print("Open the registered public service manually and start a fresh session.")
    if input("Type FRESH after confirming a fresh session: ").strip() != "FRESH":
        raise SystemExit("fresh-session confirmation not received; nothing captured")

    print("\n--- EXACT FROZEN PROMPT ---")
    print(prompt)
    print("--- END PROMPT ---\n")
    if input("Submit that exact prompt manually, then type SUBMITTED: ").strip() != "SUBMITTED":
        raise SystemExit("submission confirmation not received; nothing captured")
    submitted_at = utc_text()

    result = input("Result [CAPTURE / TECHFAIL / OUTAGE]: ").strip().upper()
    if result == "CAPTURE":
        displayed_mode = input("Displayed service mode (optional, Enter to skip): ").strip() or None
        displayed_model = input("Displayed model label (optional, Enter to skip): ").strip() or None
        output = _read_multiline_capture("the full rendered provider response")
        source_answer = input("Were citations/source cards/links displayed? [YES/NO]: ").strip().upper()
        if source_answer not in {"YES", "NO"}:
            raise SystemExit("source-display confirmation must be YES or NO; nothing captured")
        sources_displayed = source_answer == "YES"
        sources_text = None
        if sources_displayed:
            sources_text = _read_multiline_capture(
                "all displayed citation/source-card/link information available through the ordinary UI"
            )
            if not sources_text.strip():
                raise SystemExit("sources were marked displayed but no source information was captured")
        captured_at = utc_text()
        meta = ui_capture.capture_ui_observation(
            data_root=data_root, row=row, prompt_text=prompt, output_text=output,
            ui_configuration_path=configuration, operator_roster_path=roster_path,
            operator_id=operator_id, operator_confirmed_new_session=True,
            submitted_at_utc=submitted_at, captured_at_utc=captured_at,
            sources_displayed=sources_displayed, sources_text=sources_text,
            displayed_service_mode=displayed_mode, displayed_model_label=displayed_model,
            now=utc_now(),
        )
        print(json.dumps({
            "status": "CAPTURED",
            "attempt_id": row["attempt_id"],
            "output_sha256": meta["output_sha256"],
            "sources_capture_state": meta["sources_capture_state"],
            "metadata_sha256": meta["metadata_file_sha256"],
        }, indent=2))
        return

    if result == "TECHFAIL":
        print("Retry-eligible technical failure kinds:")
        print(", ".join(sorted(RETRY_ELIGIBLE)))
        kind = input("Failure kind: ").strip()
        if kind not in RETRY_ELIGIBLE:
            raise SystemExit("unregistered failure kind; nothing written")
        failed_at = utc_now()
        message = input("Short procedural description: ").strip()
        archive_failure(
            data_root=data_root, row=row, failure_kind=kind, message=message,
            failed_at_utc=utc_text(failed_at),
        )
        retry = schedule_retry(data_root=data_root, row=row, failure_kind=kind, failed_at=failed_at)
        print(json.dumps({"status": "TECHNICAL_FAILURE_RECORDED", "attempt_id": row["attempt_id"], "retry": retry}, indent=2))
        return

    if result == "OUTAGE":
        failed_at = utc_now()
        lead = input("Operations Lead name/id: ").strip()
        if lead != roster.get("operations_lead"):
            raise SystemExit("Operations Lead does not match the frozen operator roster")
        recovery_text = input("Scheduled recovery block not-before UTC (ISO 8601): ").strip()
        if not recovery_text:
            raise SystemExit("a documented recovery-block time is required; nothing written")
        notes = input("Outage notes: ").strip() or None
        try:
            retry = schedule_outage_recovery(
                data_root=data_root, row=row, failed_at=failed_at, recovery_at_utc=recovery_text,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        archive_failure(
            data_root=data_root, row=row, failure_kind="temporary_interface_failure",
            message="apparent service-wide outage; lineage paused for documented recovery block",
            failed_at_utc=utc_text(failed_at),
        )
        record = pause_lineage_for_outage(
            data_root=data_root, row=row, operations_lead=lead,
            resume_after_utc=retry["due_at_utc"], notes=notes,
        )
        print(json.dumps({"status": "LINEAGE_PAUSED_FOR_RECOVERY", "retry": retry, **record}, indent=2))
        return

    raise SystemExit("unknown result; nothing written")


def load_manifest(path: Path) -> list[dict]:
    rows = core.read_csv(path)
    errors = manifest_integrity.strict_validate_manifest(rows)
    if errors:
        raise ValueError("manifest validation failed: " + "; ".join(errors))
    if not rows or any(r["line_id"] != "LUI" for r in rows):
        raise ValueError("UI operator accepts Ecological Live LUI manifests only")
    return rows


def status(rows: list[dict], data_root: Path, roster: dict | None = None) -> dict:
    site_id = rows[0]["site_id"]
    wave_id = rows[0]["wave_id"]
    done = processed_attempt_ids(data_root, site_id, wave_id)
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        key = f"{row['service_lineage_id']}:{row['window_id']}"
        bucket = out.setdefault(key, {"intended": 0, "processed_initial_attempts": 0})
        bucket["intended"] += 1
        if row["attempt_id"] in done:
            bucket["processed_initial_attempts"] += 1
    report: dict = {"wave_id": wave_id, "site_id": site_id, "by_lineage_window": out}
    if roster is not None:
        report["service_operators"] = roster.get("service_operators")
        report["operations_lead"] = roster.get("operations_lead")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("status", "next"))
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--configuration", type=Path)
    p.add_argument("--roster", type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--operator")
    p.add_argument("--lineage")
    p.add_argument("--window", choices=("WA", "STD", "WB"))
    args = p.parse_args()

    rows = load_manifest(args.manifest)
    roster = None
    if args.roster:
        roster, _ = operator_roster.load_roster(
            args.roster, wave_id=rows[0]["wave_id"], site_id=rows[0]["site_id"]
        )
    if args.command == "status":
        print(json.dumps(status(rows, args.data_root, roster), indent=2))
        return 0
    if args.configuration is None or args.roster is None or not args.operator:
        raise SystemExit("next requires --configuration, --roster, and --operator")
    assigned = set(operator_roster.assigned_lineages(roster, args.operator))
    if not assigned:
        raise SystemExit(f"operator {args.operator!r} has no assigned service lineage in the frozen roster")
    if args.lineage and args.lineage not in assigned:
        raise SystemExit(f"operator {args.operator!r} is not assigned to {args.lineage}")
    row = select_next_row(
        rows, data_root=args.data_root, service_lineage_id=args.lineage,
        window_id=args.window, allowed_lineages=assigned,
    )
    if row is None:
        print("No eligible pending Ecological Live task is due for this operator in the registered window.")
        return 0
    run_one(
        row=row, configuration=args.configuration, roster_path=args.roster,
        data_root=args.data_root, operator_id=args.operator,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
