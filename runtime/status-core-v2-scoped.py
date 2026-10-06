#!/usr/bin/env python3
"""Display operational timestamps and counts without reading or printing answers."""
import json
from pathlib import Path
import subprocess

links = list(Path("/srv/mibo-private").glob("scoped-ready.*/readiness/RUNTIME_LINK.json"))
if not links:
    raise SystemExit("3社の実行設定はまだ作成されていません。")
latest = max(links, key=lambda p: p.stat().st_mtime)
link = json.loads(latest.read_text())
root = Path(link["data_root"]) / "v2.0.2/JP01/MIBO2-W01"
print("私有記録:", latest.parent)
print(subprocess.check_output(["systemctl", "show", link["service"], "-p", "ActiveState", "-p", "SubState"], text=True).strip())
for sid, label in [("MIBO-SL-001", "OpenAI"), ("MIBO-SL-002", "Anthropic"),
                   ("MIBO-SL-003", "Google"), ("MIBO-SL-004", "Perplexity")]:
    start = root / "metadata" / ("first-dispatch-" + sid + ".json")
    timestamp = json.loads(start.read_text())["actual_observation_start_at_utc"] if start.exists() else "未開始"
    count = 0
    for path in (root / "metadata").glob("*.json"):
        if path.name.startswith(("retry-link-", "first-dispatch-")):
            continue
        data = json.loads(path.read_text())
        if data.get("service_lineage_id") == sid and data.get("attempt_id"):
            count += 1
    print(f"{label}: 開始UTC={timestamp} / 保存済み応答={count} / 予定=280")
print("未開始・未取得は進行中の待機/未実行を含みます。最終欠測は元の時間帯の終了後に確定します。")
