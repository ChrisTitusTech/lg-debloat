# 5. Daily landscape backgrounds

Seven real landscape photographs were selected from the US Fish & Wildlife Service collection. Every source page labeled the selected image Public Domain. `assets/landscapes.json` records the page, exact source-provided JPEG variant, license label and SHA-256. No household photos or screenshots are included.

Scenes: an Alaska lake sunset, mountain vistas, the Smoky Mountains, a desert panorama, Kofa's mountains, Baca scenery and the Cabeza Prieta desert.

```sh
python3 tools/generate-icon.py
python3 tools/download-backgrounds.py
ares-package app -o dist
```

The downloader saves the original source-provided approximately 1300px variants, about 5.7 MiB combined. It does not edit photographs. Their metadata, if any, belongs to the public source and is not uploaded to this repository. Images are ignored by Git and included only in your locally built package. If a source changes, review it before updating its pinned checksum.

`backgrounds.js` selects one file using the TV's local year/month/day, converted to a UTC calendar ordinal to avoid daylight-saving arithmetic errors. Selection is stable all day and repeats every seven days. The minute clock, visibility event and Home relaunch check whether the day changed; midnight refresh may occur up to a minute later. A powered-off TV catches up when Home next opens.

Only the current image is loaded. There are no wallpaper network requests, slideshow animations, blur filters or extra background daemons. CSS crops to fill the screen and places a dark tint over the image. Translucent tiles and a strong selection border keep the controls readable. If the image fails to load, the dark fallback remains usable.

The local date must be correct. Automated tests cover same-day stability, next-day change, weekly wrap, daylight-saving boundaries, leap day and year rollover. The actual TV screen was visually checked, but its clock was not changed for a live midnight test.
