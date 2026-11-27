# LG webOS Debloat

Reduce LG promotions and unnecessary app preloading on a rooted LG TV. Keep Plex, YouTube, TV inputs, Settings and Homebrew. Optionally install a simple replacement Home screen.

No firmware flashing, app-directory deletion, or third-party in-stream ad blocking. Changes are limited to recognized capabilities and recorded for restore.

## 1. Requirements

- A rooted LG webOS TV with working, trusted, key-authenticated root SSH. Developer Mode alone is not enough.
- Python 3.9+, Git and OpenSSH on your computer.
- [webOS CLI](https://webostv.developer.lge.com/develop/tools/cli-installation) (Node.js/npm) only if installing custom Home.

Replace `tv` in the commands below with your TV's SSH alias or LAN address. Verify the TV's host key before connecting.

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@tv id
git clone https://github.com/ChrisTitusTech/lg-debloat.git
cd lg-debloat
python3 lg-debloat.py --version
```

The SSH command must report UID 0. For connection troubleshooting, see the [reference guide](docs/reference.md#access-and-backups).

## 2. Choose and preview your cleanup

```sh
python3 lg-debloat.py plan --host tv
```

The default profile hides installed advertising, Brand Shop and demo tiles, disables supported promotion/ACR settings, and adjusts selected preload policies. It does not lock or uninstall apps. Unsupported settings are skipped.

For a leaner setup with more built-in tiles hidden:

```sh
python3 lg-debloat.py plan --host tv --profile minimal
```

### Optional: custom Home

For a launcher with YouTube, Plex, HDMI 1-3, Live TV, AV and Component, install the current LG CLI and preview the combined cleanup:

```sh
npm install -g @webos-tools/cli
python3 tools/download-backgrounds.py
python3 lg-debloat.py plan --host tv --profile minimal --custom-home
```

The background download is optional: Home works with a dark fallback. The seven checksum-pinned public-domain photos rotate daily and are bundled offline. Short-press Home opens the custom launcher; hold Home for at least 1.5 seconds to open LG Home. The existing LG Home stays installed.

The script refuses an unfamiliar key-filter chain or an existing custom Home installation. These input IDs and the long-press fallback are model-dependent.

## 3. Apply

Review the plan, then apply using the **same options**. For the default profile:

```sh
python3 lg-debloat.py apply --host tv
```

If you planned the minimal/custom Home setup, append `--profile minimal` or `--profile minimal --custom-home` respectively to the apply command.

Keep `private/universal-state.json`: the script records original values before changing anything and verifies each write. The journal is private, tied to the TV's verified SSH host key, and never overwritten by a new apply.

## 4. Verify and undo

```sh
python3 lg-debloat.py status --host tv
```

Test Plex, YouTube, Settings, the inputs you use and both Home-button actions (if custom Home was installed). Reboot when ready, then run status again. Some preload policies are runtime-only and may reset on reboot.

To preview and restore the original state:

```sh
python3 lg-debloat.py restore --host tv --dry-run
python3 lg-debloat.py restore --host tv
python3 lg-debloat.py status --host tv
```

The journal is retained after restore. Use a new `--state` path for a later apply; do not delete your only recovery record. If a write or restore fails, keep the journal, resolve the error and retry restore.

## Other options

| Option | Purpose |
| --- | --- |
| `--dry-run` | Preview apply or restore without changes. |
| `--keep APP_ID` | Preserve the selected app's visibility/preload policy; repeat as needed. |
| `--state private/other-tv.json` | Separate journals for different TVs or runs; use the same path for status/restore. |
| `--identity PATH`, `--known-hosts PATH` | Use explicit SSH key and trusted-host files. |
| `--region REGION_NAME` | Choose a verified existing regional block-list file when discovery finds several. |
| `--block-updates` | Optional Homebrew update-host blocking on reboot; also prevents normal firmware security fixes. |

```sh
python3 lg-debloat.py --help
```

The [standalone v0.1 release](https://github.com/ChrisTitusTech/lg-debloat/releases/tag/v0.1) supports cleanup without custom Home. This checkout is the upcoming 0.2 development version.

## Testing and reference

```sh
sh tools/check.sh
```

The checks use local fixtures, and also build a Home IPK if `ares-package` is available. See the [development requirements](docs/reference.md#development-and-privacy).

The original manual setup was tested on a 2019-era webOS 4.x TV. The portable script has read-only plan evidence on that TV and automated apply/restore tests; live apply/restore and the updated custom Home package still need hardware acceptance. No measured speedup or universal model compatibility is claimed.

See the single [reference guide](docs/reference.md) for manual firmware-specific overlays, AirPlay/optional apps, updates, backups, build steps, recovery and observed results.

[MIT license](LICENSE) | [Photo credits and licensing](NOTICE)
