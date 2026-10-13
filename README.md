# Jellyfin + SVP for macOS

Watch your Jellyfin library with SVP smooth playback directly inside **Jellyfin Media Player**. After setup, start SVP (manually or at login), then open Jellyfin, choose a video, and press Play. Jellyfin does not launch SVP or bring its control panel forward.

**You do not need Codex, ChatGPT, an AI subscription, or a service operated by this project's author.** You run the installer from this repository once on your own Mac. It builds a small local launcher using your installed Jellyfin, SVP, and Homebrew libraries. Terminal is needed for setup and optional diagnostics, not everyday watching. No MPV Shim casting or Automator workflow is required.

**Experimental: Jellyfin Media Player 1.12.0 on Apple Silicon only.** The underlying repair worked on one Mac; the packaged installer has not yet been validated end-to-end on a fresh Mac. Intel Macs, Jellyfin Desktop 2.x, and CEF-based clients are not supported by this version.

## Start here

1. [Install the prerequisites](#1-install-the-prerequisites).
2. [Download this project](#2-download-this-project).
3. [Preview and install](#3-preview-and-install).
4. [Connect to your Jellyfin server](#4-connect-to-your-jellyfin-server).
5. [Choose your SVP settings](#5-choose-your-svp-settings).
6. [Verify smooth playback](#6-verify-smooth-playback).

Normal setup is covered entirely below. The [advanced manual](docs/manual.md) is optional and covers internal details, custom configurations, and recovery when automatic restore refuses.

## 1. Install the prerequisites

### Your Mac and Jellyfin server

- **An Apple Silicon Mac**, using a native Terminal session and a macOS release supported by your installed Homebrew and SVP versions. This project is not tested across every macOS release.
- **A working Jellyfin server**, its server address, and your Jellyfin account. The server can be on another computer or NAS; it does not need to run on this Mac. This project configures the Mac player, not the server. If you have no server yet, follow [Jellyfin's server quick start](https://jellyfin.org/docs/general/quick-start/).

### Jellyfin Media Player and SVP

- Download the **Apple Silicon Jellyfin Media Player 1.12.0** app from [Jellyfin's official release](https://github.com/jellyfin/jellyfin-media-player/releases/tag/v1.12.0). Install it at `/Applications/Jellyfin Media Player.app`. Open it once normally. Start with an **unmodified** app; the installer refuses already-patched apps and other versions.
- Install [SVP 4 Mac](https://www.svp-team.com/docs/mac/) at `/Applications/SVP 4 Mac.app`. Open it and complete its normal setup, including Rosetta if macOS requests it. SVP's own license/trial terms apply; this project does not supply a license or remove its evaluation watermark.

### Build tools and playback libraries

Install Apple's Command Line Tools if you do not already have them or Xcode:

```sh
xcode-select --install
```

Finish that installation before continuing. If macOS reports the tools are already installed, continue.

Install [Homebrew from its official website](https://brew.sh/) if needed, and follow its printed shell setup instructions so `brew` works in Terminal. On Apple Silicon, this project expects it at `/opt/homebrew`.

Then install the required packages:

```sh
brew install mpv vapoursynth python
```

- **mpv** provides the playback library Jellyfin will use. Use the Homebrew formula above, not `brew install --cask mpv`.
- **VapourSynth** lets SVP's frame interpolation run inside the player.
- **Python 3** runs this project's setup/check scripts and is also used by the VapourSynth runtime. No `pip install` step is needed for our scripts.
- **Apple's compiler** builds the small launcher. You do not need to write or edit code.

The working setup used mpv **0.41.0**, VapourSynth **R80**, and SVP **4.7.2.325**. Homebrew installs its available versions, not a frozen copy of that setup. The installer checks for the R80-style VapourSynth layout; future package versions may require changes. See [SVP's macOS guide](https://www.svp-team.com/docs/mac/) for upstream dependency setup.

## 2. Download this project

Choose either method. A GitHub account is not required to download the public source.

**Download ZIP:** On this repository's page, choose **Code → Download ZIP**, then unzip it. Open Terminal, type `cd` followed by a space, drag the extracted folder from Finder into Terminal, and press Return. This avoids guessing where your Downloads folder or extracted directory is located.

**Or clone with Git:**

```sh
git clone https://github.com/mfadzli-cmd/jellyfin-svp-macos.git
cd jellyfin-svp-macos
```

Run all remaining commands from that project folder. Review the source before applying the app modification.

## 3. Preview and install

Quit Jellyfin first. Close other mpv-based players such as mpv or IINA while setting up and testing; they may compete for the same SVP control socket.

Check the prerequisites:

```sh
python3 setup.py doctor
```

Look for Jellyfin, SVP, and Homebrew libmpv being present, and **one** VapourSynth runtime match. `SVP socket exists: False` is normal before the configured player is running. `doctor` reports presence/layout only; it does not prove that installation or interpolation works.

Preview the changes:

```sh
python3 setup.py install
```

This checks the supported app and prints what would change, without writing files. If it reports an error, fix that issue before proceeding. To apply the repair:

```sh
python3 setup.py install --yes
```

The installer builds and verifies a staged app, backs up the original app and configuration, then installs the modified copy. **Save the backup path printed at the end.** Backups live under `~/Library/Application Support/jellyfin-svp-macos/backups/`.

It adds the SVP socket and copy-back decoding options to Jellyfin's `mpv.conf` while preserving other simple settings. If your file contains profiles or includes, it stops for [manual configuration review](docs/manual.md). You do not need to edit configuration files for the normal setup.

The modified application is signed locally with the upstream entitlements. This replaces its vendor signature; it does not create Apple notarization. The installer does not disable Gatekeeper or remove quarantine. Obtain the original applications from their official sources and follow macOS's normal approval flow if needed. **Do not run this installer with `sudo`.**

## 4. Connect to your Jellyfin server

1. Ensure **SVP 4 Mac** is running, then open **Jellyfin Media Player** from Applications. See [SVP startup](#svp-startup) below for the optional login setting.
2. If your existing account and library appear, continue to the next section. The installer does not intentionally reset them.
3. Otherwise, enter your server's address in **Connect to Server**, then choose **Connect**. Use the address you normally use for Jellyfin, for example `http://YOUR-SERVER-IP:8096` on your local network or your configured HTTPS address such as `https://jellyfin.example.com`. Replace the example with your actual address, including any required port or subpath.
4. Sign in with your Jellyfin account. If you do not know the address or credentials, ask the person who manages your server.
5. Browse your library and play a video **in this Jellyfin app**. You do not need to select a cast device or send the video to MPV Shim.

If connection fails, first check that the same server address opens in your browser and that your Mac has access to the server's network or required VPN. Server connectivity and sign-in are separate from SVP setup.

SVP processes playback on this Mac. The installer does not configure your server or need your Jellyfin credentials. Watching through a separate web browser does not use this patched player.

## 5. Choose your SVP settings

Open SVP's control panel and its **Video profiles** panel. Enable frame rate conversion, start with a target of **60 fps**, and choose **Animation** if appropriate for your content. Keep SVP running while watching.

A 23.976 fps source may produce approximately 59.94 fps. Higher targets such as 120/144 fps can require more processing; check dropped frames before increasing them. The installer leaves your existing SVP profiles unchanged.

## 6. Verify smooth playback

Play a low-frame-rate video, such as a 24 fps episode, in Jellyfin. Leave it playing, allow startup to settle, and run this from the project folder:

```sh
python3 verify.py
```

It takes two measurements five seconds apart. A successful check ends with:

```text
SVP interpolation observed.
```

In the output, look for:

- **`svp_filter_enabled: true`** — SVP's filter is active.
- **`estimated-vf-fps` above `container-fps`** — the filtered video has more frames than the source, for example roughly 59.94 versus 23.976.
- **`frame-drop-count` not continually increasing** between measurements. A few startup drops alone do not tell you how steady playback is afterward.
- **`hwdec-current: videotoolbox-copy`** when supported hardware decoding is in use. Some formats may use software decoding; this field alone does not determine whether SVP works.

The check reads playback state; it never starts, pauses, seeks, or changes your video. It omits media URLs, filenames, and filter script paths. It checks whichever player owns `/tmp/mpvsocket`, so close other mpv-based players first. A paused video will not pass, and a visible SVP icon alone does not prove interpolation is active.

## Everyday use

Ensure **SVP is running → open Jellyfin Media Player → choose a video → Play**. You do not need to rerun the installer or keep Terminal, Python setup scripts, or any AI app open. The compiled launcher and installed Homebrew libraries remain necessary for playback.

### SVP startup

Choose whichever suits you:

- **Convenient:** In **System Settings → General → Login Items & Extensions → Open at Login**, click **+** and add **SVP 4 Mac** from Applications. On some macOS versions the page is named **Login Items**. See [Apple's login items guide](https://support.apple.com/guide/mac-help/mh15189/mac). This project does not change login items automatically.
- **Manual:** Open **SVP 4 Mac** before starting Jellyfin and leave it running while watching.

The SVP control panel does not need to stay visible; SVP Manager must remain running. Quitting SVP stops its ability to apply interpolation. If you forgot to start it, open SVP and restart the video, then use `python3 verify.py` to check. Jellyfin can open without SVP, but smooth interpolation requires it.

### Updating an older installation's startup behaviour

New installations already use the behaviour above. If an earlier version of this project's launcher still opens SVP whenever Jellyfin starts, download the latest project (or run `git pull` in your clone), quit Jellyfin, and run:

```sh
python3 customize.py update-launcher
python3 customize.py update-launcher --yes
```

The first command previews; the second rebuilds only the existing SVP launcher, locally signs the app, and saves a full app backup. It preserves the grid patch, playback configuration, and login items. It requires the original build tools and an existing `JellyfinSVPLauncher` installation. Your already-working manual-start launcher does not need this update.

## Optional: fix oversized episode thumbnails / restore the grid

If **Jellyfin Media Player 1.12.0** shows huge episode thumbnails in a single column while your browser shows a grid with the **ElegantFin theme**, you can apply the optional compatibility patch. It restores responsive episode columns, 16:9 thumbnails, and centred play buttons. Skip this if your layout already works. It is not a general fix for every theme or Jellyfin client.

Quit Jellyfin, then preview and apply:

```sh
python3 customize.py episode-grid
python3 customize.py episode-grid --yes
```

Reopen Jellyfin and visit a season's episode page. Check that the cards form a grid and each play button is centred on its image. The number of columns depends on window size and theme settings. This fix is separate from SVP and works on either an original supported app or one with the SVP integration installed.

The script uses Python's standard library and macOS signing tools; no Node.js or extra packages are needed. It patches only the local app, keeps the existing launcher and playback configuration, and does not alter server CSS or other clients. It refuses unsupported versions and an already-present grid patch. The patch was visually verified on one Mac with ElegantFin; other themes are not validated.

Both customization commands print a full app backup path. To undo, quit Jellyfin, move the current app somewhere safe, and copy the backed-up app to its original location using Finder. **Do not pass these customization backups to `setup.py restore`**; they contain an app backup only. Restoring a full app backup also reverts any later app customizations, so keep the current copy. An app update can remove these changes.

For contributors, `--output "/path/to/New.app"` builds and signs a separate copy without changing the installed app. See [technical details](docs/manual.md#optional-episode-grid-compatibility).

## Common problems

- **`brew: command not found`:** Complete Homebrew's shell setup instructions, then reopen Terminal.
- **`can't open file 'setup.py'`:** Terminal is in the wrong folder. Use the `cd` instructions in step 2.
- **Already modified / unsupported version:** Do not patch repeatedly. If your patched app works, keep using it. For a fresh install, use an unmodified supported 1.12.0 app. Desktop 2.x is a different, unsupported target.
- **No unique VapourSynth runtime / library failed to load:** Check the Homebrew packages and run `doctor`. A changed library layout may need a project update; do not substitute a random Python library.
- **`No module named encodings`:** This was the original bundled-Python failure. Confirm you are opening the patched app and that its entry point in `doctor` is `JellyfinSVPLauncher`. See the advanced manual if it persists.
- **Cannot verify / SVP filter is inactive:** Play a low-frame-rate video in the patched app, unpause it, keep SVP running, and close other mpv/IINA sessions. Reopen Jellyfin and retry.
- **Stuttering / increasing dropped frames:** Start at 60 fps, lower SVP quality if needed, and check the decoding status. A higher reported output rate is not proof every frame is displayed smoothly.
- **Permission denied / Apple verification prompt:** Use the official app downloads and normal macOS approval/file-management flows. Do not disable Gatekeeper globally or run the installer with sudo.

For custom profiles, detailed library diagnostics, and interrupted installs, see the [advanced manual](docs/manual.md). For unresolved issues, follow the [reporting guide](CONTRIBUTING.md); do not post raw logs or credentials.

## Undo the installation

Quit Jellyfin. Replace the example below with the exact backup directory printed when you installed:

```sh
python3 setup.py restore --backup "/path/printed/by/the/installer"
```

That previews the restore. Apply it with:

```sh
python3 setup.py restore --backup "/path/printed/by/the/installer" --yes
```

Restore returns the original app and `mpv.conf`, retaining the backup and leaving SVP/Homebrew installed. It refuses to overwrite an app update or a configuration edited since installation. If that happens, use [manual recovery](docs/manual.md#recovery-if-automated-restore-refuses) to preserve your later changes.

## Updates and moving to another Mac

A Jellyfin update or reinstall replaces this patch. Do not rerun it against a different Jellyfin version. Homebrew upgrades can also change runtime behavior; repeat the diagnostic and playback checks afterward.

On another supported Mac, follow this README from step 1 and sign into your server normally. **Do not copy the patched `.app` between Macs**: it depends on each machine's Homebrew installation. This repository contains no server settings or account credentials to migrate.

## How it works and what has been tested

Jellyfin already embeds mpv. The repair links it to Homebrew's working playback library, gives VapourSynth the correct runtime paths, and enables SVP's local connection with copy-back decoding. A small native launcher supplies those paths. SVP starts independently, either manually or through macOS login items. No ongoing service from this repository's author is involved.

The underlying manual repair played a real 1080p HEVC stream at **23.976 → approximately 59.94 fps**, using VideoToolbox copy-back decoding, with zero dropped frames during the final short measurement interval. The current suite passes 14 automated tests covering configuration handling, preview, backup/restore, optional grid changes, and error rollback. Both customization commands also built separate real app copies and passed signature verification; the updated launcher compiled with warnings treated as errors. Transaction tests use temporary fixtures and mocked macOS commands.

These are limited checks, not a guarantee for all videos or Macs. End-to-end installation on a fresh Mac, long-duration stability, and other version combinations still need validation. [Technical details and upstream references](docs/manual.md) are available for contributors.

## License

This is an independent community project, not affiliated with Jellyfin or SVP. Its original installer, launcher, tests, and documentation are MIT licensed. Jellyfin, mpv, VapourSynth, SVP, and their dependencies retain their own licenses. Their applications and binaries are not distributed here.
