# Contributing

Start with small, reproducible reports. Include macOS version, chip family, Jellyfin version, Homebrew mpv/VapourSynth versions, and SVP version. Paste the output of `doctor` and, if possible, `verify.py`.

Do not upload raw Jellyfin logs, credentials, server URLs, watch history, crash reports, local backup folders, or app bundles. Review any output before sharing it. A synthetic local test video is preferable to uploading a media file.

Run checks with:

```sh
python3 -m unittest discover -s tests -v
```

On a supported Mac, use `setup.py build` to compile and verify a staged app without installing it. Test installation and restoration on a disposable setup before claiming support for a new version. Unit tests and a successful build do not replace playback verification.

Current scope is Jellyfin Media Player 1.12.0 on Apple Silicon with Homebrew's R80-style VapourSynth layout. Broader support needs actual evidence. Do not add global security bypasses or bundle third-party applications.
