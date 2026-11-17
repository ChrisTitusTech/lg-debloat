#!/bin/sh
set -eu
if initctl status airplay-adaptor | grep -q 'start/running'; then
	initctl stop airplay-adaptor
fi
for name in airplay homekit; do
	target=/usr/sbin/$name
	if ! awk -v path="$target" '$2 == path {found=1} END {exit !found}' /proc/mounts; then
		mount --bind /bin/true "$target"
	fi
	if pidof "$name" >/dev/null; then
		killall -KILL "$name"
	fi
done
sleep 1 | luna-send -w 800 -n 1 luna://com.webos.applicationManager/lockApp '{"id":"airplay","lock":true}'
sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.applicationManager/closeByAppId '{"id":"airplay","forceMode":true}' || true
sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.settingsservice/setSystemSettings '{"category":"other","settings":{"supportAirplay":false}}'
