# 4. Optional apps and Apple services

These are explicit opt-in feature removals. Disabling them does not imply a measured speed improvement. Apply only the selection you actually want; retain recovery access.

## AirPlay and HomeKit

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

## Optional app selection

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

## What the reference scripts do

- Stop Screen Share and the standalone browser service when managed by Upstart.
- Block dedicated `miracast`, `browser-service`, `amazon-alexa-adapter`, and `nlpadapter` host executable paths with reversible bind mounts.
- Replace twelve web app folders with inert local overlays.
- Call `com.webos.applicationManager/lockApp` with `{"id":"APP_ID","lock":true}` for all 13 entries, then close them.

The browser is deliberately excluded from the folder-overlay approach: LG's native launcher recreated a private mounted app environment that bypassed it. A subsequent launch lock correctly returned error `-102`, `app is locked`. All 13 selected IDs were tested for that rejection.

This prevents USB/local media viewers, screen mirroring, voice-assistant integration and the standalone browser from being used. Sign-in flows that require the standalone browser may also become unavailable. The shared web engine, voice input/conductor, core TV/input, audio/media and DRM services remain intact.

## Stage and validate

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
