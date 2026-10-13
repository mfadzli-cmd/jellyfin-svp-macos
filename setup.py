#!/usr/bin/env python3
"""Build/install a locally signed Jellyfin 1.12.0 + SVP integration. No downloads."""
import argparse
import datetime
import glob
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
APP = Path('/Applications/Jellyfin Media Player.app')
CONFIG = Path.home() / 'Library/Application Support/Jellyfin Media Player/mpv.conf'
STATE = Path.home() / 'Library/Application Support/jellyfin-svp-macos/backups'
MPV = Path('/opt/homebrew/opt/mpv/lib/libmpv.2.dylib')
RUNTIME = '/opt/homebrew/opt/vapoursynth/libexec/lib/python*/site-packages/vapoursynth/libvsscript.dylib'
MARKER = 'JellyfinSVPIntegration'
OPTIONS = {'input-ipc-server': '/tmp/mpvsocket', 'hwdec': 'auto-copy', 'hwdec-codecs': 'all'}


def run(*args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, **kw).stdout


def plist(app):
    return plistlib.loads((app / 'Contents/Info.plist').read_bytes())


def check_version(info):
    if info.get('CFBundleIdentifier') != 'tv.jellyfin.player' or info.get('CFBundleShortVersionString') != '1.12.0':
        raise ValueError('Only Jellyfin Media Player 1.12.0 is supported. Desktop 2.x/CEF is not supported.')
    if info.get(MARKER) or info.get('CFBundleExecutable') != 'Jellyfin Media Player':
        raise ValueError('This app is already modified. Use an unmodified 1.12.0 app as the source.')


def preflight(app):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('This first release supports native Apple Silicon macOS only.')
    if not (Path('/Applications/SVP 4 Mac.app')).is_dir():
        raise ValueError('Install SVP 4 Mac in /Applications and open it once first.')
    if not MPV.is_file() or len(glob.glob(RUNTIME)) != 1:
        raise ValueError('Homebrew mpv and a unique VapourSynth R80-style runtime are required. See README.')
    check_version(plist(app))
    run('/usr/bin/codesign', '--verify', '--deep', app)
    arch = run('/usr/bin/lipo', '-archs', app / 'Contents/MacOS/Jellyfin Media Player').decode()
    if 'arm64' not in arch.split():
        raise ValueError('Download the Apple Silicon Jellyfin app.')
    run('/usr/bin/xcrun', '--find', 'clang')


def merge_config(text):
    # Profiles and includes may override these options in ways we cannot safely infer.
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('[') or re.match(r'include\s*=', s):
            raise ValueError('mpv.conf has profiles/includes: merge manually using docs/manual.md.')
    lines = [line for line in text.splitlines()
             if line.split('=', 1)[0].strip() not in OPTIONS]
    return '\n'.join(lines).rstrip() + '\n\n# Jellyfin + SVP integration\n' + ''.join(
        f'{key}={value}\n' for key, value in OPTIONS.items())


def build(source, destination):
    if destination.exists():
        raise ValueError('Build destination already exists; choose a new path.')
    run('/usr/bin/ditto', source, destination)
    lib = destination / 'Contents/Frameworks/libmpv.2.dylib'
    if not lib.is_file():
        raise ValueError('Unexpected app layout: bundled libmpv was not found.')
    lib.unlink()
    lib.symlink_to(MPV)
    macos = destination / 'Contents/MacOS'
    run('/usr/bin/xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror', ROOT / 'src/launcher.c',
        '-o', macos / 'JellyfinSVPLauncher')
    info = plist(destination)
    info['CFBundleExecutable'] = 'JellyfinSVPLauncher'
    info[MARKER] = '1'
    (destination / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    # Preserve upstream entitlements; changing Info.plist requires re-signing the old entry point too.
    entitlements = run('/usr/bin/codesign', '-d', '--entitlements', ':-', source)
    plistlib.loads(entitlements)  # Fail rather than silently sign with bad/empty entitlements.
    with tempfile.NamedTemporaryFile(suffix='.plist') as f:
        f.write(entitlements); f.flush()
        for target in (macos / 'Jellyfin Media Player', destination):
            run('/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                '--entitlements', f.name, target)
    run('/usr/bin/codesign', '--verify', '--deep', destination)


def require_closed():
    result = subprocess.run(['/usr/bin/pgrep', '-f', '/Contents/MacOS/Jellyfin Media Player'],
                            capture_output=True)
    if result.returncode == 0:
        raise ValueError('Quit Jellyfin before installing/restoring. Playback will not be stopped automatically.')
    if result.returncode != 1:
        raise ValueError('Could not check whether Jellyfin is running.')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install(app, yes):
    preflight(app)
    require_closed()
    if app.is_symlink() or CONFIG.is_symlink():
        raise ValueError('Symlinked app/config destinations are not supported.')
    if not os.access(app.parent, os.W_OK):
        raise ValueError('App folder is not writable. Do not run with sudo; see README.')
    original = CONFIG.read_bytes() if CONFIG.exists() else None
    merged = merge_config((original or b'').decode('utf-8')).encode('utf-8')
    print(f'Will back up and replace: {app}\nWill merge: {CONFIG}\nWill locally sign the app.')
    if not yes:
        print('Preview only. Run again with --yes to install. No files changed.')
        return
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=STATE))
    state = {'app': str(app), 'config': str(CONFIG), 'had_config': original is not None,
             'installed_config_sha256': digest(merged), 'status': 'prepared'}
    if original is not None:
        (backup / 'mpv.conf.original').write_bytes(original)
    state_path = backup / 'state.json'
    state_path.write_text(json.dumps(state, indent=2))
    # Stage on the same filesystem as the destination, then swap directory names.
    # Avoid writing into an installed app's protected bundle in place.
    with tempfile.TemporaryDirectory(prefix='.jellyfin-svp-', dir=app.parent) as staging:
        staged = Path(staging) / app.name
        build(app, staged)
        run('/usr/bin/ditto', app, backup / app.name)
        run('/usr/bin/codesign', '--verify', '--deep', backup / app.name)
        require_closed()
        if (CONFIG.read_bytes() if CONFIG.exists() else None) != original:
            raise ValueError('mpv.conf changed during preparation; installation cancelled.')
        old = Path(staging) / 'original.app'
        app.rename(old)
        try:
            staged.rename(app)
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_bytes(merged)
        except BaseException:
            if app.exists(): app.rename(Path(staging) / 'failed.app')
            old.rename(app)
            if original is None: CONFIG.unlink(missing_ok=True)
            else: CONFIG.write_bytes(original)
            raise
    state['status'] = 'installed'
    state_path.write_text(json.dumps(state, indent=2))
    print(f'Installed. Start SVP first (or use Open at Login), then open Jellyfin. Backup: {backup}')
    print(f'To restore: python3 setup.py restore --backup "{backup}" --yes')


def restore(backup, yes):
    state_path = backup / 'state.json'
    state = json.loads(state_path.read_text())
    if state['status'] != 'installed':
        raise ValueError('Backup is not marked as an installed transaction. See manual recovery instructions.')
    app, config = Path(state['app']), Path(state['config'])
    saved = backup / app.name
    if not saved.is_dir() or not app.is_dir() or not plist(app).get(MARKER):
        raise ValueError('Current app is not this installer’s build. Restore manually to avoid overwriting an update.')
    if config.is_symlink() or digest(config.read_bytes()) != state['installed_config_sha256']:
        raise ValueError('mpv.conf has changed since installation. Restore manually so your edits are preserved.')
    require_closed()
    print(f'Will restore app and mpv.conf from {backup}')
    if not yes:
        print('Preview only. Run with --yes to restore.')
        return
    run('/usr/bin/codesign', '--verify', '--deep', saved)
    before = config.read_bytes()
    with tempfile.TemporaryDirectory(prefix='.jellyfin-svp-restore-', dir=app.parent) as staging:
        staged, old = Path(staging) / app.name, Path(staging) / 'patched.app'
        run('/usr/bin/ditto', saved, staged)
        app.rename(old)
        try:
            staged.rename(app)
            if state['had_config']: config.write_bytes((backup / 'mpv.conf.original').read_bytes())
            else: config.unlink()
        except BaseException:
            if app.exists(): app.rename(Path(staging) / 'failed.app')
            old.rename(app)
            config.write_bytes(before)
            raise
    state['status'] = 'restored'
    state_path.write_text(json.dumps(state, indent=2))
    print('Restored. Backup retained. SVP and Homebrew packages are unchanged.')


def doctor(app):
    print(f'System: {platform.system()} {platform.machine()}')
    print(f'Jellyfin present: {app.is_dir()}')
    if app.is_dir():
        info = plist(app)
        print(f'Jellyfin version: {info.get("CFBundleShortVersionString")}')
        print(f'Integration entry point: {info.get("CFBundleExecutable")}')
        print(f'libmpv link: {(app / "Contents/Frameworks/libmpv.2.dylib").is_symlink()}')
    print(f'Homebrew libmpv present: {MPV.is_file()}')
    print(f'VapourSynth runtime matches: {len(glob.glob(RUNTIME))}')
    print(f'SVP present: {Path("/Applications/SVP 4 Mac.app").is_dir()}')
    print(f'SVP socket exists: {Path("/tmp/mpvsocket").exists()}')
    print('Presence checks only; play a video and run verify.py to verify interpolation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['doctor', 'install', 'build', 'restore'])
    parser.add_argument('--app', type=Path, default=APP)
    parser.add_argument('--output', type=Path, help='New output .app path for build-only validation')
    parser.add_argument('--backup', type=Path, help='Backup directory printed by install')
    parser.add_argument('--yes', action='store_true', help='Apply install/restore instead of previewing')
    args = parser.parse_args()
    if os.geteuid() == 0: parser.error('Run as your normal user, not sudo/root.')
    try:
        app = args.app.absolute()
        if args.action == 'doctor': doctor(app)
        elif args.action == 'install': install(app, args.yes)
        elif args.action == 'build':
            if not args.output or args.output.suffix != '.app':
                raise ValueError('build requires --output /path/to/New.app')
            preflight(app); build(app, args.output.absolute())
            print('Build and signature verification passed. Installed app/config were not changed.')
        elif args.action == 'restore':
            if not args.backup: raise ValueError('restore requires --backup PATH')
            restore(args.backup.absolute(), args.yes)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr.decode(errors='replace'), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
