#!/bin/sh
# Run as root after Homebrew startup. No firmware partitions are modified.
set -eu
base=/var/lib/lg-debloat/updates
mkdir -p "$base"
# Homebrew consumes this persistent flag before user hooks on subsequent boots.
touch /var/luna/preferences/webosbrew_block_updates
if initctl status update | grep -q 'start/running'; then
	initctl stop update
fi
if pidof update >/dev/null; then
	killall -TERM update
	sleep 1
	if pidof update >/dev/null; then
		printf '%s\n' 'Updater still running; refusing to claim protection.' >&2
		exit 1
	fi
fi
if ! test /usr/sbin/update -ef /bin/true; then
	# Refuse to stack over someone else's executable mount.
	if awk '$2=="/usr/sbin/update" {found=1} END {exit !found}' /proc/mounts; then
		printf '%s\n' 'Unexpected updater mount; inspect before proceeding.' >&2
		exit 1
	fi
	mount --bind /bin/true /usr/sbin/update
fi
# Preserve existing hosts entries, including Homebrew's current boot overlay.
if ! grep -q '^# lg-debloat update block$' /etc/hosts; then
	cp /etc/hosts "$base/hosts.before"
	cp /etc/hosts "$base/hosts.blocked"
	cat >>"$base/hosts.blocked" <<'HOSTS'

# lg-debloat update block
127.0.0.1 snu.lge.com snu-dev.lge.com su-dev.lge.com su.lge.com su-ssl.lge.com
::1 snu.lge.com snu-dev.lge.com su-dev.lge.com su.lge.com su-ssl.lge.com
HOSTS
	mount --bind "$base/hosts.blocked" /etc/hosts
fi
printf '%s\n' 'Updater stopped, executable blocked, update hosts blocked.'
