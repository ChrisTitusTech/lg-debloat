# 6. Performance and acceptance evidence

These are anonymized observations from one TV, not benchmark promises. Hardware identity, network addresses, account information, raw inventories and screenshots are intentionally omitted.

## Idle sample after initial cleanup

- Approximately 964 MiB total RAM; about 342-346 MiB available.
- CPU 91-95% idle over three five-second intervals.
- Roughly 101 MiB of swap occupied, with no sustained swapping observed.
- App storage only 18% used; deleting more inactive app files was not a storage remedy.
- A high load average coexisted with low CPU use and many TV driver tasks in uninterruptible sleep. It was not evidence of CPU saturation by itself.

Approximate proportional set size (PSS), which apportions shared pages: AirPlay renderer/services plus HomeKit 46 MiB; native LG Full Home 32 MiB; minimal Home renderer 22 MiB. These are attributed footprints, not guaranteed reclaimable memory. Core `tvservice` was a persistent CPU user, but is necessary for TV operation. A brief `sdx` spike did not persist and did not justify disabling an unidentified service.

Plex and YouTube were not playing during this sample. No streaming, decoding, network-throughput, frame-time or before/after speed benchmark was performed. For playback complaints, profile the actual affected stream first.

Keep Quick Start+ off when prioritizing clean startup over rapid power-on. [LG's memory troubleshooting](https://www.lg.com/uk/support/product-support/troubleshoot/help-library/cs-CT00008333-20154522128518/) recommends disabling it for memory-related app problems. Do not disable swap or periodically drop caches as a substitute for diagnosing pressure.

## What was verified on hardware

| Change | Evidence | Limit |
| --- | --- | --- |
| Root/Homebrew | Fresh key-authenticated root connection after reboot | No future firmware guarantee |
| Normal app removal | Fresh inventory showed selected apps absent | No firmware-space recovery |
| Home/advertising | Key route, mounts, settings and custom foreground survived reboot | Native Home remains resident |
| Navigation | Arrow/OK opened YouTube, Plex and HDMI 1 | Not every remote button tested |
| Inputs | All six destination IDs reached foreground and Home returned | No connected-source picture/audio test |
| AirPlay/HomeKit | Dedicated services absent after follow-up reboot; UI launch lock installed | Not a network-wide block |
| Optional apps | All 13 launch attempts rejected with -102 after follow-up reboot; dedicated services absent | Locks depend on application-manager state |
| LG firmware updates | Homebrew flag true, updater stopped, executable blocked and update hostnames loopback after reboot | Early boot precedes Homebrew; no router policy installed |
| Preserved apps | Plex, YouTube, HDMI 1 and minimal Home reached foreground | Launch success is not playback verification |
| Daily background | TV screenshot visually checked; date logic tested locally | No live clock manipulation or midnight wait |

Plex initially appeared to fail a short foreground check; a later check showed it had opened. Allow bounded polling for cold startup rather than assuming an immediate launch response means it is already foreground.

## Public export validation

The public edition changes personal app IDs and storage prefixes and omits proprietary icons. It is checked locally for shell/JS syntax, packaging, date/key behavior and privacy patterns. It has not been installed on the original TV. Do not describe those local checks as new hardware acceptance.
