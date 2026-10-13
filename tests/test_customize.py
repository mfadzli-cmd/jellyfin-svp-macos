import contextlib
import io
from pathlib import Path
import plistlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customize
import setup


class CustomizeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.app = self.root / 'Player.app'
        ext = self.app / customize.EXTENSION
        ext.parent.mkdir(parents=True)
        ext.write_text('window.jmpInfo = {};\n')
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundleIdentifier': 'tv.jellyfin.player', 'CFBundleShortVersionString': '1.12.0',
            'CFBundleExecutable': 'JellyfinSVPLauncher'}))
        macos = self.app / 'Contents/MacOS'
        macos.mkdir()
        (macos / 'JellyfinSVPLauncher').write_text('original launcher')
        self.backups = self.root / 'backups'
        for p in (patch.object(customize.platform, 'system', return_value='Darwin'),
                  patch.object(customize.platform, 'machine', return_value='arm64'),
                  patch.object(setup, 'require_closed'), patch.object(setup, 'STATE', self.backups),
                  patch.object(setup, 'run', side_effect=self.fake_run)):
            p.start(); self.addCleanup(p.stop)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def fake_run(self, *args):
        if str(args[0]) == '/usr/bin/ditto':
            shutil.copytree(args[1], args[2], symlinks=True)
        if '-d' in args:
            return plistlib.dumps({})
        return b''

    def test_preview_no_writes(self):
        customize.modify(self.app, 'episode-grid')
        self.assertFalse(self.backups.exists())
        self.assertEqual((self.app / customize.EXTENSION).read_text(), 'window.jmpInfo = {};\n')

    def test_grid_preserves_launcher_and_backs_up_original(self):
        customize.modify(self.app, 'episode-grid', True)
        self.assertIn(customize.GRID_MARKER, (self.app / customize.EXTENSION).read_text())
        self.assertEqual((self.app / 'Contents/MacOS/JellyfinSVPLauncher').read_text(), 'original launcher')
        backup = next(self.backups.iterdir()) / self.app.name
        self.assertEqual((backup / customize.EXTENSION).read_text(), 'window.jmpInfo = {};\n')
        with self.assertRaisesRegex(ValueError, 'already present'):
            customize.modify(self.app, 'episode-grid', True)

    def test_signing_failure_preserves_app(self):
        def fail_sign(*args):
            if '--force' in args: raise OSError('signing failed')
            return self.fake_run(*args)
        with patch.object(setup, 'run', side_effect=fail_sign):
            with self.assertRaises(OSError): customize.modify(self.app, 'episode-grid', True)
        self.assertEqual((self.app / customize.EXTENSION).read_text(), 'window.jmpInfo = {};\n')

    def test_swap_failure_restores_original(self):
        rename = Path.rename
        def fail_stage(path, dest):
            if path.name == self.app.name and path.parent.name.startswith('.jellyfin-customize-'):
                raise OSError('swap failed')
            return rename(path, dest)
        with patch.object(Path, 'rename', fail_stage):
            with self.assertRaises(OSError): customize.modify(self.app, 'episode-grid', True)
        self.assertEqual((self.app / customize.EXTENSION).read_text(), 'window.jmpInfo = {};\n')

    def test_rejects_unknown_layout_and_version(self):
        with self.assertRaises(ValueError): customize.grid_source('unrelated code')
        info = setup.plist(self.app); info['CFBundleShortVersionString'] = '2.0.0'
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        with self.assertRaisesRegex(ValueError, '1.12.0'):
            customize.validate(self.app, 'episode-grid')
