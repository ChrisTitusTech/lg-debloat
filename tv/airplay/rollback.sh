#!/bin/sh
set -eu
if [ -f /var/lib/webosbrew/init.d/45-disable-airplay ]; then
	mv /var/lib/webosbrew/init.d/45-disable-airplay /var/lib/lg-debloat/airplay/boot-hook.disabled
fi
for name in airplay homekit; do
	target=/usr/sbin/$name
	if awk -v path="$target" '$2 == path {found=1} END {exit !found}' /proc/mounts; then
		umount "$target"
	fi
done
sleep 1 | luna-send -w 800 -n 1 luna://com.webos.applicationManager/lockApp '{"id":"airplay","lock":false}'
sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.service.config/setConfigs '{"configs":{"com.webos.app.home.supportAirplay":true}}'
sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.settingsservice/setSystemSettings '{"category":"other","settings":{"supportAirplay":true}}'
if initctl status airplay-adaptor | grep -q 'start/running'; then
	initctl restart airplay-adaptor
else
	initctl start airplay-adaptor
fi
