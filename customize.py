#!/usr/bin/env python3
"""Optional local app changes: episode grid or manual SVP startup. No downloads."""
import argparse
import datetime
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile
import setup

EXTENSION = Path('Contents/Resources/web-client/extension/nativeshell.js')
GRID_MARKER = '/* Local Jellyfin 1.12 episode-grid compatibility for Chromium without :has(). */'


def grid_source(original):
    if GRID_MARKER in original or '__jmpEpisodeGridCompat' in original:
        raise ValueError('Episode grid patch is already present; no changes needed.')
    if 'window.jmpInfo' not in original:
        raise ValueError('Unexpected native extension layout; refusing to patch.')
    return original + '\n' + (setup.ROOT / 'src/episode-grid-compat.js').read_text()


def validate(app, action):
    info = setup.plist(app)
    if (info.get('CFBundleIdentifier') != 'tv.jellyfin.player' or
            info.get('CFBundleShortVersionString') != '1.12.0'):
        raise ValueError('Only Jellyfin Media Player 1.12.0 is supported.')
    if app.is_symlink():
        raise ValueError('Symlinked app destinations are not supported.')
    if action == 'update-launcher':
        if info.get('CFBundleExecutable') != 'JellyfinSVPLauncher':
            raise ValueError('Install the SVP integration first; this only updates an existing launcher.')
        if (app / 'Contents/MacOS/JellyfinSVPLauncher').is_symlink():
            raise ValueError('Symlinked launchers are not supported.')
    else:
        extension = app / EXTENSION
        if extension.is_symlink():
            raise ValueError('Symlinked native extensions are not supported.')
        grid_source(extension.read_text())


def modify(app, action, yes=False, output=None):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native Apple Silicon macOS is required.')
    validate(app, action)
    setup.run('/usr/bin/codesign', '--verify', '--deep', app)
    if output is not None and (output.exists() or output.suffix != '.app'):
        raise ValueError('--output must be a new .app path.')
    if output is None:
        setup.require_closed()
    print(f'Will apply {action} to {app}. No SVP settings, server CSS, or mpv.conf changes.')
    if not yes and output is None:
        print('Preview only. Run with --yes to apply, or --output /path/to/New.app to build a copy.')
        return
    parent = output.parent if output is not None else app.parent
    with tempfile.TemporaryDirectory(prefix='.jellyfin-customize-', dir=parent) as temp:
        stage = Path(temp) / app.name
        setup.run('/usr/bin/ditto', app, stage)
        if action == 'episode-grid':
            extension = stage / EXTENSION
            extension.write_text(grid_source(extension.read_text()))
        else:
            setup.run('/usr/bin/xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
                      setup.ROOT / 'src/launcher.c', '-o', stage / 'Contents/MacOS/JellyfinSVPLauncher')
        entitlements = setup.run('/usr/bin/codesign', '-d', '--entitlements', ':-', app)
        plistlib.loads(entitlements)
        ent = Path(temp) / 'entitlements.plist'
        ent.write_bytes(entitlements)
        setup.run('/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                  '--entitlements', ent, stage)
        setup.run('/usr/bin/codesign', '--verify', '--deep', stage)
        if output is not None:
            stage.rename(output)
            print(f'Built and verified: {output}. Installed app unchanged.')
            return
        setup.STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + action + '-', dir=setup.STATE))
        setup.run('/usr/bin/ditto', app, backup / app.name)
        setup.run('/usr/bin/codesign', '--verify', '--deep', backup / app.name)
        (backup / 'RECOVERY.txt').write_text(
            f'Customization: {action}\nOriginal app: {app}\n'
            'Quit Jellyfin. Move the current app somewhere safe, then copy this backed-up app '
            'to the original location using Finder. No configuration restore is needed. '
            'Do not use setup.py restore with this customization backup.\n')
        setup.require_closed()
        old = Path(temp) / 'original.app'
        app.rename(old)
        try:
            stage.rename(app)
        except BaseException:
            old.rename(app)
            raise
        print(f'Applied. Original app backup: {backup}\nReopen Jellyfin normally.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['update-launcher', 'episode-grid'])
    parser.add_argument('--app', type=Path, default=setup.APP)
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--output', type=Path, help='Build a new app copy without installing')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as your normal user, not sudo/root.')
    try:
        modify(args.app.absolute(), args.action, args.yes,
               args.output.absolute() if args.output else None)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.decode(errors='replace'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
