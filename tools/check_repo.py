from pathlib import Path
import json
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "automation"))

import mibo_runner as mibo

DOI = "10.5281/zenodo.21936410"
errors: list[str] = []

required_current = [
    "README.md",
    "CITATION.cff",
    "LICENSE_NOTICE.md",
    "PRE_WAVE1_EXECUTION_GATE.md",
    "RELEASE_NOTES.md",
    "docs/README.md",
    "governance/MIBO_Canonical_Decisions_Register_v1.0.md",
    "governance/MIBO_Pilot_Boundary_Record_v1.0.md",
    "execution_records/Analysis_Execution_Record_Template.md",
    "execution_records/Configuration_Freeze_Record_Template.md",
    "automation/config/instrument_v1.0.json",
    "automation/config/services_v1.0.json",
    "automation/config/waves_v1.0.json",
    "automation/README.md",
    "automation/W01_RUNBOOK.md",
    "AGENTS.md",
]

for rel in required_current:
    if not (root / rel).exists():
        errors.append(f"Missing current v1.0 file: {rel}")

# Current public-facing metadata must point to the frozen v1.0 DOI.
for rel in (
    "README.md",
    "CITATION.cff",
    "PRE_WAVE1_EXECUTION_GATE.md",
    "RELEASE_NOTES.md",
    "governance/MIBO_Canonical_Decisions_Register_v1.0.md",
):
    path = root / rel
    if path.exists() and DOI not in path.read_text(encoding="utf-8"):
        errors.append(f"Canonical DOI missing from {rel}")

citation = (root / "CITATION.cff").read_text(encoding="utf-8") if (root / "CITATION.cff").exists() else ""
for expected in (
    'title: "MIBO Core Protocol Package v1.0"',
    'version: "1.0"',
    f'doi: "{DOI}"',
    "license: CC-BY-4.0",
):
    if expected not in citation:
        errors.append(f"CITATION.cff missing: {expected}")

# The old rc3 documents may remain only as historical provenance.
docs_readme = (root / "docs" / "README.md").read_text(encoding="utf-8") if (root / "docs" / "README.md").exists() else ""
if "historical" not in docs_readme.lower() or "v1.0-rc3" not in docs_readme:
    errors.append("docs/README.md must explicitly mark rc3 files as historical")

# Machine-readable scientific configuration is executable and must re-validate
# against the frozen query text hashes, panel count, wave count and calibration IDs.
errors.extend(mibo.verify_frozen_config())

instrument = json.loads((root / "automation" / "config" / "instrument_v1.0.json").read_text(encoding="utf-8"))
forms = instrument.get("forms", [])
if len(forms) != 24:
    errors.append(f"Instrument must contain 24 query forms, found {len(forms)}")
if len({f.get("item_id") for f in forms}) != 12:
    errors.append("Instrument must contain exactly 12 conceptual Item IDs")
if sum(bool(f.get("anchor")) and f.get("language") == "EN" for f in forms) != 4:
    errors.append("Instrument must contain exactly four English Anchor query forms")

# Current automation governance must preserve the UI/API distinction and the
# no-adaptive-observer rule.
agents = (root / "AGENTS.md").read_text(encoding="utf-8") if (root / "AGENTS.md").exists() else ""
for phrase in (
    "not an adaptive scientific observer",
    "Never substitute an API observation and label it Ecological Live",
    "Raw capture is append-only",
):
    if phrase not in agents:
        errors.append(f"AGENTS.md missing governance invariant: {phrase}")

if errors:
    print("\n".join("ERROR: " + e for e in errors))
    sys.exit(1)

print("MIBO Core v1.0 repository validation passed.")
