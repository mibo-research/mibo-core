#!/usr/bin/env python3
"""Offline Core v2 audit entrypoint; never imports provider adapters."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "automation"))
from core_v2_wave_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
