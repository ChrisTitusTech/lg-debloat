#!/usr/bin/env python3
"""Generate private, device-specific payloads from successful read-only captures."""
import json
import os
from pathlib import Path
import sys

if len(sys.argv) != 4:
    raise SystemExit("Usage: prepare-home.py KEYFILTERS_JSON SETTINGS_JSON NEW_OUTPUT_DIR")
os.umask(0o077)
filters, settings = (json.loads(Path(p).read_text()) for p in sys.argv[1:3])
if filters.get("returnValue") is not True or settings.get("returnValue") is not True:
    raise SystemExit("Both captures must report returnValue true")
key = "com.webos.surfacemanager.keyFilters"
chain = filters["configs"][key]
if [x.get("handler") for x in chain[:2]] != ["handleScreenSaver", "handleAccessibility"]:
    raise SystemExit("Unfamiliar filter order: review manually before changing it")
if any(x.get("handler") == "handleMinimalHome" for x in chain):
    raise SystemExit("Custom filter already present: preserve the original rollback capture")
original = {k: settings["settings"][k] for k in ("adCookie", "homePromotion", "welcomeFeature")}
output = Path(sys.argv[3])
output.mkdir(parents=True, exist_ok=False)
new = chain[:2] + [{"file": "/var/lib/lg-debloat/home/home-keyfilter.js", "handler": "handleMinimalHome"}] + chain[2:]
for name, value in {
    "keyfilters-restore.json": {"configs": {key: chain}},
    "keyfilters-set.json": {"configs": {key: new}},
    "settings-restore.json": {"category": "general", "settings": original},
}.items():
    (output / name).write_text(json.dumps(value, indent=2) + "\n")
print("Created private payloads. Review before applying; do not commit them.")
