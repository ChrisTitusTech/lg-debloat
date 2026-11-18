# LG webOS debloat and minimal Home

A documented, reversible cleanup of an older LG webOS TV: keep YouTube, Plex, and TV inputs; suppress LG advertising surfaces; disable unused apps; and open a lightweight Home screen with daily landscape backgrounds.

This includes a **capability-aware command-line tool plus a case study and reference implementation**. No script is verified universally across all LG models. It was developed on a 2019-era webOS 4.x TV running firmware 05.40.97. Paths, app IDs, private APIs, and rooting compatibility vary by model and firmware. The public app ID and storage paths have been anonymized; this exported edition has not been redeployed to the original TV.

## Portable debloat tool

Start with the [capability-aware tool guide](docs/10-portable-tool.md). It supports discovery, dry-run, apply, status and recovery through root SSH:

```sh
python3 lg-debloat.py plan --host tv
python3 lg-debloat.py apply --host tv --profile minimal --dry-run
```

Plans do not change TV settings. Review the plan before using `apply` without `--dry-run`. The tool detects legacy/newer block-list schemas, supported settings and preload policy; refuses unknown layouts; protects core apps; and journals original values for verified restoration. Hardware validation currently covers **read-only planning on webOS 4.x**, not universal apply/restore compatibility.

## What changed

- Removed unused third-party streaming apps through the normal uninstall mechanism.
- Installed Homebrew Channel and established key-authenticated root SSH.
- Replaced Advertisement and Brand Shop runtime files with inert bind-mounted overlays. The original read-only firmware files remain intact.
- Disabled Home Promotion, advertising cookies, and the welcome feature.
- Installed a local Home screen with YouTube, Plex, HDMI 1-3, Live TV, AV, and Component.
- Added short-press Home routing and a held-Home fallback to LG Home.
- Disabled AirPlay/HomeKit and 13 optional app entries using service controls, reversible executable overlays, and app launch locks.
- Added post-install firmware-update blocking with a dedicated startup hook.
- Added seven offline landscape photographs, changing by local calendar day and repeating weekly.

No firmware partitions were flashed or made writable. No blanket removal of system services was performed. Ads inside YouTube, Plex, broadcasts, or other third-party content are not blocked by this project.

## Read in order

1. [Access, SSH troubleshooting, and rooting](docs/01-access.md)
2. [Backups, inventory, and removable apps](docs/02-backup-inventory.md)
3. [Advertising and minimal Home](docs/03-home-and-advertising.md)
4. [AirPlay, HomeKit, and optional apps](docs/04-optional-apps.md)
5. [Daily landscape backgrounds](docs/05-backgrounds.md)
6. [Performance findings and verification limits](docs/06-results.md)
7. [Rollback and recovery](docs/07-rollback.md)
8. [Public repository privacy policy](docs/08-privacy.md)
9. **[Post-install: block LG firmware updates](docs/09-post-install-updates.md)**

## Repository layout

| Path | Contents |
| --- | --- |
| `lg-debloat.py` | Capability-aware workstation CLI (Python standard library + SSH) |
| `app/` | ES5-compatible webOS Home app; public ID `org.example.minimalhome` |
| `tv/home/` | Home key filter, advertising overlays, startup and rollback references |
| `tv/airplay/` | AirPlay/HomeKit disabling and rollback references |
| `tv/updates/` | Post-install LG firmware updater blocking and rollback |
| `tv/optional/` | Explicit 13-app selection, inert web app overlays, launch locks |
| `assets/landscapes.json` | Public source URLs, license labels, and image checksums |
| `tools/` | Local image download, rollback-payload preparation, privacy checks |
| `tests/` | Date rotation and Home-key behavior checks |

Read the guides before running anything under `tv/`: those scripts require root, make live changes, and assume verified paths. They do not install themselves. Keep backups and generated device configuration under ignored `private/`, outside public history.

## Build and check locally

Requires Python 3, Node.js, ShellCheck, shfmt, and LG's `ares-package` for packaging.

```sh
python3 tools/generate-icon.py
python3 tools/download-backgrounds.py
node tests/home.test.cjs
sh tools/check.sh
mkdir -p dist
ares-package app -o dist
```

The image downloader uses only Python's standard library. The TV never downloads wallpaper: JPEGs are packaged locally. Downloaded photos and build output are ignored by Git.

## Important limits

Root access was verified after reboot. The initial Home routing, advertising overlays, and settings also survived reboot. A follow-up reboot verified firmware-update blocking, absence of the disabled Apple/optional service processes, and all 13 optional-app launch locks. A boot hook runs after early startup, not before every LG process can start.

The original LG Home remains loaded for compatibility. This project does not promise a measured speedup, full firmware recovery, or compatibility with other TVs. Keep input handling, WebAppMgr, the compositor, media/DRM, and core TV services.

## Upstream sources

- [LG Developer Mode documentation](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [faultmanager-autoroot](https://github.com/throwaway96/faultmanager-autoroot)
- [webOS Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel)
- [Root compatibility checker](https://cani.rootmy.tv/)
- [US Fish & Wildlife Service photo sources](assets/landscapes.json)

Original code and documentation here are under [MIT](LICENSE). LG software, firmware, logos, exploit code, credentials, and private backups are not redistributed. Public-domain photo provenance is recorded separately in [NOTICE](NOTICE).
