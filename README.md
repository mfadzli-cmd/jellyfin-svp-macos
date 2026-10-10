# Jellyfin + SVP for macOS

Watch from Jellyfin Media Player with SVP motion interpolation, using the normal Jellyfin app interface. Opening Jellyfin starts SVP automatically—no MPV Shim casting or Automator workflow required.

**Experimental community integration.** The underlying repair has been tested on one Apple Silicon Mac with Jellyfin Media Player **1.12.0**, Homebrew mpv **0.41.0**, VapourSynth **R80**, and SVP **4.7.2.325**. The installer is a new packaging of that repair, not a broadly tested release. Intel Macs, Jellyfin Desktop 2.x, and CEF-based clients are not supported by this version.

This project is not affiliated with Jellyfin or SVP. It distributes source code and instructions only. Install those applications separately and use SVP under its own license/trial terms.

## Why this exists

Jellyfin already uses mpv, and SVP connects to mpv through a local socket. However, a player can advertise VapourSynth support while its bundled Python runtime is incomplete. On the tested Mac, enabling SVP caused a fatal `No module named 'encodings'` error. SVP also crashed during the failed playback tests.

The working repair:

1. Connect Jellyfin's embedded player to Homebrew's `libmpv`.
2. Point it to Homebrew's working VapourSynth scripting library and Python package directory.
3. Enable the local control socket and copy-back hardware decoding.
4. Start SVP whenever Jellyfin opens.

In a brief real 1080p HEVC stream test, SVP converted **23.976 to approximately 59.94 fps**, using VideoToolbox copy-back decoding, with no dropped frames during the final measurement interval. That is a short test on one machine, not a promise for every video or Mac.

## Before installing

You need:

- A native Apple Silicon terminal session, with Homebrew at `/opt/homebrew`.
- An **unmodified Apple Silicon Jellyfin Media Player 1.12.0** app at `/Applications/Jellyfin Media Player.app`, from [Jellyfin's official release](https://github.com/jellyfin/jellyfin-media-player/releases/tag/v1.12.0). Open it normally first.
- [SVP 4 Mac](https://www.svp-team.com/docs/mac/) installed at `/Applications/SVP 4 Mac.app`. Open it and complete its normal setup first, including Rosetta if macOS requests it.
- Homebrew's **formula** version of mpv, not the mpv cask. Follow [SVP's macOS installation guide](https://www.svp-team.com/docs/mac/).
- Python 3 and Apple's command line tools to build the small native launcher.

If needed, run these commands yourself:

```sh
xcode-select --install
brew install mpv vapoursynth python
```

Homebrew packages change over time. The installer requires the R80-style VapourSynth package layout and checks for it; it does not pin or download historical packages. A future version may require updates to this project.

Quit Jellyfin before installation. Keep other mpv-based players closed during verification because the SVP socket is shared.

## Install

Download this repository using **Code → Download ZIP**, unzip it, and open Terminal in that folder. Read the source before applying a local app modification.

```sh
python3 setup.py doctor
python3 setup.py install
```

The second command previews the changes without writing files. To apply them:

```sh
python3 setup.py install --yes
```

Then open **Jellyfin Media Player** normally and play a video.

The installer:

- Checks the app identity, version, architecture, signature integrity, runtime layout, and compiler.
- Builds and verifies a staged copy before replacing the installed application.
- Preserves the original app and `mpv.conf` in a dated private local backup directory.
- Merges the socket/copy-back options while preserving other simple mpv settings. Configurations with profiles or includes are declined for manual review.
- Signs the modified app locally with the upstream entitlements. This replaces the vendor signature; it does not create Apple notarization or independently establish download provenance.
- Does **not** change Gatekeeper globally, remove quarantine, download packages, ask for passwords, copy Jellyfin credentials, or change your SVP profiles.

Backups are stored under `~/Library/Application Support/jellyfin-svp-macos/backups/`. Save the exact backup path printed by installation. Do not use `sudo` to run this script.

## Choose the smoothness setting

In SVP's Video profiles panel, start with a target of **60 fps** and choose Animation if appropriate for your content. A 23.976 fps source may produce 59.94 fps. Higher targets such as 120/144 fps can require substantially more processing. Check dropped frames before increasing the target. The installer leaves your existing settings alone.

The SVP evaluation watermark, if present, belongs to SVP's licensing/trial behavior. This project does not remove it.

## Verify

While a low-frame-rate video is playing in Jellyfin:

```sh
python3 verify.py
```

Look for `svp_filter_enabled: true`, an output frame rate above the source frame rate, and a dropped-frame count that is not continually increasing. The check samples twice, five seconds apart. It never starts, pauses, seeks, or changes playback, and it omits media URLs, filenames, and script paths from its output.

`doctor` only checks presence/layout. A successful install or a visible SVP icon does not by itself prove interpolation is active.

## Restore the original app

Quit Jellyfin. Use the backup path printed at installation:

```sh
python3 setup.py restore --backup "/path/printed/by/the/installer"
python3 setup.py restore --backup "/path/printed/by/the/installer" --yes
```

The first command previews. Restore refuses to overwrite an app update or a modified `mpv.conf`. In that case, use the [manual recovery guide](docs/manual.md) to preserve your later changes. Backups are retained after restore; Homebrew and SVP are left installed.

## Updates and another Mac

A Jellyfin update/reinstallation replaces this patch. Do not rerun it against a different Jellyfin version. Homebrew upgrades can also alter runtime behavior: rerun `doctor` and the playback check afterward.

On another supported Mac, install the prerequisites and run the installer afresh. **Do not copy the modified `.app` between Macs**: it depends on that machine's Homebrew installation. Sign into your Jellyfin server normally. Server addresses, accounts, libraries, watch history, and tokens are not stored in this repository.

See [manual repair and troubleshooting](docs/manual.md) and [how to contribute](CONTRIBUTING.md).

## License

The original installer, launcher, tests, and documentation in this repository are MIT licensed. Jellyfin, mpv, VapourSynth, SVP, and their dependencies retain their own licenses. This repository does not distribute their binaries.
