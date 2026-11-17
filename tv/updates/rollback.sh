#!/bin/sh
set -eu
base=/var/lib/lg-debloat/updates
if [ -f /var/lib/webosbrew/init.d/00-block-lg-updates ]; then
	mv /var/lib/webosbrew/init.d/00-block-lg-updates "$base/boot-hook.disabled"
fi
if test /usr/sbin/update -ef /bin/true; then
	umount /usr/sbin/update
fi
if test /etc/hosts -ef "$base/hosts.blocked"; then
	umount /etc/hosts
fi
# Restore the recorded Homebrew flag, not an assumed original value.
if [ "$(cat "$base/block-updates.before")" = false ]; then
	rm -f /var/luna/preferences/webosbrew_block_updates
fi
printf '%s\n' 'Rollback staged. Reboot to rebuild hosts and restart the updater.'
