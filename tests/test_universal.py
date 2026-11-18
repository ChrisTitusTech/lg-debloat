import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("debloat", "lg-debloat.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Remote:
    def __init__(self, schema="legacy"):
        self.files = {}
        directory, key = list(m.BLOCK_DIRS.items())[0 if schema == "legacy" else 1]
        self.block = directory + "/TEST.json"
        self.files[self.block] = {key: ["com.example.existing"], "untouched": 7}
        self.files[m.PRELOAD_FILE] = {
            "allowedApps": {"com.webos.app.browser": True},
            "other": 9,
        }
        self.policies = {
            "com.webos.app.browser": True,
            "com.webos.app.googleassistant": False,
            "youtube.leanback.v4": True,
        }
        self.settings = {
            ("general", "homePromotion"): "on",
            ("option", "livePlus"): "off",
        }
        self.flag = False
        self.writes = []
        self.fail_setting = False

    def list_blocks(self):
        return [p for p in self.files if p != m.PRELOAD_FILE]

    def read_file(self, path):
        return copy.deepcopy(self.files.get(path))

    def write_file(self, path, value):
        self.writes.append(("file", path))
        self.files[path] = copy.deepcopy(value)

    def luna(self, uri, payload):
        method = uri.rsplit("/", 1)[1]
        if method == "listApps":
            return {
                "returnValue": True,
                "apps": [
                    {"id": x}
                    for x in [
                        "com.webos.app.adapp",
                        "com.webos.app.browser",
                        "com.webos.app.googleassistant",
                        "youtube.leanback.v4",
                        "com.webos.app.fullhome",
                    ]
                ],
            }
        if method == "getPreloadPolicy":
            return {
                "returnValue": True,
                "applications": [
                    {"id": k, "isEnabled": v} for k, v in self.policies.items()
                ],
            }
        if method == "getSystemSettings":
            key = payload["keys"][0]
            value = self.settings.get((payload["category"], key))
            return {"returnValue": value is not None, "settings": {key: value}}
        if method == "getConfiguration":
            return {"returnValue": True, "blockUpdates": self.flag}
        self.writes.append((method, copy.deepcopy(payload)))
        if method == "setPreloadPolicy":
            self.policies[payload["application"]["id"]] = payload["application"][
                "isEnabled"
            ]
        elif method == "setSystemSettings":
            if self.fail_setting:
                return {"returnValue": False}
            for k, v in payload["settings"].items():
                self.settings[payload["category"], k] = v
        elif method == "setConfiguration":
            self.flag = payload["blockUpdates"]
        else:
            raise AssertionError(method)
        return {"returnValue": True}


class Universal(unittest.TestCase):
    def test_both_schemas_plan_has_no_writes_and_preserves_other_fields(self):
        for schema in ["legacy", "modern"]:
            r = Remote(schema)
            changes, _ = m.plan(m.Device(r))
            self.assertFalse(r.writes)
            block = changes[0]
            self.assertEqual(block["after"]["untouched"], 7)
            self.assertNotEqual(block["after"], block["before"])
            self.assertFalse(any(c.get("id") == "youtube.leanback.v4" for c in changes))
            self.assertFalse(
                any(c.get("id") == "com.webos.app.googleassistant" for c in changes)
            )

    def test_unsupported_preload_persistence_runtime_only(self):
        r = Remote()
        del r.files[m.PRELOAD_FILE]
        changes, notes = m.plan(m.Device(r))
        self.assertTrue(any("runtime-only" in n for n in notes))
        self.assertFalse(any(c.get("path") == m.PRELOAD_FILE for c in changes))

    def test_ambiguous_region_refuses(self):
        r = Remote()
        r.files[r.block.replace("TEST", "OTHER")] = copy.deepcopy(r.files[r.block])
        with self.assertRaises(m.Failure):
            m.plan(m.Device(r))
        m.plan(m.Device(r), region="TEST")
        self.assertFalse(r.writes)

    def test_schema_rejects_wrong_key(self):
        r = Remote()
        r.files[r.block] = {"unexpected": []}
        with self.assertRaises(m.Failure):
            m.plan(m.Device(r))
        self.assertFalse(r.writes)

    def test_keep_applies_to_hiding_and_preloads(self):
        r = Remote()
        changes, _ = m.plan(
            m.Device(r), keep=["com.webos.app.adapp", "com.webos.app.browser"]
        )
        self.assertFalse(any(c["kind"] in ["file", "preload"] for c in changes))

    def test_round_trip_and_immutable_backup(self):
        r = Remote()
        d = m.Device(r)
        before = copy.deepcopy((r.files, r.policies, r.settings, r.flag))
        changes, _ = m.plan(d, block_updates=True)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "journal.json"
            state = m.apply(d, changes, path, "fixture")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(all(c["status"] == "applied" for c in state["changes"]))
            with self.assertRaises(m.Failure):
                m.apply(d, changes, path, "fixture")
            m.restore(d, state, path)
            self.assertEqual(before, (r.files, r.policies, r.settings, r.flag))
            self.assertTrue(path.exists())

    def test_failed_restore_retains_retryable_journal(self):
        r = Remote()
        d = m.Device(r)
        changes, _ = m.plan(d)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "journal.json"
            state = m.apply(d, changes, path, "fixture")
            r.fail_setting = True
            with self.assertRaises(m.Failure):
                m.restore(d, state, path)
            self.assertTrue(
                any(
                    c["status"] == "applied"
                    for c in json.loads(path.read_text())["changes"]
                )
            )
            r.fail_setting = False
            m.restore(d, state, path)
            self.assertEqual(r.settings["general", "homePromotion"], "on")

    def test_pending_write_restored_after_lost_reply(self):
        r = Remote()
        d = m.Device(r)
        changes, _ = m.plan(d)
        original = d.write

        def write_then_fail(c, v):
            original(c, v)
            raise m.Failure("lost response")

        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "journal.json"
            d.write = write_then_fail
            with self.assertRaises(m.Failure):
                m.apply(d, changes, path, "fixture")
            state = json.loads(path.read_text())
            self.assertEqual(state["changes"][0]["status"], "pending")
            d.write = original
            m.restore(d, state, path)
            self.assertEqual(r.files[r.block], changes[0]["before"])

    def test_external_change_is_preserved_and_dry_restore_never_writes(self):
        r = Remote()
        d = m.Device(r)
        changes, _ = m.plan(d)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "journal.json"
            state = m.apply(d, changes, path, "fixture")
            saved = path.read_bytes()
            writes = len(r.writes)
            m.restore(d, state, path, dry_run=True)
            self.assertEqual(path.read_bytes(), saved)
            self.assertEqual(len(r.writes), writes)
            r.files[r.block]["external"] = True
            with self.assertRaises(m.Failure):
                m.restore(d, state, path)
            self.assertTrue(r.files[r.block]["external"])

    def test_protected_ids_and_paths(self):
        for a in [
            "com.webos.app.fullhome",
            "com.webos.app.hdmi4",
            "com.webos.app.externalinput.av1",
            "cdp-30",
        ]:
            self.assertTrue(m.protected(a))
        for p in [
            "/etc/hosts",
            "/var/preferences/../etc/hosts",
            "/var/preferences/a;bad",
        ]:
            with self.assertRaises(m.Failure):
                m.validated_path(p)

    def test_help_does_not_require_connection(self):
        self.assertEqual(
            subprocess.run(
                ["python3", "lg-debloat.py", "--help"], capture_output=True
            ).returncode,
            0,
        )

    def test_cli_apply_dry_run_creates_no_journal(self):
        from unittest.mock import patch
        from contextlib import nullcontext, redirect_stdout
        import io

        r = Remote()
        r.binding = "fixture"
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "new-directory/journal.json"
            with (
                patch.object(m, "SSH", return_value=nullcontext(r)),
                patch.object(
                    m.sys if hasattr(m, "sys") else __import__("sys"),
                    "argv",
                    [
                        "lg-debloat.py",
                        "apply",
                        "--host",
                        "example-tv",
                        "--dry-run",
                        "--state",
                        str(p),
                    ],
                ),
            ):
                with redirect_stdout(io.StringIO()):
                    m.main()
            self.assertFalse(p.parent.exists())
            self.assertFalse(r.writes)

    def test_ssh_master_uses_file_for_background_diagnostics(self):
        from unittest.mock import patch
        from types import SimpleNamespace

        commands = []

        def run(command, **kwargs):
            commands.append(command)
            if "-vv" in command:
                self.assertNotEqual(kwargs["stderr"], subprocess.PIPE)
                kwargs["stderr"].write(
                    "debug1: Server host key: ssh-ed25519 SHA256:fixture\n"
                )
                kwargs["stderr"].flush()
            return SimpleNamespace(returncode=0, stdout="0\n", stderr="")

        with patch.object(m.subprocess, "run", side_effect=run):
            with m.SSH("example-tv") as connection:
                self.assertTrue(connection.binding)
        self.assertEqual(sum("-M" in c for c in commands), 1)
        self.assertTrue(any("exit" in c for c in commands))
