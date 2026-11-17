# 2. Backups and inventory

## Two backup stages

Before changes, the restricted Developer Mode filesystem and available inventories were captured. After rooting, an expanded archive included preferences, `/etc/palm`, original advertising application files, Brand Shop, and LivePlus files.

Neither archive is a full firmware/partition backup or a guaranteed hardware recovery image. Restricted access cannot back up paths it cannot read. Record missing files, stderr and exit status; do not label a partial archive complete. Keep private backups outside this repository and verify archive listings plus full decompression before relying on them.

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

Treat preferences and archives as secrets: they may contain tokens, account data, network details, and device identifiers. These example paths are not a universal backup selection.

## App inventory

The restricted SSH account could not list all normal TV apps. LG's paired remote-control interface (SSAP) supplied `ssap://com.webos.applicationManager/listApps` and `ssap://com.webos.applicationManager/listLaunchPoints` after the on-TV connection prompt was accepted. Keep the returned client pairing key private. Some attempted running-app SSAP endpoints returned 404; do not infer that no apps are running from an unsupported endpoint.

With root access, these Luna calls worked in an interactive TV shell:

```sh
luna-send -n 1 -f luna://com.webos.applicationManager/listApps '{}'
luna-send -n 1 -f luna://com.webos.applicationManager/running '{}'
luna-send -n 1 -f luna://com.webos.applicationManager/getForegroundAppInfo '{}'
```

Capture output locally into ignored `private/` files. App metadata includes `id`, `title`, `type`, `folderPath`, and `removable`; running-app results help map renderer PIDs. Do not equate an installed app with an active process. Multiple apps can use the shared WebAppMgr engine.

## Third-party apps removed

| App | ID |
| --- | --- |
| Prime Video | `amazon` |
| Disney+ | `com.disney.disneyplus-prod` |
| Netflix | `netflix` |
| Twitch | `tv.twitch.tv.starshot.lg` |
| Pluto TV stub | `com.plutotv.app` |

These were removed through LG's normal uninstall interface and verified absent in a fresh inventory. In the paired SSAP interface, the endpoint used was `ssap://com.webos.appInstallService/remove` with `{"id":"APP_ID"}`. Verify that your client and firmware support it and that `removable` is true before requesting removal. The rooted removal workflow used:

```sh
luna-send -i -f luna://com.webos.appInstallService/remove '{"id":"APP_ID","subscribe":true}'
```

Watch the asynchronous result for completion (`statusValue: 31` or `details.state: "removed"` in the observed responses), then stop the subscription and refresh the inventory. Initial acceptance is not completion. Do not use `rm -rf` on application directories.

Kept: Plex (`cdp-30`), YouTube (`youtube.leanback.v4`), Homebrew Channel (`org.webosbrew.hbchannel`), and the custom Home. Developer Mode's removal belongs to the root migration, not ordinary debloating.

The protected LG entries were handled separately with reversible disabling. A hidden tile, a launch lock, a stopped process, and an uninstall are different operations.
