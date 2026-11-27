# Technical reference

The [README](../README.md) is the portable workflow. This guide records the
original 2019-era webOS 4.x / firmware 05.40.97 setup. The manual scripts use
firmware-specific private APIs, paths and boot hooks; they are not part of a
normal portable apply. Do not mix them with the portable tool on the same
settings. Verify the actual paths and preserve recovery access.

## Access and backups

The debloat tool assumes an already-rooted TV and trusted root SSH. See
[Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel) for
its SSH configuration. Developer Mode is a separate, restricted connection
(port 9922, user `prisoner`), not sufficient for the debloat tool. LG's
[Developer Mode documentation](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
describes its normal development workflow.

For an existing Developer Mode development connection, use LG's current
[webOS CLI](https://webostv.developer.lge.com/develop/tools/cli-installation):

```sh
npm install -g @webos-tools/cli
ares-setup-device
ares-novacom --device tv2 --getkey
ares-device --system-info --device tv2
```

On the original Fedora workstation, key retrieval worked but the handshake
failed with `signature verification failed`. A process-scoped compatibility
setting solved that case; do not globally weaken system crypto policy:

```sh
OPENSSL_ENABLE_SHA1_SIGNATURES=1 ares-device --system-info --device tv2
```

For manual commands below, open one authenticated SSH connection from the
workstation. The portable script already handles this automatically.

Example workstation setup; replace placeholders privately. Commands below assume OpenSSH on the workstation, not the TV.

```sh
umask 077
mkdir -p private
export TV_HOST='YOUR_TV_ADDRESS'
export TV_KEY='/path/to/your/dedicated/private-key'
export TV_SOCKET="$PWD/private/tv.sock"
ssh -M -S "$TV_SOCKET" -o ControlPersist=600 -o IdentitiesOnly=yes \
  -i "$TV_KEY" -fnNT "root@$TV_HOST"
ssh -S "$TV_SOCKET" -O check "root@$TV_HOST"
ssh -S "$TV_SOCKET" "root@$TV_HOST" id
# At the end of the task:
ssh -S "$TV_SOCKET" -O exit "root@$TV_HOST"
```

Verify the TV's host key rather than disabling host-key checking. Old TV SSH servers may require `scp -O` for legacy SCP. No SSH server configuration change was needed.

For repeated Luna calls, open an interactive SSH terminal with `ssh -tt -S "$TV_SOCKET" "root@$TV_HOST"`. This TV's `luna-send` could exit without a response when stdin was already closed. Reference shell hooks keep stdin open briefly with a sleep pipe. Always inspect the JSON `returnValue`; a shell exit status alone is insufficient.

### Backup and inventory

Back up your own settings and original files before manual changes. This is a partial archive, not a firmware or partition recovery image. Check errors, verify full decompression, and keep the archive private.

Example after verifying these exact paths on your firmware, from the workstation:

```sh
umask 077
mkdir -p private
ssh -S "$TV_SOCKET" "root@$TV_HOST" \
  'tar -czf - /var/preferences /etc/palm /mnt/otncabi/usr/palm/applications/com.webos.app.adapp /mnt/otncabi/usr/palm/applications/com.webos.app.brandshop' \
  > private/pre-changes.tar.gz
# Inspect command errors first. Then validate:
gzip -t private/pre-changes.tar.gz
tar -tzf private/pre-changes.tar.gz > private/archive-list.txt
sha256sum private/pre-changes.tar.gz > private/archive.sha256
```

With root access, these Luna calls worked in an interactive TV shell:

```sh
luna-send -n 1 -f luna://com.webos.applicationManager/listApps '{}'
luna-send -n 1 -f luna://com.webos.applicationManager/running '{}'
luna-send -n 1 -f luna://com.webos.applicationManager/getForegroundAppInfo '{}'
```

Third-party apps can be removed through LG's normal uninstall interface. The
original setup removed Prime Video (`amazon`), Disney+ (`com.disney.disneyplus-prod`),
Netflix (`netflix`), Twitch (`tv.twitch.tv.starshot.lg`) and Pluto TV
(`com.plutotv.app`). Verify that the app is removable before requesting removal,
wait for asynchronous completion and refresh the inventory. The portable tool
does not remove these apps.

## Portable tool details

- Recognizes legacy `blockedAppList` / `blocked_applist` and modern
  `blockedSystemAppList` / `blocked_system_applist` JSON; never guesses a
  missing regional list. Preserves unknown fields.
- Preload targets are the standalone browser, Google Assistant and Magic Link.
  Runtime-only policy changes do not terminate already-running apps.
- Disables promotion settings only when the known original value is `on`.
- A dry-run only reads state (read requests may start LG services on demand).
  Apply rechecks the values, records originals, marks writes pending, and
  verifies readback. Restore reverses the operations in order and refuses to
  overwrite unrelated changes. Preference JSON is restored semantically,
  not byte-for-byte.
- Do not run concurrent apply/restore commands or edit the journal's
  host-key binding. If a response times out, keep the journal and let the
  installer finish before checking status or restoring.

For the standalone release (without custom Home), download on the workstation:

```sh
mkdir -p lg-debloat
cd lg-debloat
curl -fL --output lg-debloat.py https://github.com/ChrisTitusTech/lg-debloat/releases/latest/download/lg-debloat.py
python3 lg-debloat.py --version
```

To verify the download, get both assets from the same version's release page
and run `sha256sum -c SHA256SUMS`. Keep existing journals when updating.

## Manual Home and advertising

Use the README's `--custom-home` for automated Home installation. The manual setup additionally includes advertising bind mounts and a Homebrew boot hook. The original ad/Brand Shop files remain on read-only firmware; this does not reclaim space.

### Save the original settings

Before touching the launcher, save the current key-filter chain and only the settings being changed. In an interactive root shell:

```sh
luna-send -n 1 -f luna://com.webos.service.config/getConfigs '{"configNames":["com.webos.surfacemanager.keyFilters"]}'
luna-send -n 1 -f luna://com.webos.settingsservice/getSystemSettings '{"category":"general","keys":["adCookie","homePromotion","welcomeFeature"]}'
```

Save the JSON responses as `private/keyfilters.json` and `private/general.json` on the workstation. Prepare narrowly scoped restoration payloads from your own TV:

```sh
python3 tools/prepare-home.py private/keyfilters.json private/general.json private/home-config
```

Review the resulting files. The helper requires the observed screen-saver/accessibility filter ordering and refuses unfamiliar layouts. It does not modify the TV.

`tv/home/overlays/` contains inert pages for
`com.webos.app.adapp` and `com.webos.app.brandshop` under
`/mnt/otncabi/usr/palm/applications/`. The settings payload disables
`adCookie`, `homePromotion` and `welcomeFeature`. Keep core TV, input,
media and DRM services. LG restored `homeAutoLaunch` on the reference TV;
the project does not depend on changing it or `defaultApps.home`.

### Build and install the launcher

```sh
python3 tools/generate-icon.py
python3 tools/download-backgrounds.py
mkdir -p dist
ares-package app -o dist
```

Photos are optional and checked against the manifest; only the current
image is loaded, with a dark fallback. Selection is based on the local
calendar day, stable all day, repeating every seven days. No wallpaper
network requests occur on the TV. See [NOTICE](../NOTICE) and
[photo sources](../assets/landscapes.json).

On a TV with an established authenticated Developer Mode app installer:

```sh
ares-install --device TV dist/org.example.minimalhome_1.0.0_all.ipk
ares-launch --device TV org.example.minimalhome
```

Do not reinstall Developer Mode merely to package or install Home on a
rooted system. Use the portable `--custom-home` option for a rooted TV.
The native key filter must be placed after the screen-saver and accessibility
handlers, preserving the remaining chain. Short Home press opens custom
Home; hold Home at least 1.5 seconds for LG Home. Streaming tiles close
custom Home before requesting YouTube/Plex launches.

### Manual staging and activation

After checking each target and backup, copy the `tv/home/` contents to `/var/lib/lg-debloat/home/` and the three generated JSON payloads into that same directory. For example, from the workstation:

```sh
ssh -S "$TV_SOCKET" "root@$TV_HOST" 'mkdir -p /var/lib/lg-debloat/home'
scp -O -r -o ControlPath="$TV_SOCKET" tv/home/. "root@$TV_HOST:/var/lib/lg-debloat/home/"
scp -O -o ControlPath="$TV_SOCKET" private/home-config/*.json "root@$TV_HOST:/var/lib/lg-debloat/home/"
```

In the interactive root shell, apply one stage at a time and inspect every response:

```sh
sh /var/lib/lg-debloat/home/apply-overlays.sh
luna-send -n 1 -f luna://com.webos.settingsservice/setSystemSettings "$(cat /var/lib/lg-debloat/home/settings-set.json)"
luna-send -n 1 -f luna://com.webos.service.config/setConfigs "$(cat /var/lib/lg-debloat/home/keyfilters-set.json)"
luna-send -n 1 -f luna://com.webos.applicationManager/launch '{"id":"org.example.minimalhome"}'
```

Only after those checks pass, install the executable boot hook:

```sh
chmod 700 /var/lib/lg-debloat/home/*.sh
cp /var/lib/lg-debloat/home/boot.sh /var/lib/webosbrew/init.d/40-lg-minimal-home
chmod 700 /var/lib/webosbrew/init.d/40-lg-minimal-home
```

The hook mounts the advertising overlays and reapplies the advertising settings. Short-press Home to open the custom launcher after power-on. The key-filter configuration persists through configd. An older hook opened Home automatically after a delay, which could take focus from an app you had already launched. Replace the installed hook with the current version if you used the older setup.

## Manual AirPlay and optional apps

These are independent opt-in features, not part of the portable profile.
They can disable screen mirroring, voice assistants, local media viewers,
and standalone-browser sign-in flows. Disabling features is not a measured
speed improvement.

### AirPlay and HomeKit

The original inspection found an AirPlay renderer, the AirPlay service, and HomeKit running. Setting `com.webos.app.home.supportAirplay` false alone did not stop the feature: LG's adaptor restarted it and reset the visible support setting.

The final reference in `tv/airplay/disable.sh`:

1. Stops the `airplay-adaptor` Upstart job.
2. Bind-mounts `/bin/true` over `/usr/sbin/airplay` and `/usr/sbin/homekit`.
3. Terminates those dedicated service processes if still present.
4. Launch-locks and closes the `airplay` UI, which had reappeared independently of the services.
5. Sets `other/supportAirplay` false.

The executable overrides prevent ordinary host-path launches but are not a general sandbox or security boundary. Private app mounts can bypass host file replacements; the UI launch lock matters.

Before activation, capture your own `supportAirplay` configuration and setting. The supplied rollback restores both to true, matching the original case; edit it if your saved values differ. Do not reset pairings or publish Apple/HomeKit credentials.

Stage the two scripts under `/var/lib/lg-debloat/airplay/`, run `disable.sh`, inspect responses and process state, then copy it to executable `/var/lib/webosbrew/init.d/45-disable-airplay` for startup. Rollback remains outside the boot-hook directory.

### Optional app selection

| Feature | App IDs |
| --- | --- |
| Store demonstrations | `com.webos.app.store-demo`, `com.webos.app.sync-demo` |
| Alexa UI/linking | `amazon.alexa.view`, `com.webos.app.amazon-echo` |
| Google Assistant/linking | `com.webos.app.googleassistant`, `com.webos.app.google-home` |
| Screen Share | `com.webos.app.miracast` |
| Music | `com.webos.app.music` |
| Photo & Video | `com.webos.app.photovideo` |
| Web Browser | `com.webos.app.browser` |
| User Guide | `com.webos.app.tvuserguide` |
| Quick Help | `com.webos.app.self-diagnosis` |
| Cheering Mode | `com.webos.app.cheeringtv` |

All 13 were marked non-removable by the TV. `targets.txt` is a reviewed selection, not a list of everything safe to delete. Removing a line from a future selection does not automatically undo a previous disable; run rollback first when changing an installed selection.

### What the reference scripts do

- Stop Screen Share and the standalone browser service when managed by Upstart.
- Block dedicated `miracast`, `browser-service`, `amazon-alexa-adapter`, and `nlpadapter` host executable paths with reversible bind mounts.
- Replace twelve web app folders with inert local overlays.
- Call `com.webos.applicationManager/lockApp` with `{"id":"APP_ID","lock":true}` for all 13 entries, then close them.

The browser is deliberately excluded from the folder-overlay approach: LG's native launcher recreated a private mounted app environment that bypassed it. A subsequent launch lock correctly returned error `-102`, `app is locked`. All 13 selected IDs were tested for that rejection.

This prevents USB/local media viewers, screen mirroring, voice-assistant integration and the standalone browser from being used. Sign-in flows that require the standalone browser may also become unavailable. The shared web engine, voice input/conductor, core TV/input, audio/media and DRM services remain intact.

### Stage and validate

Review the target folders and dedicated service executables on your TV. Copy `tv/optional/` contents to `/var/lib/lg-debloat/optional/`, including `targets.txt`, overlays, and rollback. Run `sh /var/lib/lg-debloat/optional/apply.sh` in an interactive root session and inspect its output.

These shell references print Luna responses but do not parse JSON failures into a failing shell status. An `app is not running` result during close is expected for inactive apps; a failed lock or mount is not. Stop and reconcile any unexpected result before enabling startup.

Once verified, copy `apply.sh` to executable `/var/lib/webosbrew/init.d/46-disable-optional`. Do not copy `rollback.sh` into that directory.

Check launches and running apps:

```sh
luna-send -n 1 -f luna://com.webos.applicationManager/launch '{"id":"com.webos.app.browser"}'
# Expected: returnValue false, errorCode -102, app is locked.
luna-send -n 1 -f luna://com.webos.applicationManager/running '{}'
initctl status miracast
```

Verify every selected ID, then confirm Plex, YouTube, inputs, Settings and Home still function. Check that dedicated processes remain absent after app switching. Do not sum renderer RSS values as guaranteed savings.

The initial installation was not reboot-tested. A follow-up reboot during firmware-update protection deployment verified the 13 launch locks and absence of the dedicated Apple/optional service processes. An unexpected restart of the application manager can also discard runtime locks until they are reapplied. The reference is not a permanent on-disk uninstall or an access-control guarantee.

## Firmware-update policy

The portable `--block-updates` only sets Homebrew's update-host blocking
flag, effective on reboot. It is opt-in and also prevents normal firmware
security and bug fixes while enabled. The inherited `tv/updates/` reference
is specific to the original firmware; it is not a guarantee that no update
traffic can leave the TV, especially during early startup. Never interrupt
an active firmware update. The portable tool does not modify updater
binaries or router settings.

The original manual deployment stopped the updater and verified its state
after reboot. The scripts and rollback remain in `tv/updates/`; use the
actual saved original Homebrew flag, not a guessed value.

## Manual rollback

Keep rollback scripts and the actual saved configuration on the TV and on the workstation. Run rollback after pending startup hooks have finished; otherwise a delayed hook could reapply a setting. Preserve an authenticated root session while testing changes.

Run the relevant script in a root TV shell:

```sh
# Remove firmware-update protection (reboot afterward):
sh /var/lib/lg-debloat/updates/rollback.sh
# Restore optional apps and Screen Share:
sh /var/lib/lg-debloat/optional/rollback.sh
# Restore AirPlay/HomeKit (edit restored settings to match your saved originals):
sh /var/lib/lg-debloat/airplay/rollback.sh
# Restore original Home key filters, ad settings and advertising payload views:
sh /var/lib/lg-debloat/home/rollback.sh
```

Each script disables its own startup hook before restoring runtime state. Optional-app rollback unlocks selected IDs and unmounts replacements; a reboot afterward refreshes cached app metadata. Home rollback requires `keyfilters-restore.json` and `settings-restore.json` generated from your own TV before modification. It opens LG Full Home as the fallback; confirm that ID exists on your firmware.

The public AirPlay rollback moves `45-disable-airplay` out of the hook directory and restores the original true settings observed in the case study. Do not assume those values describe a different TV. The reference scripts do not reconcile unrelated overlays installed by other projects; inspect mount ownership before unmounting.

Rollback does not unroot, reinstall removed streaming apps, restore logins,
reverse firmware updates or recover a damaged partition. Manual rollback
scripts were statically checked, not executed end-to-end against the final TV.
Use the README's restore command for portable-tool operations.

## Hardware evidence

These are anonymized observations from one TV, not benchmark promises. Hardware identity, network addresses, account information, raw inventories and screenshots are intentionally omitted.

### Idle sample after initial cleanup

- Approximately 964 MiB total RAM; about 342-346 MiB available.
- CPU 91-95% idle over three five-second intervals.
- Roughly 101 MiB of swap occupied, with no sustained swapping observed.
- App storage only 18% used; deleting more inactive app files was not a storage remedy.
- A high load average coexisted with low CPU use and many TV driver tasks in uninterruptible sleep. It was not evidence of CPU saturation by itself.

Approximate proportional set size (PSS), which apportions shared pages: AirPlay renderer/services plus HomeKit 46 MiB; native LG Full Home 32 MiB; minimal Home renderer 22 MiB. These are attributed footprints, not guaranteed reclaimable memory. Core `tvservice` was a persistent CPU user, but is necessary for TV operation. A brief `sdx` spike did not persist and did not justify disabling an unidentified service.

Plex and YouTube were not playing during this sample. No streaming, decoding, network-throughput, frame-time or before/after speed benchmark was performed. For playback complaints, profile the actual affected stream first.

Keep Quick Start+ off when prioritizing clean startup over rapid power-on. [LG's memory troubleshooting](https://www.lg.com/uk/support/product-support/troubleshoot/help-library/cs-CT00008333-20154522128518/) recommends disabling it for memory-related app problems. Do not disable swap or periodically drop caches as a substitute for diagnosing pressure.

### What was verified on hardware

| Change | Evidence | Limit |
| --- | --- | --- |
| Root/Homebrew | Fresh key-authenticated root connection after reboot | No future firmware guarantee |
| Normal app removal | Fresh inventory showed selected apps absent | No firmware-space recovery |
| Home/advertising | Key route, mounts, settings and custom foreground survived reboot | Native Home remains resident |
| Navigation | Arrow/OK opened YouTube, Plex and HDMI 1 | Not every remote button tested |
| Inputs | All six destination IDs reached foreground and Home returned | No connected-source picture/audio test |
| AirPlay/HomeKit | Dedicated services absent after follow-up reboot; UI launch lock installed | Not a network-wide block |
| Optional apps | All 13 launch attempts rejected with -102 after follow-up reboot; dedicated services absent | Locks depend on application-manager state |
| LG firmware updates | Homebrew flag true, updater stopped, executable blocked and update hostnames loopback after reboot | Early boot precedes Homebrew; no router policy installed |
| Preserved apps | Plex, YouTube, HDMI 1 and minimal Home reached foreground | Launch success is not playback verification |
| Daily background | TV screenshot visually checked; date logic tested locally | No live clock manipulation or midnight wait |

Plex initially appeared to fail a short foreground check; a later check showed it had opened. Allow bounded polling for cold startup rather than assuming an immediate launch response means it is already foreground.

### Live portable-tool follow-up

The existing manual setup was left installed. A live minimal plan and apply
dry-run agreed on four remaining operations:

- Add Advertisement (`com.webos.app.adapp`) and Brand Shop to the existing
  legacy block list.
- Disable browser and Magic Link (`com.webos.app.tips`) preload policies.
- Disable `option/webOSPromotionVideo`.

Apply recorded all four originals in a separate private journal and verified
each write. Status matched all four, restore preview listed all four undo
operations without changing the journal, and a repeat minimal plan reported
zero operations. Six supported promotion/ACR settings read back as off.
Three unsupported or unexpected settings were skipped: `general/sportsAlarm`,
`option/livePromotion`, and `other/contentRecommendation`.
Google Assistant was unavailable in the app inventory, so its preload entry
was not touched. The browser and Magic Link changes are runtime-only on this
firmware; persistence after reboot was not tested.

The manual advertising overlays (2/2) and optional-app overlays (12/12)
were still present. All 13 optional apps plus AirPlay were locked or
unavailable. AirPlay support was disabled, Homebrew's existing update-host
blocking setting was enabled, the custom Home key filter was present, and
the installed Home had the streaming handoff and startup focus fixes.
The standalone browser remained locked and its host override intact, but
one browser-service process persisted in a separate app environment; the
test did not forcibly terminate it.

After apply, YouTube, Plex (on retry), and HDMI 1 reached foreground from
custom Home, and short Home returned to the launcher. The TV was left on
custom Home with cleanup active. No live rollback, fresh installation of
the exported custom Home, or reboot was performed in this run. Modern
schemas, held-Home behavior and full restore remain automated-test evidence,
not hardware acceptance. Launch success is not playback verification.

## Development and privacy

| Path | Contents |
| --- | --- |
| `lg-debloat.py` | Portable Python/SSH tool |
| `app/` | ES5-compatible webOS launcher |
| `tv/` | Firmware-specific manual scripts and inert overlays |
| `assets/landscapes.json` | Pinned public photo sources |
| `tools/`, `tests/` | Local utilities and automated checks |

Run local validation from the checkout. Requires Python, Node.js, ShellCheck
and shfmt; add LG's `ares-package` to build Home.

```sh
sh tools/check.sh
python3 tools/generate-icon.py
ares-package app -o dist
```

Keep keys, pairing tokens, household identifiers, raw diagnostics, backups,
journals, unreviewed screenshots and generated packages outside Git. The
README includes only manually reviewed, checksum-pinned TV and terminal
captures in `docs/screenshots/`; an advertisement settings capture was excluded because
it showed a device-specific advertising identifier. The screenshots depict
the pre-existing Home setup and an actual portable-tool apply on that TV. Review
`git diff --cached` and run `python3 tools/privacy-check.py` after staging;
the scanner is heuristic. Use a public-safe commit identity. If a secret
was committed, rotate it and address history rather than just deleting the
working copy. No proprietary LG software or upstream exploit code is
distributed here.

See [MIT](../LICENSE) and [NOTICE](../NOTICE) for licensing and attribution.
