import contextlib
import io
import json
from pathlib import Path
import plistlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup


class ConfigTests(unittest.TestCase):
    def test_preserves_other_settings_and_replaces_conflicts(self):
        result = setup.merge_config('# personal settings\nvolume=42\nhwdec=no\ninput-ipc-server=/tmp/old\n')
        self.assertIn('volume=42', result)
        self.assertIn('# personal settings', result)
        self.assertEqual(result.count('hwdec='), 1)
        self.assertIn('hwdec=auto-copy', result)
        self.assertNotIn('/tmp/old', result)

    def test_refuses_profiles_and_includes(self):
        for text in ('[anime]\nscale=bilinear', 'include = custom.conf'):
            with self.assertRaises(ValueError): setup.merge_config(text)

    def test_rejects_unknown_and_patched_versions(self):
        info = {'CFBundleIdentifier': 'tv.jellyfin.player', 'CFBundleShortVersionString': '1.12.0',
                'CFBundleExecutable': 'Jellyfin Media Player'}
        setup.check_version(info)
        for changed in ({'CFBundleShortVersionString': '2.0.0'}, {setup.MARKER: '1'},
                        {'CFBundleExecutable': 'JellyfinSVPLauncher'}):
            with self.assertRaises(ValueError): setup.check_version(info | changed)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'Applications/Jellyfin Media Player.app'
        (self.app / 'Contents').mkdir(parents=True)
        self.original_plist = plistlib.dumps({'CFBundleExecutable': 'Jellyfin Media Player'})
        (self.app / 'Contents/Info.plist').write_bytes(self.original_plist)
        self.config = self.root / 'config/mpv.conf'
        self.config.parent.mkdir()
        self.config.write_text('volume=42\n')
        self.state = self.root / 'backups'
        for name, value in [('CONFIG', self.config), ('STATE', self.state)]:
            p = patch.object(setup, name, value); p.start(); self.addCleanup(p.stop)
        for name in ('preflight', 'require_closed'):
            p = patch.object(setup, name); p.start(); self.addCleanup(p.stop)
        p = patch.object(setup, 'run', self.fake_run); p.start(); self.addCleanup(p.stop)
        p = patch.object(setup, 'build', self.fake_build); p.start(); self.addCleanup(p.stop)
        p = contextlib.redirect_stdout(io.StringIO()); p.__enter__(); self.addCleanup(p.__exit__, None, None, None)

    @staticmethod
    def fake_run(*args, **kwargs):
        if str(args[0]) == '/usr/bin/ditto': shutil.copytree(args[1], args[2])
        return b''

    @staticmethod
    def fake_build(source, dest):
        shutil.copytree(source, dest)
        info = setup.plist(dest); info[setup.MARKER] = '1'
        (dest / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))

    def backup(self):
        return next(self.state.iterdir())

    def test_preview_writes_nothing(self):
        setup.install(self.app, False)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.config.read_text(), 'volume=42\n')
        self.assertEqual((self.app / 'Contents/Info.plist').read_bytes(), self.original_plist)

    def test_install_restore_round_trip(self):
        setup.install(self.app, True)
        self.assertTrue(setup.plist(self.app)[setup.MARKER])
        self.assertIn('hwdec=auto-copy', self.config.read_text())
        backup = self.backup()
        setup.restore(backup, True)
        self.assertEqual(self.config.read_text(), 'volume=42\n')
        self.assertEqual((self.app / 'Contents/Info.plist').read_bytes(), self.original_plist)
        self.assertEqual(json.loads((backup / 'state.json').read_text())['status'], 'restored')

    def test_new_config_removed_on_restore(self):
        self.config.unlink()
        setup.install(self.app, True)
        setup.restore(self.backup(), True)
        self.assertFalse(self.config.exists())

    def test_restore_protects_later_config_edits(self):
        setup.install(self.app, True)
        self.config.write_text(self.config.read_text() + 'volume=81\n')
        with self.assertRaisesRegex(ValueError, 'changed since'): setup.restore(self.backup(), True)
        self.assertIn('volume=81', self.config.read_text())
        self.assertTrue(setup.plist(self.app)[setup.MARKER])

    def test_config_failure_rolls_app_back(self):
        original_write = Path.write_bytes
        def fail_once(path, data):
            if path == self.config and b'auto-copy' in data: raise OSError('simulated write failure')
            return original_write(path, data)
        with patch.object(Path, 'write_bytes', fail_once):
            with self.assertRaises(OSError): setup.install(self.app, True)
        self.assertEqual((self.app / 'Contents/Info.plist').read_bytes(), self.original_plist)
        self.assertEqual(self.config.read_text(), 'volume=42\n')
        self.assertTrue((self.backup() / self.app.name).is_dir())

    def test_failed_build_leaves_installed_app_untouched(self):
        with patch.object(setup, 'build', side_effect=ValueError('build failed')):
            with self.assertRaises(ValueError): setup.install(self.app, True)
        self.assertEqual((self.app / 'Contents/Info.plist').read_bytes(), self.original_plist)
        self.assertEqual(self.config.read_text(), 'volume=42\n')

if __name__ == '__main__': unittest.main()
