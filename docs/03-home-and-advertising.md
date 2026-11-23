# 3. Advertising and minimal Home

For automated Home installation and Home-button routing, use [`--custom-home`](10-portable-tool.md#optional-custom-home). The steps below document the manual setup, advertising overlays, and optional boot hook.

## Restore data comes first

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

## Advertising overlays

`tv/home/overlays/` contains inert web pages, not LG's original files. `apply-overlays.sh` bind-mounts them over these observed paths:

- `/mnt/otncabi/usr/palm/applications/com.webos.app.adapp`
- `/mnt/otncabi/usr/palm/applications/com.webos.app.brandshop`

The original squashfs payloads remain on flash. This masks their usual runtime paths, does not reclaim firmware space, and is not a DNS/ad-network filter. The pages contain no external resources. Preserve TV, HDMI, ACR-related dependencies, media and DRM services; a name suggesting advertising is not enough evidence to delete a component.

The settings payload switches `adCookie`, `homePromotion`, and `welcomeFeature` off. LivePlus, customized advertising, screensaver advertising and Quick Start+ were already off in the original setup. Check their state on your own firmware rather than guessing key names.

## Build and install Home

Download the photos and package `app/` as described in the README. Install the resulting IPK using your established, authenticated app-install workflow. One option while Developer Mode is still the active access method is:

```sh
ares-install --device TV dist/org.example.minimalhome_1.0.0_all.ipk
ares-launch --device TV org.example.minimalhome
```

Do not reinstall Developer Mode just to run these commands after rooting. For a rooted TV, use its configured root-capable installer or LG's root `com.webos.appInstallService/dev/install` endpoint with the IPK copied to the TV. That endpoint is asynchronous: a successful subscription response alone does not prove installation. Verify the completed status and a subsequent launch.

The app uses `PalmServiceBridge` and `com.webos.applicationManager/launch` for each tile. IDs and inputs are firmware-specific; adjust `app/index.html` before packaging. There are three HDMI tiles because that matched the original setup, not because all LG TVs have three ports.

On the reference TV, webOS could reclaim the fullscreen custom Home app during a YouTube or Plex launch and immediately request an automatic reload. The streaming tiles marked `data-close-home` request a normal Home close before sending the app launch in the same JavaScript turn. If a streaming app is unavailable, the TV may return to the previous input or app. Press Home to return to the launcher. Input tiles use the standard launch path.

## Home key routing

The tiny `home-keyfilter.js` follows the native Qt key-filter interface:

- Short Home release launches `org.example.minimalhome`.
- Holding Home for at least 1.5 seconds then releasing requests LG Home.
- Other keys pass through the existing filter chain.
- Exceptions fall through to LG's next policy.

The filter belongs after screen saver and accessibility handling. Preserve the rest of the original chain. The stock fallback ID is `com.webos.app.home` in this reference; confirm the appropriate stock launcher on your firmware. The short-press route was tested on hardware; the held route was simulated in tests, not physically verified.

## Manual staging and activation

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

The hook mounts the advertising overlays, opens Home after a short delay, and reapplies the advertising settings. The key-filter configuration persists through configd. Stock startup may appear before the Homebrew hook runs.

## Approaches that did not solve the problem

LG repeatedly restored `homeAutoLaunch` to on. This implementation does not rely on disabling it. `defaultApps.home` was not changed. Closing the native Full Home process succeeded briefly but LG relaunched it, so the process was retained for compatibility. A newer firmware's blocked-app configuration format was not assumed to work on webOS 4.x.
