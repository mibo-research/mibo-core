from pathlib import Path
import json, re, sys

root = Path(__file__).resolve().parents[1]
docs = root / "docs"
required = [
    "MIBO_Core_Observatory_Master_Protocol_v1.0-rc3.md",
    "MIBO_Service_Registry_v1.0-rc3.md",
    "MIBO_Fixed_Query_Instrument_v1.0-rc3.md",
    "MIBO_Query_Codebook_v1.0-rc3.md",
    "MIBO_Frozen_Live_Comparability_Registry_v1.0-rc3.md",
    "MIBO_Operations_Schedule_and_Manual_v1.0-rc3.md",
    "MIBO_Statistical_Analysis_Plan_v1.0-rc3.md",
    "MIBO_Cross_Document_Consistency_Audit_v1.0-rc3.md",
]
errors = []
for name in required:
    p = docs / name
    if not p.exists():
        errors.append("Missing " + name)
    elif "v1.0-rc3" not in p.read_text(encoding="utf-8"):
        errors.append("Version mismatch in " + name)

instrument = (docs / "MIBO_Fixed_Query_Instrument_v1.0-rc3.md").read_text(encoding="utf-8")
if len(re.findall(r"^## MIBO-I\d{2} —", instrument, flags=re.M)) != 12:
    errors.append("Instrument must contain 12 items")
if len(re.findall(r"^### (?:English|Japanese) Query Form:", instrument, flags=re.M)) != 24:
    errors.append("Instrument must contain 24 query forms")

checks = json.loads((root / "audit" / "CONSISTENCY_CHECKS.json").read_text(encoding="utf-8"))
if not all(checks.values()):
    errors.append("Synchronized consistency checks failed")

if errors:
    print("\n".join("ERROR: " + e for e in errors))
    sys.exit(1)
print("MIBO Core validation passed.")
