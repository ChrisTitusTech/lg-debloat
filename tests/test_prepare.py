import json
from pathlib import Path
import subprocess
import tempfile
import unittest

class Preparation(unittest.TestCase):
    def test_preserves_restore_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            chain = [{"handler": h, "file": "/example.js"} for h in
                     ["handleScreenSaver", "handleAccessibility", "handleSystemKeys"]]
            (p / "filters.json").write_text(json.dumps({"returnValue": True, "configs": {
                "com.webos.surfacemanager.keyFilters": chain}}))
            original = {"adCookie": "on", "homePromotion": "off", "welcomeFeature": "on"}
            (p / "settings.json").write_text(json.dumps({"returnValue": True, "settings": original}))
            command = ["python3", "tools/prepare-home.py", str(p / "filters.json"),
                       str(p / "settings.json"), str(p / "output")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            restore = json.loads((p / "output/keyfilters-restore.json").read_text())
            self.assertEqual(restore["configs"]["com.webos.surfacemanager.keyFilters"], chain)
            self.assertEqual(json.loads((p / "output/settings-restore.json").read_text())["settings"], original)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            chain.reverse()
            (p / "filters.json").write_text(json.dumps({"returnValue": True, "configs": {
                "com.webos.surfacemanager.keyFilters": chain}}))
            command[-1] = str(p / "other-output")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((p / "other-output").exists())
