#!/bin/sh
set -eu
base=/var/lib/lg-debloat/optional
if [ -f /var/lib/webosbrew/init.d/46-disable-optional ]; then
	mv /var/lib/webosbrew/init.d/46-disable-optional "$base/boot-hook.disabled"
fi
while read -r id target; do
	if test "$target/appinfo.json" -ef "$base/overlays/$id/appinfo.json"; then
		umount "$target"
	fi
	sleep 1 | luna-send -w 800 -n 1 luna://com.webos.applicationManager/lockApp "{\"id\":\"$id\",\"lock\":false}"
done <"$base/targets.txt"
for name in miracast browser-service amazon-alexa-adapter nlpadapter; do
	target=/usr/sbin/$name
	if awk -v p="$target" '$2==p {found=1} END {exit !found}' /proc/mounts; then
		umount "$target"
	fi
done
if ! initctl status miracast | grep -q 'start/running'; then
	initctl start miracast
fi
printf '%s\n' 'Original files restored. Reboot to refresh cached application manifests.'
