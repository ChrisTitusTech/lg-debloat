#!/bin/sh
set -eu
base=/var/lib/lg-debloat/home
# Disable our own boot hook without deleting its rollback evidence.
if [ -f /var/lib/webosbrew/init.d/40-lg-minimal-home ]; then
	mv /var/lib/webosbrew/init.d/40-lg-minimal-home "$base/boot-hook.disabled"
fi
sleep 3 | luna-send -w 2000 -n 1 luna://com.webos.service.config/setConfigs "$(cat "$base/keyfilters-restore.json")"
sleep 3 | luna-send -w 2000 -n 1 luna://com.webos.settingsservice/setSystemSettings "$(cat "$base/settings-restore.json")"
for id in com.webos.app.adapp com.webos.app.brandshop; do
	target=/mnt/otncabi/usr/palm/applications/$id
	if awk -v p="$target" '$2==p {found=1} END {exit !found}' /proc/mounts; then umount "$target"; fi
done
sleep 3 | luna-send -w 2000 -n 1 luna://com.webos.applicationManager/launch '{"id":"com.webos.app.fullhome"}'
