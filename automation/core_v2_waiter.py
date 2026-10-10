#!/usr/bin/env python3
"""Wait for the prospectively registered Core v2 wave, then execute it once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

import core_v2_prewave as prewave


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--wave", required=True)
    p.add_argument("--site", default="JP01")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--expected-host")
    p.add_argument("--expected-source-commit")
    p.add_argument("--strict-runtime", action="store_true")
    args = p.parse_args()
    if args.timeout <= 0:
        raise ValueError("provider request timeout must be positive")
    check_args = dict(protocol_path=args.protocol, manifest_path=args.manifest,
        freeze_path=args.freeze, authorization_path=args.authorization, data_root=args.data_root,
        wave_id=args.wave, site_id=args.site, expected_host=args.expected_host,
        expected_source_commit=args.expected_source_commit, strict_runtime=args.strict_runtime)
    initial = prewave.validate_prewave(**check_args)
    print("CORE_V2_PREWAVE=PASS wave=" + args.wave + " phase=" + initial["phase"], flush=True)
    start = parse_utc(initial["registered_start_utc"])
    close = parse_utc(initial["registered_close_utc"])
    while True:
        now = datetime.now(timezone.utc)
        if now >= close:
            raise SystemExit("prospectively registered Core v2 field window has closed")
        remaining = (start - now).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 60.0))
    final = prewave.validate_prewave(**check_args)
    if final["input_hashes"] != initial["input_hashes"]:
        raise SystemExit("armed protocol/manifest/freeze/authorization changed while waiting")
    print("CORE_V2_DISPATCH_GATE=PASS wave=" + args.wave, flush=True)
    command = [
        sys.executable, "-B", str(Path(__file__).with_name("core_v2_executor.py")),
        "--protocol", str(args.protocol), "--manifest", str(args.manifest),
        "--freeze", str(args.freeze), "--authorization", str(args.authorization),
        "--data-root", str(args.data_root), "--timeout", str(args.timeout), "--execute",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
