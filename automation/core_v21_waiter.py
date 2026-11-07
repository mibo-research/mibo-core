"""Version-pinned v2.1 service entry point; never accepts a four-series protocol."""
from __future__ import annotations

import argparse
from pathlib import Path

import core_v2_runner as runner
import core_v2_waiter as waiter
import core_v21_policy as policy


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--protocol", required=True, type=Path)
    args, _ = parser.parse_known_args()
    protocol, _ = runner.load_protocol(args.protocol)
    if protocol["protocol_version"] != policy.VERSION:
        raise ValueError("v2.1 service refuses a historical four-series protocol")
    policy.require_execution_sentinels()
    return waiter.main()


if __name__ == "__main__":
    raise SystemExit(main())
