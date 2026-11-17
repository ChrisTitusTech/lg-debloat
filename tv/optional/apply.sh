#!/bin/sh
set -eu
base=/var/lib/lg-debloat/optional
for service in miracast browser-service; do
	if initctl status "$service" | grep -q 'start/running'; then
		initctl stop "$service"
	fi
done
for name in miracast browser-service amazon-alexa-adapter nlpadapter; do
	target=/usr/sbin/$name
	if ! awk -v p="$target" '$2==p {found=1} END {exit !found}' /proc/mounts; then
		mount --bind /bin/true "$target"
	fi
	if pidof "$name" >/dev/null; then
		killall -KILL "$name"
	fi
done
while read -r id target; do
	test -f "$base/overlays/$id/appinfo.json"
	if [ "$id" != com.webos.app.browser ] && ! awk -v p="$target" '$2==p {found=1} END {exit !found}' /proc/mounts; then
		mount --bind "$base/overlays/$id" "$target"
	fi
	sleep 1 | luna-send -w 800 -n 1 luna://com.webos.applicationManager/lockApp "{\"id\":\"$id\",\"lock\":true}"
	# Closing an app which is not running is harmless.
	sleep 1 | luna-send -w 800 -n 1 luna://com.webos.applicationManager/closeByAppId "{\"id\":\"$id\",\"forceMode\":true}" || true
done <"$base/targets.txt"
