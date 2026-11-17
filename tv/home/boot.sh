#!/bin/sh
# Homebrew startup hook: local overlays first, then open Home asynchronously.
set -eu
base=/var/lib/lg-debloat/home
"$base/apply-overlays.sh"
(
	sleep 12
	sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.applicationManager/launch '{"id":"org.example.minimalhome"}' >"$base/boot-launch.log" 2>&1
	sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.settingsservice/setSystemSettings "$(cat "$base/settings-set.json")" >"$base/boot-settings.log" 2>&1
) </dev/null >/dev/null 2>&1 &
