#!/usr/bin/env python3
"""Wait on the controlled runtime until a registered MIBO wave opens.

This process uses the frozen UTC timestamp in waves_v1.0.json rather than a
GitHub-hosted schedule. It launches the paired executor at or after field open.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

import mibo_runner as core


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def seconds_until_wave_start(wave_id: str, now: datetime | None = None) -> float:
    wave = core._wave(wave_id)
    start = parse_utc(wave["start_utc"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return max(0.0, (start - current).total_seconds())


def wait_until_wave_start(wave_id: str) -> None:
    while True:
        remaining = seconds_until_wave_start(wave_id)
        if remaining <= 0:
            return
        time.sleep(min(remaining, 60.0))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wave", required=True)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--freeze", required=True, type=Path)
    p.add_argument("--authorization", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()

    wave = core._wave(args.wave)
    close = parse_utc(wave["close_utc"])
    now = datetime.now(timezone.utc)
    if now >= close:
        raise SystemExit("registered primary field window has already closed")

    wait_until_wave_start(args.wave)
    command = [
        sys.executable,
        str(Path(__file__).with_name("paired_executor.py")),
        "--manifest", str(args.manifest),
        "--freeze", str(args.freeze),
        "--authorization", str(args.authorization),
        "--data-root", str(args.data_root),
        "--timeout", str(args.timeout),
        "--execute",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
