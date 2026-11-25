# 1. Access and rooting

## Initial Developer Mode connection

These steps set up the restricted Developer Mode connection. The debloat script needs root SSH instead; see [Root and Homebrew Channel](#root-and-homebrew-channel) below before modifying an already-rooted TV.


- Sign up for an LG Developer Account: https://webostv.developer.lge.com/develop/getting-started/developer-mode-app
_Note: Use the login at the top right and then sign up there_

### TV Setup
- Install Developer Mode from LG Content Store
- Sign in to App, Enable both Developer mode (reboot required) and Key Server in the TV App

### PC Setup CLI (Terminal Setup)
- Install Packages
```
npm install -g @webosose/ares-cli
```
- Connect to TV (Select Add and follow prompts)
```
ares-setup-device
```
- Enter TV Key
```
ares-novacom --device tv2 --getkey
```
- Verify Connection
```
OPENSSL_ENABLE_SHA1_SIGNATURES=1 ares-device --system-info --device tv2
```

Use `tv2` as the device name when adding the TV, or substitute your chosen name in each command. Use its LAN address, port `9922`, and SSH user `prisoner`. Keep the displayed passphrase private. The SHA-1 compatibility prefix addresses the specific handshake problem described below; it is not required on every computer.

The Developer Mode account has restricted filesystem and app-inventory access.

## SSH handshake failure

Key retrieval succeeded, but the next command failed with:

```text
Handshake failed: signature verification failed
```

On the Fedora workstation used for the original work, the old SSH implementation's SHA-1 signatures conflicted with the client's crypto policy. A process-scoped compatibility setting resolved that particular case:

```sh
OPENSSL_ENABLE_SHA1_SIGNATURES=1 ares-device --system-info --device TV
```

This is an observed workaround, not a portable fix for every SSH error. Do not globally weaken system crypto policy. Check the TV address, Developer Mode state, current key, passphrase, client version, and actual SSH error first. The environment variable may not be supported by other OpenSSL builds. Avoid exposing keys or passphrases in terminal transcripts.

## Root and Homebrew Channel

Compatibility was checked against the TV's actual firmware/OTA information, then the upstream faultmanager-autoroot script was reviewed and used. Homebrew Channel 0.7.3 was installed in the original session. This repository deliberately does not mirror or auto-run an exploit.

1. Check your own device with [cani.rootmy.tv](https://cani.rootmy.tv/).
2. Read the current [faultmanager-autoroot instructions](https://github.com/throwaway96/faultmanager-autoroot), including prerequisites and removal of LG Developer Mode.
3. Download and review the upstream script before following its installation procedure.
4. Use [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel) to configure root SSH and install a dedicated public key.
5. Verify a fresh key-authenticated connection, `id` returning root, and access after reboot.

Developer Mode was removed as part of this root method. Do not reinstall it into this rooted setup without consulting the method's instructions. Root SSH is a different connection from the old `prisoner` account on port 9922. Telnet was disabled. Firmware-update blocking was initially left off, then enabled in the [post-install protection step](09-post-install-updates.md). No ongoing root compatibility with future updates is claimed.

## Reuse one authenticated SSH connection

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
