# Capability-aware LG debloat tool

`lg-debloat.py` is a single-file Python 3.9+ workstation tool for rooted LG webOS TVs. It aims to support multiple firmware generations by inspecting capabilities, not by assuming every LG TV has the same paths. **Universal compatibility is not claimed.** It does not run on non-webOS TVs or turn Developer Mode SSH into root.

## Upstream review

[Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv/tree/3ece7766ad5d6af79a2c4dd73e77b4b9623dfeca) targets Android/Google TV. Its README explicitly excludes LG webOS. Its ADB package commands cannot be reused here. The useful design ideas are inventory before changes, preserving core UI functions, and keeping a restore record.

[webos-debloat revision a269896](https://gist.github.com/lucataco/7c303b443934008a9031a55cfca552ec/a269896606b83a31bb85f2f25146b51ceb876fe6) inspired checking preload policy as a separate concern from tile visibility. Inspection found a newer regional-list format than the case-study TV uses. Isolated tests also confirmed backup writes during an apply dry-run, unconditional preload re-enabling, and loss of settings restoration state after a failed restore. This implementation is independently written, with explicit JSON parsing and a retryable recovery journal.

## What it supports

- Installed-app discovery through either known application-manager service name.
- Existing legacy `blockedAppList` / `blocked_applist` or modern `blockedSystemAppList` / `blocked_system_applist` JSON.
- Conservative hiding of Advertisement, Brand Shop, Store Demo and Sync Demo, only when installed.
- A `minimal` profile adding selected assistant/linking, media-viewer, help and Cheering Mode tiles.
- Disabling supported preload policies for the standalone browser, Google Assistant and Magic Link.
- Updating the existing writable `allowedApps` map when that persistent preload format is recognized.
- Switching supported promotion/ACR settings off, only if their current value is the expected string `on`.
- Optional Homebrew update-host blocking, preserving its original value for restore.
- Optional custom Home installation and Home-button routing on a recognized webOS configuration.

Hiding changes launcher visibility. It is not an uninstall, execution lock, or service shutdown. Preload policy changes do not close already-running apps. When no recognized writable preload configuration exists, the tool explicitly reports runtime-only changes; it does not modify `/etc/palm` or pretend persistence was established.

Plex, YouTube, Developer Mode, Homebrew, stock Home, settings, first-use UI and inputs are protected. The browser remains launchable; only its preload is targeted. `--keep APP_ID` excludes a selected app from both hiding and preload changes. Keep Plex and YouTube IDs adapted to your firmware if they differ from the documented identifiers.

## Prerequisites

- Python 3.9+ and OpenSSH on the workstation; no Python installation on the TV.
- Root SSH with a trusted host key already registered. Password prompts and unknown host keys are refused.
- `luna-send`, ordinary shell tools and writable `/var/preferences` on the TV.
- No other tool editing the same settings concurrently. Finish existing boot hooks first.

The tool opens one task-scoped SSH master, reuses its channels, then closes it. Its recovery journal is bound to the verified server host key, not a potentially reassigned LAN address. Use a separate journal for each TV. If the TV legitimately rotates its host key, investigate and plan recovery manually; do not blindly edit the journal binding.

## Install or update

Download the standalone script from the [latest release](https://github.com/ChrisTitusTech/lg-debloat/releases/latest). The custom Home option builds from a repository checkout.

```sh
mkdir -p lg-debloat
cd lg-debloat
curl -fL --output lg-debloat.py https://github.com/ChrisTitusTech/lg-debloat/releases/latest/download/lg-debloat.py
python3 lg-debloat.py --version
```

To update, download the script again into the same folder. Keep your `private/` folder and existing recovery journals. Read the release notes before updating. Releases also include `SHA256SUMS` to check the downloaded file; download both assets from the same version's release page and run `sha256sum -c SHA256SUMS` in their folder.

## Start with a plan

From the folder containing the downloaded script, using an SSH alias whose host key you have verified:

```sh
python3 lg-debloat.py plan --host tv
python3 lg-debloat.py plan --host tv --profile minimal --keep com.webos.app.music
```

To specify connection files:

```sh
python3 lg-debloat.py plan --host tv \
  --identity /path/to/dedicated-key \
  --known-hosts /path/to/trusted-known-hosts
```

If several regional lists exist, the tool refuses to choose the first one. Use `--region REGION_NAME` only after verifying the active existing file. Unknown schemas are errors; missing capabilities are reported as skipped. It never creates a guessed regional block list.

## Apply and inspect

```sh
python3 lg-debloat.py apply --host tv --profile minimal --dry-run
python3 lg-debloat.py apply --host tv --profile minimal --state private/tv-state.json
python3 lg-debloat.py status --host tv --state private/tv-state.json
```

A plan/dry-run does not create a journal, write preferences, or apply API mutations. Read requests may start an LG service on demand. Actual apply reruns discovery, records every original value before the first mutation, checks for changes since planning, and verifies each write by reading it back. The output lists operation labels; it does not print private preference contents.

The journal contains private device state. It is mode 0600, stored under ignored `private/` by default, and must not be committed. An existing journal is never overwritten by another apply. Status returns failure if state has drifted, including a runtime-only preload resetting after reboot. Do not run multiple apply/restore operations concurrently.

To opt into Homebrew update-host blocking, include `--block-updates` in plan and apply. This flag takes effect through Homebrew on reboot. It is weaker than the dedicated updater stop/executable-block workflow in [the post-install update guide](09-post-install-updates.md). This portable tool does not independently disable updater binaries or guarantee all update traffic is blocked.

## Optional custom Home

Use the full repository checkout and install LG's `ares-package` on your computer. To include the landscape photos, run `python3 tools/download-backgrounds.py` from the checkout before applying. Home can also use its dark background.

```sh
python3 lg-debloat.py plan --host tv --custom-home
python3 lg-debloat.py apply --host tv --custom-home --dry-run
python3 lg-debloat.py apply --host tv --custom-home
```

The option adds Home to the normal debloat plan. Apply packages the current launcher in a temporary directory, including the handoff that closes Home before launching YouTube or Plex. The script verifies installation and routes a short Home press to the custom launcher. Holding Home for at least 1.5 seconds opens LG Home. Home opens on demand, so there is no delayed boot launch competing with a selected app.

The TV must expose LG Home (`com.webos.app.home`) and the recognized key-filter order. The script refuses an existing custom Home install or route to preserve its original rollback path. Use the same `--state` path for status and restore. Restore reinstates the saved key-filter chain before deleting the managed filter and uninstalling the app. If an install response times out, let the TV installer finish before checking status or restoring.

## Restore, including partial failures

```sh
python3 lg-debloat.py restore --host tv --state private/tv-state.json --dry-run
python3 lg-debloat.py restore --host tv --state private/tv-state.json
```

Restore works in reverse order. It restores original JSON values, including originally disabled policies, rather than assuming everything was on. Preference files are restored semantically as JSON, not byte-for-byte formatting. Unknown fields are preserved when building an edit.

An operation is journaled as pending before it is sent, so a lost response after a successful write remains recoverable. Failed restorations retain their entries and return failure. If current state matches neither the saved original nor the desired value, restoration refuses to overwrite the external change; reconcile it manually and retry. There is no automatic rollback that could conceal a partially applied run. Keep the journal until you have verified recovery.

This is not a distributed transaction: another LG component can change a file between the check and write. Atomic file replacement limits partial-file damage, but serialize maintenance and verify the results.

## Persistence and scope boundaries

Custom Home is the only application this tool installs or uninstalls. For boot hooks, root, Homebrew, or the firmware-specific overlays, use the separate reference guides.

After an actual apply, test required apps and inputs and reboot when appropriate. Check status again. Add firmware-specific persistence only after determining how that firmware restores policy. Do not copy a newer TV's preload configuration over an older TV's configuration.

## Validation

Automated fixtures cover both block-list schemas, preserved unrelated fields, protected apps, excluded apps, ambiguous regions, unsupported persistence, read-only dry-run behavior, exact restoration, failed restore retries, interrupted writes, conflict refusal, private journal permissions, and multiplexed SSH setup. Custom Home fixtures also cover the install and restore order, existing Home routing, and asynchronous installer replies.

A read-only `minimal` plan was run successfully on the case-study webOS 4.x TV. It recognized the legacy block format and proposed browser/Google Assistant/Magic Link preload changes plus disabling `option/webOSPromotionVideo`. It correctly reported that preload persistence was not established and skipped missing settings. No changes were applied to that TV by this tool. Modern firmware support is fixture-tested, not hardware-verified; apply/restore hardware acceptance remains outstanding.
