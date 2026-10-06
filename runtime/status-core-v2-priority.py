#!/usr/bin/env python3
"""Display Google tier/start/count metadata without printing observation answers."""
import json
from pathlib import Path
import subprocess

anchor = Path("/srv/mibo-private/MIBO2-W01-priority-runtime.json")
if not anchor.exists():
    raise SystemExit("Google Priorityの設定は未作成です。")
record = json.loads(anchor.read_text())
print("Priority私有記録:", record["readiness"])
print(subprocess.check_output(["systemctl", "show", "mibo-core-v2-google-priority.service",
    "-p", "LoadState", "-p", "ActiveState", "-p", "SubState"], text=True).strip())
root = Path(record["data_root"]) / "v2.0.3/JP01/MIBO2-W01"
dispatch = root / "metadata/first-dispatch-MIBO-SL-003.json"
started = json.loads(dispatch.read_text())["actual_observation_start_at_utc"] if dispatch.exists() else "未開始"
counts = {"priority": 0, "standard": 0, "unknown": 0}
for path in (root / "metadata").glob("*.json"):
    if path.name.startswith(("first-dispatch-", "retry-link-")): continue
    value = json.loads(path.read_text())
    if value.get("service_lineage_id") != "MIBO-SL-003" or not value.get("attempt_id"): continue
    tier = (value.get("response_metadata") or {}).get("service_tier_actual")
    counts[tier if tier in {"priority", "standard"} else "unknown"] += 1
print(f"Google開始UTC: {started} / 保存済み={sum(counts.values())} / 予定=280")
print("実処理区分:", json.dumps(counts))
print("観測時間帯は元の予定を維持。3社のv2.0.2記録とGoogleのv2.0.3記録は別々に保持します。")
