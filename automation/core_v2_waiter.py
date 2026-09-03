#!/usr/bin/env python3
"""Wait for the prospectively registered Core v2 wave, then execute it once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

import core_v2_runner as runner


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True, type=Path)
    p.add_argument("--wave", required=True)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    protocol, _ = runner.load_protocol(args.protocol)
    wave = runner.wave(protocol, args.wave)
    start = parse_utc(wave["start_utc"])
    close = parse_utc(wave["close_utc"])
    while True:
        now = datetime.now(timezone.utc)
        if now >= close:
            raise SystemExit("prospectively registered Core v2 field window has closed")
        remaining = (start - now).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 60.0))
    command = [
        sys.executable, str(Path(__file__).with_name("core_v2_executor.py")),
        "--protocol", str(args.protocol), "--manifest", str(args.manifest),
        "--freeze", str(args.freeze), "--authorization", str(args.authorization),
        "--data-root", str(args.data_root), "--timeout", str(args.timeout), "--execute",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
