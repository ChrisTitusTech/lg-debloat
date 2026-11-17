# 9. Post-install: block LG firmware updates

Do this after Homebrew/root setup and before treating the debloat installation as complete. Disabling the Software Update tile or hiding update notifications does not stop the firmware updater. In the original setup, Homebrew initially reported `blockUpdates: false` and the updater was running.

This protection targets **LG firmware updates**. It does not disable Plex/YouTube app-store updates, Homebrew updates, or every connection to LG services.

## Protection layers

1. Enable Homebrew Channel's `blockUpdates` option. Its startup script redirects its known LG update hostnames to loopback.
2. Stop the Upstart `update` job and confirm that the dedicated updater process exits.
3. Bind-mount `/bin/true` over `/usr/sbin/update`, preventing that executable from running again during the current boot.
4. Preserve existing hosts entries and add IPv4/IPv6 loopback entries for `snu.lge.com`, `snu-dev.lge.com`, `su-dev.lge.com`, `su.lge.com`, and `su-ssl.lge.com`.
5. Install `00-block-lg-updates` as the first project hook under Homebrew's `init.d` directory and verify after reboot.

No firmware partition is made writable. The executable and hosts overrides are reversible mounts. The hosts list is not exhaustive protection against arbitrary future update infrastructure or hardcoded addresses; stopping and blocking the updater adds a separate layer.

## Before applying

Use an authenticated root session as described in [access](01-access.md). Verify these paths and the Upstart job on your firmware. Read the updater's current state without initiating a network check:

```sh
luna-send -n 1 -f luna://com.webos.service.update/getCurStatus '{}'
luna-send -n 1 -f luna://org.webosbrew.hbchannel.service/getConfiguration '{}'
```

Proceed only when the updater is idle. Do not interrupt an active installation or flashing operation. Capture the current Homebrew flag and keep it on the TV for rollback:

```sh
umask 077
mkdir -p /var/lib/lg-debloat/updates
if [ ! -f /var/lib/lg-debloat/updates/block-updates.before ]; then
  if [ -e /var/luna/preferences/webosbrew_block_updates ]; then
    echo true
  else
    echo false
  fi > /var/lib/lg-debloat/updates/block-updates.before
fi
cp /etc/init/update.conf /var/lib/lg-debloat/updates/update.conf.before
```

The saved files are private device state, not files to commit. The scripts require Homebrew's existing startup mechanism and the observed `/usr/sbin/update` path. They do not install root or modify the system Upstart configuration.

## Apply and persist

From the workstation, copy the two reference scripts:

```sh
scp -O -o ControlPath="$TV_SOCKET" tv/updates/*.sh \
  "root@$TV_HOST:/var/lib/lg-debloat/updates/"
```

In the interactive TV root shell:

```sh
chmod 700 /var/lib/lg-debloat/updates/*.sh
luna-send -n 1 -f luna://org.webosbrew.hbchannel.service/setConfiguration '{"blockUpdates":true}'
sh /var/lib/lg-debloat/updates/apply.sh
```

Inspect the JSON response and require `returnValue: true`. The script also ensures the persistent flag exists. It refuses an unexpected preexisting mount over the updater, and fails if the updater remains alive after a normal termination request. Do not install the hook if apply fails.

After apply succeeds:

```sh
cp /var/lib/lg-debloat/updates/apply.sh /var/lib/webosbrew/init.d/00-block-lg-updates
chmod 700 /var/lib/webosbrew/init.d/00-block-lg-updates
```

## Verify, including after reboot

```sh
initctl status update
# Expected: update stop/waiting
pidof update
# Expected: no PIDs (nonzero exit is expected).
test /usr/sbin/update -ef /bin/true
# Expected: success.
getent hosts snu.lge.com su.lge.com su-ssl.lge.com snu-dev.lge.com
# Expected: loopback addresses, not external servers.
luna-send -n 1 -f luna://org.webosbrew.hbchannel.service/getConfiguration '{}'
# Expected: blockUpdates true.
```

Verify both IPv4 and IPv6 entries in `/etc/hosts`; `getent hosts` may display only IPv6. Repeat apply once to check idempotence. Then reboot, reconnect with a fresh authenticated session, wait for Homebrew startup to complete, and repeat these checks. Confirm Home, Plex, YouTube and inputs still launch. Do not trigger a firmware check as a test: process, mount, configuration and resolution checks establish the intended protection without requesting an update.

## Verified deployment

On the case-study TV, the updater reported idle before installation. Live application and an idempotent repeat passed. After reboot, Homebrew reported `blockUpdates: true` and `failsafe: false`; the update job was stopped, no updater process or updater-owned TCP sockets were present, the executable override was active, and update hostnames resolved to loopback. Plex, YouTube, HDMI 1 and minimal Home reached foreground. This is runtime verification after startup, not a packet capture of the entire boot. The public update scripts use the same generic paths as the deployed scripts.

## Scope and boot-window limitation

Homebrew runs after some early LG startup. The native updater starts on `minimal-boot-done`, before this user hook may run. This protection is active after Homebrew startup, not a proof that no update request can ever leave the TV during early boot, failsafe mode, or after another component removes the mounts.

For a strict network-level guarantee, enforce an independent router/firewall policy before the TV connects. A DNS-only block cannot stop hardcoded-IP traffic or a different resolver. An allowlist can be stronger but must be tested with required streaming services. This project does not configure your router, and no network-wide guarantee is claimed.

Blocking firmware updates also blocks LG security/bug-fix delivery through this updater. Revisit the policy deliberately before a planned firmware change, including checking root-method compatibility and having recovery access.

## Rollback

```sh
sh /var/lib/lg-debloat/updates/rollback.sh
```

Rollback disables the project hook, removes only the recognized project mounts, and restores the recorded Homebrew flag. It does not immediately restart the updater. Reboot afterward so Homebrew rebuilds its hosts layer and the normal updater starts. If Homebrew blocking was originally enabled, it stays enabled. Rollback was statically checked, not executed on the final protected TV.
