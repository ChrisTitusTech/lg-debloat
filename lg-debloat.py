#!/usr/bin/env python3
"""Capability-aware LG webOS cleanup over authenticated root SSH. Python 3.9+."""

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

VERSION = "0.1"
HOME_ID = "org.example.minimalhome"
STOCK_HOME_ID = "com.webos.app.home"
HOME_CONFIG = "com.webos.service.config"
HOME_CHAIN = "com.webos.surfacemanager.keyFilters"
HOME_HANDLER = "handleMinimalHome"
HOME_FILTER = "/var/lib/lg-debloat-custom-home.js"
APP_INSTALLER = "com.webos.appInstallService/dev/"

PROTECTED = {
    STOCK_HOME_ID,
    "com.webos.app.fullhome",
    "com.webos.app.launcher",
    "com.palm.app.settings",
    "com.webos.app.settings",
    "com.webos.app.quicksettings",
    "com.palm.app.firstuse",
    "com.webos.app.firstuse",
    "com.webos.app.eula",
    "com.webos.app.livetv",
    "com.webos.app.inputcommon",
    "com.webos.app.inputlist",
    "com.webos.app.webapphost",
    "com.webos.app.browser",
    "com.webos.app.discovery",
    "com.webos.app.screensaver",
    "org.webosbrew.hbchannel",
    "com.palmdts.devmode",
    HOME_ID,
    "youtube.leanback.v4",
    "cdp-30",
}
HIDE = [
    "com.webos.app.adapp",
    "com.webos.app.brandshop",
    "com.webos.app.store-demo",
    "com.webos.app.sync-demo",
]
EXTRAS = [
    "com.webos.app.amazon-echo",
    "com.webos.app.google-home",
    "com.webos.app.googleassistant",
    "com.webos.app.music",
    "com.webos.app.photovideo",
    "com.webos.app.tvuserguide",
    "com.webos.app.self-diagnosis",
    "com.webos.app.cheeringtv",
]
PRELOAD = [
    "com.webos.app.browser",
    "com.webos.app.googleassistant",
    "com.webos.app.tips",
]
SETTINGS = [
    ("general", "homePromotion"),
    ("general", "adCookie"),
    ("general", "welcomeFeature"),
    ("general", "sportsAlarm"),
    ("option", "livePromotion"),
    ("option", "webOSPromotionVideo"),
    ("option", "promotionStreamer"),
    ("option", "livePlus"),
    ("other", "contentRecommendation"),
]
BLOCK_DIRS = {
    "/var/preferences/com.webos.applicationManager/blockedAppList": "blocked_applist",
    "/var/preferences/com.webos.applicationManager/blockedSystemAppList": "blocked_system_applist",
}
PRELOAD_FILE = "/var/preferences/webos-preload-manager-conf.json"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class Failure(RuntimeError):
    pass


def protected(app):
    return (
        app in PROTECTED
        or app.startswith("com.webos.app.hdmi")
        or app.startswith("com.webos.app.externalinput.")
    )


def validated_path(path):
    if not re.fullmatch(
        r"/var/preferences/[A-Za-z0-9_./-]+", path
    ) or ".." in path.split("/"):
        raise Failure("Refusing unexpected preference path")
    return path


def luna_command(uri, payload, options):
    return (
        "luna-send "
        + options
        + " "
        + shlex.quote("luna://" + uri)
        + " "
        + shlex.quote(json.dumps(payload, separators=(",", ":")))
    )


def installer_result(output, uri, status):
    for line in output:
        if not line.strip():
            continue
        try:
            result = json.loads(line)
        except ValueError as exc:
            raise Failure("Invalid TV app installer response") from exc
        if not isinstance(result, dict):
            raise Failure("Unexpected TV app installer response")
        details = result.get("details")
        if (
            result.get("returnValue") is False
            or (isinstance(details, dict) and "errorCode" in details)
            or (status == 31 and result.get("statusValue") == 25)
        ):
            raise Failure("TV app installer rejected " + uri)
        if result.get("statusValue") == status:
            return result
    raise Failure("TV app installer did not confirm completion of " + uri)


class SSH:
    def __init__(self, host, identity=None, known_hosts=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:%_-]*", host):
            raise Failure("Use a hostname, IP address, or SSH alias without a username")
        self.host = host
        self.temp = tempfile.TemporaryDirectory(prefix="lg-debloat-")
        self.socket = str(Path(self.temp.name) / "ssh.sock")
        self.options = [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "ServerAliveInterval=10",
            "-o",
            "ServerAliveCountMax=2",
            "-S",
            self.socket,
        ]
        if identity:
            self.options += [
                "-i",
                str(Path(identity).expanduser()),
                "-o",
                "IdentitiesOnly=yes",
            ]
        if known_hosts:
            self.options += [
                "-o",
                "UserKnownHostsFile=" + str(Path(known_hosts).expanduser()),
            ]
        self.target = "root@" + host
        self.binding = None

    def __enter__(self):
        try:
            # A background master can retain stderr. Use a file, not a PIPE,
            # so subprocess.run does not wait for the master's lifetime to end.
            with tempfile.TemporaryFile(mode="w+") as diagnostic:
                result = subprocess.run(
                    ["ssh", "-vv"]
                    + self.options
                    + ["-M", "-o", "ControlPersist=120", "-fnNT", self.target],
                    stdout=subprocess.DEVNULL,
                    stderr=diagnostic,
                    timeout=20,
                )
                diagnostic.seek(0)
                match = re.search(
                    r"Server host key: (\S+ SHA256:\S+)", diagnostic.read()
                )
            if result.returncode or not match:
                raise Failure(
                    "Cannot establish authenticated SSH and verified host-key binding"
                )
            self._ssh(["-O", "check"])
            if self.run("id -u").strip() != "0":
                raise Failure(
                    "Root SSH is required; Developer Mode SSH is insufficient"
                )
            self.binding = hashlib.sha256(match.group(1).encode()).hexdigest()
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def _ssh(self, extra, data=None):
        result = subprocess.run(
            ["ssh"] + self.options + extra + [self.target],
            input=data,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode:
            raise Failure(
                "SSH command failed; check authentication, host trust and connectivity"
            )
        return result.stdout

    def run(self, command, data=None):
        result = subprocess.run(
            ["ssh"] + self.options + [self.target, command],
            input=data,
            text=not isinstance(data, bytes),
            capture_output=True,
            timeout=30,
        )
        if result.returncode:
            raise Failure("Remote command failed: " + command.split()[0])
        return (
            result.stdout if isinstance(result.stdout, str) else result.stdout.decode()
        )

    def __exit__(self, *_):
        subprocess.run(
            ["ssh"] + self.options + ["-O", "exit", self.target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        self.temp.cleanup()

    def luna(self, uri, payload):
        command = luna_command(uri, payload, "-w 8000 -n 1 -f")
        # Keep an interactive channel's stdin open until Luna exits. Closing it
        # early makes some webOS releases silently discard the response.
        with (
            subprocess.Popen(
                ["ssh", "-tt"] + self.options + [self.target, command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as process,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            output = pool.submit(process.stdout.read)
            errors = pool.submit(process.stderr.read)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise Failure("Luna request timed out: " + uri)
            finally:
                process.stdin.close()
            raw = output.result()
            errors.result()
            if process.returncode:
                raise Failure("Luna SSH channel failed: " + uri)
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise Failure("No valid Luna response for " + uri) from exc
        if not isinstance(value, dict):
            raise Failure("Unexpected Luna response type")
        return value

    def installer_request(self, method, payload, status):
        uri = APP_INSTALLER + method
        command = luna_command(uri, dict(payload, subscribe=True), "-w 60000 -i")
        # Keep stdin open and read past the initial subscription acknowledgment.
        with (
            subprocess.Popen(
                ["ssh", "-tt"] + self.options + [self.target, command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            ) as process,
            ThreadPoolExecutor(max_workers=1) as pool,
        ):
            response = pool.submit(installer_result, process.stdout, uri, status)
            try:
                return response.result(timeout=65)
            except FutureTimeout as exc:
                raise Failure("Timed out awaiting TV app installer: " + method) from exc
            finally:
                if process.poll() is None:
                    process.kill()

    def install_home(self, package):
        directory = self.run("mktemp -d /tmp/lg-debloat-home.XXXXXX").strip()
        if not re.fullmatch(r"/tmp/lg-debloat-home\.[A-Za-z0-9]+", directory):
            raise Failure("Unexpected temporary package directory on TV")
        ipk = directory + "/home.ipk"
        try:
            self.run(
                f"set -eu; cat > {ipk}; chmod 644 {ipk}; chmod 755 {directory}",
                package,
            )
            response = self.installer_request(
                "install", {"id": HOME_ID, "ipkUrl": ipk}, 30
            )
            details = response.get("details")
            if not isinstance(details, dict) or details.get("packageId") != HOME_ID:
                raise Failure("TV app installer reported an unexpected package ID")
        finally:
            self.run(f"rm -f {ipk}; rmdir {directory}")

    def read_home_filter(self):
        result = self.run(
            f'set -eu; p={HOME_FILTER}; test ! -L "$p"; '
            'if [ -e "$p" ]; then test -f "$p"; printf "file\\n"; cat "$p"; fi'
        )
        return result.removeprefix("file\n") if result else None

    def write_home_filter(self, value):
        if value is None:
            self.run(f"rm -f {HOME_FILTER}")
        else:
            self.run(
                f'set -eu; p={HOME_FILTER}; t=$(mktemp "$p.XXXXXX"); '
                'trap \'rm -f "$t"\' EXIT; cat > "$t"; chmod 644 "$t"; '
                'test ! -e "$p"; test ! -L "$p"; ln "$t" "$p"',
                value,
            )

    def read_file(self, path):
        path = validated_path(path)
        raw = self.run(
            "if [ -f "
            + shlex.quote(path)
            + " ]; then cat "
            + shlex.quote(path)
            + "; fi"
        )
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise Failure("Malformed JSON in " + path) from exc
        if not isinstance(value, dict):
            raise Failure("Expected JSON object in " + path)
        return value

    def list_blocks(self):
        paths = " ".join(shlex.quote(p) for p in BLOCK_DIRS)
        # Only discover existing layouts; never invent a region or a new schema.
        return self.run(
            "for d in " + paths + '; do if [ -d "$d" ]; then '
            'for f in "$d"/*.json; do [ ! -f "$f" ] || printf "%s\\n" "$f"; '
            "done; fi; done"
        ).splitlines()

    def write_file(self, path, value):
        path = validated_path(path)
        # Existing regular files only; preserve ownership/mode and replace atomically.
        command = (
            "set -eu; p=" + shlex.quote(path) + '; test -f "$p"; test ! -L "$p"; '
            'mode=$(stat -c %a "$p"); owner=$(stat -c %u:%g "$p"); '
            't=$(mktemp "$p.lgdebloat.XXXXXX"); trap \'rm -f "$t"\' EXIT; '
            'cat > "$t"; chmod "$mode" "$t"; chown "$owner" "$t"; mv "$t" "$p"'
        )
        self.run(command, json.dumps(value, indent=2) + "\n")


def success(response, operation):
    if response.get("returnValue") is not True:
        raise Failure(operation + " rejected by TV")
    return response


class Device:
    def __init__(self, remote):
        self.remote = remote
        self.sam = None
        self.home_package = None

    def apps(self):
        for service in [
            "com.webos.applicationManager",
            "com.webos.service.applicationmanager",
        ]:
            result = self.remote.luna(service + "/listApps", {})
            if result.get("returnValue") is True and isinstance(
                result.get("apps"), list
            ):
                self.sam = service
                return {
                    a["id"]: a for a in result["apps"] if isinstance(a.get("id"), str)
                }
        raise Failure("No supported full application inventory API")

    def preloads(self):
        r = self.remote.luna("com.webos.service.preloadmanager/getPreloadPolicy", {})
        if r.get("returnValue") is not True:
            return None
        return {
            a["id"]: a["isEnabled"]
            for a in r.get("applications", [])
            if isinstance(a.get("isEnabled"), bool) and isinstance(a.get("id"), str)
        }

    def setting(self, category, key):
        r = self.remote.luna(
            "com.webos.settingsservice/getSystemSettings",
            {"category": category, "keys": [key]},
        )
        return r.get("settings", {}).get(key) if r.get("returnValue") is True else None

    def home_chain(self):
        response = success(
            self.remote.luna(
                HOME_CONFIG + "/getConfigs", {"configNames": [HOME_CHAIN]}
            ),
            "Read Home key filters",
        )
        configs = response.get("configs")
        chain = configs.get(HOME_CHAIN) if isinstance(configs, dict) else None
        if not isinstance(chain, list) or not all(
            isinstance(entry, dict) and isinstance(entry.get("handler"), str)
            for entry in chain
        ):
            raise Failure("Unsupported Home key filter configuration")
        return chain

    def check_home_unrouted(self):
        if any(custom_home_filter(entry) for entry in self.home_chain()):
            raise Failure(
                "Restore Home key routing before removing custom Home or its filter"
            )

    def read(self, change):
        kind = change["kind"]
        if kind == "file":
            return self.remote.read_file(change["path"])
        if kind == "setting":
            return self.setting(change["category"], change["key"])
        if kind == "preload":
            policies = self.preloads()
            return policies.get(change["id"]) if policies is not None else None
        if kind == "updates":
            r = self.remote.luna("org.webosbrew.hbchannel.service/getConfiguration", {})
            return r.get("blockUpdates") if r.get("returnValue") is True else None
        if kind == "home-app":
            home = self.apps().get(HOME_ID)
            if home is None:
                return None
            if not isinstance(home.get("version"), str):
                raise Failure("Cannot verify installed custom Home version")
            return home["version"]
        if kind == "home-filter":
            return self.remote.read_home_filter()
        if kind == "home-routing":
            return self.home_chain()
        raise Failure("Unknown operation kind")

    def write(self, change, value):
        kind = change["kind"]
        if kind == "file":
            self.remote.write_file(change["path"], value)
            return
        if kind == "home-app":
            if value is None:
                self.check_home_unrouted()
                self.remote.installer_request("remove", {"id": HOME_ID}, 31)
            elif self.home_package is None:
                raise Failure("Custom Home package is missing")
            else:
                self.remote.install_home(self.home_package)
            return
        if kind == "home-filter":
            if value is None:
                self.check_home_unrouted()
            self.remote.write_home_filter(value)
            return
        if kind == "setting":
            uri = "com.webos.settingsservice/setSystemSettings"
            payload = {
                "category": change["category"],
                "settings": {change["key"]: value},
            }
        elif kind == "preload":
            uri = "com.webos.service.preloadmanager/setPreloadPolicy"
            payload = {"application": {"id": change["id"], "isEnabled": value}}
        elif kind == "updates":
            uri = "org.webosbrew.hbchannel.service/setConfiguration"
            payload = {"blockUpdates": value}
        elif kind == "home-routing":
            uri = HOME_CONFIG + "/setConfigs"
            payload = {"configs": {HOME_CHAIN: value}}
        else:
            raise Failure("Unknown operation kind")
        success(self.remote.luna(uri, payload), change["label"])


def custom_home_filter(entry):
    return entry.get("handler") == HOME_HANDLER or entry.get("file") == HOME_FILTER


def checkout_path():
    return Path(__file__).resolve().parent


def plan_home(device, apps):
    if HOME_ID in apps:
        raise Failure(
            "Custom Home is already installed; use its original journal or manual rollback"
        )
    if STOCK_HOME_ID not in apps:
        raise Failure(
            "Custom Home requires the recognized LG Home app for the long-press fallback"
        )
    chain = device.home_chain()
    if any(custom_home_filter(entry) for entry in chain):
        raise Failure(
            "Existing custom Home key routing found; use its original rollback before installing"
        )
    if [entry["handler"] for entry in chain[:2]] != [
        "handleScreenSaver",
        "handleAccessibility",
    ]:
        raise Failure("Unfamiliar Home key filter order; no changes made")
    if device.remote.read_home_filter() is not None:
        raise Failure(
            "Custom Home filter file already exists; use its original recovery journal"
        )

    root = checkout_path()
    try:
        app = json.loads((root / "app/appinfo.json").read_text())
        filter_source = (root / "tv/home/home-keyfilter.js").read_text()
    except FileNotFoundError as exc:
        raise Failure(
            "--custom-home requires the full lg-debloat repository checkout"
        ) from exc
    version = app.get("version")
    if (
        app.get("id") != HOME_ID
        or not isinstance(version, str)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
    ):
        raise Failure("Unexpected custom Home app metadata")
    entry = {"file": HOME_FILTER, "handler": HOME_HANDLER}
    return [
        dict(
            kind="home-app", before=None, after=version, label="Install custom Home app"
        ),
        dict(
            kind="home-filter",
            before=None,
            after=filter_source,
            label="Install custom Home key filter",
        ),
        dict(
            kind="home-routing",
            before=chain,
            after=chain[:2] + [entry] + chain[2:],
            label="Route short Home press to custom Home and hold to LG Home",
        ),
    ]


def build_home(version):
    packager = shutil.which("ares-package")
    if packager is None:
        raise Failure("Install ares-package to build custom Home")
    root = checkout_path()
    with tempfile.TemporaryDirectory(prefix="lg-debloat-build-") as build_dir:
        build = Path(build_dir)
        shutil.copytree(root / "app", build / "app")
        if not (build / "app/icon.png").is_file():
            generator = build / "tools/generate-icon.py"
            generator.parent.mkdir()
            shutil.copyfile(root / "tools/generate-icon.py", generator)
            result = subprocess.run(
                [sys.executable, str(generator)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode or not (build / "app/icon.png").is_file():
                raise Failure("Could not generate the custom Home icon")
            (build / "app/icon.png").chmod(0o644)
        result = subprocess.run(
            [packager, str(build / "app"), "-o", str(build)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        package = build / f"{HOME_ID}_{version}_all.ipk"
        if result.returncode or not package.is_file():
            raise Failure(
                "ares-package failed to build the custom Home IPK: "
                + result.stderr.strip()
            )
        return package.read_bytes()


def plan(
    device,
    profile="conservative",
    region=None,
    keep=(),
    block_updates=False,
    custom_home=False,
):
    apps = device.apps()
    changes, notes = [], []
    if custom_home:
        changes.extend(plan_home(device, apps))
        notes.append(
            "Custom Home opens with the Home button. There is no delayed startup launch."
        )
    targets = HIDE + (EXTRAS if profile == "minimal" else [])
    targets = [a for a in targets if a in apps and a not in keep and not protected(a)]
    files = device.remote.list_blocks()
    if region:
        if not ID.fullmatch(region):
            raise Failure("Invalid region name")
        files = [f for f in files if Path(f).stem == region]
    if len(files) == 1:
        path = files[0]
        key = BLOCK_DIRS.get(str(Path(path).parent))
        original = device.remote.read_file(path)
        if (
            not key
            or not isinstance(original, dict)
            or not isinstance(original.get(key), list)
            or not all(isinstance(x, str) for x in original[key])
        ):
            raise Failure("Unrecognized app-block schema; no changes made")
        updated = copy.deepcopy(original)
        updated[key] += [a for a in targets if a not in updated[key]]
        if updated != original:
            changes.append(
                dict(
                    kind="file",
                    path=path,
                    before=original,
                    after=updated,
                    label="Hide installed app entries ("
                    + key
                    + "): "
                    + ", ".join(a for a in targets if a not in original[key]),
                )
            )
    elif len(files) > 1:
        raise Failure(
            "Multiple block lists discovered; choose an explicit --region or inspect layouts"
        )
    else:
        notes.append(
            "App hiding skipped: no single existing regional block-list file found."
        )
    policies = device.preloads()
    if policies is None:
        notes.append("Preloads skipped: API unavailable or rejected.")
    else:
        selected = [
            a
            for a in PRELOAD
            if a in apps and a not in keep and policies.get(a) is True
        ]
        config = device.remote.read_file(PRELOAD_FILE)
        allowed = config.get("allowedApps") if config else None
        if config is not None and not isinstance(allowed, dict):
            raise Failure("Unknown persistent preload schema; no changes made")
        updated = copy.deepcopy(config)
        for app in selected:
            if allowed is not None and isinstance(allowed.get(app), bool):
                updated["allowedApps"][app] = False
            else:
                notes.append(
                    app
                    + ": preload change is runtime-only; persistence not established."
                )
        if updated != config:
            changes.append(
                dict(
                    kind="file",
                    path=PRELOAD_FILE,
                    before=config,
                    after=updated,
                    label="Persist recognized preload policy entries",
                )
            )
        for app in selected:
            changes.append(
                dict(
                    kind="preload",
                    id=app,
                    before=True,
                    after=False,
                    label="Disable preload: " + app,
                )
            )
    for category, key in SETTINGS:
        value = device.setting(category, key)
        if value == "on":
            changes.append(
                dict(
                    kind="setting",
                    category=category,
                    key=key,
                    before=value,
                    after="off",
                    label="Disable setting: " + category + "/" + key,
                )
            )
        elif value != "off":
            notes.append(
                "Setting skipped (unsupported or unexpected value): "
                + category
                + "/"
                + key
            )
    if block_updates:
        change = dict(kind="updates", label="Enable Homebrew update-host blocking")
        value = device.read(change)
        if not isinstance(value, bool):
            raise Failure("Requested update blocking is unsupported; no changes made")
        if not value:
            changes.append(dict(change, before=False, after=True))
        notes.append(
            "Homebrew update-host blocking takes effect on reboot. See the post-install guide for stronger updater blocking."
        )
    return changes, notes


def save(path, state):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def apply(device, changes, path, binding):
    path = Path(path)
    if path.exists():
        raise Failure(
            "State file already exists; use status/restore, never overwrite a backup"
        )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation prevents a concurrent invocation from replacing a journal.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    state = {"version": 1, "binding": binding, "changes": copy.deepcopy(changes)}
    save(path, state)  # Entire original state committed before the first TV write.
    for change in state["changes"]:
        if device.read(change) != change["before"]:
            raise Failure("State changed since planning: " + change["label"])
        change["status"] = "pending"
        save(path, state)  # Pending also covers a lost reply after a successful write.
        device.write(change, change["after"])
        if device.read(change) != change["after"]:
            raise Failure("Readback failed: " + change["label"])
        change["status"] = "applied"
        save(path, state)
    return state


def restore(device, state, path, dry_run=False):
    errors = []
    for change in reversed(state["changes"]):
        if change.get("status") not in ("pending", "applied"):
            continue
        try:
            current = device.read(change)
            if current == change["before"]:
                if not dry_run:
                    change["status"] = "restored"
                    save(path, state)
                continue
            if current != change["after"]:
                raise Failure(
                    "Concurrent change; refusing to overwrite: " + change["label"]
                )
            if dry_run:
                print("Would restore:", change["label"])
                continue
            device.write(change, change["before"])
            if device.read(change) != change["before"]:
                raise Failure("Restore readback failed: " + change["label"])
            change["status"] = "restored"
            save(path, state)
        except Failure as exc:
            errors.append(str(exc))
    if errors:
        raise Failure(
            "; ".join(errors)
            + ". Recovery journal retained; correct the issue and retry."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("action", choices=["plan", "apply", "status", "restore"])
    parser.add_argument(
        "--host", required=True, help="Trusted root SSH hostname/IP/alias"
    )
    parser.add_argument("--identity")
    parser.add_argument("--known-hosts")
    parser.add_argument("--state", default="private/universal-state.json")
    parser.add_argument(
        "--profile", choices=["conservative", "minimal"], default="conservative"
    )
    parser.add_argument(
        "--region", help="Select an existing regional JSON basename; never guessed"
    )
    parser.add_argument("--keep", action="append", default=[], metavar="APP_ID")
    parser.add_argument(
        "--block-updates",
        action="store_true",
        help="Opt in to Homebrew update-host blocking",
    )
    parser.add_argument(
        "--custom-home",
        action="store_true",
        help="Install this checkout's Home launcher and remap a short Home-button press",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.custom_home and args.action not in ("plan", "apply"):
        parser.error("--custom-home is only used with plan or apply")
    os.umask(0o077)
    with SSH(args.host, args.identity, args.known_hosts) as remote:
        device = Device(remote)
        if args.action in ("plan", "apply"):
            changes, notes = plan(
                device,
                args.profile,
                args.region,
                args.keep,
                args.block_updates,
                custom_home=args.custom_home,
            )
            for change in changes:
                print("PLAN:", change["label"])
            for note in notes:
                print("NOTE:", note)
            print("Planned operations:", len(changes))
            if args.action == "apply" and not args.dry_run and changes:
                if args.custom_home:
                    version = next(
                        change["after"]
                        for change in changes
                        if change["kind"] == "home-app"
                    )
                    device.home_package = build_home(version)
                apply(device, changes, args.state, remote.binding)
                print(
                    "Applied and verified. Keep the private recovery journal:",
                    args.state,
                )
        else:
            state = json.loads(Path(args.state).read_text())
            if state.get("version") != 1 or state.get("binding") != remote.binding:
                raise Failure("Journal version or verified TV host key does not match")
            if args.action == "restore":
                restore(device, state, args.state, args.dry_run)
                print(
                    "Restore preview complete."
                    if args.dry_run
                    else "Restored; recovery journal retained."
                )
            else:
                drift = False
                for change in state["changes"]:
                    expected = (
                        change["after"]
                        if change.get("status") == "applied"
                        else change["before"]
                    )
                    matches = device.read(change) == expected
                    print("MATCH" if matches else "DRIFT", change["label"])
                    drift |= not matches
                if drift:
                    raise Failure("Some recorded state no longer matches the TV")


if __name__ == "__main__":
    try:
        main()
    except (Failure, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        raise SystemExit("ERROR: " + str(exc))
