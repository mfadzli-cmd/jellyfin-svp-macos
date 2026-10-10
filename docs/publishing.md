# Suggested GitHub repository settings

- Name: `jellyfin-svp-macos`
- Description: `Experimental macOS installer and guide for Jellyfin Media Player + SVP smooth playback on Apple Silicon.`
- Visibility: Public, if you want the community to use it.
- Topics: `jellyfin`, `svp`, `mpv`, `vapoursynth`, `macos`, `apple-silicon`, `motion-interpolation`
- Create an empty repository. The local project already includes README, MIT license, and .gitignore.

Publish only this repository folder, not its parent repair workspace. Do not commit `build/`, application bundles, local backups, test media, raw logs, or account configuration.

Suggested first release: `v0.1.0-alpha`. Describe it as an experimental, version-specific installer. Do not attach a patched Jellyfin app; users should obtain the upstream application themselves and build the local modification.

## Validation performed before initial publication

- Nine automated tests passed: configuration preservation, refusal of unsupported inputs, preview behavior, backup/restore, protection of later config edits, rollback on config-write failure, and failure before application replacement.
- The native launcher compiled with warnings treated as errors.
- A real app copy was patched, locally signed, and passed deep signature verification in build-only mode.
- The earlier manual repair played a real 1080p HEVC Jellyfin stream with SVP active at approximately 59.94 fps, using copy-back decoding, with zero dropped frames during its final short measurement interval.

Not yet established: end-to-end installation on a fresh Mac, long-duration playback stability, compatibility with different Jellyfin/macOS/dependency versions, or the updated packaged launcher's playback on a second machine. The installer’s transaction tests use temporary fixtures and mocked macOS signing/copy commands; the separate real build validates compilation and signing.
