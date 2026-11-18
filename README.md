# LG webOS Debloat

Reduce LG promotions and unused background activity on a rooted LG webOS TV. Keep Plex, YouTube, Developer Mode, Homebrew, and TV inputs.

The script hides selected built-in apps, turns off supported promotion settings, and stops selected apps from loading in advance. It keeps a private record so you can undo its changes. It does not uninstall apps or block ads inside YouTube, Plex, or other streaming services.

## Before you start

You need **a rooted LG webOS TV with working root SSH access**, plus Python 3.9+ and OpenSSH on your computer. Developer Mode alone is not enough. See the [connection and setup guide](docs/01-access.md) if you need help.

Support varies by model. Read-only planning has been tested on webOS 4.x; applying and undoing changes have automated tests but have not yet been verified on a real TV with this new script.

## Quick start

Download the [latest release](https://github.com/ChrisTitusTech/lg-debloat/releases/latest) on your computer (requires `curl`):

```sh
mkdir -p lg-debloat
cd lg-debloat
curl -fL --output lg-debloat.py https://github.com/ChrisTitusTech/lg-debloat/releases/latest/download/lg-debloat.py
python3 lg-debloat.py --version
python3 lg-debloat.py plan --host tv
```

Replace `tv` with your TV's IP address or SSH alias. SSH must already trust the TV's host key and connect using a key without a password prompt. For connection options, see the [script guide](docs/10-portable-tool.md#prerequisites).

**Review the plan first.** The command above does not change TV settings. To apply the default cleanup:

```sh
python3 lg-debloat.py apply --host tv
python3 lg-debloat.py status --host tv
```

Keep the generated `private/universal-state.json` file: it contains the original settings needed to undo this run. Do not share it. To undo:

```sh
python3 lg-debloat.py restore --host tv
```

For more cleanup, preview `plan --host tv --profile minimal`. Use the same `--profile minimal` option when applying. The [full script guide](docs/10-portable-tool.md) covers dry-runs, keeping specific apps, separate backups for multiple TVs, and recovery after errors.

## Full documentation

Start with the script guide. The other guides describe optional, model-specific work; the script does not install the custom Home screen or disable AirPlay for you.

- [Debloat script: options, backups, and undo](docs/10-portable-tool.md)
- [TV access and SSH troubleshooting](docs/01-access.md)
- [Backups and app inventory](docs/02-backup-inventory.md)
- [Advertising and a minimal Home screen](docs/03-home-and-advertising.md)
- [AirPlay, HomeKit, and optional apps](docs/04-optional-apps.md)
- [Daily landscape backgrounds](docs/05-backgrounds.md)
- [Post-install: block LG firmware updates](docs/09-post-install-updates.md)
- [Performance findings and testing limits](docs/06-results.md)
- [Recovery for the reference setup](docs/07-rollback.md)
- [Privacy and safe sharing](docs/08-privacy.md)
- [Reference setup, building, and development](docs/11-reference-and-development.md)

[MIT license](LICENSE). Photo credits and licensing are in [NOTICE](NOTICE).
