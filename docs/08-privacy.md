# 8. Public repository privacy

Only an explicit allowlist of authored source, generic documentation, synthetic tests and public image URLs belongs here. The private working directory is not a publishable artifact.

Excluded:

- Device IP/MAC addresses, serial numbers, household device names and OTA/device identifiers.
- Account logins, passphrases, SSH keys, known-hosts records and SSAP pairing/client keys.
- Cookies, tokens, preferences, HomeKit setup codes and authorization records.
- Raw logs, inventories, process command lines, captured responses and backup archives.
- Screenshots that might reveal accounts, media libraries, notifications, room names or timestamps.
- Original LG firmware files, manifests, logos, downloaded IPKs and copied upstream exploit sources.
- Workstation usernames, absolute home-directory paths and private commit author email addresses.

The public app ID is `org.example.minimalhome`; TV data lives under `/var/lib/lg-debloat/`. Examples use `TV_HOST`, `TV_KEY`, `TV_SOCKET` and placeholders. Firmware version and generic app/service IDs are technical compatibility information, not unique device identifiers.

`.gitignore` reduces accidental staging but is not a secrecy guarantee. Run `python3 tools/privacy-check.py` after staging, inspect `git diff --cached`, and inspect staged filenames before publishing. The checker scans staged blob contents, including ignored files forcibly added to Git. It rejects binaries, common private-data patterns and credential-shaped values. It is a heuristic, not proof that every secret has been detected.

Use a public-safe Git author identity when committing this repository. Review author/committer metadata as well as file content. Never post private diagnostics in an issue to demonstrate that the scan works. Describe failures using sanitized excerpts or synthetic fixtures.

If a secret was ever committed, removing the current file is insufficient: revoke/rotate it and address history and caches before publication. This repository was assembled from selected files rather than importing the private workspace history.
