# 7. Rollback and recovery

Keep rollback scripts and the actual saved configuration on the TV and on the workstation. Run rollback after pending startup hooks have finished; otherwise a delayed hook could reapply a setting. Preserve an authenticated root session while testing changes.

Run the relevant script in a root TV shell:

```sh
# Restore optional apps and Screen Share:
sh /var/lib/lg-debloat/optional/rollback.sh
# Restore AirPlay/HomeKit (edit restored settings to match your saved originals):
sh /var/lib/lg-debloat/airplay/rollback.sh
# Restore original Home key filters, ad settings and advertising payload views:
sh /var/lib/lg-debloat/home/rollback.sh
```

Each script disables its own startup hook before restoring runtime state. Optional-app rollback unlocks selected IDs and unmounts replacements; a reboot afterward refreshes cached app metadata. Home rollback requires `keyfilters-restore.json` and `settings-restore.json` generated from your own TV before modification. It opens LG Full Home as the fallback; confirm that ID exists on your firmware.

The public AirPlay rollback moves `45-disable-airplay` out of the hook directory and restores the original true settings observed in the case study. Do not assume those values describe a different TV. The reference scripts do not reconcile unrelated overlays installed by other projects; inspect mount ownership before unmounting.

For backgrounds alone, keep a copy of the previous `index.html` and `home.js`, restore them to the installed custom app, and close/reopen it. Extra photo files are harmless if left behind. Rebuilding the launcher without the background enhancement is another option.

Rollback does **not** unroot the TV, uninstall Homebrew, reinstall removed streaming apps, restore app logins, reverse firmware updates, or recover a damaged firmware partition. The backups are partial file archives. Follow upstream recovery guidance for root changes. Rollback scripts were syntax-checked, not executed end to end against the final TV state.
