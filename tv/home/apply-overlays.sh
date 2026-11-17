#!/bin/sh
set -eu
base=/var/lib/lg-debloat/home
for id in com.webos.app.adapp com.webos.app.brandshop; do
	target=/mnt/otncabi/usr/palm/applications/$id
	test -f "$base/overlays/$id/appinfo.json"
	test -d "$target"
	if ! awk -v p="$target" '$2==p {found=1} END {exit !found}' /proc/mounts; then
		mount --bind "$base/overlays/$id" "$target"
	fi
done
