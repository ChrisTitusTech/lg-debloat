#!/usr/bin/env python3
"""Download checksum-pinned public photographs; never upload local files."""
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1]
for item in json.loads((root / "assets/landscapes.json").read_text()):
    destination = root / "app" / item["file"]
    if destination.parent != root / "app/backgrounds":
        raise SystemExit("Unexpected destination in manifest")
    if not item["image"].startswith("https://www.fws.gov/"):
        raise SystemExit("Unexpected image source")
    if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == item["sha256"]:
        print("Already verified:", destination.name)
        continue
    with urllib.request.urlopen(item["image"], timeout=60) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise SystemExit("Image changed; review source before updating checksum: " + item["title"])
    if not data.startswith(b"\xff\xd8"):
        raise SystemExit("Expected JPEG")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(destination)
    print("Downloaded:", item["title"])
