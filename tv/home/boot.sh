#!/bin/sh
# Homebrew startup hook: apply overlays and reapply advertising settings.
# The Home key opens the launcher so startup cannot interrupt another app.
set -eu
base=/var/lib/lg-debloat/home
"$base/apply-overlays.sh"
(
	sleep 12
	sleep 5 | luna-send -w 4000 -n 1 luna://com.webos.settingsservice/setSystemSettings "$(cat "$base/settings-set.json")" >"$base/boot-settings.log" 2>&1
) </dev/null >/dev/null 2>&1 &
