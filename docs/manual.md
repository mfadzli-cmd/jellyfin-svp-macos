# Advanced repair and recovery

For prerequisites, installation, server connection, playback checks, and everyday use, follow the [README](../README.md). This document is optional reference for custom configurations, contributors, and recovery.

## What changes

The app's `Contents/Frameworks/libmpv.2.dylib` becomes a symbolic link to `/opt/homebrew/opt/mpv/lib/libmpv.2.dylib`. The original executable remains in `Contents/MacOS/Jellyfin Media Player`.

A compiled C launcher is added alongside it, and `CFBundleExecutable` points to the launcher. The launcher finds exactly one runtime at:

```
/opt/homebrew/opt/vapoursynth/libexec/lib/python*/site-packages/vapoursynth/libvsscript.dylib
```

It sets `VSSCRIPT_PATH` to that file and `PYTHONPATH` to its `site-packages` directory, clears inherited `PYTHONHOME`, opens SVP, and executes Jellyfin. Environment changes apply to that app process and its children, not your global shell configuration.

Changing Info.plist invalidates the original signature, so the build locally signs both the original entry point and the bundle, retaining the upstream entitlements. `codesign --verify --deep` checks integrity, not notarization or developer reputation. macOS can still require its normal local-app approval. The project does not automate bypassing security prompts.

The following options go in `~/Library/Application Support/Jellyfin Media Player/mpv.conf`:

```ini
input-ipc-server=/tmp/mpvsocket
hwdec=auto-copy
hwdec-codecs=all
```

For configurations containing `[profiles]` or `include=`, manually review where those options apply. A later profile can override them. Back up the file first. Do not put these options only in `~/.config/mpv/mpv.conf` and assume embedded Jellyfin will read them.

## Build without installing

This creates a modified copy and verifies its signature. It does not change the installed app or mpv configuration:

```sh
python3 setup.py build --app "/path/to/unmodified/Jellyfin Media Player.app" --output "$PWD/build/Jellyfin SVP.app"
```

Build outputs are for local inspection/testing, not redistributable project releases. A build-only copy does not configure SVP's socket. Keep generated apps out of Git.

## Recovery if automated restore refuses

1. Quit Jellyfin.
2. Find the dated backup printed by the installer. It includes the original app, a `state.json`, and an original mpv configuration if one existed.
3. Move the current Jellyfin app somewhere safe, then copy the backed-up app to the original location. Replacing the whole bundle avoids the in-place App Management failure encountered in testing.
4. Compare your current `mpv.conf` with the backed-up version. Preserve later edits while removing/reverting the three integration settings. If the configuration was newly created solely by this installer, move it aside.
5. Open the restored application normally. Retain the backup until satisfied.

If installation is interrupted, inspect `state.json` and any `.jellyfin-svp-*` staging folder in the application folder. Ordinary errors trigger rollback; a power loss or forced termination can interrupt that process. The durable original-app backup is created before the application swap.

## Common problems

- **Already modified:** The script refuses to patch the same app twice. Use your original backup or reinstall the same official supported version. The initial hand-repaired Mac already has a working patch; it does not need this new installer run over it.
- **No unique runtime:** Homebrew VapourSynth is missing or has a different layout. Check its installed version; do not randomly link an incompatible Python library.
- **`No module named encodings`:** The original failure involved bundled Python initialization. Check that the app is using the new launcher and Homebrew mpv. The launcher clears inherited PYTHONHOME to avoid a stale Python prefix.
- **`Failed to load VapourSynth VSScript library`:** Verify VSSCRIPT_PATH and the Homebrew package layout. Finding libmpv alone is insufficient.
- **SVP cannot see playback:** Close other mpv/IINA sessions, open the patched Jellyfin app, and check `/tmp/mpvsocket`. This socket can control the player and is not intended as a network service; do not forward/expose it.
- **Frames drop:** Compare counters over time after playback settles. Try 60 fps, reduce SVP quality, and confirm copy-back decoding. A filter generating 144 fps is not proof all 144 frames are displayed.
- **Library blocked by Apple verification:** Obtain applications from their official sources and use macOS's normal approval flow if appropriate. Do not disable Gatekeeper globally. The unsigned Jellyfin 2.0 development build was not needed for the tested repair.
- **Permission denied:** Do not run the installer with sudo. Use a writable app location via `--app`, or manage the destination through Finder. macOS may prompt about moving an app outside Applications when launched.
- **Jellyfin/SVP updates:** This is a workaround tied to tested versions, not an upstream integration contract. Re-test rather than assuming every newer build works.

## Sources

- [SVP macOS installation and mpv configuration](https://www.svp-team.com/docs/mac/)
- [Jellyfin Media Player 1.12.0 release](https://github.com/jellyfin/jellyfin-media-player/releases/tag/v1.12.0)
- [VapourSynth installation and VSSCRIPT_PATH](https://www.vapoursynth.com/doc/installation.html)
- [mpv source](https://github.com/mpv-player/mpv)
